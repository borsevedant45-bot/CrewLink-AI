import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/* Doc #8 §1.3 — Chat Bridge
 *   - 3.1.2 Language of Parts: every message bubble carries the correct `lang` attribute
 *   - 1.4.10 Reflow: translated text reflows without clipping (20–30% length variance)
 *   - §4.2 Human-in-the-loop: confidence chip, back-translation, Request human interpreter
 */

interface ChatMessageData {
  message_id: string;
  session_id: string;
  sender: 'volunteer' | 'fan';
  original_text: string;
  original_language: string;
  translated_text: string;
  translated_language: string;
  confidence: number | null;
  emergency_flag: boolean;
  fallback_used: boolean;
  back_translation: string | null;
  high_stakes: boolean;
  model_tier: string;
  created_at: string;
}

interface ChatSessionData {
  session_id: string;
  zone_id: string;
  volunteer_language: string;
  fan_language: string;
  status: string;
  created_at: string;
}

function confidenceLabel(score: number | null): 'high' | 'medium' | 'low' {
  if (score === null) return 'low';
  if (score >= 0.7) return 'high';
  if (score >= 0.4) return 'medium';
  return 'low';
}

export function ChatBridge() {
  const { t } = useTranslation();
  const { sessionId } = useParams<{ sessionId: string }>();
  const { accessToken, getWsTicket: _getWsTicket } = useAuth();

  const [session, setSession] = useState<ChatSessionData | null>(null);
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [inputText, setInputText] = useState('');
  const [sending, setSending] = useState(false);
  const [requestingInterpreter, setRequestingInterpreter] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Fetch session detail on mount
  useEffect(() => {
    if (!sessionId || !accessToken) return;

    fetch(`/api/v1/chat-sessions/${sessionId}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then((r) => r.json())
      .then((data) => setSession(data))
      .catch(() => {});
  }, [sessionId, accessToken]);

  // Poll messages (WS polling fallback per Doc #5 §3.2)
  useEffect(() => {
    if (!sessionId || !accessToken) return;

    const fetchMessages = () => {
      fetch(`/api/v1/chat-sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
        .then((r) => r.json())
        .then((data) => {
          if (data.items) setMessages(data.items);
        })
        .catch(() => {});
    };

    fetchMessages();
    pollIntervalRef.current = setInterval(fetchMessages, 3000);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [sessionId, accessToken]);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = useCallback(async () => {
    if (!inputText.trim() || !sessionId || !accessToken || sending) return;

    setSending(true);
    try {
      const resp = await fetch(`/api/v1/chat-sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sender: 'volunteer',
          original_text: inputText,
          original_language: session?.volunteer_language ?? 'en',
        }),
      });

      if (resp.ok) {
        const msg: ChatMessageData = await resp.json();
        setMessages((prev) => [...prev, msg]);
        setInputText('');
      }
    } catch {
      // Silently fail — translation fallback handles it
    } finally {
      setSending(false);
    }
  }, [inputText, sessionId, accessToken, sending, session]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const requestHumanInterpreter = useCallback(async () => {
    if (!sessionId || !accessToken || requestingInterpreter) return;
    setRequestingInterpreter(true);
    try {
      await fetch(`/api/v1/incidents`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          zone_id: session?.zone_id ?? 'unknown',
          description: 'Human interpreter requested for chat session',
          category_hint: 'translation',
          source: 'VOLUNTEER_REPORTED',
        }),
      });
    } catch {
      // Silently fail
    } finally {
      setRequestingInterpreter(false);
    }
  }, [sessionId, accessToken, requestingInterpreter, session]);

  if (!sessionId) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col p-4" role="alert">
        <p className="text-field-base text-field-text-secondary">
          {t('chat.noSession')}
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col p-4" role="region" aria-label={t('chat.title')}>
      <header className="mb-4">
        <h1 className="text-field-xl">{t('chat.title')}</h1>
        {session && (
          <p className="text-field-base text-field-text-secondary">
            {session.fan_language.toUpperCase()} &rarr; {session.volunteer_language.toUpperCase()}
          </p>
        )}
      </header>

      {/* Message list — Doc #8 §1.3: lang attribute per bubble, reflow-safe */}
      <div
        className="mb-4 flex-1 space-y-3 overflow-y-auto"
        role="log"
        aria-live="polite"
        aria-label={t('chat.messages')}
      >
        {messages.length === 0 && (
          <p className="text-field-base text-field-text-secondary" role="status">
            {t('chat.noMessages')}
          </p>
        )}

        {messages.map((msg) => {
          const label = confidenceLabel(msg.confidence);
          const showChip = label !== 'high';
          const showBackTranslation = showChip && msg.high_stakes && msg.back_translation;

          return (
            <div
              key={msg.message_id}
              className={`flex ${msg.sender === 'volunteer' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                lang={msg.translated_language}
                className={`max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg ${
                  msg.sender === 'volunteer'
                    ? 'bg-field-text-accent text-white'
                    : 'bg-field-surface text-field-text-primary'
                } rounded-lg px-4 py-2 shadow-sm`}
                // Doc #8 §1.3: reflow-safe — overflow-wrap handles 20–30% length variance
                style={{ overflowWrap: 'break-word', wordBreak: 'break-word' }}
              >
                {/* Translated text bubble */}
                <p className="text-field-base">{msg.translated_text}</p>

                {/* Original text (smaller, secondary) */}
                <p
                  lang={msg.original_language}
                  className="mt-1 text-field-sm text-field-text-secondary opacity-75"
                >
                  {msg.original_text}
                </p>

                {/* Confidence chip — Doc #8 §4.2 */}
                {showChip && (
                  <span
                    className={`mt-1 inline-block rounded-full px-2 py-0.5 text-field-xs font-medium ${
                      label === 'medium'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                    role="status"
                    aria-label={`Translation confidence: ${label}`}
                  >
                    {label === 'medium' ? t('chat.confidenceMedium') : t('chat.confidenceLow')}
                  </span>
                )}

                {/* Back-translation — Doc #8 §4.2: shown for medium/low + high-stakes */}
                {showBackTranslation && (
                  <p
                    className="mt-1 border-t border-current border-opacity-20 pt-1 text-field-xs italic opacity-75"
                    lang={msg.original_language}
                  >
                    &ldquo;{msg.back_translation}&rdquo;
                  </p>
                )}

                {/* SIMULATED / fallback badge */}
                {msg.fallback_used && (
                  <span
                    className="mt-1 inline-block rounded bg-orange-100 px-2 py-0.5 text-field-xs text-orange-700"
                    role="status"
                  >
                    {t('chat.fallbackUsed')}
                  </span>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Request human interpreter — Doc #8 §4.2 */}
      {messages.some((m) => m.high_stakes && confidenceLabel(m.confidence) !== 'high') && (
        <div className="mb-2 flex justify-center">
          <button
            onClick={requestHumanInterpreter}
            disabled={requestingInterpreter}
            className="rounded-lg border border-field-border bg-field-surface px-4 py-2 text-field-sm text-field-text-primary transition-colors hover:bg-field-bg-secondary disabled:opacity-50"
            aria-label={t('chat.requestInterpreter')}
          >
            {requestingInterpreter ? t('chat.requesting') : t('chat.requestInterpreter')}
          </button>
        </div>
      )}

      {/* Doc #8 §1.3 — 4.1.3: "Translating…" via live region */}
      <div
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {sending ? t('chat.translating') : ''}
      </div>

      {/* Input bar */}
      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={t('chat.inputPlaceholder')}
          className="min-h-thumb flex-1 rounded border border-field-border bg-field-surface px-3 text-field-base focus:outline-none focus:ring-2 focus:ring-field-text-accent"
          aria-label={t('chat.inputPlaceholder')}
          disabled={sending}
        />
        <button
          onClick={sendMessage}
          disabled={sending || !inputText.trim()}
          className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          aria-label={t('chat.send')}
        >
          {sending ? '...' : t('chat.send')}
        </button>
      </div>
    </div>
  );
}

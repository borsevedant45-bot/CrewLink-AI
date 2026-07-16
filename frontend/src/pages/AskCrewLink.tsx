import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface QAPair {
  question: string;
  answer: string;
  grounded: boolean;
  fallback_used: boolean;
}

export function AskCrewLink() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<QAPair[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const historyEndRef = useRef<HTMLDivElement>(null);

  const handleSubmit = async () => {
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
      const res = await fetch(`${BASE_URL}/knowledge-base/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as {
        answer: string | null;
        grounded: boolean;
        fallback_message: string | null;
        fallback_used: boolean;
      };
      const answerText = data.answer ?? data.fallback_message ?? t('ask.noResults');
      setHistory((prev) => [
        ...prev,
        {
          question: q,
          answer: answerText,
          grounded: data.grounded,
          fallback_used: data.fallback_used ?? !data.answer,
        },
      ]);
      setQuery('');
    } catch (err) {
      setError(t('ask.error'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl p-4">
      <h1 className="text-field-xl">{t('ask.title')}</h1>

      <div className="mt-4">
        <label htmlFor="ask-input" className="mb-2 block text-field-base font-semibold">
          {t('ask.placeholder')}
        </label>
        <div className="flex gap-2">
          <textarea
            id="ask-input"
            rows={3}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('ask.placeholder')}
            className="w-full rounded border border-field-border bg-field-surface px-3 py-2 text-field-base"
          />
        </div>
        <div className="mt-2 flex gap-2">
          <button
            onClick={handleSubmit}
            disabled={loading || !query.trim()}
            className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white disabled:opacity-50"
            aria-label={t('common.confirm')}
          >
            {loading ? t('app.loading') : t('common.confirm')}
          </button>

          {/* FR-13: Voice input stub — disabled, cites Key Assumption 3
           * Per Doc #1 §9 Key Assumption 3: "Multilingual support is text-based
           * for the MVP; voice-to-voice is a stretch goal." This button is
           * present-but-disabled with a visible citation so the gap is not silent. */}
          <button
            disabled
            title={t('ask.voiceDisabled')}
            className="min-h-thumb rounded-lg border border-field-border bg-field-surface px-4 text-field-base text-field-text-secondary opacity-50"
            aria-label={t('ask.voiceInput')}
          >
            {t('ask.voiceInput')}
          </button>
        </div>
      </div>

      {/* Doc #8 §1.4 — 4.1.3: searching live region */}
      {loading && (
        <div className="mt-6" role="status" aria-live="polite" aria-atomic="true">
          <p className="text-field-base text-field-text-secondary">{t('ask.searching')}</p>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mt-4 rounded border border-field-priority-urgent bg-field-priority-urgent/10 p-3 text-field-base text-field-priority-urgent"
        >
          {error}
        </div>
      )}

      {/* Doc #8 §1.4 — 1.3.1: Q&A history structured as pairs */}
      {history.length > 0 && (
        <div className="mt-6 space-y-4" role="list" aria-label={t('ask.history')}>
          {history.map((pair, idx) => (
            <article
              key={idx}
              role="listitem"
              className="rounded border border-field-border bg-field-surface p-4"
              aria-labelledby={`qa-question-${idx}`}
            >
              <h3 id={`qa-question-${idx}`} className="text-field-base font-semibold text-field-text-primary">
                {pair.question}
              </h3>
              {/* Doc #8 §1.4 — 3.3.1: fallback includes concrete next step */}
              <div className="mt-2 text-field-base text-field-text-primary">
                {pair.fallback_used ? (
                  <div>
                    <p>{pair.answer}</p>
                    <p className="mt-2 text-field-sm text-field-text-secondary">
                      {t('ask.fallbackNextStep')}
                    </p>
                  </div>
                ) : (
                  <p>{pair.answer}</p>
                )}
              </div>
              {pair.fallback_used && (
                <span
                  className="mt-2 inline-block rounded bg-orange-100 px-2 py-0.5 text-field-xs text-orange-700"
                  role="status"
                >
                  {t('ask.fallbackBadge')}
                </span>
              )}
            </article>
          ))}
          <div ref={historyEndRef} />
        </div>
      )}
    </div>
  );
}

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { ChatBridge } from '../src/pages/ChatBridge';
import { AuthContext } from '../src/contexts/AuthContext';
import { LanguageProvider } from '../src/contexts/LanguageContext';
import React, { useMemo } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

/*
 * Doc #8 §1.3 — Chat Bridge tests:
 *   - WCAG 3.1.2: lang attribute per message bubble
 *   - WCAG 1.4.10: reflow-safe rendering
 *   - Doc #8 §4.2: confidence chip, back-translation, Request human interpreter
 */

type FetchResponse = { ok: boolean; json: () => Promise<unknown> };

beforeEach(() => {
  vi.useFakeTimers();
  // JSDOM doesn't implement scrollIntoView
  Element.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

function MockAuthProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(
    () => ({
      volunteerId: 'vol_test',
      role: 'volunteer' as const,
      zoneId: 'zone_test',
      accessToken: 'mock-access-token',
      isAuthenticated: true,
      getWsTicket: async () => 'mock-ws-ticket',
      refreshToken: async () => {},
      login: async () => ({ access_token: 'mock-token', refresh_token: 'mock-refresh', volunteer_id: 'V001', role: 'volunteer' as const, zone_id: 'zone_east_concourse' }),
      logout: () => {},
    }),
    [],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function renderChatBridge(sessionId = 'chat_test_001') {
  return render(
    <MemoryRouter initialEntries={[`/chat/${sessionId}`]}>
      <Routes>
        <Route
          path="/chat/:sessionId"
          element={
            <MockAuthProvider>
              <LanguageProvider>
                <ChatBridge />
              </LanguageProvider>
            </MockAuthProvider>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ChatBridge — lang attribute and reflow [Doc #8 §1.3]', () => {
  it('renders messages with correct lang attribute on translated text', async () => {
    let resolveSession: (v: unknown) => void;
    let resolveMessages: (v: unknown) => void;

    const sessionPromise = new Promise((resolve) => { resolveSession = resolve; });
    const messagesPromise = new Promise((resolve) => { resolveMessages = resolve; });

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/chat-sessions/') && !url.endsWith('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              sessionPromise.then(() => ({
                session_id: 'chat_test_001',
                zone_id: 'zone_test',
                volunteer_language: 'en',
                fan_language: 'es',
                status: 'active',
                created_at: new Date().toISOString(),
              })),
          } as FetchResponse);
        }
        if (url.includes('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              messagesPromise.then(() => ({
                items: [
                  {
                    message_id: 'msg_001',
                    session_id: 'chat_test_001',
                    sender: 'fan',
                    original_text: '¿Dónde está la salida?',
                    original_language: 'es',
                    translated_text: 'Where is the exit?',
                    translated_language: 'en',
                    confidence: 0.95,
                    emergency_flag: false,
                    fallback_used: false,
                    back_translation: null,
                    high_stakes: false,
                    model_tier: 'fast_cheap',
                    created_at: new Date().toISOString(),
                  },
                ],
                has_more: false,
              })),
          } as FetchResponse);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as FetchResponse);
      }),
    );

    renderChatBridge();

    // Resolve session fetch
    await act(async () => {
      resolveSession!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    // Resolve messages fetch  
    await act(async () => {
      resolveMessages!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    const translatedBubble = screen.getByText('Where is the exit?');
    expect(translatedBubble).toBeTruthy();

    // Check the parent bubble has lang="en" (translated_language)
    const bubbleParent = translatedBubble.closest('[lang]');
    expect(bubbleParent).toBeTruthy();
    expect(bubbleParent?.getAttribute('lang')).toBe('en');

    // Check original text has lang="es"
    const originalText = screen.getByText('¿Dónde está la salida?');
    expect(originalText).toBeTruthy();
    expect(originalText.closest('[lang]')?.getAttribute('lang')).toBe('es');
  });

  it('shows confidence chip for medium/low confidence translations', async () => {
    let resolveSession: (v: unknown) => void;
    let resolveMessages: (v: unknown) => void;

    const sessionPromise = new Promise((resolve) => { resolveSession = resolve; });
    const messagesPromise = new Promise((resolve) => { resolveMessages = resolve; });

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/chat-sessions/') && !url.endsWith('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              sessionPromise.then(() => ({
                session_id: 'chat_test_001',
                zone_id: 'zone_test',
                volunteer_language: 'en',
                fan_language: 'es',
                status: 'active',
                created_at: new Date().toISOString(),
              })),
          } as FetchResponse);
        }
        if (url.includes('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              messagesPromise.then(() => ({
                items: [
                  {
                    message_id: 'msg_002',
                    session_id: 'chat_test_001',
                    sender: 'fan',
                    original_text: 'Necesito ayuda',
                    original_language: 'es',
                    translated_text: 'I need help',
                    translated_language: 'en',
                    confidence: 0.45,
                    emergency_flag: false,
                    fallback_used: false,
                    back_translation: null,
                    high_stakes: false,
                    model_tier: 'fast_cheap',
                    created_at: new Date().toISOString(),
                  },
                ],
                has_more: false,
              })),
          } as FetchResponse);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as FetchResponse);
      }),
    );

    renderChatBridge();

    await act(async () => {
      resolveSession!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    await act(async () => {
      resolveMessages!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    // Confidence chip should render for medium/low confidence
    const chip = screen.getByRole('status', { name: /Translation confidence/i });
    expect(chip).toBeTruthy();
  });

  it('shows back-translation for high-stakes + medium/low confidence messages', async () => {
    let resolveSession: (v: unknown) => void;
    let resolveMessages: (v: unknown) => void;

    const sessionPromise = new Promise((resolve) => { resolveSession = resolve; });
    const messagesPromise = new Promise((resolve) => { resolveMessages = resolve; });

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/chat-sessions/') && !url.endsWith('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              sessionPromise.then(() => ({
                session_id: 'chat_test_001',
                zone_id: 'zone_test',
                volunteer_language: 'en',
                fan_language: 'es',
                status: 'active',
                created_at: new Date().toISOString(),
              })),
          } as FetchResponse);
        }
        if (url.includes('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              messagesPromise.then(() => ({
                items: [
                  {
                    message_id: 'msg_003',
                    session_id: 'chat_test_001',
                    sender: 'fan',
                    original_text: '¡Ayuda, me duele el pecho!',
                    original_language: 'es',
                    translated_text: 'Help, my chest hurts!',
                    translated_language: 'en',
                    confidence: 0.55,
                    emergency_flag: true,
                    fallback_used: false,
                    back_translation: 'Help, my chest hurts!',
                    high_stakes: true,
                    model_tier: 'fast_cheap',
                    created_at: new Date().toISOString(),
                  },
                ],
                has_more: false,
              })),
          } as FetchResponse);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as FetchResponse);
      }),
    );

    renderChatBridge();

    await act(async () => {
      resolveSession!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    await act(async () => {
      resolveMessages!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    // Back-translation should be visible (appears twice: translated + back-translation)
    const backTranslations = screen.getAllByText(/Help, my chest hurts!/);
    expect(backTranslations.length).toBeGreaterThanOrEqual(2);

    // Request human interpreter button should appear for high-stakes + medium/low
    const interpreterBtn = screen.getByRole('button', { name: /Request human interpreter/i });
    expect(interpreterBtn).toBeTruthy();
  });

  it('shows fallback badge when fallback_used is true', async () => {
    let resolveSession: (v: unknown) => void;
    let resolveMessages: (v: unknown) => void;

    const sessionPromise = new Promise((resolve) => { resolveSession = resolve; });
    const messagesPromise = new Promise((resolve) => { resolveMessages = resolve; });

    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        if (url.includes('/chat-sessions/') && !url.endsWith('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              sessionPromise.then(() => ({
                session_id: 'chat_test_001',
                zone_id: 'zone_test',
                volunteer_language: 'en',
                fan_language: 'es',
                status: 'active',
                created_at: new Date().toISOString(),
              })),
          } as FetchResponse);
        }
        if (url.includes('/messages')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              messagesPromise.then(() => ({
                items: [
                  {
                    message_id: 'msg_004',
                    session_id: 'chat_test_001',
                    sender: 'volunteer',
                    original_text: 'Hello',
                    original_language: 'en',
                    translated_text: 'Hello',
                    translated_language: 'es',
                    confidence: 0.0,
                    emergency_flag: false,
                    fallback_used: true,
                    back_translation: null,
                    high_stakes: false,
                    model_tier: 'fast_cheap',
                    created_at: new Date().toISOString(),
                  },
                ],
                has_more: false,
              })),
          } as FetchResponse);
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({}),
        } as FetchResponse);
      }),
    );

    renderChatBridge();

    await act(async () => {
      resolveSession!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    await act(async () => {
      resolveMessages!({});
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(screen.getByText(/Translation unavailable/i)).toBeTruthy();
  });
});

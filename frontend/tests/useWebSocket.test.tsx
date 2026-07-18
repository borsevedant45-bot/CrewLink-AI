import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { useWebSocket } from '../src/hooks/useWebSocket';
import { AuthContext } from '../src/contexts/AuthContext';
import type { WsEvent } from '../src/types';
import React, { useMemo } from 'react';

/*
 * Test 1: WS-drop -> polling fallback, identical render output
 * Test 3: 4401 close code -> re-issue ws-ticket -> reconnect
 */

let mockWsInstances: FakeWebSocket[] = [];
let mockFetchCalls: Array<{ url: string; options: RequestInit }> = [];

class FakeWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  url: string;
  readyState: number = FakeWebSocket.CONNECTING;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    mockWsInstances.push(this);
    setTimeout(() => {
      this.readyState = FakeWebSocket.OPEN;
      if (this.onopen) this.onopen(new Event('open'));
    }, 0);
  }

  send(_data: string): void {}

  close(code?: number, reason?: string): void {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: true }));
    }
  }

  triggerMessage(data: Record<string, unknown>): void {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', {
        data: JSON.stringify(data),
      }));
    }
  }

  triggerClose(code: number = 1000, reason: string = ''): void {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: true }));
    }
  }
}

beforeEach(() => {
  mockWsInstances = [];
  mockFetchCalls = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal(
    'fetch',
    vi.fn(function (_url: string, _options?: RequestInit) {
      mockFetchCalls.push({ url: _url, options: _options ?? {} });
      return Promise.resolve({
        ok: true,
        json: function () {
          return Promise.resolve({
            data: [],
            pagination: { next_cursor: null, has_more: false },
          });
        },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  mockWsInstances = [];
  mockFetchCalls = [];
});

function latestWs(): FakeWebSocket | null {
  return mockWsInstances.length > 0
    ? mockWsInstances[mockWsInstances.length - 1]!
    : null;
}

/* --- Shared test helpers --- */

function MockAuthProvider({
  children,
  getWsTicket,
  refreshToken,
  accessToken,
}: {
  children: React.ReactNode;
  getWsTicket?: () => Promise<string>;
  refreshToken?: () => Promise<void>;
  accessToken?: string | null;
}) {
  const value = useMemo(
    () => ({
      volunteerId: 'vol_test',
      role: 'volunteer' as const,
      zoneId: 'zone_test',
      accessToken: accessToken ?? 'mock-access-token',
      isAuthenticated: true,
      getWsTicket: getWsTicket ?? (async () => 'mock-ws-ticket'),
      refreshToken: refreshToken ?? (async () => {}),
      login: async () => ({ access_token: 'mock-token', refresh_token: 'mock-refresh', volunteer_id: 'V001', role: 'volunteer' as const, zone_id: 'zone_east_concourse' }),
      logout: () => {},
    }),
    [getWsTicket, refreshToken, accessToken],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function TestConsumer({
  onUpdate,
}: {
  onUpdate: (event: WsEvent) => void;
}) {
  const { status, isOffline } = useWebSocket({
    channel: 'tasks',
    pollEndpoint: '/incidents/feed',
    onUpdate,
    pollInterval: 100,
  });
  return (
    <div>
      <span data-testid="connection-status">{status}</span>
      <span data-testid="offline-status">{String(isOffline)}</span>
    </div>
  );
}

/* ================================================================
 * Test 1: WS drop -> polling fallback [Doc #8 S2.1, FR-3]
 * ================================================================ */

describe('WebSocket hook -- polling fallback [Doc #8 S2.1, FR-3]', () => {
  it('falls back to polling when WebSocket disconnects', async () => {
    vi.useFakeTimers();

    const updates: WsEvent[] = [];

    expect(mockWsInstances.length).toBe(0);
    expect(mockFetchCalls.length).toBe(0);

    await act(async () => {
      render(
        <MockAuthProvider>
          <TestConsumer onUpdate={(evt) => updates.push(evt)} />
        </MockAuthProvider>,
      );
    });

    /* Advance past setTimeout(0) for WS onopen */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(mockWsInstances.length).toBe(1);
    expect(latestWs()?.readyState).toBe(FakeWebSocket.OPEN);
    expect(screen.getByTestId('connection-status').textContent).toBe('connected');

    /* Close the WS (non-4401) -- triggers startPolling() */
    await act(async () => {
      latestWs()?.triggerClose(1006, 'Abnormal closure');
    });

    /* Status changes to 'polling' synchronously with the close handler */
    expect(screen.getByTestId('connection-status').textContent).toBe('polling');

    /* Advance enough for polling interval (100ms) but NOT reconnect (3000ms) */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    /* Polling fallback calls fetch on /incidents/feed */
    const feedCalls = mockFetchCalls.filter(
      (c) => typeof c.url === 'string' && c.url.includes('/incidents/feed'),
    );
    expect(feedCalls.length).toBeGreaterThan(0);

    /* Updates are delivered through the same onUpdate path regardless of transport */
    const pollUpdates = updates.filter((u) => u.event === 'poll.update');
    expect(pollUpdates.length).toBeGreaterThan(0);

    /* Still polling -- reconnect hasn't fired yet */
    expect(screen.getByTestId('connection-status').textContent).toBe('polling');
  });

  it('delivers updates through same callback regardless of transport', async () => {
    vi.useFakeTimers();

    const wsUpdates: WsEvent[] = [];
    const pollUpdates: WsEvent[] = [];

    function Tracker() {
      const { status } = useWebSocket({
        channel: 'tasks',
        pollEndpoint: '/incidents/feed',
        onUpdate: (evt) => {
          if (evt.event === 'poll.update') pollUpdates.push(evt);
          else wsUpdates.push(evt);
        },
        pollInterval: 100,
      });
      return (
        <div>
          <span data-testid="transport-status">{status}</span>
        </div>
      );
    }

    await act(async () => {
      render(
        <MockAuthProvider>
          <Tracker />
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    /* WS delivers an update */
    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: { id: 'inc_001' },
        emitted_at: new Date().toISOString(),
      });
    });

    expect(wsUpdates.length).toBe(1);

    /* WS drops -- polling takes over */
    await act(async () => {
      latestWs()?.triggerClose(1006);
    });

    expect(screen.getByTestId('transport-status').textContent).toBe('polling');

    await act(async () => {
      await vi.advanceTimersByTimeAsync(1500);
    });

    expect(pollUpdates.length).toBeGreaterThan(0);

    /* Both transport paths use the SAME onUpdate callback */
    expect(wsUpdates[0]?.event).toBe('incident.created');
    expect(pollUpdates[0]?.event).toBe('poll.update');

    const totalUpdates = wsUpdates.length + pollUpdates.length;
    expect(totalUpdates).toBeGreaterThan(1);
  });
});

/* ================================================================
 * Test 2: Offline detection — 3 consecutive polling failures -> isOffline [FR-5]
 * ================================================================ */

describe('WebSocket hook — offline detection [FR-5]', () => {
  it('sets isOffline=true after 3 consecutive polling failures', async () => {
    vi.useFakeTimers();

    let fetchCount = 0;
    /* First fetch succeeds (WS initial poll), then fail everything */
    vi.stubGlobal(
      'fetch',
      vi.fn(function (_url: string, _options?: RequestInit) {
        fetchCount++;
        if (fetchCount >= 2) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({
          ok: true,
          json: function () {
            return Promise.resolve({
              data: [],
              pagination: { next_cursor: null, has_more: false },
            });
          },
        });
      }),
    );

    function OfflineConsumer() {
      const { status, isOffline } = useWebSocket({
        channel: 'tasks',
        pollEndpoint: '/incidents/feed',
        onUpdate: () => {},
        pollInterval: 100,
      });
      return (
        <div>
          <span data-testid="connection-status">{status}</span>
          <span data-testid="offline-status">{String(isOffline)}</span>
        </div>
      );
    }

    await act(async () => {
      render(
        <MockAuthProvider accessToken="mock-access-token">
          <OfflineConsumer />
        </MockAuthProvider>,
      );
    });

    /* WS connects */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(screen.getByTestId('connection-status').textContent).toBe('connected');
    expect(screen.getByTestId('offline-status').textContent).toBe('false');

    /* Drop WS — triggers polling */
    await act(async () => {
      latestWs()?.triggerClose(1006, 'Abnormal closure');
    });

    expect(screen.getByTestId('connection-status').textContent).toBe('polling');

    /* Advance past 3 polling intervals (100ms each) + buffer */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    /* After 3 consecutive poll failures, status should be 'error' and isOffline true */
    expect(screen.getByTestId('connection-status').textContent).toBe('error');
    expect(screen.getByTestId('offline-status').textContent).toBe('true');
  });
});

/* ================================================================
 * Test 3: 4401 close code -> reconnect [Doc #5 S3.1]
 * ================================================================ */

describe('WebSocket hook -- 4401 reconnect [Doc #5 S3.1]', () => {
  it('re-issues ws-ticket and reconnects on 4401 close code', async () => {
    vi.useFakeTimers();

    let ticketCount = 0;
    const originalTicket = 'mock-ws-ticket-original';
    const refreshedTicket = 'mock-ws-ticket-refreshed';

    const customGetWsTicket = async () => {
      ticketCount++;
      return ticketCount === 1 ? originalTicket : refreshedTicket;
    };

    await act(async () => {
      render(
        <MockAuthProvider getWsTicket={customGetWsTicket}>
          <TestConsumer onUpdate={() => {}} />
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    expect(mockWsInstances.length).toBe(1);
    expect(ticketCount).toBe(1);
    expect(mockWsInstances[0]?.url).toContain(originalTicket);

    /* Simulate 4401 close (token expired per Doc #5 S3.1 step 3) */
    await act(async () => {
      latestWs()?.triggerClose(4401, 'token_expired');
    });

    /* 4401 handler: refreshToken -> reconnect (500ms delay) */
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    /* A new WebSocket was created with refreshed ticket */
    expect(mockWsInstances.length).toBe(2);
    expect(mockWsInstances[1]?.url).toContain(refreshedTicket);
  });

  it('preserves in-flight state across 4401 reconnect', async () => {
    vi.useFakeTimers();

    let ticketCount = 0;
    const customGetWsTicket = async () => {
      ticketCount++;
      return `ticket-${ticketCount}`;
    };

    const receivedUpdates: WsEvent[] = [];

    await act(async () => {
      render(
        <MockAuthProvider getWsTicket={customGetWsTicket}>
          <TestConsumer onUpdate={(evt) => receivedUpdates.push(evt)} />
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    /* Event before disconnect */
    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: { id: 'inc_001' },
        emitted_at: new Date().toISOString(),
      });
    });

    expect(receivedUpdates.length).toBe(1);

    /* 4401 close */
    await act(async () => {
      latestWs()?.triggerClose(4401, 'token_expired');
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });

    /* Event after reconnect */
    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: { id: 'inc_002' },
        emitted_at: new Date().toISOString(),
      });
    });

    /*
     * Both events delivered through the same onUpdate path.
     * No in-flight state was dropped.
     */
    expect(receivedUpdates.length).toBe(2);
    expect(receivedUpdates[0]?.event).toBe('incident.created');
    expect(receivedUpdates[1]?.event).toBe('incident.created');
  });
});

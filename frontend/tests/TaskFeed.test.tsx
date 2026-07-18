import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { TaskFeed } from '../src/pages/TaskFeed';
import { AuthContext } from '../src/contexts/AuthContext';
import { LanguageProvider } from '../src/contexts/LanguageContext';
import React, { useMemo } from 'react';

/*
 * Doc #8 §2.1 — aria-live delta announcements (not full list re-read)
 * Doc #8 §2.3 — three-channel priority rendering
 * Doc #8 §1.5 — focus not relocated on update
 */

let mockWsInstances: FakeWebSocket[] = [];

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
  close(_code?: number, _reason?: string): void {
    this.readyState = FakeWebSocket.CLOSED;
  }

  triggerMessage(data: Record<string, unknown>): void {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', {
        data: JSON.stringify(data),
      }));
    }
  }
}

beforeEach(() => {
  mockWsInstances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal(
    'fetch',
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            pagination: { next_cursor: null, has_more: false },
          }),
      }),
    ),
  );
  vi.useFakeTimers();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  mockWsInstances = [];
});

function latestWs(): FakeWebSocket | null {
  return mockWsInstances.length > 0
    ? mockWsInstances[mockWsInstances.length - 1]!
    : null;
}

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

describe('TaskFeed — live region and priority channels [Doc #8 §2.1, §2.3]', () => {
  it('renders empty state initially', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    expect(screen.getByText('No tasks')).toBeTruthy();
  });

  it('renders incidents with priority-based styling', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: {
          incident_id: 'inc_001',
          category: 'medical',
          description: 'Fan collapsed at Gate 4',
          source: 'VOLUNTEER_REPORTED',
          zone_id: 'zone_east_concourse',
          status: 'Reported',
          priority_score: 90,
          created_at: new Date().toISOString(),
        },
        emitted_at: new Date().toISOString(),
      });
    });

    expect(screen.getByText('medical')).toBeTruthy();
    const list = screen.getByRole('list');
    expect(list).toBeTruthy();
    expect(list.children.length).toBe(1);

    const priorityItem = screen.getByText('Urgent');
    expect(priorityItem).toBeTruthy();
  });

  it('shows moderate priority for medium scores', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: {
          incident_id: 'inc_002',
          category: 'crowd_queue',
          description: 'Long queue',
          source: 'VOLUNTEER_REPORTED',
          zone_id: 'zone_west_concourse',
          status: 'Reported',
          priority_score: 50,
          created_at: new Date().toISOString(),
        },
        emitted_at: new Date().toISOString(),
      });
    });

    const priorityItem = screen.getByText('Moderate');
    expect(priorityItem).toBeTruthy();
  });

  it('shows low priority for low scores', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: {
          incident_id: 'inc_003',
          category: 'lost_item',
          description: 'Lost phone',
          source: 'VOLUNTEER_REPORTED',
          zone_id: 'zone_east_concourse',
          status: 'Reported',
          priority_score: 20,
          created_at: new Date().toISOString(),
        },
        emitted_at: new Date().toISOString(),
      });
    });

    const priorityItem = screen.getByText('Low');
    expect(priorityItem).toBeTruthy();
  });

  it('aria-live region broadcasts delta announcements not full list', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    const liveRegion = document.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeTruthy();
    expect(liveRegion?.textContent).toBe('');

    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: {
          incident_id: 'inc_001',
          category: 'medical',
          description: 'Emergency',
          source: 'VOLUNTEER_REPORTED',
          zone_id: 'zone_east_concourse',
          status: 'Reported',
          priority_score: 90,
          created_at: new Date().toISOString(),
        },
        emitted_at: new Date().toISOString(),
      });
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(600);
    });

    expect(liveRegion?.textContent).toBeTruthy();
    expect(liveRegion?.textContent).toContain('1');
  });

  it('supports SIMULATED badge rendering', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <TaskFeed />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    await act(async () => {
      latestWs()?.triggerMessage({
        event: 'incident.created',
        data: {
          incident_id: 'inc_sim',
          category: 'general',
          description: 'Test simulation',
          source: 'SIMULATED',
          zone_id: 'zone_east_concourse',
          status: 'Reported',
          priority_score: 30,
          created_at: new Date().toISOString(),
        },
        emitted_at: new Date().toISOString(),
      });
    });

    expect(screen.getByText('[Simulated]')).toBeTruthy();
  });
});

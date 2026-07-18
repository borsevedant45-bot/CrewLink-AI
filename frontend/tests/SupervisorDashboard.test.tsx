import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { SupervisorDashboard } from '../src/pages/SupervisorDashboard';
import { AuthContext } from '../src/contexts/AuthContext';
import { LanguageProvider } from '../src/contexts/LanguageContext';
import React, { useMemo } from 'react';

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
      this.onmessage(
        new MessageEvent('message', {
          data: JSON.stringify(data),
        }),
      );
    }
  }

  triggerClose(code: number = 1000, reason: string = ''): void {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, reason, wasClean: true }));
    }
  }
}

const MOCK_ROLLUP = {
  zones: [
    {
      zone_id: 'zone_east_concourse',
      name: 'East Concourse',
      open_incident_count: 3,
      active_volunteer_count: 6,
      available_volunteer_count: 4,
      current_crowd_density: 'MODERATE',
    },
    {
      zone_id: 'zone_west_concourse',
      name: 'West Concourse',
      open_incident_count: 1,
      active_volunteer_count: 5,
      available_volunteer_count: 3,
      current_crowd_density: 'LOW',
    },
    {
      zone_id: 'zone_north_gate',
      name: 'North Gate',
      open_incident_count: 0,
      active_volunteer_count: 4,
      available_volunteer_count: 4,
      current_crowd_density: null,
    },
  ],
  venue_total_open: 4,
  generated_at: '2026-07-11T14:30:00Z',
};

beforeEach(() => {
  mockWsInstances = [];
  vi.stubGlobal('WebSocket', FakeWebSocket);
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/supervisor/rollup')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(MOCK_ROLLUP),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ items: [], has_more: false }),
      });
    }),
  );
  vi.useFakeTimers();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  mockWsInstances = [];
});

function MockAuthProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(
    () => ({
      volunteerId: 'vol_supervisor',
      role: 'supervisor' as const,
      zoneId: null,
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

describe('SupervisorDashboard — FR-17/FR-18/FR-19 rollup display', () => {
  it('renders zone cards with open incidents', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <SupervisorDashboard />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await vi.waitFor(() => {
      expect(screen.getByText('East Concourse')).toBeTruthy();
    });

    expect(screen.getByText('West Concourse')).toBeTruthy();
    expect(screen.getByText('North Gate')).toBeTruthy();
  });

  it('shows venue-wide open incident count', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <SupervisorDashboard />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await vi.waitFor(() => {
      expect(screen.getByText(/Venue-wide/i)).toBeTruthy();
    });
  });

  it('displays crowd-density for zones that have it (FR-19)', async () => {
    await act(async () => {
      render(
        <MockAuthProvider>
          <LanguageProvider>
            <SupervisorDashboard />
          </LanguageProvider>
        </MockAuthProvider>,
      );
    });

    await vi.waitFor(() => {
      const densityLabels = screen.getAllByText('Crowd Density');
      expect(densityLabels.length).toBeGreaterThanOrEqual(2);
    });
  });
});

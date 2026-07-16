import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { IncidentDetail } from '../src/pages/IncidentDetail';
import { AuthContext } from '../src/contexts/AuthContext';
import { LanguageProvider } from '../src/contexts/LanguageContext';
import React, { useMemo } from 'react';

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn((url: string) => {
      if (url.includes('/incidents/')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              incident_id: 'inc_001',
              category: 'medical',
              description: 'Fan collapsed at Gate 4',
              source: 'VOLUNTEER_REPORTED',
              zone_id: 'zone_east_concourse',
              status: 'Dispatched',
              priority_score: 90,
              assigned_volunteer_id: 'vol_maria',
              created_at: '2026-07-11T14:22:03Z',
              triaged_at: null,
              resolved_at: null,
            }),
        });
      }
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function MockAuthProvider({ children }: { children: React.ReactNode }) {
  const value = useMemo(
    () => ({
      volunteerId: 'vol_test',
      role: 'volunteer' as const,
      zoneId: 'zone_east_concourse',
      accessToken: 'mock-access-token',
      isAuthenticated: true,
      getWsTicket: async () => 'mock-ws-ticket',
      refreshToken: async () => {},
      login: async () => {},
      logout: () => {},
    }),
    [],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

function renderWithRouter(route: string) {
  return render(
    <MockAuthProvider>
      <LanguageProvider>
        <MemoryRouter initialEntries={[route]}>
          <Routes>
            <Route path="/incidents/:id" element={<IncidentDetail />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>
    </MockAuthProvider>,
  );
}

describe('IncidentDetail — FR-4 one-tap status buttons [Doc #1 §5.1 FR-4]', () => {
  it('shows Acknowledge button when status is Dispatched', async () => {
    await act(async () => {
      renderWithRouter('/incidents/inc_001');
    });

    await vi.waitFor(() => {
      expect(screen.getByText('Acknowledge')).toBeTruthy();
    });
  });

  it('shows En Route button after acknowledging', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, options?: RequestInit) => {
        if (options?.method === 'PATCH') {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                incident_id: 'inc_001',
                category: 'medical',
                description: 'Fan collapsed',
                source: 'VOLUNTEER_REPORTED',
                zone_id: 'zone_east_concourse',
                status: 'Acknowledged',
                priority_score: 90,
                assigned_volunteer_id: 'vol_maria',
                created_at: '2026-07-11T14:22:03Z',
                triaged_at: null,
                resolved_at: null,
              }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              incident_id: 'inc_001',
              category: 'medical',
              description: 'Fan collapsed',
              source: 'VOLUNTEER_REPORTED',
              zone_id: 'zone_east_concourse',
              status: 'Acknowledged',
              priority_score: 90,
              assigned_volunteer_id: 'vol_maria',
              created_at: '2026-07-11T14:22:03Z',
              triaged_at: null,
              resolved_at: null,
            }),
        });
      }),
    );

    await act(async () => {
      renderWithRouter('/incidents/inc_001');
    });

    await vi.waitFor(() => {
      const buttons = screen.getAllByRole('button');
      const enRoute = buttons.find((b) => b.textContent === 'En Route');
      expect(enRoute).toBeTruthy();
    });
  });
});

describe('IncidentDetail — FR-21 navigation route stub [Doc #1 §5.6 FR-21, G19]', () => {
  it('shows suggested route section', async () => {
    await act(async () => {
      renderWithRouter('/incidents/inc_001');
    });

    await vi.waitFor(() => {
      expect(screen.getByText('Route')).toBeTruthy();
    });
  });

  it('includes zone name in route text', async () => {
    await act(async () => {
      renderWithRouter('/incidents/inc_001');
    });

    await vi.waitFor(() => {
      const routeSection = screen.getByText('Route').closest('section');
      expect(routeSection).toBeTruthy();
      expect(routeSection?.textContent).toMatch(/zone_east_concourse/i);
    });
  });
});

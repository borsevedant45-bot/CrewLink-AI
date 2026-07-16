import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';
import ICU from 'i18next-icu';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { runAxe, formatViolations } from './a11y';
import { TaskFeed } from '@/pages/TaskFeed';
import { IncidentDetail } from '@/pages/IncidentDetail';
import { ChatBridge } from '@/pages/ChatBridge';
import { AskCrewLink } from '@/pages/AskCrewLink';

void i18n.use(ICU).init({
  resources: {
    en: { translation: {
      app: { title: 'CrewLink AI', loading: 'Loading...', error: 'Error', retry: 'Retry', offline: 'Offline' },
      nav: { tasks: 'Tasks', chat: 'Chat', ask: 'Ask CrewLink', supervisor: 'Supervisor', settings: 'Settings', logout: 'Log Out' },
      auth: { login: 'Log In', badgeCode: 'Code', pin: 'PIN', loginError: 'Invalid', sessionExpired: 'Expired' },
      task: { feed: 'Task Feed', empty: 'No tasks', newTasks: '{count} new tasks', highestPriority: 'Highest: {priority}', ariaNewTask: 'New: {category}, {zone}, {priority}' },
      incident: { detail: 'Incident Detail', category: 'Category', location: 'Location', description: 'Description', source: 'Source', actions: 'Actions', acknowledge: 'Acknowledge', enRoute: 'En Route', resolve: 'Resolve', escalate: 'Escalate', confirmEscalate: 'Confirm?', notes: 'Notes', notesPlaceholder: 'Describe...', notesRequired: 'Required', sessionExpired: 'Session expired', reauth: 'Log in', routeTitle: 'Route', routeBody: 'From {zone} to {section}' },
      chat: { title: 'Chat Bridge', inputPlaceholder: 'Type...', send: 'Send', translating: 'Translating...', detectedLanguage: 'Detected: {language}', wrongLanguage: 'Wrong?', sessionClosed: 'Closed', noSession: 'No session', noMessages: 'No messages', messages: 'Messages', confidenceMedium: 'Moderate', confidenceLow: 'Low', fallbackUsed: 'Unavailable', requestInterpreter: 'Interpreter', requesting: 'Requesting...' },
      ask: { title: 'Ask CrewLink', placeholder: 'Ask...', searching: 'Searching...', noResults: 'Not found', error: 'Failed', voiceInput: 'Voice Input', voiceDisabled: 'Not available (Key Assumption 3)', fallbackNextStep: 'Confirm with supervisor.', fallbackBadge: 'Unverified', history: 'Q&A History' },
      supervisor: { title: 'Dashboard', incidents: 'Incidents', zones: 'Zones', volunteers: 'Volunteers', openIncidents: 'Open', totalVolunteers: 'Total', available: 'Available', density: 'Density', crowdHigh: 'High', loading: 'Loading...', error: 'Error', venueTotal: 'Venue-wide: {count}' },
      source: { simulated: 'Simulated', volunteer: 'Volunteer Reported', supervisor: 'Supervisor Created' },
      priority: { urgent: 'Urgent', moderate: 'Moderate', low: 'Low' },
      theme: { light: 'Light', dark: 'Dark', toggle: 'Toggle theme' },
      common: { back: 'Back', close: 'Close', confirm: 'Confirm', cancel: 'Cancel', save: 'Save', delete: 'Delete' },
      status: { reported: 'Reported', triaged: 'Triaged', dispatched: 'Dispatched', acknowledged: 'Acknowledged', enRoute: 'En Route', inProgress: 'In Progress', resolved: 'Resolved', cancelled: 'Cancelled', escalated: 'Escalated' },
      offline: { title: 'Offline', description: 'Offline description' },
    } },
  },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnObjects: true,
});

/* eslint-disable @typescript-eslint/no-explicit-any */

/* jsdom doesn't implement scrollIntoView — stub it globally */
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {};
}
const mockAuthValue: Record<string, any> = {
  volunteerId: 'vol_001',
  accessToken: 'test-token',
  role: 'volunteer',
  zoneId: 'zone_east_concourse',
  login: async () => {},
  logout: () => {},
  refreshToken: async () => {},
  getWsTicket: async () => 'ws-ticket',
  isAuthenticated: true,
};

function renderWithProviders(ui: React.ReactElement, { initialEntries, path }: { initialEntries?: string[]; path?: string } = {}) {
  const content = path ? (
    <Routes>
      <Route path={path} element={ui} />
    </Routes>
  ) : ui;
  return render(
    <I18nextProvider i18n={i18n}>
      <AuthContext.Provider value={mockAuthValue as any}>
        <LanguageProvider>
          <MemoryRouter initialEntries={initialEntries}>
            {content}
          </MemoryRouter>
        </LanguageProvider>
      </AuthContext.Provider>
    </I18nextProvider>,
  );
}

describe('TaskFeed — Doc #8 §1.1 axe-core audit', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('has zero WCAG 2.1 AA violations', async () => {
    const { container } = renderWithProviders(<TaskFeed />);
    const results = await runAxe(container);
    expect(results.violations, formatViolations(results.violations)).toHaveLength(0);
  });
});

describe('IncidentDetail — Doc #8 §1.2 axe-core audit', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          incident_id: 'inc_001',
          category: 'medical',
          description: 'Fan collapsed',
          source: 'VOLUNTEER_REPORTED',
          zone_id: 'zone_east_concourse',
          status: 'Dispatched',
          priority_score: 90,
          assigned_volunteer_id: null,
          created_at: '2026-07-16T10:00:00Z',
          triaged_at: null,
          resolved_at: null,
        }),
      })
    ));
    /* IncidentDetail uses useParams, so we need to set window.location for the Router */
  });

  it('has zero WCAG 2.1 AA violations', async () => {
    const { container } = renderWithProviders(<IncidentDetail />, { initialEntries: ['/incidents/inc_001'], path: '/incidents/:id' });
    await screen.findByRole('heading', { level: 1, name: 'Incident Detail' });
    const results = await runAxe(container);
    expect(results.violations, formatViolations(results.violations)).toHaveLength(0);
  });
});

describe('ChatBridge — Doc #8 §1.3 axe-core audit', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ session_id: 'sess_001', zone_id: 'zone_east', volunteer_language: 'en', fan_language: 'es', status: 'active', created_at: '2026-07-16T10:00:00Z' }),
      })
    ));
  });

  it('has zero WCAG 2.1 AA violations', async () => {
    const { container } = renderWithProviders(<ChatBridge />, { initialEntries: ['/chat/sess_001'], path: '/chat/:sessionId' });
    await screen.findByRole('heading', { level: 1, name: 'Chat Bridge' });
    const results = await runAxe(container);
    expect(results.violations, formatViolations(results.violations)).toHaveLength(0);
  });
});

describe('AskCrewLink — Doc #8 §1.4 axe-core audit', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('has zero WCAG 2.1 AA violations', async () => {
    const { container } = renderWithProviders(<AskCrewLink />);
    const results = await runAxe(container);
    expect(results.violations, formatViolations(results.violations)).toHaveLength(0);
  });
});

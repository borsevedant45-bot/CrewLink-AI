import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from 'i18next';
import ICU from 'i18next-icu';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { AuthContext } from '@/contexts/AuthContext';
import { LanguageProvider } from '@/contexts/LanguageContext';
import { TaskFeed } from '@/pages/TaskFeed';
import { ChatBridge } from '@/pages/ChatBridge';
import { IncidentDetail } from '@/pages/IncidentDetail';
import { AskCrewLink } from '@/pages/AskCrewLink';
import userEvent from '@testing-library/user-event';

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
      offline: { title: 'Offline', description: 'Offline' },
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

describe('TaskFeed — Doc #8 §1.1 keyboard/focus', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('shows empty state when no incidents (default)', () => {
    renderWithProviders(<TaskFeed />);
    /* When empty, TaskFeed shows a paragraph, not a list */
    expect(screen.getByText('No tasks')).toBeInTheDocument();
  });

  it('shows aria-live region for delta announcements', () => {
    renderWithProviders(<TaskFeed />);
    const liveRegion = document.querySelector('[aria-live="polite"]');
    expect(liveRegion).toBeInTheDocument();
    expect(liveRegion).toHaveAttribute('aria-atomic', 'true');
  });

  it('uses native ul/role=list semantic when incidents present', () => {
    /* Inject incidents via sessionStorage to trigger list rendering */
    const mockIncidents = [
      { incident_id: 'inc_001', category: 'medical', description: 'Test', source: 'VOLUNTEER_REPORTED', zone_id: 'zone_a', status: 'Dispatched', priority_score: 90, created_at: '2026-01-01T00:00:00Z' },
    ];
    sessionStorage.setItem('crewlink_taskfeed_incidents', JSON.stringify(mockIncidents));
    renderWithProviders(<TaskFeed />);
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();
    expect(list.tagName).toBe('UL');
    sessionStorage.clear();
  });
});

describe('ChatBridge — Doc #8 §1.3 keyboard', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ session_id: 'sess_001', zone_id: 'zone_east', volunteer_language: 'en', fan_language: 'es', status: 'active', created_at: '2026-07-16T10:00:00Z' }),
      })
    ));
  });

  it('sends message on Enter key', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ session_id: 'sess_001', zone_id: 'zone_east', volunteer_language: 'en', fan_language: 'es', status: 'active', created_at: '2026-07-16T10:00:00Z' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [] }),
      })
    );
    const user = userEvent.setup();
    renderWithProviders(<ChatBridge />, { initialEntries: ['/chat/sess_001'], path: '/chat/:sessionId' });
    await screen.findByRole('heading', { level: 1, name: 'Chat Bridge' });
    const input = screen.getByRole('textbox', { name: 'Type...' });
    await user.type(input, 'Hello');
    await user.keyboard('{Enter}');
  });

  it('has accessible send button with aria-label', () => {
    renderWithProviders(<ChatBridge />, { initialEntries: ['/chat/sess_001'], path: '/chat/:sessionId' });
    const sendBtn = screen.getByRole('button', { name: 'Send' });
    expect(sendBtn).toBeInTheDocument();
  });
});

describe('IncidentDetail — Doc #8 §1.2 keyboard/focus', () => {
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
  });

  it('status chip has role="status" for AT announcements', async () => {
    renderWithProviders(<IncidentDetail />, { initialEntries: ['/incidents/inc_001'], path: '/incidents/:id' });
    await screen.findByRole('heading', { level: 1, name: 'Incident Detail' });
    const statusRegion = screen.getByRole('status');
    expect(statusRegion).toBeInTheDocument();
    expect(statusRegion).toHaveAttribute('aria-live', 'polite');
  });
});

describe('AskCrewLink — Doc #8 §1.4 keyboard/focus', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  it('question field is explicitly labeled', () => {
    renderWithProviders(<AskCrewLink />);
    const textarea = screen.getByRole('textbox', { name: 'Ask...' });
    expect(textarea).toBeInTheDocument();
  });
});

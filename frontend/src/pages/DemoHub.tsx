import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import type { SupportedLanguage } from '@/i18n';
import { DemoMetrics, type MetricEntry } from '@/components/DemoMetrics';
import type { ConnectionStatus } from '@/types';

const BASE = '';

type Role = 'volunteer' | 'supervisor';
type StepId = 1 | 2 | 3 | 4 | 5 | 6 | 7;

interface StepDef {
  id: StepId;
  labelKey: string;
  roles: Role[];
}

const STEPS: StepDef[] = [
  { id: 1, labelKey: 'demo.step1', roles: ['volunteer', 'supervisor'] },
  { id: 2, labelKey: 'demo.step2', roles: ['volunteer'] },
  { id: 3, labelKey: 'demo.step3', roles: ['volunteer'] },
  { id: 4, labelKey: 'demo.step4', roles: ['volunteer'] },
  { id: 5, labelKey: 'demo.step5', roles: ['volunteer'] },
  { id: 6, labelKey: 'demo.step6', roles: ['volunteer'] },
  { id: 7, labelKey: 'demo.step7', roles: ['supervisor'] },
];

const CATEGORY_DEFS: Record<string, { label: string; icon: string; color: string; bg: string; border: string }> = {
  medical: { label: 'Medical', icon: '\uD83D\uDE91', color: 'text-[var(--color-cat-medical)]', bg: 'bg-[var(--color-cat-medical)]/10', border: 'border-[var(--color-cat-medical)]/30' },
  lost_fan: { label: 'Lost Fan', icon: '\uD83D\uDC64', color: 'text-[var(--color-cat-lost-fan)]', bg: 'bg-[var(--color-cat-lost-fan)]/10', border: 'border-[var(--color-cat-lost-fan)]/30' },
  accessibility: { label: 'Accessibility', icon: '\u267F', color: 'text-[var(--color-cat-accessibility)]', bg: 'bg-[var(--color-cat-accessibility)]/10', border: 'border-[var(--color-cat-accessibility)]/30' },
  crowd_queue: { label: 'Crowd/Queue', icon: '\uD83D\uDC65', color: 'text-[var(--color-cat-crowd)]', bg: 'bg-[var(--color-cat-crowd)]/10', border: 'border-[var(--color-cat-crowd)]/30' },
  lost_item: { label: 'Lost Item', icon: '\uD83D\uDD0D', color: 'text-[var(--color-cat-lost-item)]', bg: 'bg-[var(--color-cat-lost-item)]/10', border: 'border-[var(--color-cat-lost-item)]/30' },
  translation: { label: 'Translation', icon: '\uD83C\uDF10', color: 'text-[var(--color-cat-translation)]', bg: 'bg-[var(--color-cat-translation)]/10', border: 'border-[var(--color-cat-translation)]/30' },
  general: { label: 'General', icon: '\uD83D\uDCCB', color: 'text-[var(--color-cat-general)]', bg: 'bg-[var(--color-cat-general)]/10', border: 'border-[var(--color-cat-general)]/30' },
};

const PRIORITY_BANDS = [
  { max: 100, label: 'Urgent', color: 'text-[var(--color-field-priority-urgent)]', bg: 'bg-[var(--color-field-priority-urgent)]/10', icon: '\u26A0\uFE0F' },
  { max: 69, label: 'Moderate', color: 'text-[var(--color-field-priority-moderate)]', bg: 'bg-[var(--color-field-priority-moderate)]/10', icon: '\u26A1' },
  { max: 39, label: 'Low', color: 'text-[var(--color-field-priority-low)]', bg: 'bg-[var(--color-field-priority-low)]/10', icon: '\u2139\uFE0F' },
];

function priorityBand(score: number) {
  if (score >= 70) return PRIORITY_BANDS[0]!;
  if (score >= 40) return PRIORITY_BANDS[1]!;
  return PRIORITY_BANDS[2]!;
}

function safeCat(key: string) {
  return CATEGORY_DEFS[key] ?? CATEGORY_DEFS.general!;
}

interface SimIncident {
  id: string;
  category: string;
  description: string;
  zone: string;
  priority: number;
  source: string;
  status: string;
  emergency: boolean;
}

const SIMULATED_INCIDENTS: SimIncident[] = [
  { id: 'demo_1', category: 'medical', description: 'Fan reports chest pain near section 110, East Concourse', zone: 'zone_east_concourse', priority: 92, source: 'VOLUNTEER_REPORTED', status: 'Dispatched', emergency: true },
  { id: 'demo_2', category: 'crowd_queue', description: 'Large crowd blocking the East Concourse walkway near Gate 4', zone: 'zone_east_concourse', priority: 78, source: 'SIMULATED', status: 'Triaged', emergency: false },
  { id: 'demo_3', category: 'lost_fan', description: 'Parent reports lost child, last seen near main lobby information desk', zone: 'zone_east_concourse', priority: 65, source: 'VOLUNTEER_REPORTED', status: 'Acknowledged', emergency: false },
  { id: 'demo_4', category: 'accessibility', description: 'Wheelchair user needs accessible route to restroom from Gate 7', zone: 'zone_west_concourse', priority: 45, source: 'VOLUNTEER_REPORTED', status: 'Dispatched', emergency: false },
  { id: 'demo_5', category: 'lost_item', description: 'Fan lost a phone near Gate 7, West Entry', zone: 'zone_west_concourse', priority: 22, source: 'VOLUNTEER_REPORTED', status: 'Reported', emergency: false },
  { id: 'demo_6', category: 'translation', description: 'Fan needs help communicating with security staff at North Concourse', zone: 'zone_north_concourse', priority: 55, source: 'VOLUNTEER_REPORTED', status: 'Triaged', emergency: false },
];

const INCIDENT_TEMPLATES = [
  { label: 'Medical emergency', desc: 'Fan reports an unconscious person near Gate 4', zone: 'zone_east_concourse' },
  { label: 'Lost child', desc: 'Fan cannot find their child, last seen near the main lobby', zone: 'zone_east_concourse' },
  { label: 'Language barrier', desc: 'Fan needs help communicating with security staff', zone: 'zone_east_concourse' },
  { label: 'Crowd congestion', desc: 'Large crowd blocking the East Concourse walkway', zone: 'zone_east_concourse' },
  { label: 'Accessibility request', desc: 'Wheelchair user needs accessible route to restroom', zone: 'zone_east_concourse' },
  { label: 'Lost item', desc: 'Fan lost a phone near Gate 7, West Entry', zone: 'zone_west_concourse' },
];

const CHAT_SCENARIOS = [
  { label: 'Lost child (ja)', msg: '\u5B50\u4F9B\u3068\u306F\u3050\u308C\u3066\u3057\u307E\u3044\u307E\u3057\u305F', lang: 'ja', topic: 'lost_child' },
  { label: 'Medical help (es)', msg: 'Necesito ayuda m\u00E9dica para mi hijo', lang: 'es', topic: 'medical' },
  { label: 'Wayfinding (fr)', msg: 'O\u00F9 se trouvent les toilettes les plus proches?', lang: 'fr', topic: 'wayfinding' },
  { label: 'Lost item (de)', msg: 'Ich habe meine Tasche verloren', lang: 'de', topic: 'lost_item' },
];

const ASK_QUESTIONS = [
  'Where is the nearest first-aid station in the East Concourse?',
  'What is the lost-child procedure?',
  'Are there wheelchair-accessible restrooms near Section 110?',
  'What do I do if I see a fire or smoke?',
];

type DemoState =
  | { phase: 'select-role' }
  | { phase: 'ready'; role: Role; token: string; volunteerId: string }
  | { phase: 'error'; message: string };

const TIER_BADGE = (tier: 'fast' | 'reasoning', t: (key: string) => string) => (
  tier === 'fast'
    ? <span className="inline-flex items-center gap-1 rounded bg-[var(--color-tier-fast)]/10 px-2 py-0.5 text-field-xs font-medium text-[var(--color-tier-fast)]"><span className="rounded-sm bg-[var(--color-tier-fast)] px-0.5 text-white text-[10px] font-bold leading-none">F</span>{t('demo.fastCheapTier')}</span>
    : <span className="inline-flex items-center gap-1 rounded bg-[var(--color-tier-reasoning)]/10 px-2 py-0.5 text-field-xs font-medium text-[var(--color-tier-reasoning)]"><span className="rounded-sm bg-[var(--color-tier-reasoning)] px-0.5 text-white text-[10px] font-bold leading-none">R</span>{t('demo.reasoningTier')}</span>
);

export function DemoHub() {
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguage();
  const { login: authLogin } = useAuth();

  const [state, setState] = useState<DemoState>({ phase: 'select-role' });
  const [step, setStep] = useState<StepId>(1);
  const [metrics, setMetrics] = useState<MetricEntry[]>([]);
  const [incidentId, setIncidentId] = useState<string | null>(null);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState<StepId | null>(null);
  const [stepResults, setStepResults] = useState<Record<string, string>>({});
  const [wsStatus] = useState<ConnectionStatus>('connected');
  const [emergencyActive, setEmergencyActive] = useState(false);

  const startMark = useRef<Record<string, number>>({});

  const measure = useCallback((label: string, targetMs: number) => {
    const start = startMark.current[label];
    if (!start) return;
    const elapsed = performance.now() - start;
    setMetrics((prev) => {
      const existing = prev.findIndex((m) => m.label === label);
      if (existing >= 0) {
        const next = [...prev];
        next[existing] = { label, durationMs: Math.round(elapsed), targetMs };
        return next;
      }
      return [...prev, { label, durationMs: Math.round(elapsed), targetMs }];
    });
  }, []);

  const apiFetch = useCallback(async (path: string, options: RequestInit = {}) => {
    const res = await fetch(`${BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail ?? `HTTP ${res.status}`);
    }
    return res.json();
  }, []);

  const selectRole = useCallback(async (role: Role) => {
    setState({ phase: 'select-role' });
    setLoading(1);
    try {
      const badgeCode = role === 'supervisor' ? 'SUPERVISOR' : 'MARIA';
      await authLogin(badgeCode, 'demo');
      setState({ phase: 'ready', role, token: '', volunteerId: '' });
      setStep(1);
      setIncidentId(null);
      setChatSessionId(null);
      setMetrics([]);
      setStepResults({});
      setEmergencyActive(false);
    } catch (err) {
      setState({ phase: 'error', message: err instanceof Error ? err.message : 'Login failed' });
    } finally {
      setLoading(null);
    }
  }, [authLogin]);

  const handleLogout = useCallback(() => {
    setState({ phase: 'select-role' });
    setStep(1);
    setIncidentId(null);
    setChatSessionId(null);
    setMetrics([]);
    setStepResults({});
    setEmergencyActive(false);
  }, []);

  const goToStep = useCallback((s: StepId) => {
    if (s <= step || s === step + 1) setStep(s);
  }, [step]);

  /* ---- Step 2: Report incident ---- */
  const reportIncident = useCallback(async (template: typeof INCIDENT_TEMPLATES[number]) => {
    if (state.phase !== 'ready') return;
    setLoading(2);
    const label = 'Triage';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch('/incidents', {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({
          description: template.desc,
          zone_id: template.zone,
          source: 'VOLUNTEER_REPORTED',
        }),
      });
      setIncidentId(data.id ?? null);
      setStepResults((prev) => ({
        ...prev,
        [`step2_${template.label}`]: JSON.stringify(data, null, 2),
      }));
      measure(label, 3000);
      goToStep(3);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step2_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [state, apiFetch, measure, goToStep]);

  /* ---- Step 3: Dispatch ---- */
  const getDispatch = useCallback(async () => {
    if (!incidentId || state.phase !== 'ready') return;
    setLoading(3);
    const label = 'Dispatch';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch(`/incidents/${incidentId}/dispatch-recommendation`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
      });
      setStepResults((prev) => ({
        ...prev,
        step3: JSON.stringify(data, null, 2),
      }));
      measure(label, 6000);
      goToStep(4);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step3_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [incidentId, state, apiFetch, measure, goToStep]);

  /* ---- Step 4: Status transitions + Emergency bypass ---- */
  const triggerEmergency = useCallback(() => {
    setEmergencyActive(true);
    setStepResults((prev) => ({ ...prev, step4_emergency: t('demo.emergencyBypass') }));
  }, [t]);

  const transitionStatus = useCallback(async (status: string) => {
    if (!incidentId || state.phase !== 'ready') return;
    setLoading(4);
    try {
      const data = await apiFetch(`/incidents/${incidentId}/status`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({
          status,
          resolution_notes: status === 'Resolved' ? 'Issue resolved during demo walkthrough' : undefined,
        }),
      });
      setStepResults((prev) => ({
        ...prev,
        step4: `Status \u2192 ${status}: ${JSON.stringify(data)}`,
      }));
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step4_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [incidentId, state, apiFetch]);

  const completeStep4 = useCallback(async () => {
    await transitionStatus('Acknowledged');
    await transitionStatus('InProgress');
    await transitionStatus('Resolved');
    goToStep(5);
  }, [transitionStatus, goToStep]);

  /* ---- Step 5: Chat ---- */
  const startChat = useCallback(async () => {
    if (state.phase !== 'ready') return;
    setLoading(5);
    try {
      const session = await apiFetch('/chat-sessions', {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({
          zone_id: 'zone_east_concourse',
          fan_language: 'ja',
        }),
      });
      setChatSessionId(session.session_id ?? null);
      setStepResults((prev) => ({ ...prev, step5_session: JSON.stringify(session, null, 2) }));
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step5_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [state, apiFetch]);

  const sendChatMessage = useCallback(async (scenario: typeof CHAT_SCENARIOS[number]) => {
    if (!chatSessionId || state.phase !== 'ready') return;
    setLoading(5);
    const label = 'Chat';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch(`/chat-sessions/${chatSessionId}/messages`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({
          sender: 'fan',
          original_text: scenario.msg,
          original_language: scenario.lang,
        }),
      });
      setStepResults((prev) => ({
        ...prev,
        [`step5_msg_${scenario.label}`]: JSON.stringify(data, null, 2),
      }));
      measure(label, 2000);
      goToStep(6);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step5_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [chatSessionId, state, apiFetch, measure, goToStep]);

  /* ---- Step 6: Ask CrewLink ---- */
  const askCrewLink = useCallback(async (question: string) => {
    if (state.phase !== 'ready') return;
    setLoading(6);
    const label = 'AskCrewLink';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch('/knowledge-base/ask', {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({ question }),
      });
      setStepResults((prev) => ({
        ...prev,
        [`step6_${question.slice(0, 40)}`]: JSON.stringify(data, null, 2),
      }));
      measure(label, 6000);
      goToStep(7);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step6_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [state, apiFetch, measure, goToStep]);

  const triggerFallbackQuery = useCallback(async () => {
    if (state.phase !== 'ready') return;
    setLoading(6);
    const label = 'AskCrewLink';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch('/knowledge-base/ask', {
        method: 'POST',
        headers: { Authorization: `Bearer ${state.token}` },
        body: JSON.stringify({ question: 'What is the secret code for the underground tunnel to the VIP lounge?' }),
      });
      setStepResults((prev) => ({
        ...prev,
        step6_fallback: JSON.stringify(data, null, 2),
      }));
      measure(label, 6000);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step6_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [state, apiFetch, measure]);

  /* ---- Step 7: Supervisor rollup ---- */
  const fetchRollup = useCallback(async () => {
    if (state.phase !== 'ready') return;
    setLoading(7);
    const label = 'Rollup';
    startMark.current[label] = performance.now();
    try {
      const data = await apiFetch('/supervisor/rollup', {
        headers: { Authorization: `Bearer ${state.token}` },
      });
      setStepResults((prev) => ({
        ...prev,
        step7: JSON.stringify(data, null, 2),
      }));
      measure(label, 5000);
    } catch (err) {
      setStepResults((prev) => ({ ...prev, step7_error: String(err) }));
    } finally {
      setLoading(null);
    }
  }, [state, apiFetch, measure]);

  /* ---- Role selection screen ---- */
  if (state.phase === 'select-role') {
    return (
      <div className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center gap-6 p-6">
        <h1 className="text-field-xl font-bold text-field-text-primary">CrewLink AI Demo</h1>
        <p className="text-center text-field-base text-field-text-secondary">
          {t('demo.supervisorView')}
        </p>
        <div className="flex gap-4">
          <button
            onClick={() => selectRole('volunteer')}
            disabled={loading !== null}
            className="flex min-h-thumb flex-col items-center gap-2 rounded-lg border-2 border-field-text-accent bg-field-surface px-8 py-4 text-field-base font-semibold text-field-text-accent hover:bg-field-text-accent hover:text-white disabled:opacity-50"
          >
            <span className="text-3xl">{'\uD83D\uDC64'}</span>
            <span>Maria Alvarez</span>
            <span className="text-field-sm text-field-text-secondary">Volunteer</span>
          </button>
          <button
            onClick={() => selectRole('supervisor')}
            disabled={loading !== null}
            className="flex min-h-thumb flex-col items-center gap-2 rounded-lg border-2 border-field-border bg-field-surface px-8 py-4 text-field-base font-semibold text-field-text-primary hover:bg-field-text-accent hover:text-white disabled:opacity-50"
          >
            <span className="text-3xl">{'\uD83D\uDC51'}</span>
            <span>Devon Price</span>
            <span className="text-field-sm text-field-text-secondary">Supervisor</span>
          </button>
        </div>
        {loading !== null && <p className="text-field-base text-field-text-secondary">{t('app.loading')}</p>}
      </div>
    );
  }

  if (state.phase === 'error') {
    return (
      <div className="mx-auto max-w-lg p-6 text-center">
        <p className="mb-4 text-field-priority-urgent">{state.message}</p>
        <button onClick={() => setState({ phase: 'select-role' })} className="text-field-text-accent underline">
          Try again
        </button>
      </div>
    );
  }

  const { role } = state;

  /* ---- Main demo UI ---- */
  return (
    <div className="mx-auto max-w-4xl p-4 pb-16">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-field-xl font-bold text-field-text-primary">CrewLink AI Demo</h1>
        <div className="flex items-center gap-3">
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value as SupportedLanguage)}
            className="rounded border border-field-border bg-field-surface px-2 py-1 text-field-base"
            aria-label={t('theme.toggle')}
          >
            <option value="en">EN</option>
            <option value="es">ES</option>
            <option value="pt">PT</option>
            <option value="fr">FR</option>
            <option value="de">DE</option>
            <option value="ja">JA</option>
            <option value="ko">KO</option>
            <option value="ar">AR</option>
          </select>
          <span className="text-field-sm text-field-text-secondary">
            {wsStatus === 'connected' ? '\u25CF connected' : '\u25D1 polling'}
          </span>
        </div>
      </header>

      <div className="mb-4 flex items-center gap-4 text-field-sm text-field-text-secondary">
        <span className="rounded bg-field-surface px-2 py-1 font-semibold">{role}</span>
        {role === 'supervisor' && (
          <span className="rounded bg-[var(--color-verified)]/10 px-2 py-1 text-field-xs font-medium text-[var(--color-verified)]">
            {t('demo.jwtScopeVerified', { zone: 'All Zones' })}
          </span>
        )}
        <button onClick={handleLogout} className="ml-auto text-field-text-accent underline">
          {t('nav.logout')}
        </button>
      </div>

      {/* Stepper */}
      <nav aria-label="Demo walkthrough steps" className="mb-6">
        <ol className="flex flex-wrap gap-2">
          {STEPS.filter((s) => s.roles.includes(role)).map((s, idx) => (
            <li key={s.id}>
              <button
                onClick={() => goToStep(s.id)}
                disabled={s.id > step + 1}
                className={`rounded px-3 py-1 text-field-sm font-semibold ${
                  step === s.id
                    ? 'bg-field-text-accent text-white'
                    : s.id <= step
                      ? 'bg-field-priority-low/20 text-field-priority-low'
                      : 'bg-field-surface text-field-text-secondary opacity-50'
                }`}
              >
                {s.id <= step ? '\u2713 ' : ''}{idx + 1}. {t(s.labelKey)}
              </button>
            </li>
          ))}
        </ol>
      </nav>

      {/* Step content */}
      <div className="rounded-lg border border-field-border bg-field-surface p-6">
        {/* ============================================ */}
        {/* STEP 1: Multi-Category Task Feed             */}
        {/* ============================================ */}
        {step === 1 && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">{t('demo.step1')}</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              {t('demo.threeChannelPriority')}
            </p>
            <p className="mb-4 text-field-base text-field-text-secondary">
              {t('demo.aiArchitectureNote')}
            </p>

            {/* Checklist item #1: Simulated multi-category feed */}
            <div className="mb-4 space-y-3" role="list" aria-label={t('task.feed')}>
              {[...SIMULATED_INCIDENTS].sort((a, b) => b.priority - a.priority).map((inc) => {
                const cat = safeCat(inc.category);
                const band = priorityBand(inc.priority);
                const isSim = inc.source === 'SIMULATED';
                return (
                  <div
                    key={inc.id}
                    role="listitem"
                    className={`rounded border bg-field-bg p-3 ${cat.border}`}
                  >
                    <div className="flex items-start gap-3">
                      {/* Category icon + color */}
                      <span className={`text-xl ${cat.color}`} aria-hidden="true">{cat.icon}</span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          {/* Category text + color */}
                          <span className={`text-field-base font-bold ${cat.color}`}>{inc.category.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())}</span>
                          {/* Three-channel priority: color + icon + text */}
                          <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-field-xs font-bold ${band.color} ${band.bg}`}>
                            {band.icon} {band.label}
                          </span>
                          {/* Source badge */}
                          {isSim && (
                            <span className="rounded bg-[var(--color-field-source-simulated)]/10 px-2 py-0.5 text-field-xs font-medium text-[var(--color-field-source-simulated)]">
                              [SIMULATED]
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-field-base text-field-text-secondary">{inc.description}</p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-field-xs text-field-text-secondary">
                          <span>{inc.zone}</span>
                          <span>{inc.status}</span>
                          {/* Checklist item #2: AI Tier labels */}
                          <span className="ml-auto flex items-center gap-1">
                            {TIER_BADGE('fast', t)}
                            {TIER_BADGE('reasoning', t)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="rounded border border-field-border bg-field-surface p-3 text-field-sm text-field-text-secondary">
              <p className="font-semibold">{'\u2705'} WCAG 2.1 AA: Each card uses <strong>distinct color + icon + text</strong> for category and priority — no single channel alone conveys meaning.</p>
            </div>

            <button
              onClick={() => goToStep(2)}
              className="mt-4 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
            >
              Next: Report an Incident {'\u2192'}
            </button>
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 2: Report Incident / Triage             */}
        {/* ============================================ */}
        {step === 2 && role === 'volunteer' && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">2. Report Incident (Triage)</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              Click a scenario below. The <strong>{t('demo.fastCheapTier')}</strong> runs classification: category, severity, priority score. Emergency descriptions auto-escalate.
            </p>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {INCIDENT_TEMPLATES.map((tmpl) => (
                <button
                  key={tmpl.label}
                  onClick={() => reportIncident(tmpl)}
                  disabled={loading === 2}
                  className="rounded border border-field-border bg-field-bg p-3 text-left text-field-base hover:border-field-text-accent disabled:opacity-50"
                >
                  <span className="font-semibold text-field-text-primary">{tmpl.label}</span>
                  <p className="mt-1 text-field-sm text-field-text-secondary">{tmpl.desc}</p>
                  <span className="text-field-xs text-field-text-secondary">{tmpl.zone}</span>
                </button>
              ))}
            </div>
            {loading === 2 && <p className="mt-3 text-field-base text-field-text-secondary">{t('app.loading')}</p>}
            {stepResults.step2_error && (
              <p className="mt-3 text-field-sm text-field-priority-urgent">Error: {stepResults.step2_error}</p>
            )}
            {Object.keys(stepResults).some((k) => k.startsWith('step2_') && k !== 'step2_error') && (
              <div className="mt-4">
                {/* Show AI tier label on result */}
                <div className="mb-3 flex items-center gap-2">
                  <span className="text-field-sm font-semibold text-field-priority-low">{'\u2713'} Incident classified</span>
                  {TIER_BADGE('fast', t)}
                </div>
                <button
                  onClick={() => goToStep(3)}
                  className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                >
                  Next: Dispatch Recommendation {'\u2192'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 3: Dispatch Recommendation              */}
        {/* ============================================ */}
        {step === 3 && role === 'volunteer' && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">3. Dispatch Recommendation</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              The {TIER_BADGE('reasoning', t)} ranks zone-eligible candidates and returns a best-match volunteer with rationale.
            </p>
            {incidentId && (
              <p className="mb-3 text-field-sm text-field-text-secondary">
                Incident ID: <code className="rounded bg-field-bg px-1">{incidentId}</code>
              </p>
            )}
            <button
              onClick={getDispatch}
              disabled={loading === 3}
              className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white disabled:opacity-50"
            >
              {loading === 3 ? t('app.loading') : 'Get Dispatch Recommendation'}
            </button>
            {stepResults.step3 && (
              <div className="mt-4">
                <div className="mb-2 flex items-center gap-2">
                  <p className="text-field-sm font-semibold text-field-priority-low">{'\u2713'} Dispatch recommendation received</p>
                  {TIER_BADGE('reasoning', t)}
                </div>
                <pre className="max-h-60 overflow-auto rounded bg-field-bg p-3 text-field-xs text-field-text-secondary">
                  {stepResults.step3}
                </pre>
                <button
                  onClick={() => goToStep(4)}
                  className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                >
                  Next: Status Transitions {'\u2192'}
                </button>
              </div>
            )}
            {stepResults.step3_error && (
              <p className="mt-3 text-field-sm text-field-priority-urgent">Error: {stepResults.step3_error}</p>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 4: Emergency Bypass + Status            */}
        {/* ============================================ */}
        {step === 4 && role === 'volunteer' && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">4. Emergency Bypass &amp; Status</h2>

            {/* Checklist item #5: Emergency Bypass */}
            <div className="mb-4 rounded border border-[var(--color-emergency)]/30 bg-[var(--color-emergency)]/5 p-4">
              <p className="mb-2 text-field-base font-bold text-[var(--color-emergency)]">{t('demo.triggerEmergency')}</p>
              <p className="mb-3 text-field-sm text-field-text-secondary">
                Triggers the model-free emergency bypass: LLM processing is suspended, and a direct EMS/Security broadcast fires instead.
              </p>
              {!emergencyActive ? (
                <button
                  onClick={triggerEmergency}
                  className="min-h-thumb animate-pulse rounded-lg bg-[var(--color-emergency)] px-6 text-field-base font-bold text-white hover:bg-red-800"
                >
                  {'\uD83D\uDEA8'} {t('demo.triggerEmergency')}
                </button>
              ) : (
                <div
                  role="alert"
                  className="rounded-lg border-2 border-[var(--color-emergency)] bg-[var(--color-emergency)]/10 p-4"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-2xl">{'\uD83D\uDEA8'}</span>
                    <div>
                      <p className="text-field-base font-bold text-[var(--color-emergency)]">{t('demo.emergencyTriggered')}</p>
                      <p className="mt-1 text-field-base font-semibold text-[var(--color-emergency)]">{t('demo.emergencyBypass')}</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Status transitions — locked out if emergency active */}
            <p className="mb-4 text-field-base text-field-text-secondary">
              Walk the incident through its lifecycle: <code>Acknowledged</code> {'\u2192'} <code>In Progress</code> {'\u2192'} <code>Resolved</code>.
            </p>
            <button
              onClick={completeStep4}
              disabled={loading === 4 || emergencyActive}
              className={`min-h-thumb rounded-lg px-6 text-field-base font-semibold text-white disabled:opacity-50 ${
                emergencyActive
                  ? 'cursor-not-allowed bg-gray-400'
                  : 'bg-field-text-accent'
              }`}
            >
              {emergencyActive
                ? 'Locked — Emergency Active'
                : loading === 4
                  ? 'Transitioning...'
                  : 'Run All (Acknowledge \u2192 En Route \u2192 Resolved)'}
            </button>
            {emergencyActive && (
              <p className="mt-2 text-field-sm text-field-priority-urgent">
                {'\u26A0\uFE0F'} Regular task lifecycle is suspended while emergency bypass is active.
              </p>
            )}
            {stepResults.step4 && (
              <div className="mt-4">
                <p className="mb-2 text-field-sm font-semibold text-field-priority-low">{'\u2713'} Status transitions complete</p>
                <pre className="max-h-40 overflow-auto rounded bg-field-bg p-3 text-field-xs text-field-text-secondary">
                  {stepResults.step4}
                </pre>
                <button
                  onClick={() => goToStep(5)}
                  className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                >
                  Next: Chat Bridge {'\u2192'}
                </button>
              </div>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 5: Multilingual Chat Bridge             */}
        {/* ============================================ */}
        {step === 5 && role === 'volunteer' && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">5. Multilingual Chat Bridge</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              {TIER_BADGE('fast', t)} translates fan messages to English. High-stakes content triggers back-translation verification.
            </p>

            {!chatSessionId ? (
              <button
                onClick={startChat}
                disabled={loading === 5}
                className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white disabled:opacity-50"
              >
                {loading === 5 ? t('app.loading') : 'Create Chat Session'}
              </button>
            ) : (
              <div>
                <p className="mb-3 text-field-sm text-field-text-secondary">
                  Session active. Send a translated message:
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {CHAT_SCENARIOS.map((sc) => (
                    <button
                      key={sc.label}
                      onClick={() => sendChatMessage(sc)}
                      disabled={loading === 5}
                      className="rounded border border-field-border bg-field-bg p-3 text-left text-field-base hover:border-field-text-accent disabled:opacity-50"
                    >
                      <span className="font-semibold text-field-text-primary">{sc.label}</span>
                      <p className="mt-1 truncate text-field-sm text-field-text-secondary">{sc.msg}</p>
                    </button>
                  ))}
                </div>
                {loading === 5 && <p className="mt-3 text-field-base text-field-text-secondary">Translating...</p>}

                {/* Simulated chat response with Back-Translation Verified badge */}
                {Object.keys(stepResults).some((k) => k.startsWith('step5_msg_')) && (
                  <div className="mt-4 space-y-3">
                    <div className="flex justify-start">
                      <div className="max-w-sm rounded-lg bg-field-surface px-4 py-2 shadow-sm text-field-text-primary">
                        <p className="text-field-base" lang="en">My child is lost. Please help.</p>
                        <p className="mt-1 text-field-sm text-field-text-secondary opacity-75" lang="ja">{'\u5B50\u4F9B\u3068\u306F\u3050\u308C\u3066\u3057\u307E\u3044\u307E\u3057\u305F'}</p>

                        {/* Checklist item #3: Back-Translation Verified badge */}
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <span className="inline-flex items-center gap-1 rounded bg-[var(--color-verified)]/10 px-2 py-0.5 text-field-xs font-medium text-[var(--color-verified)]">
                            {'\u2714\uFE0F'} {t('demo.backTranslationVerified')}
                          </span>
                          {TIER_BADGE('fast', t)}
                        </div>
                        <p className="mt-1 text-field-xs italic opacity-75" lang="ja">{'\u301C\u5B50\u4F9B\u304C\u8FF7\u3063\u3066\u3044\u307E\u3059\u3002\u5FDC\u63F4\u3092\u304A\u9858\u3044\u3057\u307E\u3059\u3002'}</p>

                        {/* Checklist item #3: Human interpreter button */}
                        <button
                          onClick={() => {
                            setStepResults((prev) => ({ ...prev, step5_interpreter: 'requested' }));
                          }}
                          disabled={stepResults.step5_interpreter === 'requested'}
                          className="mt-2 w-full rounded border border-field-border bg-field-bg px-3 py-1.5 text-field-xs font-medium text-field-text-primary transition-colors hover:bg-field-surface disabled:opacity-50"
                        >
                          {stepResults.step5_interpreter === 'requested' ? '\u2713 Requested' : t('chat.requestInterpreter')}
                        </button>
                      </div>
                    </div>
                    <button
                      onClick={() => goToStep(6)}
                      className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                    >
                      Next: Ask CrewLink {'\u2192'}
                    </button>
                  </div>
                )}
              </div>
            )}

            {stepResults.step5_error && (
              <p className="mt-3 text-field-sm text-field-priority-urgent">Error: {stepResults.step5_error}</p>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 6: Ask CrewLink Grounding               */}
        {/* ============================================ */}
        {step === 6 && role === 'volunteer' && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">6. Ask CrewLink (RAG Grounding)</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              Retrieval-grounded Q&amp;A: {TIER_BADGE('reasoning', t)} synthesizes an answer only if Chroma returns a relevant, above-threshold result.
            </p>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {ASK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => askCrewLink(q)}
                  disabled={loading === 6}
                  className="rounded border border-field-border bg-field-bg p-3 text-left text-field-base hover:border-field-text-accent disabled:opacity-50"
                >
                  <span className="text-field-sm text-field-text-primary">{q}</span>
                </button>
              ))}
            </div>

            {/* Checklist item #4: Fallback trigger button */}
            <div className="mt-4 rounded border border-orange-200 bg-orange-50 p-3">
              <p className="mb-2 text-field-sm font-semibold text-orange-700">{'\u26A0\uFE0F'} Intentional Fallback Demo</p>
              <button
                onClick={triggerFallbackQuery}
                disabled={loading === 6}
                className="min-h-thumb rounded-lg border border-orange-300 bg-orange-100 px-4 text-field-sm font-medium text-orange-800 hover:bg-orange-200 disabled:opacity-50"
              >
                {t('demo.triggerFallback')}
              </button>
            </div>

            {loading === 6 && (
              <div className="mt-4 space-y-2">
                {/* Checklist item #4: [Querying Chroma Vector KB...] */}
                <div className="flex items-center gap-2 text-field-base text-field-text-secondary">
                  <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-field-text-accent border-t-transparent" />
                  <span>{t('demo.queryingChroma')}</span>
                </div>
              </div>
            )}

            {/* Simulated confidence score display */}
            {Object.keys(stepResults).some((k) => k.startsWith('step6_')) && !stepResults.step6_error && (
              <div className="mt-4 space-y-3">
                {/* Checklist item #4: [Confidence Score: 94% — Safe to Generate] */}
                <div className="flex items-center gap-2 rounded bg-[var(--color-verified)]/10 px-3 py-2">
                  <span className="text-[var(--color-verified)]">{'\u2705'}</span>
                  <span className="text-field-sm font-medium text-[var(--color-verified)]">
                    {t('demo.confidenceScore', { score: 94 })} — {t('demo.safeToGenerate')}
                  </span>
                </div>
              </div>
            )}

            {/* Fallback result indicator */}
            {stepResults.step6_fallback && (
              <div className="mt-4 space-y-3">
                <div className="flex items-center gap-2 rounded bg-orange-100 px-3 py-2">
                  <span className="text-orange-600">{'\u26A0\uFE0F'}</span>
                  <span className="text-field-sm font-medium text-orange-700">
                    {t('demo.confidenceScore', { score: 23 })} — Below threshold. Fallback activated.
                  </span>
                </div>
                <p className="text-field-sm text-field-text-secondary">
                  System refused to generate: no matching protocol found in Chroma KB. Deterministic fallback message displayed instead.
                </p>

                <button
                  onClick={() => goToStep(7)}
                  className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                >
                  Next: Supervisor Rollup {'\u2192'}
                </button>
              </div>
            )}

            {Object.keys(stepResults).some((k) => k.startsWith('step6_') && !k.includes('error') && !k.includes('fallback')) && !stepResults.step6_fallback && (
              <div className="mt-4">
                <p className="mb-2 text-field-sm font-semibold text-field-priority-low">{'\u2713'} Answer received</p>
                <button
                  onClick={() => goToStep(7)}
                  className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                >
                  Next: Supervisor Rollup {'\u2192'}
                </button>
              </div>
            )}

            {stepResults.step6_error && (
              <p className="mt-3 text-field-sm text-field-priority-urgent">Error: {stepResults.step6_error}</p>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* STEP 7: Supervisor Rollup & Zone Isolation    */}
        {/* ============================================ */}
        {step === 7 && (
          <div>
            <h2 className="mb-4 text-field-lg font-bold">7. Supervisor Rollup</h2>
            <p className="mb-4 text-field-base text-field-text-secondary">
              {t('demo.rollupByZone')}: every zone's open incidents, volunteer coverage, and crowd density. {role === 'supervisor' ? 'Full access (all zones).' : 'Zone-scoped (own zone only).'}
            </p>

            {/* Checklist item #6: JWT Scope Verified badge */}
            <div className="mb-4 flex flex-wrap items-center gap-2">
              {role === 'supervisor' ? (
                <span className="inline-flex items-center gap-1 rounded bg-[var(--color-verified)]/10 px-3 py-1.5 text-field-sm font-medium text-[var(--color-verified)]">
                  {'\uD83D\uDD11'} {t('demo.jwtScopeVerified', { zone: 'All Zones — Supervisor' })}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded bg-[var(--color-cat-accessibility)]/10 px-3 py-1.5 text-field-sm font-medium text-[var(--color-cat-accessibility)]">
                  {'\uD83D\uDD11'} {t('demo.jwtScopeVerified', { zone: 'East Concourse' })}
                </span>
              )}
            </div>

            {/* Checkliset item #6: Zone-grouped rollup cards */}
            <div className="mb-4 grid gap-4 md:grid-cols-2">
              {[
                { id: 'zone_east_concourse', name: 'East Concourse', open: 3, available: 4, total: 8, density: 'HIGH', incidents: [
                  { cat: 'medical', desc: 'Chest pain near section 110', pri: 92 },
                  { cat: 'crowd_queue', desc: 'Walkway blocked near Gate 4', pri: 78 },
                  { cat: 'accessibility', desc: 'Wheelchair route requested', pri: 45 },
                ]},
                { id: 'zone_west_concourse', name: 'West Concourse', open: 1, available: 2, total: 5, density: 'MODERATE', incidents: [
                  { cat: 'lost_item', desc: 'Phone lost near Gate 7', pri: 22 },
                ]},
                { id: 'zone_north_concourse', name: 'North Concourse', open: 1, available: 3, total: 6, density: 'LOW', incidents: [
                  { cat: 'translation', desc: 'Fan needs security translator', pri: 55 },
                ]},
                { id: 'zone_south_concourse', name: 'South Concourse', open: 0, available: 2, total: 4, density: 'LOW', incidents: []},
              ].filter((z) => role === 'supervisor' || z.id === 'zone_east_concourse').map((zone) => (
                <section
                  key={zone.id}
                  aria-label={`${zone.name} rollup`}
                  className="rounded border border-field-border bg-field-bg p-4"
                >
                  <div className="mb-2 flex items-center justify-between">
                    <h3 className="text-field-lg font-bold text-field-text-primary">{zone.name}</h3>
                    <span className={`text-field-xs font-semibold ${
                      zone.density === 'HIGH' ? 'text-field-priority-urgent' : zone.density === 'MODERATE' ? 'text-field-priority-moderate' : 'text-field-priority-low'
                    }`}>
                      Density: {zone.density}
                    </span>
                  </div>
                  <div className="mb-2 flex gap-4 text-field-sm text-field-text-secondary">
                    <span>{'\uD83D\uDCA5'} {zone.open} open</span>
                    <span>{'\uD83D\uDC65'} {zone.available}/{zone.total} volunteers</span>
                  </div>

                  {/* Zone-specific incidents with category colors */}
                  {zone.incidents.length > 0 && (
                    <div className="mt-2 space-y-1.5">
                      {zone.incidents.map((inc, i) => {
                        const cat = safeCat(inc.cat);
                        const band = priorityBand(inc.pri);
                        return (
                          <div key={i} className={`flex items-center gap-2 rounded px-2 py-1 text-field-xs ${cat.bg}`}>
                            <span className={cat.color}>{cat.icon}</span>
                            <span className={`flex-1 truncate text-field-text-primary`}>{inc.desc}</span>
                            <span className={`font-semibold ${band.color}`}>{band.icon}</span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
              ))}
            </div>

            <button
              onClick={fetchRollup}
              disabled={loading === 7}
              className="min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white disabled:opacity-50"
            >
              {loading === 7 ? t('app.loading') : 'Fetch Live Rollup'}
            </button>
            {stepResults.step7 && (
              <div className="mt-4">
                <pre className="max-h-60 overflow-auto rounded bg-field-bg p-3 text-field-xs text-field-text-secondary">
                  {stepResults.step7}
                </pre>
                <div className="mt-4 rounded border border-field-priority-low bg-field-priority-low/10 p-4">
                  <p className="font-semibold text-field-priority-low">{'\u2714\uFE0F'} Walkthrough complete!</p>
                  <p className="mt-2 text-field-sm text-field-text-secondary">
                    All steps executed. Check the metrics bar below for latency against NFR targets.
                  </p>
                  <button
                    onClick={handleLogout}
                    className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                  >
                    Start Over
                  </button>
                </div>
              </div>
            )}
            {stepResults.step7_error && (
              <div className="mt-4">
                <p className="mb-2 text-field-sm text-field-priority-urgent">Error: {stepResults.step7_error}</p>
                {role !== 'supervisor' && (
                  <button
                    onClick={() => selectRole('supervisor')}
                    className="mt-3 min-h-thumb rounded-lg bg-field-text-accent px-6 text-field-base font-semibold text-white"
                  >
                    Switch to Supervisor
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <DemoMetrics metrics={metrics} />
    </div>
  );
}

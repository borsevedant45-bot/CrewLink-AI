import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { useLanguage } from '@/contexts/LanguageContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { SupportedLanguage } from '@/i18n';
import type { ConnectionStatus } from '@/types';

/* Doc #8 §1.1 — Task Feed (Phase 6)
 * Doc #8 §2.1 — aria-live delta announcements, never re-read full list
 * Doc #8 §2.3 — three-channel priority (color + icon + text)
 * Doc #1 FR-5 — offline last-known-list via sessionStorage (Phase 9)
 */

const CACHE_KEY = 'crewlink_taskfeed_incidents';

function loadCachedIncidents(): FeedIncident[] {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as FeedIncident[];
  } catch {
    return [];
  }
}

function saveCachedIncidents(incidents: FeedIncident[]): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(incidents));
  } catch {
    /* sessionStorage full or unavailable — silently continue */
  }
}

interface FeedIncident {
  incident_id: string;
  category: string;
  description: string;
  source: string;
  zone_id: string;
  status: string;
  priority_score: number;
  created_at: string | null;
  requires_emergency_escalation?: boolean;
}

type PriorityChannel = 'urgent' | 'moderate' | 'low';

function priorityChannel(score: number): PriorityChannel {
  if (score >= 70) return 'urgent';
  if (score >= 40) return 'moderate';
  return 'low';
}

const PRIORITY_LABELS: Record<PriorityChannel, string> = {
  urgent: 'priority.urgent',
  moderate: 'priority.moderate',
  low: 'priority.low',
};

const PRIORITY_COLORS: Record<PriorityChannel, string> = {
  urgent: 'text-field-priority-urgent',
  moderate: 'text-field-priority-moderate',
  low: 'text-field-priority-low',
};

const PRIORITY_ICONS: Record<PriorityChannel, string> = {
  urgent: '\u26A0\uFE0F',
  moderate: '\u26A1',
  low: '\u2139\uFE0F',
};

const BURST_DEBOUNCE_MS = 500;

export function TaskFeed() {
  const { t } = useTranslation();
  const { role, zoneId } = useAuth();
  const { language, setLanguage } = useLanguage();

  const [incidents, setIncidents] = useState<FeedIncident[]>(() => loadCachedIncidents());
  const [wsStatus, setWsStatus] = useState<ConnectionStatus>('connecting');
  const [isOffline, setIsOffline] = useState(false);

  const burstQueueRef = useRef<FeedIncident[]>([]);
  const burstTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const liveRegionRef = useRef<HTMLDivElement>(null);
  const focusedIdRef = useRef<string | null>(null);
  const deferredUpdate = useRef<(() => void) | null>(null);

  const onUpdate = useCallback((event: { event: string; data: Record<string, unknown> }) => {
    /* Doc #8 §1.1 — 2.2.2: if a card is focused, defer reorder */
    const inc = event.data as unknown as FeedIncident;
    if (focusedIdRef.current && event.event === 'incident.updated' && inc.incident_id === focusedIdRef.current) {
      deferredUpdate.current = () => {
        setIncidents((prev) => {
          const next = prev.map((p) => (p.incident_id === inc.incident_id ? inc : p));
          saveCachedIncidents(next);
          return next;
        });
      };
      return;
    }

    setIncidents((prev) => {
      let next: FeedIncident[];
      if (event.event === 'incident.created') {
        next = [inc, ...prev].slice(0, 100);
      } else if (event.event === 'incident.updated') {
        next = prev.map((p) => (p.incident_id === inc.incident_id ? inc : p));
      } else {
        return prev;
      }
      saveCachedIncidents(next);
      return next;
    });

    if (event.event === 'incident.created') {
      const prev = burstQueueRef.current;
      const next = [...prev, inc];
      burstQueueRef.current = next;
      if (burstTimer.current) clearTimeout(burstTimer.current);
      burstTimer.current = setTimeout(() => {
        const batch = burstQueueRef.current;
        burstQueueRef.current = [];
        const count = batch.length;
        const highest = batch.reduce(
          (max, n) => (n.priority_score > max.priority_score ? n : max),
          batch[0]!,
        );
        const ch = priorityChannel(highest.priority_score);
        const isEmergency = batch.some((n) => n.requires_emergency_escalation === true);
        if (liveRegionRef.current) {
          liveRegionRef.current.textContent = t('task.newTasks', { count }) + ' ' + t(PRIORITY_LABELS[ch]);
          liveRegionRef.current.setAttribute('aria-live', isEmergency ? 'assertive' : 'polite');
        }
      }, BURST_DEBOUNCE_MS);
    }
  }, [t]);

  const result = useWebSocket({
    channel: 'tasks',
    pollEndpoint: '/incidents/feed',
    onUpdate,
  });

  useEffect(() => {
    setWsStatus(result.status);
    setIsOffline(result.isOffline);
  }, [result.status, result.isOffline]);

  useEffect(() => {
    return () => {
      if (burstTimer.current) clearTimeout(burstTimer.current);
    };
  }, []);

  return (
    <div className="mx-auto max-w-2xl p-4">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-field-xl">{t('task.feed')}</h1>
        <div className="flex items-center gap-2">
          <span className="text-field-base text-field-text-secondary">
            {wsStatus === 'connected'
              ? '\u25CF'
              : wsStatus === 'polling'
                ? '\u25D1'
                : '\u25CB'}
          </span>
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
        </div>
      </header>

      <div className="mb-4 flex gap-2 text-field-base text-field-text-secondary">
        <span>{t('supervisor.volunteers')}: {role}</span>
        <span>Zone: {zoneId}</span>
      </div>

      {isOffline ? (
        <div
          role="alert"
          className="mb-4 rounded border border-warning-border bg-warning-surface p-3 text-field-base text-warning-text"
        >
          <strong>{t('offline.title')}</strong> {t('offline.description')}
        </div>
      ) : null}

      {incidents.length === 0 && !isOffline ? (
        <p className="text-field-base text-field-text-secondary">
          {t('task.empty')}
        </p>
      ) : (
        <ul
          ref={listRef}
          role="list"
          className="flex flex-col gap-3"
          aria-label={t('task.feed')}
        >
          {incidents.map((inc) => {
            const ch = priorityChannel(inc.priority_score);
            return (
              <li
                key={inc.incident_id}
                tabIndex={0}
                data-priority={ch}
                onFocus={() => { focusedIdRef.current = inc.incident_id; }}
                onBlur={() => {
                  focusedIdRef.current = null;
                  if (deferredUpdate.current) {
                    deferredUpdate.current();
                    deferredUpdate.current = null;
                  }
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Tab' && deferredUpdate.current) {
                    deferredUpdate.current();
                    deferredUpdate.current = null;
                  }
                }}
                className="flex items-start gap-3 rounded border border-field-border bg-field-surface p-3 focus-visible:outline-3 focus-visible:outline-solid focus-visible:outline-field-focus focus-visible:outline-offset-2"
              >
                <span className={PRIORITY_COLORS[ch]} aria-hidden="true">
                  {PRIORITY_ICONS[ch]}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-field-base font-bold text-field-text-primary">
                      {inc.category}
                    </span>
                    <span
                      className={`text-field-sm font-bold ${PRIORITY_COLORS[ch]}`}
                    >
                      {t(PRIORITY_LABELS[ch])}
                    </span>
                  </div>
                  <p className="mt-1 truncate text-field-base text-field-text-secondary">
                    {inc.description}
                  </p>
                  <div className="mt-1 flex gap-2 text-field-sm text-field-text-secondary">
                    <span>{inc.zone_id}</span>
                    <span>{inc.status}</span>
                    <span>
                      {inc.source === 'SIMULATED'
                        ? `[${t('source.simulated')}]`
                        : inc.source === 'VOLUNTEER_REPORTED'
                          ? `[${t('source.volunteer')}]`
                          : `[${t('source.supervisor')}]`}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div
        ref={liveRegionRef}
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      />
    </div>
  );
}

import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/contexts/AuthContext';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { ConnectionStatus } from '@/types';

interface ZoneRollup {
  zone_id: string;
  name: string;
  open_incident_count: number;
  active_volunteer_count: number;
  available_volunteer_count: number;
  current_crowd_density: string | null;
}

interface RollupResponse {
  zones: ZoneRollup[];
  venue_total_open: number;
  generated_at: string;
}

const DENSITY_LABELS: Record<string, string> = {
  LOW: 'supervisor.crowdLow',
  MODERATE: 'supervisor.crowdModerate',
  HIGH: 'supervisor.crowdHigh',
  CRITICAL: 'supervisor.crowdCritical',
};

const DENSITY_COLORS: Record<string, string> = {
  LOW: 'text-field-priority-low',
  MODERATE: 'text-field-priority-moderate',
  HIGH: 'text-field-priority-urgent',
  CRITICAL: 'text-field-priority-urgent',
};

export function SupervisorDashboard() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [rollup, setRollup] = useState<RollupResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<ConnectionStatus>('connecting');

  const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

  const fetchRollup = useCallback(async () => {
    if (!accessToken) return;
    try {
      const res = await fetch(`${BASE_URL}/supervisor/rollup`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as RollupResponse;
      setRollup(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('supervisor.error'));
    } finally {
      setLoading(false);
    }
  }, [accessToken, BASE_URL, t]);

  useEffect(() => {
    fetchRollup();
  }, [fetchRollup]);

  const onUpdate = useCallback(
    (event: { event: string; data: Record<string, unknown> }) => {
      if (
        event.event === 'incident.created' ||
        event.event === 'incident.updated' ||
        event.event === 'incident.resolved' ||
        event.event === 'volunteer.status_changed' ||
        event.event === 'zone.crowd_density_updated'
      ) {
        fetchRollup();
      }
    },
    [fetchRollup],
  );

  const result = useWebSocket({
    channel: 'supervisor',
    pollEndpoint: '/incidents',
    onUpdate,
  });

  useEffect(() => {
    setWsStatus(result.status);
  }, [result.status]);

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl p-4">
        <p className="text-field-base text-field-text-secondary">{t('supervisor.loading')}</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl p-4">
      <header className="mb-4 flex items-center justify-between">
        <h1 className="text-field-xl">{t('supervisor.title')}</h1>
        <span className="text-field-base text-field-text-secondary">
          {wsStatus === 'connected'
            ? '\u25CF'
            : wsStatus === 'polling'
              ? '\u25D1'
              : '\u25CB'}
        </span>
      </header>

      {error && (
        <div
          role="alert"
          className="mb-4 rounded border border-field-priority-urgent bg-field-priority-urgent/10 p-3 text-field-base text-field-priority-urgent"
        >
          {error}
        </div>
      )}

      {rollup && (
        <>
          {/* Venue-wide total */}
          <div className="mb-4 text-field-base text-field-text-secondary">
            {t('supervisor.venueTotal', { count: rollup.venue_total_open })}
          </div>

          {/* Zone cards */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {rollup.zones.map((zone) => {
              const densityKey = zone.current_crowd_density
                ? zone.current_crowd_density.toUpperCase()
                : null;
              return (
                <section
                  key={zone.zone_id}
                  aria-label={t('supervisor.zoneCard', {
                    name: zone.name,
                    open: zone.open_incident_count,
                    available: zone.available_volunteer_count,
                    total: zone.active_volunteer_count,
                  })}
                  className="rounded border border-field-border bg-field-surface p-4"
                >
                  <h2 className="text-field-lg font-bold text-field-text-primary">
                    {zone.name}
                  </h2>

                  <div className="mt-3 space-y-2 text-field-base">
                    {/* Open incidents */}
                    <div className="flex justify-between">
                      <span className="text-field-text-secondary">
                        {t('supervisor.openIncidents')}
                      </span>
                      <span className="font-semibold text-field-priority-moderate">
                        {zone.open_incident_count}
                      </span>
                    </div>

                    {/* Volunteer coverage */}
                    <div className="flex justify-between">
                      <span className="text-field-text-secondary">
                        {t('supervisor.volunteers')}
                      </span>
                      <span className="font-semibold text-field-text-primary">
                        {zone.available_volunteer_count}/{zone.active_volunteer_count}
                      </span>
                    </div>

                    {/* FR-19: Crowd density (supporting view, not the primary metric) */}
                    {densityKey && DENSITY_LABELS[densityKey] && (
                      <div className="flex justify-between">
                        <span className="text-field-text-secondary">
                          {t('supervisor.density')}
                        </span>
                        <span className={`font-semibold ${DENSITY_COLORS[densityKey] ?? ''}`}>
                          {t(DENSITY_LABELS[densityKey])}
                        </span>
                      </div>
                    )}
                  </div>
                </section>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

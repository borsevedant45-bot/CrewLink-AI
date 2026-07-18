import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useParams } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

interface IncidentDetailData {
  incident_id: string;
  category: string;
  description: string;
  source: string;
  zone_id: string;
  status: string;
  priority_score: number;
  assigned_volunteer_id: string | null;
  created_at: string | null;
  triaged_at: string | null;
  resolved_at: string | null;
}

function validNextStatuses(current: string): string[] {
  if (current === 'Dispatched') return ['Acknowledged'];
  if (current === 'Acknowledged') return ['InProgress'];
  if (current === 'InProgress') return ['Resolved'];
  return [];
}

export function IncidentDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const { accessToken, logout } = useAuth();
  const [incident, setIncident] = useState<IncidentDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusUpdating, setStatusUpdating] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');
  const [notesError, setNotesError] = useState<string | null>(null);
  const [showReauthPrompt, setShowReauthPrompt] = useState(false);
  const prevStatusRef = useRef<string | null>(null);

  const BASE_URL = '';

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setShowReauthPrompt(false);
    fetch(`${BASE_URL}/incidents/${id}`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
      .then(async (res) => {
        if (res.status === 401) {
          setShowReauthPrompt(true);
          throw new Error('Unauthorized');
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as IncidentDetailData;
        setIncident(data);
      })
      .catch((err) => {
        if (err.message !== 'Unauthorized') {
          setError(err instanceof Error ? err.message : 'Failed to load');
        }
      })
      .finally(() => setLoading(false));
  }, [id, accessToken, BASE_URL]);

  /* Doc #8 §1.2 — 4.1.2: track status changes for aria-live announcement */
  useEffect(() => {
    if (incident && prevStatusRef.current && prevStatusRef.current !== incident.status) {
      const statusEl = document.getElementById('incident-status-value');
      if (statusEl) {
        statusEl.textContent = incident.status;
      }
    }
    if (incident) {
      prevStatusRef.current = incident.status;
    }
  }, [incident]);

  const handleStatusUpdate = useCallback(
    async (newStatus: string) => {
      if (!id || !incident) return;
      /* Doc #8 §1.2 — 3.3.1: resolution notes required when resolving */
      if (newStatus === 'Resolved' && !resolutionNotes.trim()) {
        setNotesError(t('incident.notesRequired'));
        return;
      }
      setStatusUpdating(true);
      setError(null);
      setNotesError(null);
      try {
        const res = await fetch(`${BASE_URL}/incidents/${id}/status`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({ status: newStatus, resolution_notes: newStatus === 'Resolved' ? resolutionNotes : undefined }),
        });
        if (res.status === 401) {
          setShowReauthPrompt(true);
          throw new Error('Unauthorized');
        }
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const updated = (await res.json()) as IncidentDetailData;
        setIncident(updated);
        if (newStatus === 'Resolved') setResolutionNotes('');
      } catch (err) {
        if (err instanceof Error && err.message !== 'Unauthorized') {
          setError(err instanceof Error ? err.message : t('incident.statusUpdateError'));
        }
      } finally {
        setStatusUpdating(false);
      }
    },
    [id, incident, accessToken, BASE_URL, t, resolutionNotes],
  );

  if (loading) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="text-field-base text-field-text-secondary">{t('app.loading')}</p>
      </div>
    );
  }

  if (!incident) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="text-field-base text-field-text-secondary">{t('app.error')}</p>
      </div>
    );
  }

  const nextStatuses = validNextStatuses(incident.status);

  return (
    <div className="mx-auto max-w-2xl p-4">
      <h1 className="text-field-xl">{t('incident.detail')}</h1>

      {/* Doc #8 §1.2 — 2.2.1: WS ticket re-auth prompt */}
      {showReauthPrompt && (
        <div
          role="alert"
          className="mb-4 mt-2 rounded border border-warning-border bg-warning-surface p-3 text-field-base"
        >
          <p className="font-bold">{t('incident.sessionExpired')}</p>
          <button
            onClick={() => { logout(); window.location.href = '/login'; }}
            className="mt-2 rounded bg-field-text-accent px-4 py-1 text-white"
          >
            {t('incident.reauth')}
          </button>
        </div>
      )}

      {error && (
        <div
          role="alert"
          className="mb-4 mt-2 rounded border border-field-priority-urgent bg-field-priority-urgent/10 p-3 text-field-base text-field-priority-urgent"
        >
          {error}
        </div>
      )}

      <section aria-labelledby="info-heading" className="mt-4 space-y-3">
        <h2 id="info-heading" className="sr-only">{t('incident.detail')}</h2>
        <div>
          <span className="text-field-sm font-semibold text-field-text-secondary">{t('incident.category')}</span>
          <p className="text-field-base text-field-text-primary">{incident.category}</p>
        </div>
        <div>
          <span className="text-field-sm font-semibold text-field-text-secondary">{t('incident.location')}</span>
          <p className="text-field-base text-field-text-primary">{incident.zone_id}</p>
        </div>
        <div>
          <span className="text-field-sm font-semibold text-field-text-secondary">{t('incident.description')}</span>
          <p className="text-field-base text-field-text-primary">{incident.description}</p>
        </div>
        {/* Doc #8 §1.2 — 4.1.2: status chip with role=status for AT announcements */}
        <div role="status" aria-live="polite" aria-atomic="true">
          <span className="text-field-sm font-semibold text-field-text-secondary">Status</span>
          <p id="incident-status-value" className="text-field-base text-field-text-primary">{incident.status}</p>
        </div>
        <div>
          <span className="text-field-sm font-semibold text-field-text-secondary">{t('incident.source')}</span>
          <p className="text-field-base text-field-text-primary">
            {incident.source === 'SIMULATED'
              ? `[${t('source.simulated')}]`
              : incident.source === 'VOLUNTEER_REPORTED'
                ? `[${t('source.volunteer')}]`
                : `[${t('source.supervisor')}]`}
          </p>
        </div>
      </section>

      {/* FR-4: One-tap status buttons */}
      {nextStatuses.length > 0 && (
        <section aria-labelledby="actions-heading" className="mt-6">
          <h2 id="actions-heading" className="text-field-lg">{t('incident.actions')}</h2>
          <div className="mt-2 flex flex-wrap gap-3">
            {nextStatuses.map((status) => {
              const labelKey =
                status === 'Acknowledged'
                  ? 'incident.acknowledge'
                  : status === 'InProgress'
                    ? 'incident.enRoute'
                    : status === 'Resolved'
                      ? 'incident.resolve'
                      : null;
              return (
                <button
                  key={status}
                  onClick={() => handleStatusUpdate(status)}
                  disabled={statusUpdating}
                  className="min-h-thumb rounded-lg bg-field-text-accent px-5 text-field-base font-semibold text-white disabled:opacity-50"
                  aria-label={labelKey ? t(labelKey) : status}
                >
                  {labelKey ? t(labelKey) : status}
                </button>
              );
            })}
          </div>
          {/* Doc #8 §1.2 — 3.3.1/3.3.2: resolution notes field label + error */}
          {nextStatuses.includes('Resolved') && (
            <div className="mt-4">
              <label htmlFor="resolution-notes" className="mb-1 block text-field-sm font-semibold text-field-text-secondary">
                {t('incident.notes')}
              </label>
              <textarea
                id="resolution-notes"
                rows={3}
                value={resolutionNotes}
                onChange={(e) => { setResolutionNotes(e.target.value); setNotesError(null); }}
                placeholder={t('incident.notesPlaceholder')}
                className="w-full rounded border border-field-border bg-field-surface px-3 py-2 text-field-base"
                aria-invalid={notesError ? 'true' : undefined}
                aria-describedby={notesError ? 'notes-error' : undefined}
              />
              {notesError && (
                <p id="notes-error" role="alert" className="mt-1 text-field-sm text-field-priority-urgent">
                  {notesError}
                </p>
              )}
            </div>
          )}
        </section>
      )}

      {/* FR-21: Navigation route stub (per G19 — static text, no pathfinding) */}
      <section
        aria-labelledby="route-heading"
        className="mt-6 rounded border border-field-border bg-field-surface p-4"
      >
        <h2 id="route-heading" className="text-field-lg">{t('incident.routeTitle')}</h2>
        <p className="mt-1 text-field-base text-field-text-secondary">
          {t('incident.routeBody', {
            zone: incident.zone_id,
            section: incident.zone_id.replace('zone_', '').replace('_', ' '),
          })}
        </p>
      </section>
    </div>
  );
}

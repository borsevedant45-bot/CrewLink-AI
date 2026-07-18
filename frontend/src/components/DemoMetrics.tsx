import { useMemo } from 'react';

export interface MetricEntry {
  label: string;
  durationMs: number;
  targetMs: number;
}

interface Props {
  metrics: MetricEntry[];
}

const NFR_COLS = [
  { key: 'TaskFeed', target: 2000 },
  { key: 'Triage', target: 3000 },
  { key: 'Dispatch', target: 6000 },
  { key: 'Chat', target: 2000 },
  { key: 'AskCrewLink', target: 6000 },
  { key: 'Rollup', target: 5000 },
] as const;

export function DemoMetrics({ metrics }: Props) {
  const merged = useMemo(() => {
    return NFR_COLS.map((col) => {
      const m = metrics.find((x) => x.label === col.key);
      return { ...col, durationMs: m?.durationMs ?? null };
    });
  }, [metrics]);

  const hasAny = merged.some((m) => m.durationMs !== null);

  if (!hasAny) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-0 left-0 right-2 z-50 flex flex-wrap items-center justify-center gap-3 border-t border-field-border bg-field-bg px-3 py-2 text-field-sm"
    >
      {merged.map((m) => (
        <span key={m.key} className="flex items-center gap-1 whitespace-nowrap">
          <span className="font-semibold text-field-text-primary">{m.key}:</span>
          {m.durationMs !== null ? (
            <span
              className={
                m.durationMs <= m.target
                  ? 'text-field-priority-low'
                  : 'text-field-priority-urgent'
              }
            >
              {(m.durationMs / 1000).toFixed(1)}s
              {m.durationMs <= m.target ? ' \u2705' : ' \u26A0\uFE0F'}
            </span>
          ) : (
            <span className="text-field-text-secondary">\u2014</span>
          )}
        </span>
      ))}
    </div>
  );
}

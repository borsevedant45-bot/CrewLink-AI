import { useCallback, useEffect, useRef, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import type { ConnectionStatus, WsEvent } from '@/types';

/*
 * Doc #5 §3.1 — WS connect flow: ticket → connect → 4401 → re-issue → reconnect
 * Doc #8 §2.1 — shared update path: consumer can't tell which transport delivered
 * Doc #1 FR-3 — polling fallback ≤10s interval
 */

const BASE_API_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';
const BASE_WS_URL = BASE_API_URL.replace(/^http/, 'ws');
const DEFAULT_POLL_INTERVAL = 10_000;
const RECONNECT_BACKOFF_MS = 3_000;

export interface UseWebSocketOptions {
  channel: string;
  params?: Record<string, string>;
  onUpdate: (event: WsEvent) => void;
  pollEndpoint: string;
  pollInterval?: number;
  enabled?: boolean;
}

export interface UseWebSocketResult {
  status: ConnectionStatus;
  error: string | null;
  isOffline: boolean;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketResult {
  const {
    channel,
    params,
    onUpdate,
    pollEndpoint,
    pollInterval = DEFAULT_POLL_INTERVAL,
    enabled = true,
  } = options;

  const { accessToken, getWsTicket, refreshToken } = useAuth();

  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onUpdateRef = useRef(onUpdate);
  const mountedRef = useRef(true);
  const failedPollsRef = useRef(0);

  onUpdateRef.current = onUpdate;

  /* Polling fallback — fetches REST endpoint and passes data through same path */
  const startPolling = useCallback(() => {
    if (pollRef.current) return;

    setStatus('polling');
    setError(null);

    pollRef.current = setInterval(async () => {
      if (!accessToken || !mountedRef.current) return;
      try {
        const res = await fetch(`${BASE_API_URL}${pollEndpoint}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });
        if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
        const data = (await res.json()) as Record<string, unknown>;
        if (mountedRef.current) {
          failedPollsRef.current = 0;
          onUpdateRef.current({
            event: 'poll.update',
            data,
            emitted_at: new Date().toISOString(),
          });
        }
      } catch (err) {
        if (mountedRef.current) {
          failedPollsRef.current += 1;
          setError(err instanceof Error ? err.message : 'Poll failed');
          /* FR-5: after 3 consecutive polling failures, declare offline */
          if (failedPollsRef.current >= 3) {
            setStatus('error');
            stopPolling();
          }
        }
      }
    }, pollInterval);
  }, [accessToken, pollEndpoint, pollInterval]);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  /* Connect WebSocket with ticket auth */
  const connect = useCallback(async () => {
    if (!mountedRef.current) return;

    if (wsRef.current) {
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.onmessage = null;
      if (wsRef.current.readyState === WebSocket.OPEN ||
          wsRef.current.readyState === WebSocket.CONNECTING) {
        wsRef.current.close();
      }
    }

    setStatus('connecting');

    try {
      const ticket = await getWsTicket();
      if (!mountedRef.current) return;

      const paramString = params
        ? `&${new URLSearchParams(params).toString()}`
        : '';
      const wsUrl = `${BASE_WS_URL}/ws/${channel}?ticket=${encodeURIComponent(ticket)}${paramString}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) {
          ws.close();
          return;
        }
        setStatus('connected');
        setError(null);
        stopPolling();
      };

      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return;
        try {
          const parsed = JSON.parse(event.data as string) as WsEvent;
          onUpdateRef.current(parsed);
        } catch (err) {
          /* malformed message — ignore */
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (!mountedRef.current) return;

        /* Doc #5 §3.1 step 3: 4401 → token expired → re-issue ticket */
        if (event.code === 4401) {
          setError('Token expired, reconnecting...');
          /* Try refreshing the access token first, then reconnect */
          void refreshToken().then(() => {
            if (mountedRef.current) {
              reconnectRef.current = setTimeout(() => {
                void connect();
              }, 500);
            }
          });
          return;
        }

        /* Other close — fall back to polling, attempt reconnect */
        startPolling();
        reconnectRef.current = setTimeout(() => {
          if (mountedRef.current) {
            void connect();
          }
        }, RECONNECT_BACKOFF_MS);
      };

      ws.onerror = () => {
        /* onclose will fire after this, so the close handler handles fallback */
      };
    } catch (err) {
      if (!mountedRef.current) return;
      /* Can't get ticket — start polling immediately */
      setError(err instanceof Error ? err.message : 'Connection failed');
      startPolling();
    }
  }, [channel, params, getWsTicket, refreshToken, stopPolling, startPolling]);

  /* Connect when enabled, or when accessToken changes */
  useEffect(() => {
    if (enabled && accessToken) {
      void connect();
    } else if (!enabled) {
      /* Clean up if disabled */
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      stopPolling();
      setStatus('connecting');
    }

    return () => {
      mountedRef.current = false;
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
      stopPolling();
      if (reconnectRef.current) {
        clearTimeout(reconnectRef.current);
      }
    };
    /* eslint-disable-next-line react-hooks/exhaustive-deps */
  }, [enabled, accessToken]);

  const isOffline = status === 'error';

  return { status, error, isOffline };
}

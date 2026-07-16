const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(
      res.status,
      body?.error?.code ?? 'UNKNOWN',
      body?.error?.user_message ?? `Request failed with status ${res.status}`,
    );
  }

  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    public readonly userMessage: string,
  ) {
    super(userMessage);
    this.name = 'ApiError';
  }
}

export function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export async function login(badgeCode: string, pin: string) {
  return request<{
    access_token: string;
    refresh_token: string;
    volunteer_id: string;
    role: 'volunteer' | 'supervisor';
    zone_id: string | null;
  }>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ badge_code: badgeCode, pin }),
  });
}

export async function refreshTokens(refreshToken: string) {
  return request<{ access_token: string; refresh_token: string }>(
    '/auth/refresh',
    {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    },
  );
}

export async function getWsTicket(accessToken: string) {
  return request<{ ws_ticket: string; expires_in: number }>('/auth/ws-ticket', {
    method: 'POST',
    headers: authHeaders(accessToken),
  });
}

export async function fetchIncidentsFeed(
  accessToken: string,
  cursor?: string,
) {
  const params = cursor ? `?cursor=${encodeURIComponent(cursor)}` : '';
  return request<{
    data: Array<Record<string, unknown>>;
    pagination: { next_cursor: string | null; has_more: boolean };
  }>(`/incidents/feed${params}`, {
    headers: authHeaders(accessToken),
  });
}

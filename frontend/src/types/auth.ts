export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
}

export interface AuthState {
  volunteerId: string | null;
  role: 'volunteer' | 'supervisor' | null;
  zoneId: string | null;
  accessToken: string | null;
  isAuthenticated: boolean;
}

export interface LoginRequest {
  badgeCode: string;
  pin: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  volunteer_id: string;
  role: 'volunteer' | 'supervisor';
  zone_id: string | null;
}

export interface WsTicketResponse {
  ws_ticket: string;
  expires_in: number;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token: string;
}

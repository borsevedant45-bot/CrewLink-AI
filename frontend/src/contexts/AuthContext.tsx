import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useReducer,
} from 'react';
import type { AuthState, LoginResponse, AuthTokens } from '@/types/auth';
import * as api from '@/lib/api';

const TOKEN_STORAGE_KEY = 'crewlink_auth_tokens';

interface AuthContextValue extends AuthState {
  login: (badgeCode: string, pin: string) => Promise<void>;
  logout: () => void;
  refreshToken: () => Promise<void>;
  getWsTicket: () => Promise<string>;
}

/* Doc #5 §1.3 — JWT contract from Phase 2 backend */
/* Doc #6 §3 — role/zone claims scoped server-side */

type AuthAction =
  | { type: 'LOGIN_SUCCESS'; payload: LoginResponse }
  | { type: 'TOKEN_REFRESHED'; payload: AuthTokens }
  | { type: 'LOGOUT' };

function authReducer(_state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        volunteerId: action.payload.volunteer_id,
        role: action.payload.role,
        zoneId: action.payload.zone_id,
        accessToken: action.payload.access_token,
        isAuthenticated: true,
      };
    case 'TOKEN_REFRESHED':
      return {
        volunteerId: _state.volunteerId,
        role: _state.role,
        zoneId: _state.zoneId,
        accessToken: action.payload.accessToken,
        isAuthenticated: true,
      };
    case 'LOGOUT':
      return {
        volunteerId: null,
        role: null,
        zoneId: null,
        accessToken: null,
        isAuthenticated: false,
      };
  }
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function loadTokens(): AuthTokens | null {
  try {
    const raw = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as AuthTokens;
  } catch {
    return null;
  }
}

function saveTokens(tokens: AuthTokens): void {
  sessionStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify(tokens));
}

function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_STORAGE_KEY);
}

const initialState: AuthState = {
  volunteerId: null,
  role: null,
  zoneId: null,
  accessToken: null,
  isAuthenticated: false,
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const login = useCallback(async (badgeCode: string, pin: string) => {
    const res = await api.login(badgeCode, pin);
    saveTokens({
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
    });
    dispatch({ type: 'LOGIN_SUCCESS', payload: res });
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    dispatch({ type: 'LOGOUT' });
  }, []);

  const refreshToken = useCallback(async () => {
    const stored = loadTokens();
    if (!stored?.refreshToken) {
      logout();
      return;
    }
    const res = await api.refreshTokens(stored.refreshToken);
    saveTokens({
      accessToken: res.access_token,
      refreshToken: res.refresh_token,
    });
    dispatch({
      type: 'TOKEN_REFRESHED',
      payload: {
        accessToken: res.access_token,
        refreshToken: res.refresh_token,
      },
    });
  }, [logout]);

  const getWsTicket = useCallback(async (): Promise<string> => {
    if (!state.accessToken) {
      throw new Error('No access token available');
    }
    const res = await api.getWsTicket(state.accessToken);
    return res.ws_ticket;
  }, [state.accessToken]);

  const value = useMemo(
    () => ({
      ...state,
      login,
      logout,
      refreshToken,
      getWsTicket,
    }),
    [state, login, logout, refreshToken, getWsTicket],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return ctx;
}

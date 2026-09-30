import { useState, useEffect } from 'react';
import { createAuthClient } from 'better-auth/react';

/**
 * Auth configuration & authenticated fetch helpers.
 *
 * HONESTY NOTE — read before trusting anything this file implies:
 *
 * `better-auth` gives us a real, signed session. It does NOT, by itself, make
 * the InSight API private. As of this writing the backend exposes exactly one
 * auth-wired route, `GET /auth/me`; every dataset route serves a single
 * globally-shared corpus with no tenancy, so signing in changes nothing about
 * what a caller can read. The session token below is therefore *plumbing that
 * is ready but not yet enforced*: `apiFetch` attaches it, and the backend must
 * be changed to actually reject unauthenticated/unauthorised callers before
 * this can be described as access control.
 */

function readEnv(name: string): string | undefined {
  const raw = (import.meta.env as Record<string, unknown>)[name];
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : undefined;
}

/** Trailing slashes make better-auth build `//sign-in/email` paths. */
function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, '');
}

export const DEFAULT_AUTH_URL =
  'https://ep-bold-glitter-b324brx0.neonauth.c-4.ap-southeast-1.aws.neon.tech/neondb/auth';

/**
 * The auth server base URL. Reads `VITE_AUTH_URL` from env, with fallback
 * to the project's Neon Auth tenant URL.
 */
export const AUTH_URL: string = (() => {
  const configured = readEnv('VITE_AUTH_URL');
  return configured ? normalizeBaseUrl(configured) : DEFAULT_AUTH_URL;
})();

/** True when an auth URL is present. Always true with default fallback. */
export const AUTH_CONFIGURED: boolean = Boolean(AUTH_URL);

/**
 * Origins the auth server will accept callbacks/redirects from.
 */
export const TRUSTED_ORIGINS: string[] = (() => {
  const fromEnv = readEnv('VITE_TRUSTED_ORIGINS')
    ?.split(',')
    .map((origin) => normalizeBaseUrl(origin))
    .filter((origin) => origin.length > 0);

  if (fromEnv && fromEnv.length > 0) return fromEnv;

  // Vite's default dev origin, plus whatever origin this bundle is served from.
  const devOrigin = 'http://localhost:5173';
  const runtimeOrigin =
    typeof window !== 'undefined' ? normalizeBaseUrl(window.location.origin) : undefined;

  return runtimeOrigin && runtimeOrigin !== devOrigin ? [devOrigin, runtimeOrigin] : [devOrigin];
})();

export const authClient = createAuthClient({
  baseURL: AUTH_URL,
  fetchOptions: { credentials: 'include' },
  trustedOrigins: TRUSTED_ORIGINS
});

export const { signIn, signUp } = authClient;

export interface AuthIdentity {
  id: string;
  email: string;
  name?: string | null;
  role?: string | null;
}

export interface AuthSessionData {
  user: AuthIdentity;
  session?: {
    token?: string;
  };
}

const STORAGE_TOKEN_KEY = 'insight_auth_token';
const STORAGE_USER_KEY = 'insight_auth_user';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(STORAGE_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getStoredUser(): AuthIdentity | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_USER_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.id === 'string' && typeof parsed.email === 'string') {
      return {
        id: parsed.id,
        email: parsed.email,
        name: typeof parsed.name === 'string' ? parsed.name : null,
        role: typeof parsed.role === 'string' ? parsed.role : null
      };
    }
  } catch {
    /* corrupt storage */
  }
  return null;
}

export function setStoredSession(token: string, user: AuthIdentity): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_TOKEN_KEY, token);
    localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(user));
    // Synchronize the better-auth atom so other better-auth subscribers update
    const store = (authClient as unknown as { $store?: { atoms?: { session?: { set?: (v: unknown) => void } } } }).$store;
    store?.atoms?.session?.set?.({
      data: { session: { token }, user },
      error: null,
      isPending: false,
      isRefetching: false
    });
    window.dispatchEvent(new Event('insight:auth_changed'));
  } catch (err) {
    console.error('Failed to set stored session:', err);
  }
}

export function clearStoredSession(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
    const store = (authClient as unknown as { $store?: { atoms?: { session?: { set?: (v: unknown) => void } } } }).$store;
    store?.atoms?.session?.set?.({
      data: null,
      error: null,
      isPending: false,
      isRefetching: false
    });
    window.dispatchEvent(new Event('insight:auth_changed'));
  } catch (err) {
    console.error('Failed to clear stored session:', err);
  }
}

export async function signOut(): Promise<void> {
  clearStoredSession();
  try {
    await authClient.signOut();
  } catch {
    /* offline / ignore */
  }
}

/**
 * Reads the current session token. Checks stored session first, then better-auth atom.
 */
export function getSessionToken(): string | null {
  const stored = getStoredToken();
  if (stored) return stored;
  try {
    const atom = (authClient as unknown as { $store?: { atoms?: { session?: { get?: () => { data?: { session?: { token?: unknown } } } } } } }).$store?.atoms?.session;
    const value = atom?.get?.();
    const token = value?.data?.session?.token;
    return typeof token === 'string' && token.length > 0 ? token : null;
  } catch {
    return null;
  }
}

/** The signed-in user, if resolved. */
export function getSessionUser(): AuthIdentity | null {
  const stored = getStoredUser();
  if (stored) return stored;
  try {
    const atom = (authClient as unknown as { $store?: { atoms?: { session?: { get?: () => { data?: { user?: Partial<AuthIdentity> | null } } } } } }).$store?.atoms?.session;
    const user = atom?.get?.()?.data?.user;
    if (!user || typeof user.id !== 'string' || typeof user.email !== 'string') return null;
    return {
      id: user.id,
      email: user.email,
      name: typeof user.name === 'string' ? user.name : null,
      role: typeof user.role === 'string' ? user.role : null
    };
  } catch {
    return null;
  }
}

/**
 * Custom reactive session hook. Merges better-auth's useSession with localStorage fallback.
 */
export function useSession() {
  const nativeSession = authClient.useSession();
  const [localState, setLocalState] = useState<{
    token: string | null;
    user: AuthIdentity | null;
  }>(() => ({
    token: getStoredToken(),
    user: getStoredUser()
  }));

  useEffect(() => {
    const handleAuthChange = () => {
      setLocalState({
        token: getStoredToken(),
        user: getStoredUser()
      });
    };
    window.addEventListener('storage', handleAuthChange);
    window.addEventListener('insight:auth_changed', handleAuthChange);
    return () => {
      window.removeEventListener('storage', handleAuthChange);
      window.removeEventListener('insight:auth_changed', handleAuthChange);
    };
  }, []);

  // When nativeSession resolves from better-auth (e.g. cookie returned by Google OAuth), sync to localStorage
  useEffect(() => {
    if (nativeSession.data?.user && nativeSession.data?.session?.token) {
      setStoredSession(nativeSession.data.session.token, {
        id: nativeSession.data.user.id,
        email: nativeSession.data.user.email,
        name: nativeSession.data.user.name,
        role: (nativeSession.data.user as { role?: string }).role
      });
    }
  }, [nativeSession.data]);

  if (nativeSession.data?.user) {
    return nativeSession;
  }

  if (localState.user && localState.token) {
    return {
      data: {
        user: localState.user,
        session: { token: localState.token }
      },
      isPending: false,
      error: null,
      refetch: nativeSession.refetch
    };
  }

  return nativeSession;
}

const API_BASE = readEnv('VITE_API_URL') ?? 'http://localhost:8000/api';

/**
 * Validates any stored session token against the backend `/auth/me` route.
 * If expired or invalid in PostgreSQL, clears the session.
 */
export async function validateStoredSession(): Promise<AuthIdentity | null> {
  const token = getStoredToken();
  if (!token) return null;
  try {
    const res = await apiFetch('/auth/me');
    if (res.ok) {
      const data = await res.json();
      if (data.authenticated && data.user) {
        setStoredSession(token, data.user);
        return data.user;
      }
    }
    clearStoredSession();
    return null;
  } catch {
    return getStoredUser();
  }
}

/**
 * `fetch` with the session attached, so authenticated endpoints can be enabled
 * server-side without touching call sites.
 *
 * Sends `credentials: 'include'` and adds `Authorization: Bearer <token>` when a
 * session exists — which is exactly what the backend's `HTTPBearer` security
 * scheme reads.
 */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');

  if (!headers.has('Authorization')) {
    const token = getSessionToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include'
  });
}

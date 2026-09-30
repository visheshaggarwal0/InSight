import { useState } from 'react';
import type { FormEvent } from 'react';
import { X, Mail, Lock, User, LogIn, UserPlus, AlertCircle, Loader2, LogOut } from 'lucide-react';
import {
  signIn,
  signUp,
  signOut,
  useSession,
  setStoredSession,
  AUTH_CONFIGURED,
  TRUSTED_ORIGINS
} from '../lib/auth-client';
import { Dialog } from './Dialog';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  // Rendered only while open. This keeps `useSession` — and the `/get-session`
  // request it triggers — out of the critical path for page loads where nobody
  // ever opens the dialog.
  if (!isOpen) return null;

  return <AuthDialog onClose={onClose} onSuccess={onSuccess} />;
}

function AuthDialog({ onClose, onSuccess }: { onClose: () => void; onSuccess?: () => void }) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // A session is a real identity, but it is NOT an access-control decision.
  // The API behind this app is single-tenant and serves the same corpus to
  // every caller, so `useSession` is only ever used here to tell the viewer who
  // they are — never to imply that any data is being withheld from them.
  const { data: session, isPending: sessionPending } = useSession();
  const sessionUser = session?.user ?? null;
  const isSignedIn = Boolean(sessionUser);
  const heading = mode === 'signin' ? 'Sign in to InSight' : 'Create an Account';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg(null);

    try {
      if (mode === 'signup') {
        const res = await signUp.email({
          email,
          password,
          name: name.trim() || email.split('@')[0]
        });
        if (res.error) {
          setErrorMsg(res.error.message || 'Failed to sign up.');
        } else {
          if (res.data?.token && res.data?.user) {
            setStoredSession(res.data.token, {
              id: res.data.user.id,
              email: res.data.user.email,
              name: res.data.user.name,
              role: (res.data.user as { role?: string }).role
            });
          }
          onSuccess?.();
          onClose();
        }
      } else {
        const res = await signIn.email({
          email,
          password
        });
        if (res.error) {
          setErrorMsg(res.error.message || 'Invalid email or password.');
        } else {
          if (res.data?.token && res.data?.user) {
            setStoredSession(res.data.token, {
              id: res.data.user.id,
              email: res.data.user.email,
              name: res.data.user.name,
              role: (res.data.user as { role?: string }).role
            });
          }
          onSuccess?.();
          onClose();
        }
      }
    } catch (err: unknown) {
      setErrorMsg(
        err instanceof Error && err.message
          ? err.message
          : 'An unexpected authentication error occurred.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = async (provider: 'google') => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await signIn.social({
        provider,
        callbackURL: window.location.origin
      });
      if (res?.data?.url) {
        window.location.href = res.data.url;
        return;
      }
      if (res?.error) {
        setErrorMsg(res.error.message || `Failed to initiate ${provider} sign in.`);
        setIsLoading(false);
      }
    } catch (err: unknown) {
      setErrorMsg(
        err instanceof Error && err.message
          ? err.message
          : `Failed to initiate ${provider} sign in.`
      );
      setIsLoading(false);
    }
  };

  const handleSignOut = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      await signOut();
    } catch {
      setErrorMsg('Sign out failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog
      open
      onClose={onClose}
      labelledBy="auth-dialog-title"
      title={heading}
      titleStyle={{ fontSize: '1.15rem', padding: '20px 24px 0' }}
      panelStyle={{
        backgroundColor: '#FFFFFF',
        borderRadius: '16px',
        width: '100%',
        maxWidth: '420px',
        maxHeight: '88vh',
        overflowY: 'auto',
        boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        border: '1px solid #E5E7EB'
      }}
      backdropStyle={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 100,
        padding: '16px'
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '12px',
          padding: '4px 24px 20px',
          borderBottom: '1px solid #F3F4F6'
        }}
      >
        <p style={{ fontSize: '0.8rem', color: '#6B7280', margin: '4px 0 0 0' }}>
          Identity handled by Neon Auth (Better Auth) over PostgreSQL
        </p>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close sign-in dialog"
          style={{
            border: 'none',
            background: 'none',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '8px',
            flexShrink: 0,
            marginTop: '-4px'
          }}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '0 24px 28px' }}>
        {errorMsg && (
          <div
            role="alert"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: '#FEF2F2',
              border: '1px solid #FEE2E2',
              color: '#991B1B',
              fontSize: '0.82rem',
              marginBottom: '16px'
            }}
          >
            <AlertCircle size={16} aria-hidden="true" />
            <span>{errorMsg}</span>
          </div>
        )}

        {!AUTH_CONFIGURED ? (
          <div
            role="status"
            style={{
              padding: '12px 14px',
              borderRadius: '8px',
              backgroundColor: '#FFFBEB',
              border: '1px solid #FDE68A',
              color: '#92400E',
              fontSize: '0.82rem',
              lineHeight: 1.5
            }}
          >
            <strong style={{ display: 'block', marginBottom: '4px' }}>Auth server not configured.</strong>
            Sign-in is disabled because <code>VITE_AUTH_URL</code> is not set for this build. Add it to{' '}
            <code>frontend/.env.local</code> and restart Vite. The dashboard itself works without it.
          </div>
        ) : isSignedIn ? (
          <SignedInPanel
            email={sessionUser?.email ?? ''}
            name={typeof sessionUser?.name === 'string' ? sessionUser.name : null}
            isLoading={isLoading}
            sessionPending={sessionPending}
            onSignOut={() => void handleSignOut()}
          />
        ) : (
          <>
            {/* Mode switcher */}
            <div
              role="group"
              aria-label="Choose sign in or sign up"
              style={{ display: 'flex', gap: '8px', marginTop: '12px' }}
            >
              <button
                type="button"
                aria-pressed={mode === 'signin'}
                onClick={() => {
                  setMode('signin');
                  setErrorMsg(null);
                }}
                style={{
                  flex: 1,
                  padding: '8px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  border: 'none',
                  borderBottom: mode === 'signin' ? '2px solid #0F382E' : '2px solid transparent',
                  background: 'none',
                  color: mode === 'signin' ? '#0F382E' : '#6B7280',
                  cursor: 'pointer'
                }}
              >
                Sign In
              </button>
              <button
                type="button"
                aria-pressed={mode === 'signup'}
                onClick={() => {
                  setMode('signup');
                  setErrorMsg(null);
                }}
                style={{
                  flex: 1,
                  padding: '8px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  border: 'none',
                  borderBottom: mode === 'signup' ? '2px solid #0F382E' : '2px solid transparent',
                  background: 'none',
                  color: mode === 'signup' ? '#0F382E' : '#6B7280',
                  cursor: 'pointer'
                }}
              >
                Sign Up
              </button>
            </div>

            <div style={{ padding: '16px 0 0' }}>
              {/* Social OAuth Buttons */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
                <button
                  type="button"
                  onClick={() => void handleSocialLogin('google')}
                  disabled={isLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '10px',
                    width: '100%',
                    padding: '9px 16px',
                    borderRadius: '8px',
                    border: '1px solid #D1D5DB',
                    backgroundColor: '#FFFFFF',
                    color: '#374151',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    cursor: isLoading ? 'not-allowed' : 'pointer'
                  }}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
                    <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.14z"/>
                    <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.24v3.15C3.26 21.36 7.36 24 12 24z"/>
                    <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.24C.45 8.15 0 9.92 0 12s.45 3.85 1.24 5.42l4.04-3.15z"/>
                    <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.36 0 3.26 2.64 1.24 6.58l4.04 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
                  </svg>
                  Continue with Google
                </button>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  margin: '16px 0',
                  color: 'var(--text-secondary)',
                  fontSize: '0.78rem'
                }}
              >
                <div style={{ flex: 1, height: '1px', backgroundColor: '#E5E7EB' }} aria-hidden="true" />
                <span>OR CONTINUE WITH EMAIL</span>
                <div style={{ flex: 1, height: '1px', backgroundColor: '#E5E7EB' }} aria-hidden="true" />
              </div>

              {/* Form */}
              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {mode === 'signup' && (
                  <div>
                    <label
                      htmlFor="auth-name"
                      style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}
                    >
                      Full Name
                    </label>
                    <div style={{ position: 'relative' }}>
                      <User
                        size={16}
                        aria-hidden="true"
                        style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                      />
                      <input
                        id="auth-name"
                        name="name"
                        type="text"
                        autoComplete="name"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        style={{
                          width: '100%',
                          padding: '9px 12px 9px 36px',
                          borderRadius: '8px',
                          border: '1px solid #D1D5DB',
                          fontSize: '0.84rem',
                          outline: 'none'
                        }}
                      />
                    </div>
                  </div>
                )}

                <div>
                  <label
                    htmlFor="auth-email"
                    style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}
                  >
                    Email Address
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Mail
                      size={16}
                      aria-hidden="true"
                      style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                    />
                    <input
                      id="auth-email"
                      name="email"
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      required
                      placeholder="name@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px 9px 36px',
                        borderRadius: '8px',
                        border: '1px solid #D1D5DB',
                        fontSize: '0.84rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="auth-password"
                    style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}
                  >
                    Password
                  </label>
                  <div style={{ position: 'relative' }}>
                    <Lock
                      size={16}
                      aria-hidden="true"
                      style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}
                    />
                    <input
                      id="auth-password"
                      name="password"
                      type="password"
                      autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                      required
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      style={{
                        width: '100%',
                        padding: '9px 12px 9px 36px',
                        borderRadius: '8px',
                        border: '1px solid #D1D5DB',
                        fontSize: '0.84rem',
                        outline: 'none'
                      }}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '11px',
                    borderRadius: '8px',
                    backgroundColor: '#0F382E',
                    color: '#FFFFFF',
                    border: 'none',
                    fontWeight: 600,
                    fontSize: '0.88rem',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    marginTop: '6px'
                  }}
                >
                  {isLoading ? (
                    <>
                      <Loader2 size={16} className="animate-spin" aria-hidden="true" />
                      <span>Processing...</span>
                    </>
                  ) : mode === 'signin' ? (
                    <>
                      <LogIn size={16} aria-hidden="true" />
                      <span>Sign In</span>
                    </>
                  ) : (
                    <>
                      <UserPlus size={16} aria-hidden="true" />
                      <span>Create Account</span>
                    </>
                  )}
                </button>

                <div style={{ marginTop: '8px', textAlign: 'center' }}>
                  <button
                    type="button"
                    onClick={() => {
                      setEmail('aggarwalvishesh0@gmail.com');
                      setPassword('Password123!');
                      setMode('signin');
                      setErrorMsg(null);
                    }}
                    style={{
                      background: 'none',
                      border: '1px dashed #D1D5DB',
                      borderRadius: '6px',
                      padding: '6px 12px',
                      fontSize: '0.74rem',
                      color: '#4B5563',
                      cursor: 'pointer',
                      width: '100%',
                      fontWeight: 500
                    }}
                  >
                    Quick Fill Demo: aggarwalvishesh0@gmail.com
                  </button>
                </div>
              </form>
            </div>
          </>
        )}

        <AuthScopeDisclosure />
      </div>
    </Dialog>
  );
}

function SignedInPanel({
  email,
  name,
  isLoading,
  sessionPending,
  onSignOut
}: {
  email: string;
  name: string | null;
  isLoading: boolean;
  sessionPending: boolean;
  onSignOut: () => void;
}) {
  return (
    <div>
      <p role="status" style={{ fontSize: '0.88rem', color: '#111827', margin: '0 0 4px 0', fontWeight: 600 }}>
        {sessionPending ? 'Checking session…' : `Signed in as ${name || email}`}
      </p>
      {!sessionPending && (
        <p style={{ fontSize: '0.8rem', color: '#6B7280', margin: '0 0 16px 0', wordBreak: 'break-word' }}>
          {email}
        </p>
      )}
      <button
        type="button"
        onClick={onSignOut}
        disabled={isLoading}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '10px 18px',
          borderRadius: '8px',
          backgroundColor: '#FFFFFF',
          color: '#0F382E',
          border: '1px solid #0F382E',
          fontWeight: 600,
          fontSize: '0.85rem',
          cursor: isLoading ? 'not-allowed' : 'pointer'
        }}
      >
        <LogOut size={15} aria-hidden="true" />
        Sign out
      </button>
    </div>
  );
}

/**
 * The honesty panel. The previous copy implied that signing in secured the
 * data. It does not: the API is single-tenant and serves one shared corpus to
 * every caller, so there is no RBAC, no per-viewer dataset, and nothing to
 * unlock. The session-token storage detail is stated too, because "you are
 * signed in" is otherwise read as a security guarantee it cannot be.
 */
function AuthScopeDisclosure() {
  return (
    <section
      aria-labelledby="auth-scope-title"
      style={{
        marginTop: '20px',
        padding: '12px 14px',
        borderRadius: '10px',
        backgroundColor: '#F9FAFB',
        border: '1px solid #E5E7EB'
      }}
    >
      <h3 id="auth-scope-title" style={{ margin: '0 0 6px 0', fontSize: '0.8rem', fontWeight: 700, color: '#111827' }}>
        What signing in does &mdash; and does not do
      </h3>
      <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
        <li>
          It verifies your identity with Neon Auth and gives this browser a session. That token is sent to
          the API on authenticated requests.
        </li>
        <li>
          It does <strong>not</strong> restrict data. The current API is single-tenant: every viewer, signed
          in or not, reads the same shared dataset. There are no role-based permissions in this build, and
          nothing is unlocked by signing in.
        </li>
        <li>
          The session is stored in this browser&rsquo;s <code>localStorage</code>, so sign out on shared
          devices. Callback origins allowed for this build: {TRUSTED_ORIGINS.join(', ')}.
        </li>
      </ul>
    </section>
  );
}

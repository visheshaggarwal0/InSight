import { useCallback, useEffect, useRef, useState } from 'react';
import { Search, Bell, ChevronDown, Database, Upload, ShieldCheck, BarChart3, LogIn, LogOut, Menu, Sparkles } from 'lucide-react';
import type { DatasetInfo } from '../types/telemetry';
import { useSession, signOut } from '../lib/auth-client';
import { EmptyState } from './EmptyState';
import { fmtPct } from '../lib/formatters';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const CUSTOM_DOMAIN_ID = 'custom';

interface TopBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  datasets: DatasetInfo[];
  activeDomain: string;
  onSelectDomain: (domain: string) => void;
  onUploadCsv: (file: File) => void;
  /** Real model accuracy from /governance, in [0, 1]. */
  governanceAccuracy?: number;
  onOpenGovernance?: () => void;
  onOpenDemoPitch?: () => void;
  onOpenAuth?: () => void;
  onToggleMobileMenu?: () => void;
}

function useDismissable(
  isOpen: boolean,
  onClose: () => void,
  containerRef: React.RefObject<HTMLElement | null>
) {
  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen, onClose, containerRef]);
}

export function TopBar({
  searchQuery,
  onSearchChange,
  datasets,
  activeDomain,
  onSelectDomain,
  onUploadCsv,
  governanceAccuracy,
  onOpenGovernance,
  onOpenDemoPitch,
  onOpenAuth,
  onToggleMobileMenu
}: TopBarProps) {
  const [isDomainOpen, setIsDomainOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [searchDraft, setSearchDraft] = useState(searchQuery);
  const [exportState, setExportState] = useState<'idle' | 'loading' | 'error'>('idle');
  const [exportError, setExportError] = useState<string | null>(null);
  const session = useSession();

  const domainRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);
  const csvInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const closeDomain = useCallback(() => setIsDomainOpen(false), []);
  const closeUser = useCallback(() => setIsUserMenuOpen(false), []);
  const closeNotif = useCallback(() => setIsNotifOpen(false), []);
  useDismissable(isDomainOpen, closeDomain, domainRef);
  useDismissable(isUserMenuOpen, closeUser, userRef);
  useDismissable(isNotifOpen, closeNotif, notifRef);

  // Debounce global search so every keystroke doesn't re-render the whole tree.
  useEffect(() => {
    if (searchDraft === searchQuery) return;
    const t = setTimeout(() => onSearchChange(searchDraft), 300);
    return () => clearTimeout(t);
  }, [searchDraft, searchQuery, onSearchChange]);

  // Flush a pending debounce if the user hits Enter.
  const handleSearchKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') onSearchChange(searchDraft);
    },
    [onSearchChange, searchDraft]
  );

  // ⌘K / Ctrl+K focuses the search field.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
        searchInputRef.current?.select();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  const handleCsvPicked = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      e.target.value = '';
      if (file) {
        onUploadCsv(file);
        setIsDomainOpen(false);
      }
    },
    [onUploadCsv]
  );

  const handleExportPowerBi = useCallback(async () => {
    setExportState('loading');
    setExportError(null);
    try {
      const res = await fetch(`${API_BASE}/export/powerbi`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'insight_powerbi_export.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExportState('idle');
    } catch (err) {
      setExportState('error');
      setExportError(`Power BI export failed: ${(err as Error).message}`);
    }
  }, []);

  const activeDatasetObj = datasets.find((d) => d.id === activeDomain);
  const domainDisplayName = activeDatasetObj?.name
    ? activeDatasetObj.name.includes('(')
      ? activeDatasetObj.name.split('(')[0].trim()
      : activeDatasetObj.name
    : 'Switch Dataset';

  const hasAccuracy = typeof governanceAccuracy === 'number' && Number.isFinite(governanceAccuracy);
  const accuracyLabel = hasAccuracy ? fmtPct((governanceAccuracy as number) * 100) : '—';
  const accuracyPillLabel = hasAccuracy ? `${accuracyLabel} Trust` : 'Trust —';

  return (
    <header className="topbar-header">
      {/* Left Search + Mobile Hamburger Group */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: '1 1 auto', minWidth: 0 }}>
        {onToggleMobileMenu && (
          <button
            onClick={onToggleMobileMenu}
            className="mobile-menu-btn"
            aria-label="Toggle navigation menu"
          >
            <Menu size={18} />
          </button>
        )}

        {/* Search Input with Ctrl K */}
        <div className="topbar-search-box">
          <Search
            size={16}
            style={{
              position: 'absolute',
              left: '14px',
              top: '50%',
              transform: 'translateY(-50%)',
              color: '#9CA3AF'
            }}
          />
          <input
            ref={searchInputRef}
            type="text"
            className="topbar-search-input"
            value={searchDraft}
            onChange={(e) => setSearchDraft(e.target.value)}
            onKeyDown={handleSearchKeyDown}
            placeholder="Search feedback, themes, quotes..."
            aria-label="Search feedback, themes, and quotes"
            style={{
              width: '100%',
              padding: '9px 72px 9px 38px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#F9FAFB',
              fontSize: '0.84rem',
              color: '#111827',
              outline: 'none',
              transition: 'all 0.15s ease'
            }}
            onFocus={(e) => {
              e.target.style.backgroundColor = '#FFFFFF';
              e.target.style.borderColor = '#10B981';
              e.target.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
            }}
            onBlur={(e) => {
              e.target.style.backgroundColor = '#F9FAFB';
              e.target.style.borderColor = '#E5E7EB';
              e.target.style.boxShadow = 'none';
            }}
          />
          <span
            className="topbar-search-shortcut"
            style={{
              position: 'absolute',
              right: '12px',
              top: '50%',
              transform: 'translateY(-50%)',
              fontSize: '0.68rem',
              color: '#6B7280',
              backgroundColor: '#E5E7EB',
              padding: '2px 6px',
              borderRadius: '4px',
              fontWeight: 600,
              pointerEvents: 'none'
            }}
          >
            Ctrl K
          </span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="topbar-controls">
        {/* 60s Demo Story Walkthrough Button */}
        {onOpenDemoPitch && (
          <button
            type="button"
            onClick={onOpenDemoPitch}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 14px',
              borderRadius: '999px',
              border: '1px solid #10B981',
              backgroundColor: '#0F382E',
              color: '#FFFFFF',
              fontSize: '0.78rem',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: '0 2px 6px rgba(15, 56, 46, 0.25)',
              transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#047857')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#0F382E')}
            title="Launch 60-second interactive demo pitch for hackathon judges"
          >
            <Sparkles size={14} style={{ color: '#34D399' }} />
            <span>🎯 60s Demo Story</span>
          </button>
        )}

        {/* Model Trust Score Pill — accuracy comes from /governance */}
        {onOpenGovernance && (
          <button
            type="button"
            onClick={onOpenGovernance}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              borderRadius: '999px',
              border: '1px solid #A7F3D0',
              backgroundColor: '#ECFDF5',
              color: '#065F46',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            title={`Inspect Platt Calibration (${accuracyLabel} Accuracy), Confusion Matrix, and PSI Drift`}
          >
            <ShieldCheck size={14} style={{ color: '#10B981' }} />
            <span>{accuracyPillLabel}</span>
          </button>
        )}

        {/* Power BI Live Connector Bridge */}
        <button
          type="button"
          onClick={() => void handleExportPowerBi()}
          disabled={exportState === 'loading'}
          className="hide-on-mobile"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 12px',
            borderRadius: '999px',
            border: '1px solid #FDE68A',
            backgroundColor: '#FFFBEB',
            color: '#92400E',
            fontSize: '0.78rem',
            fontWeight: 600,
            textDecoration: 'none',
            cursor: exportState === 'loading' ? 'wait' : 'pointer',
            transition: 'all 0.15s ease'
          }}
          title={exportError ?? 'Download live relational telemetry dataset formatted for Microsoft Power BI'}
        >
          <BarChart3 size={14} style={{ color: '#D97706' }} />
          <span>{exportState === 'loading' ? 'Exporting…' : 'Power BI Feed'}</span>
        </button>

        {/* Domain Switcher */}
        <div style={{ position: 'relative' }} ref={domainRef}>
          <button
            type="button"
            onClick={() => setIsDomainOpen(!isDomainOpen)}
            aria-haspopup="menu"
            aria-expanded={isDomainOpen}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#FFFFFF',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: '#374151',
              cursor: 'pointer'
            }}
          >
            <Database size={15} style={{ color: '#10B981' }} />
            <span>{domainDisplayName}</span>
            <ChevronDown size={14} style={{ color: '#9CA3AF' }} />
          </button>

          {isDomainOpen && (
            <div
              role="menu"
              aria-label="Select dataset"
              style={{
                position: 'absolute',
                top: '110%',
                right: 0,
                width: '260px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E5E7EB',
                borderRadius: '12px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
                padding: '6px',
                zIndex: 30
              }}>
              <div style={{ padding: '6px 8px', fontSize: '0.72rem', fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase' }}>
                Select Domain
              </div>
              {datasets.length === 0 && (
                <EmptyState label="No datasets available." />
              )}
              {datasets.map((d) => {
                const isCustom = d.id === CUSTOM_DOMAIN_ID;
                return (
                  <button
                    key={d.id}
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      if (isCustom) {
                        csvInputRef.current?.click();
                      } else {
                        onSelectDomain(d.id);
                      }
                      setIsDomainOpen(false);
                    }}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                      width: '100%',
                      padding: '8px 10px',
                      borderRadius: '8px',
                      border: 'none',
                      backgroundColor: activeDomain === d.id ? '#ECFDF5' : 'transparent',
                      color: activeDomain === d.id ? '#065F46' : '#111827',
                      cursor: 'pointer',
                      textAlign: 'left'
                    }}
                  >
                    <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>{d.name}</span>
                    <span style={{ fontSize: '0.72rem', color: '#6B7280' }}>
                      {isCustom
                        ? 'Choose a CSV file to replace the active dataset'
                        : `${d.review_count?.toLocaleString() ?? '—'} reviews`}
                    </span>
                  </button>
                );
              })}

              <div style={{ borderTop: '1px solid #E5E7EB', marginTop: '6px', paddingTop: '6px' }}>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => {
                    csvInputRef.current?.click();
                    setIsDomainOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: '#4B5563',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <Upload size={14} />
                  <span>Upload Custom CSV</span>
                </button>
                <input
                  ref={csvInputRef}
                  type="file"
                  accept=".csv"
                  style={{ display: 'none' }}
                  onChange={handleCsvPicked}
                />
              </div>
            </div>
          )}
        </div>

        {/* Notifications */}
        <div style={{ position: 'relative' }} ref={notifRef}>
          <button
            type="button"
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            aria-haspopup="menu"
            aria-expanded={isNotifOpen}
            aria-label="Notifications"
            style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              border: '1px solid #E5E7EB',
              backgroundColor: isNotifOpen ? '#E5E7EB' : '#F3F4F6',
              color: '#4B5563',
              cursor: 'pointer'
            }}
          >
            <Bell size={17} style={{ color: '#4B5563' }} />
          </button>

          {isNotifOpen && (
            <div
              role="menu"
              aria-label="Notifications"
              style={{
                position: 'absolute',
                top: '110%',
                right: 0,
                width: '280px',
                backgroundColor: '#FFFFFF',
                border: '1px solid #E5E7EB',
                borderRadius: '12px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
                padding: '8px',
                zIndex: 30
              }}
            >
              <div style={{ padding: '6px 8px', fontSize: '0.72rem', fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase' }}>
                Notifications
              </div>
              <EmptyState
                label="No notifications."
                hint="Drift alerts are surfaced on the Trends tab."
              />
            </div>
          )}
        </div>

        {/* Auth User Pill / Login Trigger */}
        {session?.data?.user ? (
          <div style={{ position: 'relative' }} ref={userRef}>
            <button
              type="button"
              onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
              aria-haspopup="menu"
              aria-expanded={isUserMenuOpen}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                padding: '4px 12px 4px 4px',
                borderRadius: '999px',
                backgroundColor: '#F9FAFB',
                border: '1px solid #E5E7EB',
                cursor: 'pointer'
              }}
            >
              <span style={{
                width: '30px',
                height: '30px',
                borderRadius: '50%',
                backgroundColor: '#0F382E',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.82rem',
                fontWeight: 700
              }}>
                {session.data.user.name ? session.data.user.name[0].toUpperCase() : 'U'}
              </span>
              <span style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#111827', lineHeight: 1.1 }}>
                  {session.data.user.name || 'User'}
                </span>
                <span style={{ fontSize: '0.68rem', color: '#059669', fontWeight: 600 }}>Neon Auth</span>
              </span>
            </button>

            {isUserMenuOpen && (
              <div
                role="menu"
                aria-label="Account"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: '42px',
                  width: '190px',
                  backgroundColor: '#FFFFFF',
                  borderRadius: '10px',
                  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                  border: '1px solid #E5E7EB',
                  padding: '8px',
                  zIndex: 30
                }}>
                <div style={{ padding: '6px 8px', borderBottom: '1px solid #F3F4F6', marginBottom: '6px' }}>
                  <div style={{ fontSize: '0.74rem', color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {session.data.user.email}
                  </div>
                </div>
                <button
                  type="button"
                  role="menuitem"
                  onClick={async () => {
                    await signOut();
                    setIsUserMenuOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    width: '100%',
                    padding: '8px',
                    borderRadius: '6px',
                    border: 'none',
                    backgroundColor: '#FEF2F2',
                    color: '#DC2626',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    cursor: 'pointer'
                  }}
                >
                  <LogOut size={14} />
                  <span>Sign Out</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          <button
            onClick={onOpenAuth}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 16px',
              borderRadius: '999px',
              backgroundColor: '#0F382E',
              color: '#FFFFFF',
              border: 'none',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background-color 0.15s ease'
            }}
          >
            <LogIn size={14} />
            <span>Sign In</span>
          </button>
        )}
      </div>
    </header>
  );
}

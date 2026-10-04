import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { TopBar } from './components/TopBar';
import { HeroBanner } from './components/HeroBanner';
import { OverviewCards } from './components/OverviewCards';
import { SentimentTrendCard } from './components/SentimentTrendCard';
import { RatingDistributionCard } from './components/RatingDistributionCard';
import { TopThemesList } from './components/TopThemesList';
import { ExampleReviewsList } from './components/ExampleReviewsList';
import { SentimentBySource } from './components/SentimentBySource';
import { KeywordCloud } from './components/KeywordCloud';
import { RecentInsights } from './components/RecentInsights';
import { ActionBanner } from './components/ActionBanner';
import { VerbatimDrawer } from './components/VerbatimDrawer';
import { ModelGovernanceModal } from './components/ModelGovernanceModal';
import { TicketModal } from './components/TicketModal';
import { DriftTimeline } from './components/DriftTimeline';
import { ThemeCard } from './components/ThemeCard';
import { AuthModal } from './components/AuthModal';
import { ComplaintClusterDashboard } from './components/ComplaintClusterDashboard';
import { ProductStrengthsView } from './components/ProductStrengthsView';
import { FeatureRequestsView } from './components/FeatureRequestsView';
import { Skeleton } from './components/EmptyState';
import { validateStoredSession, apiFetch } from './lib/auth-client';
import type {
  DatasetInfo,
  OverviewMetrics,
  ThemeCluster,
  DriftData,
  ModelGovernanceData,
  GeneratedTicket,
  ComplaintClusterItem,
  PraiseClusterItem,
  FeatureRequestItem
} from './types/telemetry';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

type EndpointKey = 'datasets' | 'overview' | 'themes' | 'drift' | 'governance' | 'complaints' | 'features' | 'strengths';
type EndpointErrors = Partial<Record<EndpointKey, string>>;

const ENDPOINTS: Array<[EndpointKey, string]> = [
  ['datasets', '/datasets'],
  ['overview', '/overview'],
  ['themes', '/themes'],
  ['drift', '/drift'],
  ['governance', '/governance'],
  ['complaints', '/complaint-clusters'],
  ['features', '/feature-requests'],
  ['strengths', '/praise-clusters']
];

async function readErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (body && typeof body.detail === 'string') return body.detail;
  } catch {
    /* non-JSON error body */
  }
  return `HTTP ${res.status}`;
}

export function App() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDomain, setActiveDomain] = useState<string>('');
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [driftData, setDriftData] = useState<DriftData | null>(null);
  const [governanceData, setGovernanceData] = useState<ModelGovernanceData | null>(null);
  const [complaintClusters, setComplaintClusters] = useState<ComplaintClusterItem[]>([]);
  const [featureRequests, setFeatureRequests] = useState<FeatureRequestItem[]>([]);
  const [praiseClusters, setPraiseClusters] = useState<PraiseClusterItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errors, setErrors] = useState<EndpointErrors>({});
  const [actionError, setActionError] = useState<string | null>(null);

  // Navigation & Search State
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);

  // Modals & Drawers
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [selectedClusterTitle, setSelectedClusterTitle] = useState<string | null>(null);
  const [isVerbatimDrawerOpen, setIsVerbatimDrawerOpen] = useState<boolean>(false);
  const [drawerIsComplaint, setDrawerIsComplaint] = useState<boolean>(false);
  const [drawerIsPraise, setDrawerIsPraise] = useState<boolean>(false);
  const [drawerIsSilentDefects, setDrawerIsSilentDefects] = useState<boolean>(false);
  const [isGovernanceOpen, setIsGovernanceOpen] = useState<boolean>(false);
  const [activeTicket, setActiveTicket] = useState<GeneratedTicket | null>(null);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState<boolean>(false);
  const [isDriftModalOpen, setIsDriftModalOpen] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  // Monotonic request generation: responses from superseded loads are discarded.
  const generationRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  const loadAllData = useCallback(async () => {
    const generation = ++generationRef.current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setIsLoading(true);
    setErrors({});

    const settled = await Promise.allSettled(
      ENDPOINTS.map(([, path]) => apiFetch(path, { signal: controller.signal }))
    );

    if (generation !== generationRef.current) return;

    const nextErrors: EndpointErrors = {};
    const parsed = await Promise.all(
      settled.map(async (result, idx) => {
        const key = ENDPOINTS[idx][0];
        if (result.status === 'rejected') {
          nextErrors[key] =
            (result.reason as Error)?.name === 'AbortError'
              ? 'Request cancelled'
              : `Network unreachable (${API_BASE})`;
          return null;
        }
        const res = result.value;
        if (!res.ok) {
          nextErrors[key] = await readErrorDetail(res);
          return null;
        }
        try {
          return await res.json();
        } catch {
          nextErrors[key] = 'Malformed JSON response';
          return null;
        }
      })
    );

    if (generation !== generationRef.current) return;

    const [ds, ov, th, dr, gov, comp, feat, praise] = parsed;

    // Never render a partially-updated mix of domains: clear what failed.
    if (nextErrors.datasets) {
      setDatasets([]);
      setActiveDomain('');
    } else {
      setDatasets(Array.isArray(ds?.available_domains) ? (ds.available_domains as DatasetInfo[]) : []);
      setActiveDomain(typeof ds?.active_domain === 'string' ? ds.active_domain : '');
    }

    setOverview(nextErrors.overview ? null : ((ov as OverviewMetrics) ?? null));
    setThemes(nextErrors.themes || !Array.isArray(th?.themes) ? [] : (th.themes as ThemeCluster[]));
    setDriftData(nextErrors.drift ? null : ((dr as DriftData) ?? null));
    setGovernanceData(nextErrors.governance ? null : ((gov as ModelGovernanceData) ?? null));

    const rawComp = Array.isArray(comp?.clusters)
      ? comp.clusters
      : Array.isArray(comp?.complaint_clusters)
      ? comp.complaint_clusters
      : [];
    setComplaintClusters(nextErrors.complaints ? [] : (rawComp as ComplaintClusterItem[]));

    setFeatureRequests(
      nextErrors.features || !Array.isArray(feat?.feature_requests)
        ? []
        : (feat.feature_requests as FeatureRequestItem[])
    );

    const rawPraise = Array.isArray(praise?.clusters)
      ? praise.clusters
      : Array.isArray(praise?.praise_clusters)
      ? praise.praise_clusters
      : [];
    setPraiseClusters(nextErrors.strengths ? [] : (rawPraise as PraiseClusterItem[]));

    setErrors(nextErrors);
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();
    abortRef.current = controller;

    void (async () => {
      await validateStoredSession();
      if (!cancelled) await loadAllData();
    })();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [loadAllData]);

  const handleSelectDomain = useCallback(
    async (domainId: string) => {
      setActionError(null);
      try {
        const res = await fetch(`${API_BASE}/datasets/select`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ domain: domainId })
        });
        if (!res.ok) {
          setActionError(`Could not switch to "${domainId}": ${await readErrorDetail(res)}`);
          return;
        }
        await loadAllData();
      } catch (err) {
        setActionError(`Could not switch to "${domainId}": ${(err as Error).message}`);
      }
    },
    [loadAllData]
  );

  const handleUploadCsv = useCallback(
    async (file: File) => {
      setActionError(null);
      try {
        const formData = new FormData();
        formData.append('file', file);
        const res = await fetch(`${API_BASE}/datasets/upload`, {
          method: 'POST',
          body: formData
        });
        if (!res.ok) {
          setActionError(`Upload failed for "${file.name}": ${await readErrorDetail(res)}`);
          return;
        }
        await loadAllData();
      } catch (err) {
        setActionError(`Upload failed for "${file.name}": ${(err as Error).message}`);
      }
    },
    [loadAllData]
  );

  const handleInspectVerbatims = useCallback((clusterId: number, title: string) => {
    setSelectedClusterId(clusterId);
    setSelectedClusterTitle(title);
    setSearchQuery('');
    setDrawerIsComplaint(false);
    setDrawerIsPraise(false);
    setDrawerIsSilentDefects(false);
    setIsVerbatimDrawerOpen(true);
  }, []);

  const handleInspectComplaintVerbatims = useCallback((clusterId: number, title: string) => {
    setSelectedClusterId(clusterId);
    setSelectedClusterTitle(`Complaint Cluster #${clusterId}: ${title}`);
    setSearchQuery('');
    setDrawerIsComplaint(true);
    setDrawerIsPraise(false);
    setDrawerIsSilentDefects(false);
    setIsVerbatimDrawerOpen(true);
  }, []);

  const handleInspectPraiseVerbatims = useCallback((clusterId: number, title: string) => {
    setSelectedClusterId(clusterId);
    setSelectedClusterTitle(`Product Strength #${clusterId}: ${title}`);
    setSearchQuery('');
    setDrawerIsComplaint(false);
    setDrawerIsPraise(true);
    setDrawerIsSilentDefects(false);
    setIsVerbatimDrawerOpen(true);
  }, []);

  const handleInspectSilentDefects = useCallback(() => {
    setSelectedClusterId(null);
    setSelectedClusterTitle('⚡ Silent Defects (Hidden Faults in 4★ & 5★ Reviews)');
    setSearchQuery('');
    setDrawerIsComplaint(false);
    setDrawerIsPraise(false);
    setDrawerIsSilentDefects(true);
    setIsVerbatimDrawerOpen(true);
  }, []);

  const handleInspectAllVerbatims = useCallback(() => {
    setSelectedClusterId(null);
    setSearchQuery('');
    setDrawerIsComplaint(false);
    setDrawerIsPraise(false);
    setDrawerIsSilentDefects(false);
    const total = overview?.total_reviews;
    setSelectedClusterTitle(
      typeof total === 'number' && Number.isFinite(total)
        ? `All Customer Verbatims (${total.toLocaleString()})`
        : 'All Customer Verbatims'
    );
    setIsVerbatimDrawerOpen(true);
  }, [overview?.total_reviews]);

  const handleSelectKeyword = useCallback((word: string) => {
    setSearchQuery(word);
    setSelectedClusterId(null);
    setDrawerIsComplaint(false);
    setDrawerIsPraise(false);
    setDrawerIsSilentDefects(false);
    setSelectedClusterTitle(`Quotes containing "${word}"`);
    setIsVerbatimDrawerOpen(true);
  }, []);

  const handleGenerateTicket = useCallback(async (clusterId: number) => {
    setActionError(null);
    try {
      const res = await fetch(`${API_BASE}/ticket/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cluster_id: clusterId })
      });
      if (!res.ok) {
        setActionError(`Ticket generation failed for cluster #${clusterId}: ${await readErrorDetail(res)}`);
        return;
      }
      const t = (await res.json()) as GeneratedTicket;
      setActiveTicket(t);
      setIsTicketModalOpen(true);
    } catch (err) {
      setActionError(`Ticket generation failed for cluster #${clusterId}: ${(err as Error).message}`);
    }
  }, []);

  const handleDispatchIncidentTicket = useCallback(async (clusterId: number, severityOverride?: string) => {
    setActionError(null);
    try {
      const res = await apiFetch('/ticket/generate-incident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          cluster_id: clusterId,
          ...(severityOverride ? { severity_override: severityOverride } : {})
        })
      });
      if (!res.ok) {
        setActionError(`Incident ticket dispatch failed for cluster #${clusterId}: ${await readErrorDetail(res)}`);
        return;
      }
      const t = (await res.json()) as GeneratedTicket;
      setActiveTicket(t);
      setIsTicketModalOpen(true);
    } catch (err) {
      setActionError(`Incident ticket dispatch failed for cluster #${clusterId}: ${(err as Error).message}`);
    }
  }, []);

  const handleExportReport = useCallback(async () => {
    if (themes.length === 0) {
      setActionError('Cannot generate an incident report: no themes are loaded.');
      return;
    }
    await handleGenerateTicket(themes[0].cluster_id);
  }, [themes, handleGenerateTicket]);

  const handleOpenGovernance = useCallback(() => setIsGovernanceOpen(true), []);
  const handleOpenDrift = useCallback(() => setIsDriftModalOpen(true), []);
  const handleCloseDrawer = useCallback(() => setIsVerbatimDrawerOpen(false), []);
  const handleOpenAuth = useCallback(() => setIsAuthModalOpen(true), []);
  const handleToggleMobileMenu = useCallback(() => setIsMobileMenuOpen((v) => !v), []);

  // Filter themes by search query
  const filteredThemes = useMemo(() => {
    const q = searchQuery.toLowerCase();
    if (!q) return themes;
    return themes.filter(
      (t) =>
        t.title.toLowerCase().includes(q) ||
        (t.keywords || []).some((k) => k.toLowerCase().includes(q))
    );
  }, [themes, searchQuery]);

  const criticalError = errors.overview ?? errors.themes ?? null;
  const secondaryError = errors.drift ?? errors.governance ?? null;
  const safeDatasets = datasets ?? [];

  return (
    <div className="app-container">
      {/* Mobile Backdrop for Off-Canvas Sidebar */}
      <div
        className={`sidebar-backdrop ${isMobileMenuOpen ? 'active' : ''}`}
        onClick={() => setIsMobileMenuOpen(false)}
        aria-hidden="true"
      />

      {/* Left Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        onOpenGovernance={handleOpenGovernance}
        isOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="main-wrapper">
        {/* Sticky Top Bar */}
        <TopBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          datasets={safeDatasets}
          activeDomain={activeDomain}
          onSelectDomain={handleSelectDomain}
          onUploadCsv={handleUploadCsv}
          governanceAccuracy={governanceData?.evaluation?.accuracy}
          onOpenGovernance={handleOpenGovernance}
          onOpenAuth={handleOpenAuth}
          onToggleMobileMenu={handleToggleMobileMenu}
        />

        {/* Global Loading Bar */}
        {isLoading && (
          <div style={{ height: '3px', width: '100%', backgroundColor: '#E5E7EB', overflow: 'hidden' }}>
            <div style={{
              height: '100%',
              width: '40%',
              backgroundColor: '#10B981',
              borderRadius: '999px',
              animation: 'pulse 1s infinite ease-in-out'
            }} />
          </div>
        )}

        {/* Dynamic View Body */}
        <main className="main-body">
          {criticalError && (
            <div
              role="alert"
              style={{
                marginBottom: '24px',
                padding: '20px 22px',
                borderRadius: '12px',
                border: '1px solid #FECACA',
                backgroundColor: '#FEF2F2',
                color: '#991B1B',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px'
              }}
            >
              <strong style={{ fontSize: '0.95rem' }}>
                Could not load dashboard data{errors.overview && errors.themes ? ' (/overview and /themes)' : errors.overview ? ' (/overview)' : ' (/themes)'}
              </strong>
              <span style={{ fontSize: '0.82rem' }}>{criticalError}</span>
              <span style={{ fontSize: '0.78rem' }}>
                No figures are shown in place of missing data.
              </span>
              <div>
                <button type="button" className="btn-primary" onClick={() => void loadAllData()}>
                  Retry
                </button>
              </div>
            </div>
          )}

          {actionError && (
            <div
              role="alert"
              style={{
                marginBottom: '16px',
                padding: '12px 16px',
                borderRadius: '10px',
                border: '1px solid #FDE68A',
                backgroundColor: '#FFFBEB',
                color: '#92400E',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '12px'
              }}
            >
              <span>{actionError}</span>
              <button
                type="button"
                onClick={() => setActionError(null)}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', fontWeight: 700 }}
              >
                Dismiss
              </button>
            </div>
          )}

          {secondaryError && (
            <div
              role="status"
              style={{
                marginBottom: '16px',
                padding: '10px 16px',
                borderRadius: '10px',
                backgroundColor: '#F9FAFB',
                border: '1px solid #E5E7EB',
                color: '#6B7280',
                fontSize: '0.78rem'
              }}
            >
              Partial data: {secondaryError}
            </div>
          )}

          {currentTab === 'dashboard' && (
            <>
              {/* Hero Banner with SVG Flow Diagram */}
              {overview ? (
                <HeroBanner totalReviews={overview.total_reviews} />
              ) : (
                <section className="hero-section">
                  <div style={{ maxWidth: '580px', width: '100%' }}>
                    <h1 className="hero-title">
                      Your users are talking.<br />
                      <span style={{ color: '#059669' }}>We help you listen.</span>
                    </h1>
                    <p style={{ fontSize: '0.82rem', color: '#6B7280', marginTop: '8px' }}>
                      Review volume: —
                    </p>
                  </div>
                </section>
              )}

              {/* Actionable Signal Funnel (4-Way Intent Partitioning) */}
              {overview?.intent_breakdown && (
                <div
                  style={{
                    marginBottom: '20px',
                    backgroundColor: '#FFFFFF',
                    borderRadius: '16px',
                    border: '1px solid #E5E7EB',
                    padding: '16px 20px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '12px',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          backgroundColor: '#F3F4F6',
                          color: '#374151',
                          padding: '2px 8px',
                          borderRadius: '999px',
                          border: '1px solid #E5E7EB',
                        }}
                      >
                        ACTIONABLE SIGNAL FUNNEL
                      </span>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#111827' }}>
                        4-Way Sentence Intent Deconstruction
                      </span>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: '#047857', fontWeight: 700 }}>
                      ⚡ {overview.intent_breakdown.actionable_rate_pct}% Actionable Customer Telemetry
                    </div>
                  </div>

                  {/* Funnel Pools Bar */}
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '12px',
                    }}
                  >
                    {/* Complaints */}
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setCurrentTab('complaints')}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') setCurrentTab('complaints');
                      }}
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#FEF2F2',
                        borderRadius: '10px',
                        border: '1px solid #FECACA',
                        cursor: 'pointer',
                        transition: 'transform 0.15s, box-shadow 0.15s',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#991B1B', textTransform: 'uppercase' }}>
                        🔴 Complaints
                      </div>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          color: '#B91C1C',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {overview.intent_breakdown.complaints.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#7F1D1D' }}>Defects &amp; friction radar &rarr;</div>
                    </div>

                    {/* Praise / Product Strengths */}
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setCurrentTab('strengths')}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') setCurrentTab('strengths');
                      }}
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#ECFDF5',
                        borderRadius: '10px',
                        border: '1px solid #A7F3D0',
                        cursor: 'pointer',
                        transition: 'transform 0.15s, box-shadow 0.15s',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#065F46', textTransform: 'uppercase' }}>
                        🟢 Product Strengths
                      </div>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          color: '#047857',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {overview.intent_breakdown.praise.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#064E3B' }}>Sensory delight &amp; efficacy &rarr;</div>
                    </div>

                    {/* Recommendations / Feature Requests */}
                    <div
                      role="button"
                      tabIndex={0}
                      onClick={() => setCurrentTab('features')}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') setCurrentTab('features');
                      }}
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#EEF2FF',
                        borderRadius: '10px',
                        border: '1px solid #C7D2FE',
                        cursor: 'pointer',
                        transition: 'transform 0.15s, box-shadow 0.15s',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#3730A3', textTransform: 'uppercase' }}>
                        🔵 Feature Requests
                      </div>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          color: '#4338CA',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {overview.intent_breakdown.recommendations.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#312E81' }}>Customer wishlist &amp; backlog &rarr;</div>
                    </div>

                    {/* Noise / Quarantined */}
                    <div
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#F9FAFB',
                        borderRadius: '10px',
                        border: '1px solid #E5E7EB',
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#4B5563', textTransform: 'uppercase' }}>
                        ⚪ Neutral / Noise
                      </div>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          color: '#6B7280',
                          fontFamily: "'JetBrains Mono', monospace",
                        }}
                      >
                        {overview.intent_breakdown.noise.toLocaleString()}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6B7280' }}>Quarantined non-actionable</div>
                    </div>
                  </div>
                </div>
              )}

              {/* 4 KPI Cards */}
              <OverviewCards metrics={overview} onOpenGovernance={handleOpenGovernance} />

              {/* Row 2: Charts (Sentiment Trend & Rating Distribution) */}
              <div className="responsive-row-2">
                <SentimentTrendCard trendPoints={overview?.sentiment_trend} />
                <RatingDistributionCard ratings={overview?.rating_distribution} />
              </div>

              {/* Row 3: Lists (Top Themes & Example Reviews) */}
              <div className="responsive-row-2">
                <TopThemesList
                  themes={filteredThemes}
                  selectedClusterId={selectedClusterId}
                  onSelectCluster={handleInspectVerbatims}
                  onViewAll={handleInspectAllVerbatims}
                />
                <ExampleReviewsList
                  themes={themes}
                  selectedClusterId={selectedClusterId}
                  onViewAll={handleInspectAllVerbatims}
                  onViewSilentDefects={handleInspectSilentDefects}
                />
              </div>

              {/* Row 4: Analytics Cards (Sentiment by Source, Keyword Cloud, Recent Insights) */}
              <div className="responsive-row-3">
                <SentimentBySource sources={overview?.sentiment_by_source} />
                <KeywordCloud
                  keywords={overview?.keyword_cloud}
                  onSelectWord={handleSelectKeyword}
                  onViewAll={handleInspectAllVerbatims}
                />
                <RecentInsights
                  driftData={driftData}
                  insights={overview?.recent_insights}
                  onViewDrift={handleOpenDrift}
                />
              </div>

              {/* Row 5: Action Banner */}
              <ActionBanner onExportReport={() => void handleExportReport()} />

              {/* Footer */}
              <footer style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '24px',
                borderTop: '1px solid #E8ECE9',
                color: '#9CA3AF',
                fontSize: '0.78rem',
                flexWrap: 'wrap',
                gap: '12px'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <strong style={{ color: '#0F382E', fontFamily: "'DM Serif Display', Georgia, serif", fontSize: '1rem' }}>
                    InSight
                  </strong>
                  <span>v1.0.0</span>
                </div>
                <div style={{ display: 'flex', gap: '20px' }}>
                  <a href="#privacy" style={{ color: '#9CA3AF', textDecoration: 'none' }}>Privacy</a>
                  <a href="#terms" style={{ color: '#9CA3AF', textDecoration: 'none' }}>Terms</a>
                  <a href="#contact" style={{ color: '#9CA3AF', textDecoration: 'none' }}>Contact</a>
                </div>
              </footer>
            </>
          )}

          {currentTab === 'complaints' && (
            <ComplaintClusterDashboard
              clusters={complaintClusters}
              isLoading={isLoading}
              onInspectVerbatims={handleInspectComplaintVerbatims}
              onDispatchTicket={(id) => void handleDispatchIncidentTicket(id)}
            />
          )}

          {currentTab === 'strengths' && (
            <ProductStrengthsView
              clusters={praiseClusters}
              isLoading={isLoading}
              onInspectVerbatims={handleInspectPraiseVerbatims}
            />
          )}

          {currentTab === 'features' && (
            <FeatureRequestsView
              featureRequests={featureRequests}
              isLoading={isLoading}
            />
          )}

          {currentTab === 'reviews' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '14px' }}>
                <div>
                  <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                    Customer Verbatims &amp; Raw Feedback
                  </h2>
                  <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                    Complete audit trail with server-side PII masking and calibrated sentiment classification.
                  </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <button
                    type="button"
                    onClick={handleInspectSilentDefects}
                    className="btn-outline"
                    style={{
                      borderColor: '#FCD34D',
                      backgroundColor: '#FFFBEB',
                      color: '#B45309',
                      fontWeight: 600,
                      fontSize: '0.82rem',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                  >
                    <span>⚡ Trojan Horse Defects (4★-5★)</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleInspectAllVerbatims}
                    className="btn-primary"
                  >
                    Open Verbatim Drawer
                  </button>
                </div>
              </div>
              <ExampleReviewsList
                themes={themes}
                selectedClusterId={null}
                onViewAll={handleInspectAllVerbatims}
                onViewSilentDefects={handleInspectSilentDefects}
              />
            </div>
          )}

          {currentTab === 'themes' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                  Discovered Semantic Themes
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Unsupervised HDBSCAN clustering &amp; TF-IDF keyphrase extraction across customer reviews.
                </p>
              </div>
              {isLoading ? (
                <Skeleton rows={5} label="Loading themes" />
              ) : themes.length === 0 ? (
                <p style={{ fontSize: '0.84rem', color: '#6B7280' }}>
                  No themes are available for the active dataset.
                </p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                  {themes.map((theme) => (
                    <ThemeCard
                      key={theme.cluster_id}
                      theme={theme}
                      onInspectVerbatims={handleInspectVerbatims}
                      onGenerateTicket={(id) => void handleGenerateTicket(id)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}

          {currentTab === 'sentiment' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                  Sentiment Intelligence &amp; Model Governance
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Platt-scaled 3-class classifier metrics benchmarked on the gold-standard ground-truth review set.
                </p>
              </div>
              <div className="responsive-row-2">
                <SentimentTrendCard trendPoints={overview?.sentiment_trend} />
                <RatingDistributionCard ratings={overview?.rating_distribution} />
              </div>
              <button
                onClick={handleOpenGovernance}
                className="btn-primary"
              >
                Inspect Empirical Confusion Matrix &amp; Calibration Curve
              </button>
            </div>
          )}

          {currentTab === 'trends' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                  Statistical Drift Monitoring (PSI)
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Population Stability Index tracking distribution shifts between reference batches and production telemetry.
                </p>
              </div>
              {driftData ? (
                <DriftTimeline driftData={driftData} />
              ) : (
                <p style={{ fontSize: '0.84rem', color: '#6B7280' }}>
                  {isLoading ? 'Loading drift telemetry…' : 'No drift telemetry is available.'}
                </p>
              )}
            </div>
          )}

          {currentTab === 'compare' && (
            <div style={{ paddingTop: '32px' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                Domain &amp; Cross-Dataset Benchmark
              </h2>
              <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px', marginBottom: '24px' }}>
                Compare customer sentiment and defect frequencies across multiple product verticals.
              </p>
              {safeDatasets.length === 0 ? (
                <p style={{ fontSize: '0.84rem', color: '#6B7280' }}>
                  {isLoading ? 'Loading datasets…' : 'No datasets are available.'}
                </p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '20px' }}>
                  {safeDatasets.map((d) => (
                    <div key={d.id} className="dashboard-card" style={{ padding: '24px' }}>
                      <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>{d.name}</h3>
                      <p style={{ fontSize: '0.8rem', color: '#6B7280', marginTop: '4px' }}>Category: {d.category}</p>
                      <div style={{ marginTop: '16px', fontSize: '1.5rem', fontWeight: 700, color: '#0F382E' }}>
                        {d.review_count?.toLocaleString()} reviews
                      </div>
                      <button
                        onClick={() => void handleSelectDomain(d.id)}
                        className="btn-outline"
                        style={{ marginTop: '16px', width: '100%', justifyContent: 'center' }}
                      >
                        {activeDomain === d.id ? 'Active Dataset' : 'Switch to this Domain'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {currentTab === 'settings' && (
            <div style={{ paddingTop: '32px' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                Data &amp; Privacy Configuration
              </h2>
              <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px', marginBottom: '24px' }}>
                Configure live PII scrubbing rules, audit trails, and custom dataset ingestion.
              </p>
              <div className="dashboard-card" style={{ padding: '24px', maxWidth: '600px' }}>
                <h4 style={{ fontSize: '1rem', fontWeight: 700, color: '#111827', marginBottom: '8px' }}>
                  Custom Dataset Upload
                </h4>
                <p style={{ fontSize: '0.82rem', color: '#6B7280', marginBottom: '16px' }}>
                  Upload any raw CSV containing review text, ratings, or customer telemetry.
                </p>
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    e.target.value = '';
                    if (file) void handleUploadCsv(file);
                  }}
                  style={{ fontSize: '0.84rem' }}
                />
              </div>
            </div>
          )}
        </main>
      </div>

      {/* Slide-out Verbatim Drawer */}
      <VerbatimDrawer
        isOpen={isVerbatimDrawerOpen}
        onClose={handleCloseDrawer}
        clusterId={selectedClusterId}
        clusterTitle={selectedClusterTitle}
        search={searchQuery}
        isComplaintCluster={drawerIsComplaint}
        isPraiseCluster={drawerIsPraise}
        isSilentDefects={drawerIsSilentDefects}
      />

      {/* Model Governance Modal */}
      <ModelGovernanceModal
        isOpen={isGovernanceOpen}
        onClose={() => setIsGovernanceOpen(false)}
        governanceData={governanceData}
      />

      {/* Ticket Modal */}
      <TicketModal
        isOpen={isTicketModalOpen}
        onClose={() => setIsTicketModalOpen(false)}
        ticket={activeTicket}
      />

      {/* Drift Modal */}
      {isDriftModalOpen && driftData && (
        <div className="overlay-backdrop">
          <div style={{
            width: '90%',
            maxWidth: '800px',
            maxHeight: '85vh',
            overflowY: 'auto',
            padding: '24px',
            backgroundColor: '#FFFFFF',
            borderRadius: '16px',
            border: '1px solid #E5E7EB',
            boxShadow: '0 20px 40px rgba(0,0,0,0.15)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>Statistical Drift Timeline</h3>
              <button
                onClick={() => setIsDriftModalOpen(false)}
                style={{ background: 'none', border: 'none', fontSize: '1rem', cursor: 'pointer', color: '#6B7280' }}
              >
                ✕
              </button>
            </div>
            <DriftTimeline driftData={driftData} />
          </div>
        </div>
      )}

      {/* Neon Auth Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onSuccess={() => void loadAllData()}
      />
    </div>
  );
}

export default App;

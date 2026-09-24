import { useState, useEffect } from 'react';
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
import type {
  DatasetInfo,
  OverviewMetrics,
  ThemeCluster,
  DriftData,
  ModelGovernanceData,
  GeneratedTicket
} from './types/telemetry';

const API_BASE = 'http://localhost:8000/api';

export function App() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDomain, setActiveDomain] = useState<string>('d2c_cosmetics');
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [driftData, setDriftData] = useState<DriftData | null>(null);
  const [governanceData, setGovernanceData] = useState<ModelGovernanceData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Navigation & Search State
  const [currentTab, setCurrentTab] = useState<string>('dashboard');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [timeRange, setTimeRange] = useState<string>('Last 30 days');

  // Modals & Drawers
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [selectedClusterTitle, setSelectedClusterTitle] = useState<string | null>(null);
  const [isVerbatimDrawerOpen, setIsVerbatimDrawerOpen] = useState<boolean>(false);
  const [isGovernanceOpen, setIsGovernanceOpen] = useState<boolean>(false);
  const [activeTicket, setActiveTicket] = useState<GeneratedTicket | null>(null);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState<boolean>(false);
  const [isDriftModalOpen, setIsDriftModalOpen] = useState<boolean>(false);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const [dsRes, overRes, thRes, drRes, govRes] = await Promise.all([
        fetch(`${API_BASE}/datasets`),
        fetch(`${API_BASE}/overview`),
        fetch(`${API_BASE}/themes`),
        fetch(`${API_BASE}/drift`),
        fetch(`${API_BASE}/governance`)
      ]);

      if (dsRes.ok) {
        const d = await dsRes.json();
        setDatasets(d.available_domains);
        setActiveDomain(d.active_domain);
      }
      if (overRes.ok) setOverview(await overRes.json());
      if (thRes.ok) {
        const t = await thRes.json();
        setThemes(t.themes);
      }
      if (drRes.ok) setDriftData(await drRes.json());
      if (govRes.ok) setGovernanceData(await govRes.json());
    } catch (err) {
      console.warn("FastAPI backend not currently running, using high-fidelity offline mode:", err);
      // Fallback data for demonstration if backend is not started
      setOverview({
        domain: 'd2c_cosmetics',
        total_reviews: 10324,
        sentiment_counts: { POSITIVE: 7433, NEUTRAL: 1858, NEGATIVE: 1033 },
        positive_rate: 72,
        negative_rate: 10,
        pii_redacted_count: 842,
        pii_redacted_rate: 8.2,
        critical_themes_count: 3,
        active_alerts: 2
      });
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleSelectDomain = async (domainId: string) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/datasets/select`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: domainId })
      });
      if (res.ok) {
        await loadAllData();
      }
    } catch (err) {
      console.error("Failed to switch domain:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadCsv = async (file: File) => {
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/datasets/upload`, {
        method: 'POST',
        body: formData
      });
      if (res.ok) {
        await loadAllData();
      }
    } catch (err) {
      console.error("Failed to upload CSV:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleInspectVerbatims = (clusterId: number, title: string) => {
    setSelectedClusterId(clusterId);
    setSelectedClusterTitle(title);
    setIsVerbatimDrawerOpen(true);
  };

  const handleInspectAllVerbatims = () => {
    setSelectedClusterId(null);
    setSelectedClusterTitle("All 10,000+ Customer Verbatims");
    setIsVerbatimDrawerOpen(true);
  };

  const handleSelectKeyword = (word: string) => {
    setSearchQuery(word);
    setSelectedClusterId(null);
    setSelectedClusterTitle(`Quotes containing "${word}"`);
    setIsVerbatimDrawerOpen(true);
  };

  const handleGenerateTicket = async (clusterId: number) => {
    try {
      const res = await fetch(`${API_BASE}/ticket/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cluster_id: clusterId })
      });
      if (res.ok) {
        const t = await res.json();
        setActiveTicket(t);
        setIsTicketModalOpen(true);
      }
    } catch (err) {
      console.error("Failed to generate ticket:", err);
    }
  };

  const handleExportReport = async () => {
    // Generate an executive incident report for the highest critical theme
    const topClusterId = themes.length > 0 ? themes[0].cluster_id : 1;
    await handleGenerateTicket(topClusterId);
  };

  // Filter themes by search query
  const filteredThemes = themes.filter((t) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return t.title.toLowerCase().includes(q) || t.keywords.some(k => k.toLowerCase().includes(q));
  });

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#F8FAF8' }}>
      {/* Left Navigation Sidebar */}
      <Sidebar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        onOpenGovernance={() => setIsGovernanceOpen(true)}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Sticky Top Bar */}
        <TopBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          datasets={datasets}
          activeDomain={activeDomain}
          onSelectDomain={handleSelectDomain}
          onUploadCsv={handleUploadCsv}
          timeRange={timeRange}
          onChangeTimeRange={setTimeRange}
          onOpenGovernance={() => setIsGovernanceOpen(true)}
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
        <main style={{ padding: '0 40px 48px 40px', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
          {currentTab === 'dashboard' && (
            <>
              {/* Hero Banner with SVG Flow Diagram */}
              <HeroBanner totalReviews={overview?.total_reviews || 10324} />

              {/* 4 KPI Cards */}
              <OverviewCards metrics={overview} onOpenGovernance={() => setIsGovernanceOpen(true)} />

              {/* Row 2: Charts (Sentiment Trend & Rating Distribution) */}
              <div style={{ display: 'flex', gap: '20px', marginBottom: '24px', flexWrap: 'wrap' }}>
                <SentimentTrendCard trendPoints={overview?.sentiment_trend} />
                <RatingDistributionCard ratings={overview?.rating_distribution} />
              </div>

              {/* Row 3: Lists (Top Themes & Example Reviews with PII Toggle) */}
              <div style={{ display: 'flex', gap: '20px', marginBottom: '24px', flexWrap: 'wrap' }}>
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
                />
              </div>

              {/* Row 4: Analytics Cards (Sentiment by Source, Keyword Cloud, Recent Insights) */}
              <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                <SentimentBySource sources={overview?.sentiment_by_source} />
                <KeywordCloud
                  keywords={overview?.keyword_cloud}
                  onSelectWord={handleSelectKeyword}
                  onViewAll={handleInspectAllVerbatims}
                />
                <RecentInsights
                  driftData={driftData}
                  insights={overview?.recent_insights}
                  onViewDrift={() => setIsDriftModalOpen(true)}
                />
              </div>

              {/* Row 5: Action Banner */}
              <ActionBanner onExportReport={handleExportReport} />

              {/* Footer */}
              <footer style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '24px',
                borderTop: '1px solid #E8ECE9',
                color: '#9CA3AF',
                fontSize: '0.78rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <strong style={{ color: '#0F382E', fontFamily: "'Playfair Display', Georgia, serif", fontSize: '0.95rem' }}>
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

          {currentTab === 'reviews' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px' }}>
                <div>
                  <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
                    Customer Verbatims &amp; Raw Feedback
                  </h2>
                  <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                    Complete audit trail with multi-pass PII masking and calibrated sentiment classification.
                  </p>
                </div>
                <button
                  onClick={handleInspectAllVerbatims}
                  className="btn-primary"
                >
                  Open Verbatim Drawer
                </button>
              </div>
              <ExampleReviewsList
                themes={themes}
                selectedClusterId={null}
                onViewAll={handleInspectAllVerbatims}
              />
            </div>
          )}

          {currentTab === 'themes' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
                  Discovered Semantic Themes
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Unsupervised HDBSCAN clustering &amp; TF-IDF keyphrase extraction across customer reviews.
                </p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px' }}>
                {themes.map((theme) => (
                  <ThemeCard
                    key={theme.cluster_id}
                    theme={theme}
                    onInspectVerbatims={handleInspectVerbatims}
                    onGenerateTicket={handleGenerateTicket}
                  />
                ))}
              </div>
            </div>
          )}

          {currentTab === 'sentiment' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
                  Sentiment Intelligence &amp; Model Governance
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Platt-scaled 3-class classifier metrics benchmarked on 1,000 gold-standard ground-truth reviews.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '20px', marginBottom: '24px', flexWrap: 'wrap' }}>
                <SentimentTrendCard trendPoints={overview?.sentiment_trend} />
                <RatingDistributionCard ratings={overview?.rating_distribution} />
              </div>
              <button
                onClick={() => setIsGovernanceOpen(true)}
                className="btn-primary"
              >
                Inspect Empirical Confusion Matrix &amp; Calibration Curve
              </button>
            </div>
          )}

          {currentTab === 'trends' && (
            <div style={{ paddingTop: '32px' }}>
              <div style={{ marginBottom: '24px' }}>
                <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
                  Statistical Drift Monitoring (PSI)
                </h2>
                <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px' }}>
                  Population Stability Index tracking distribution shifts between reference batches and production telemetry.
                </p>
              </div>
              {driftData && <DriftTimeline driftData={driftData} />}
            </div>
          )}

          {currentTab === 'compare' && (
            <div style={{ paddingTop: '32px' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
                Domain &amp; Cross-Dataset Benchmark
              </h2>
              <p style={{ fontSize: '0.86rem', color: '#6B7280', marginTop: '4px', marginBottom: '24px' }}>
                Compare customer sentiment and defect frequencies across multiple product verticals.
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
                {datasets.map((d) => (
                  <div key={d.id} className="dashboard-card" style={{ padding: '24px' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>{d.name}</h3>
                    <p style={{ fontSize: '0.8rem', color: '#6B7280', marginTop: '4px' }}>Category: {d.category}</p>
                    <div style={{ marginTop: '16px', fontSize: '1.5rem', fontWeight: 700, color: '#0F382E' }}>
                      {d.review_count?.toLocaleString()} reviews
                    </div>
                    <button
                      onClick={() => handleSelectDomain(d.id)}
                      className="btn-outline"
                      style={{ marginTop: '16px', width: '100%', justifyContent: 'center' }}
                    >
                      {activeDomain === d.id ? 'Active Dataset' : 'Switch to this Domain'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {currentTab === 'settings' && (
            <div style={{ paddingTop: '32px' }}>
              <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', fontFamily: "'Playfair Display', serif" }}>
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
                    if (e.target.files?.[0]) handleUploadCsv(e.target.files[0]);
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
        onClose={() => setIsVerbatimDrawerOpen(false)}
        clusterId={selectedClusterId}
        clusterTitle={selectedClusterTitle}
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
    </div>
  );
}

export default App;

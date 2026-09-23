import { useState, useEffect } from 'react';
import { DomainSwitcher } from './components/DomainSwitcher';
import { OverviewCards } from './components/OverviewCards';
import { ThemeCard } from './components/ThemeCard';
import { VerbatimDrawer } from './components/VerbatimDrawer';
import { DriftTimeline } from './components/DriftTimeline';
import { ModelGovernanceModal } from './components/ModelGovernanceModal';
import { TicketModal } from './components/TicketModal';
import type {
  DatasetInfo,
  OverviewMetrics,
  ThemeCluster,
  DriftData,
  ModelGovernanceData,
  GeneratedTicket
} from './types/telemetry';
import { Shield, Sparkles, ListFilter } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export function App() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDomain, setActiveDomain] = useState<string>('d2c_cosmetics');
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [driftData, setDriftData] = useState<DriftData | null>(null);
  const [governanceData, setGovernanceData] = useState<ModelGovernanceData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Modals & Drawers
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null);
  const [selectedClusterTitle, setSelectedClusterTitle] = useState<string | null>(null);
  const [isVerbatimDrawerOpen, setIsVerbatimDrawerOpen] = useState<boolean>(false);
  const [isGovernanceOpen, setIsGovernanceOpen] = useState<boolean>(false);
  const [activeTicket, setActiveTicket] = useState<GeneratedTicket | null>(null);
  const [isTicketModalOpen, setIsTicketModalOpen] = useState<boolean>(false);

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
      console.error("Error loading InSight data:", err);
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
    setSelectedClusterTitle("All 10,000 Customer Verbatims");
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

  return (
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '24px 32px' }}>
      {/* Top Navbar */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '42px',
              height: '42px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 20px rgba(59, 130, 246, 0.4)'
            }}
          >
            <Sparkles size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.4rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#fff' }}>
              InSight <span style={{ fontSize: '0.8rem', color: '#60a5fa', fontWeight: 600 }}>v1.0</span>
            </h1>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Universal Product & Review Telemetry Intelligence • Team The Lookouts
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={handleInspectAllVerbatims}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <ListFilter size={15} />
            Explore All Verbatims
          </button>

          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid rgba(59, 130, 246, 0.4)',
              background: 'rgba(59, 130, 246, 0.1)',
              color: '#60a5fa',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer'
            }}
          >
            <Shield size={15} />
            Model Governance (Acc &amp; F1)
          </button>
        </div>
      </header>

      {/* Domain Switcher */}
      <DomainSwitcher
        datasets={datasets}
        activeDomain={activeDomain}
        onSelectDomain={handleSelectDomain}
        onUploadCsv={handleUploadCsv}
        isLoading={isLoading}
      />

      {/* High-Level Overview Metrics */}
      <OverviewCards
        metrics={overview}
        onOpenGovernance={() => setIsGovernanceOpen(true)}
      />

      {/* Release & Batch Drift Engine Timeline */}
      <DriftTimeline driftData={driftData} />

      {/* Unsupervised Thematic Cluster Explorer */}
      <section style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--text-primary)' }}>
              Discovered Themes &amp; Anomaly Clusters
            </h2>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Unsupervised semantic groupings surfaced across 10,000 reviews without predefined categories.
            </p>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {themes.length} Active Semantic Neighborhoods
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '18px' }}>
          {themes.map((theme) => (
            <ThemeCard
              key={theme.cluster_id}
              theme={theme}
              onInspectVerbatims={handleInspectVerbatims}
              onGenerateTicket={handleGenerateTicket}
            />
          ))}
        </div>
      </section>

      {/* Modals & Drawers */}
      <VerbatimDrawer
        isOpen={isVerbatimDrawerOpen}
        onClose={() => setIsVerbatimDrawerOpen(false)}
        clusterId={selectedClusterId}
        clusterTitle={selectedClusterTitle}
      />

      <ModelGovernanceModal
        isOpen={isGovernanceOpen}
        onClose={() => setIsGovernanceOpen(false)}
        governanceData={governanceData}
      />

      <TicketModal
        isOpen={isTicketModalOpen}
        onClose={() => setIsTicketModalOpen(false)}
        ticket={activeTicket}
      />
    </div>
  );
}

export default App;

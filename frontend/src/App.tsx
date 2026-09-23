import { useState, useEffect } from 'react';
import { DomainSwitcher } from './components/DomainSwitcher';
import { OverviewCards } from './components/OverviewCards';
import { ThemeCard } from './components/ThemeCard';
import { VerbatimDrawer } from './components/VerbatimDrawer';
import { InteractiveTimelineChart } from './components/InteractiveTimelineChart';
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
import { Shield, Sparkles, ListFilter, Activity, LayoutGrid } from 'lucide-react';

const API_BASE = 'http://localhost:8000/api';

export function App() {
  const [datasets, setDatasets] = useState<DatasetInfo[]>([]);
  const [activeDomain, setActiveDomain] = useState<string>('d2c_cosmetics');
  const [overview, setOverview] = useState<OverviewMetrics | null>(null);
  const [themes, setThemes] = useState<ThemeCluster[]>([]);
  const [driftData, setDriftData] = useState<DriftData | null>(null);
  const [governanceData, setGovernanceData] = useState<ModelGovernanceData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Filters
  const [activeTab, setActiveTab] = useState<'themes' | 'drift'>('themes');
  const [themeFilter, setThemeFilter] = useState<'all' | 'critical' | 'high'>('all');

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

  const filteredThemes = themes.filter((t) => {
    if (themeFilter === 'critical') return t.severity === 'CRITICAL';
    if (themeFilter === 'high') return t.severity === 'HIGH' || t.severity === 'CRITICAL';
    return true;
  });

  return (
    <div style={{ maxWidth: '1380px', margin: '0 auto', padding: '24px 32px', minHeight: '100vh' }}>
      {/* Top Navigation Bar */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '9px',
              background: '#181820',
              border: '1px solid #272730',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Sparkles size={18} color="#fafafa" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
                InSight
              </h1>
              <span style={{ fontSize: '0.68rem', background: '#1c1c24', color: 'var(--text-secondary)', padding: '2px 7px', borderRadius: '4px', fontWeight: 600, border: '1px solid #272730' }}>
                v1.0
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: 'var(--color-pos)', fontWeight: 500 }}>
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-pos)', display: 'inline-block' }} />
                LIVE
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Enterprise Review &amp; Feedback Telemetry &bull; Team The Lookouts
            </p>
          </div>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={handleInspectAllVerbatims}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '7px',
              border: '1px solid var(--border-card)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <ListFilter size={14} />
            Inspect 10,000 Verbatims
          </button>

          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '7px',
              border: '1px solid var(--border-active)',
              background: '#1c1c24',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <Shield size={14} color="var(--text-secondary)" />
            Model Governance (88.2% Acc)
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

      {/* Overview Metric Cards */}
      <OverviewCards
        metrics={overview}
        onOpenGovernance={() => setIsGovernanceOpen(true)}
      />

      {/* Interactive Timeline & Drift Flow Chart */}
      <InteractiveTimelineChart driftData={driftData} />

      {/* Anomaly Alerts */}
      <DriftTimeline driftData={driftData} />

      {/* Filter Tabs Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={() => setActiveTab('themes')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: activeTab === 'themes' ? '1px solid var(--border-active)' : '1px solid transparent',
              background: activeTab === 'themes' ? '#181820' : 'transparent',
              color: activeTab === 'themes' ? 'var(--text-primary)' : 'var(--text-muted)'
            }}
          >
            <LayoutGrid size={14} />
            Discovered Thematic Clusters ({themes.length})
          </button>

          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '0.8rem',
              fontWeight: 500,
              cursor: 'pointer',
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--text-muted)'
            }}
          >
            <Activity size={14} />
            Supervised Validation
          </button>
        </div>

        {/* Severity Filters */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginRight: '4px' }}>Severity:</span>
          {(['all', 'critical', 'high'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setThemeFilter(lvl)}
              style={{
                padding: '4px 9px',
                borderRadius: '5px',
                fontSize: '0.72rem',
                fontWeight: 500,
                cursor: 'pointer',
                border: themeFilter === lvl ? '1px solid var(--border-active)' : '1px solid var(--border-subtle)',
                background: themeFilter === lvl ? '#202028' : 'var(--bg-card)',
                color: themeFilter === lvl ? 'var(--text-primary)' : 'var(--text-muted)'
              }}
            >
              {lvl === 'all' ? 'All Clusters' : lvl === 'critical' ? 'Critical' : 'High & Critical'}
            </button>
          ))}
        </div>
      </div>

      {/* Thematic Cluster Cards Grid */}
      <section style={{ marginBottom: '36px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px' }}>
          {filteredThemes.map((theme) => (
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

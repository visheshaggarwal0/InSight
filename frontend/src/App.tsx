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

  // Tab State
  const [activeTab, setActiveTab] = useState<'themes' | 'drift' | 'governance'>('themes');
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
    <div style={{ maxWidth: '1440px', margin: '0 auto', padding: '28px 36px', minHeight: '100vh' }}>
      {/* Top Navigation Cockpit */}
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '28px', flexWrap: 'wrap', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div
            style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 25px rgba(59, 130, 246, 0.45)',
              border: '1px solid rgba(255, 255, 255, 0.2)'
            }}
          >
            <Sparkles size={24} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h1 style={{ fontSize: '1.5rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#fff' }}>
                InSight
              </h1>
              <span style={{ fontSize: '0.75rem', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '2px 8px', borderRadius: '6px', fontWeight: 700, border: '1px solid rgba(59, 130, 246, 0.3)' }}>
                v1.0 ENTERPRISE
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.72rem', color: '#34d399', fontWeight: 600 }}>
                <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: '#10b981', display: 'inline-block' }} className="pulse-indicator" />
                TELEMETRY LIVE
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Universal Product &amp; Review Telemetry Intelligence &bull; Team The Lookouts
            </p>
          </div>
        </div>

        {/* Global Action Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={handleInspectAllVerbatims}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '9px 16px',
              borderRadius: '9px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              background: 'rgba(15, 23, 42, 0.7)',
              color: 'var(--text-secondary)',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            <ListFilter size={15} />
            Inspect 10,000 Verbatims
          </button>

          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '9px 18px',
              borderRadius: '9px',
              border: '1px solid rgba(59, 130, 246, 0.45)',
              background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1))',
              color: '#93c5fd',
              fontSize: '0.82rem',
              fontWeight: 800,
              cursor: 'pointer',
              boxShadow: '0 0 15px rgba(59, 130, 246, 0.25)',
              transition: 'all 0.15s ease'
            }}
          >
            <Shield size={16} color="#60a5fa" />
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

      {/* High-Level Overview Metrics */}
      <OverviewCards
        metrics={overview}
        onOpenGovernance={() => setIsGovernanceOpen(true)}
      />

      {/* Interactive Visual Timeline & Drift Bar Chart */}
      <InteractiveTimelineChart driftData={driftData} />

      {/* Regression Alert Banners */}
      <DriftTimeline driftData={driftData} />

      {/* Navigation Pills: Themes vs Governance */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '14px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            onClick={() => setActiveTab('themes')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer',
              border: activeTab === 'themes' ? '1px solid #3b82f6' : '1px solid transparent',
              background: activeTab === 'themes' ? 'rgba(59, 130, 246, 0.2)' : 'transparent',
              color: activeTab === 'themes' ? '#60a5fa' : 'var(--text-muted)'
            }}
          >
            <LayoutGrid size={15} />
            Discovered Thematic Clusters ({themes.length})
          </button>

          <button
            onClick={() => setIsGovernanceOpen(true)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 700,
              cursor: 'pointer',
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--text-muted)'
            }}
          >
            <Activity size={15} />
            Supervised Validation Benchmark
          </button>
        </div>

        {/* Severity Filter Pills */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginRight: '4px' }}>Severity:</span>
          {(['all', 'critical', 'high'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setThemeFilter(lvl)}
              style={{
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '0.74rem',
                fontWeight: 700,
                cursor: 'pointer',
                textTransform: 'uppercase',
                border: themeFilter === lvl ? '1px solid #3b82f6' : '1px solid var(--border-subtle)',
                background: themeFilter === lvl ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-card)',
                color: themeFilter === lvl ? '#93c5fd' : 'var(--text-secondary)'
              }}
            >
              {lvl === 'all' ? 'All Clusters' : lvl === 'critical' ? 'Critical Only' : 'High & Critical'}
            </button>
          ))}
        </div>
      </div>

      {/* Thematic Cluster Cards Grid */}
      <section style={{ marginBottom: '40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
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

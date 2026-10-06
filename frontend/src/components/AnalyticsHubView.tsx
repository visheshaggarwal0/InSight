import { useState, memo } from 'react';
import { LineChart, TrendingUp, BarChart3 } from 'lucide-react';
import { VisualAnalyticsView } from './VisualAnalyticsView';
import { PowerBIView } from './PowerBIView';
import { DriftTimeline } from './DriftTimeline';
import { AnomalySimulatorBanner } from './AnomalySimulatorBanner';
import type { OverviewMetrics, ThemeCluster, DriftData } from '../types/telemetry';

export type AnalyticsSubTab = 'curves' | 'drift' | 'powerbi';

interface AnalyticsHubViewProps {
  activeDomain: string;
  overview: OverviewMetrics | null;
  themes: ThemeCluster[];
  driftData: DriftData | null;
  isLoading?: boolean;
  initialSubTab?: AnalyticsSubTab;
  onInspectVerbatims?: (clusterId: number | null, title: string, searchOverride?: string) => void;
  onDispatchTicket?: (clusterId: number, severity?: string) => void;
  onRefreshData?: () => void;
}

export const AnalyticsHubView = memo(function AnalyticsHubView({
  activeDomain,
  overview,
  themes,
  driftData,
  isLoading = false,
  initialSubTab = 'curves',
  onInspectVerbatims,
  onDispatchTicket,
  onRefreshData,
}: AnalyticsHubViewProps) {
  const [subTab, setSubTab] = useState<AnalyticsSubTab>(initialSubTab);

  return (
    <div style={{ paddingTop: '28px' }}>
      {/* Header & Sub-Tab Navigation Bar */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
          marginBottom: '24px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.72rem',
                fontWeight: 700,
                backgroundColor: '#EFF6FF',
                color: '#1D4ED8',
                padding: '2px 8px',
                borderRadius: '999px',
                border: '1px solid #BFDBFE',
              }}
            >
              <LineChart size={12} /> ENTERPRISE VISUAL INTELLIGENCE
            </span>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              &bull; Interactive Trajectories, PSI Drift &amp; Power BI Suite
            </span>
          </div>
          <h2
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: '#111827',
              fontFamily: "'DM Serif Display', Georgia, serif",
            }}
          >
            Analytics &amp; Visual BI Suite
          </h2>
          <p style={{ fontSize: '0.86rem', color: '#4B5563', marginTop: '4px', maxWidth: '780px' }}>
            Multi-dimensional telemetry across temporal cohorts, statistical drift vectors, Trojan Horse defects,
            and exportable enterprise Power BI reporting.
          </p>
        </div>

        {/* View Switcher Pills */}
        <div
          role="tablist"
          aria-label="Analytics view options"
          style={{
            display: 'inline-flex',
            backgroundColor: '#F3F4F6',
            borderRadius: '10px',
            padding: '4px',
            border: '1px solid #E5E7EB',
            gap: '4px',
          }}
        >
          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'curves'}
            onClick={() => setSubTab('curves')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '7px',
              fontSize: '0.8rem',
              fontWeight: subTab === 'curves' ? 700 : 500,
              color: subTab === 'curves' ? '#0F382E' : '#4B5563',
              backgroundColor: subTab === 'curves' ? '#FFFFFF' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              boxShadow: subTab === 'curves' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <LineChart size={14} style={{ color: subTab === 'curves' ? '#047857' : '#6B7280' }} />
            <span>Deep-Dive Curves</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'drift'}
            onClick={() => setSubTab('drift')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '7px',
              fontSize: '0.8rem',
              fontWeight: subTab === 'drift' ? 700 : 500,
              color: subTab === 'drift' ? '#0F382E' : '#4B5563',
              backgroundColor: subTab === 'drift' ? '#FFFFFF' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              boxShadow: subTab === 'drift' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <TrendingUp size={14} style={{ color: subTab === 'drift' ? '#D97706' : '#6B7280' }} />
            <span>Drift &amp; PSI Radar</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={subTab === 'powerbi'}
            onClick={() => setSubTab('powerbi')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 14px',
              borderRadius: '7px',
              fontSize: '0.8rem',
              fontWeight: subTab === 'powerbi' ? 700 : 500,
              color: subTab === 'powerbi' ? '#0F382E' : '#4B5563',
              backgroundColor: subTab === 'powerbi' ? '#FFFFFF' : 'transparent',
              border: 'none',
              cursor: 'pointer',
              boxShadow: subTab === 'powerbi' ? '0 1px 3px rgba(0,0,0,0.08)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            <BarChart3 size={14} style={{ color: subTab === 'powerbi' ? '#2563EB' : '#6B7280' }} />
            <span>Power BI Suite</span>
          </button>
        </div>
      </div>

      {/* Dynamic Sub-Tab View */}
      {subTab === 'curves' && (
        <VisualAnalyticsView
          activeDomain={activeDomain}
          onInspectVerbatims={onInspectVerbatims}
          onDispatchTicket={onDispatchTicket}
        />
      )}

      {subTab === 'drift' && (
        <div>
          {/* Defect Injection Simulator */}
          <AnomalySimulatorBanner
            onAnomalyInjected={onRefreshData}
            onReset={onRefreshData}
          />

          {driftData ? (
            <DriftTimeline driftData={driftData} />
          ) : (
            <p style={{ fontSize: '0.84rem', color: '#6B7280', marginTop: '16px' }}>
              {isLoading ? 'Loading drift telemetry…' : 'No drift telemetry is available for this dataset.'}
            </p>
          )}
        </div>
      )}

      {subTab === 'powerbi' && (
        <PowerBIView
          overview={overview}
          themes={themes}
          driftData={driftData}
          activeDomain={activeDomain}
          onInspectVerbatims={(clusterId, title) => onInspectVerbatims?.(clusterId, title)}
        />
      )}
    </div>
  );
});

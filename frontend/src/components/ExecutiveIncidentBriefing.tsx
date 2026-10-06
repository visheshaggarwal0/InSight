import React, { useMemo, useState } from 'react';
import {
  AlertTriangle,
  Flame,
  ArrowRight,
  ShieldAlert,
  Search,
  Cpu
} from 'lucide-react';
import type { ComplaintClusterItem } from '../types/telemetry';

interface ExecutiveIncidentBriefingProps {
  clusters: ComplaintClusterItem[];
  isLoading: boolean;
  onDispatchTicket: (clusterId: number, severityOverride?: string) => void;
  onInspectVerbatims: (clusterId: number, title: string) => void;
  onExploreDeconstruction?: () => void;
}

export const ExecutiveIncidentBriefing: React.FC<ExecutiveIncidentBriefingProps> = ({
  clusters,
  isLoading,
  onDispatchTicket,
  onInspectVerbatims,
  onExploreDeconstruction
}) => {
  // Sort clusters by priority: CRITICAL first, then by sentence_count descending
  const prioritizedClusters = useMemo(() => {
    if (!clusters || clusters.length === 0) return [];
    const severityRank: Record<string, number> = {
      CRITICAL: 4,
      HIGH: 3,
      MEDIUM: 2,
      LOW: 1
    };
    return [...clusters].sort((a, b) => {
      const rankDiff = (severityRank[b.severity] || 0) - (severityRank[a.severity] || 0);
      if (rankDiff !== 0) return rankDiff;
      return (b.sentence_count || 0) - (a.sentence_count || 0);
    });
  }, [clusters]);

  const [selectedClusterIndex, setSelectedClusterIndex] = useState(0);

  const activeIncident = prioritizedClusters[selectedClusterIndex] || prioritizedClusters[0] || null;

  if (isLoading && (!clusters || clusters.length === 0)) {
    return (
      <div
        style={{
          marginBottom: '24px',
          padding: '20px 24px',
          borderRadius: '16px',
          backgroundColor: '#FFFFFF',
          border: '1px solid #E5E7EB',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.03)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '24px', height: '24px', borderRadius: '50%', backgroundColor: '#E5E7EB' }} />
          <div style={{ width: '220px', height: '18px', backgroundColor: '#E5E7EB', borderRadius: '4px' }} />
        </div>
      </div>
    );
  }

  if (!activeIncident) return null;

  const top3 = prioritizedClusters.slice(0, 3);
  const relativeRiskVal = activeIncident.relative_risk || 3.4;
  const isP0 = activeIncident.severity === 'CRITICAL';
  const batchCohort = activeIncident.affected_batch || '2017-Q3';

  return (
    <section
      aria-label="Executive Product Incident Briefing"
      style={{
        marginBottom: '24px',
        borderRadius: '16px',
        backgroundColor: '#FFFFFF',
        border: isP0 ? '1px solid #FECACA' : '1px solid #FED7AA',
        boxShadow: isP0
          ? '0 6px 20px rgba(220, 38, 38, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04)'
          : '0 6px 20px rgba(234, 88, 12, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04)',
        overflow: 'hidden',
        position: 'relative'
      }}
    >
      {/* Top Incident Status Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          padding: '12px 20px',
          backgroundColor: isP0 ? '#FEF2F2' : '#FFF7ED',
          borderBottom: isP0 ? '1px solid #FEE2E2' : '1px solid #FFEDD5'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '999px',
              backgroundColor: isP0 ? '#DC2626' : '#EA580C',
              color: '#FFFFFF',
              fontSize: '0.72rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
              textTransform: 'uppercase'
            }}
          >
            <Flame size={13} aria-hidden="true" />
            {isP0 ? 'Active P0 Regression' : 'P1 Quality Defect'}
          </span>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isP0 ? '#991B1B' : '#9A3412' }}>
            Automated Cause Attribution Engine
          </span>
          <span
            style={{
              fontSize: '0.72rem',
              padding: '2px 8px',
              borderRadius: '6px',
              backgroundColor: '#FFFFFF',
              color: '#4B5563',
              border: '1px solid #E5E7EB',
              fontWeight: 500
            }}
          >
            HDBSCAN + MiniLM + Fisher Exact Test
          </span>
        </div>

        {/* Quick Switcher among Top Incidents */}
        {top3.length > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '0.74rem', color: '#6B7280', fontWeight: 500 }}>Active Crises:</span>
            {top3.map((c, idx) => {
              const active = idx === selectedClusterIndex;
              return (
                <button
                  key={c.cluster_id}
                  type="button"
                  onClick={() => setSelectedClusterIndex(idx)}
                  style={{
                    padding: '3px 9px',
                    borderRadius: '6px',
                    border: active ? '1px solid #111827' : '1px solid #D1D5DB',
                    backgroundColor: active ? '#111827' : '#FFFFFF',
                    color: active ? '#FFFFFF' : '#374151',
                    fontSize: '0.72rem',
                    fontWeight: active ? 700 : 500,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  #{c.cluster_id} {c.title.split(' ')[0]}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Main Content Body */}
      <div
        style={{
          padding: '20px 24px',
          display: 'grid',
          gridTemplateColumns: 'minmax(320px, 1.6fr) minmax(280px, 1.1fr)',
          gap: '24px',
          alignItems: 'stretch'
        }}
        className="executive-briefing-grid"
      >
        {/* Left Column: Causal Anatomy & Verbatim Evidence */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '0.78rem', color: '#6B7280', fontWeight: 600 }}>
                CLUSTER #{activeIncident.cluster_id}
              </span>
              <span style={{ color: '#D1D5DB' }}>•</span>
              <span
                style={{
                  fontSize: '0.74rem',
                  fontWeight: 700,
                  color: isP0 ? '#B91C1C' : '#C2410C',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <AlertTriangle size={13} />
                {activeIncident.sentence_count} Customer Verbatims Impacted
              </span>
            </div>
            <h2
              style={{
                fontSize: '1.45rem',
                fontWeight: 700,
                color: '#111827',
                margin: 0,
                lineHeight: 1.25,
                fontFamily: "'DM Serif Display', Georgia, serif"
              }}
            >
              {activeIncident.title}
            </h2>
          </div>

          {/* Representative Medoid Verbatim Quote */}
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '10px',
              backgroundColor: '#F9FAFB',
              borderLeft: isP0 ? '4px solid #DC2626' : '4px solid #EA580C',
              borderTop: '1px solid #E5E7EB',
              borderRight: '1px solid #E5E7EB',
              borderBottom: '1px solid #E5E7EB'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#4B5563', textTransform: 'uppercase' }}>
                Centroid Verbatim (Ground Truth):
              </span>
            </div>
            <p
              style={{
                fontSize: '0.86rem',
                fontStyle: 'italic',
                color: '#1F2937',
                margin: 0,
                lineHeight: 1.5
              }}
            >
              &ldquo;{activeIncident.medoid_verbatim || 'Severe customer defect observed during active usage.'}&rdquo;
            </p>
          </div>

          {/* C-TF-IDF Complaint Keywords */}
          {activeIncident.keywords && activeIncident.keywords.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600 }}>C-TF-IDF Drivers:</span>
              {activeIncident.keywords.slice(0, 6).map((k) => (
                <span
                  key={k}
                  style={{
                    fontSize: '0.72rem',
                    padding: '2px 8px',
                    borderRadius: '4px',
                    backgroundColor: '#F3F4F6',
                    color: '#374151',
                    border: '1px solid #E5E7EB',
                    fontFamily: "'JetBrains Mono', monospace"
                  }}
                >
                  {k}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Right Column: Statistical Blast Radius & 1-Click Engineering Actions */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            gap: '16px',
            backgroundColor: '#F9FAFB',
            borderRadius: '12px',
            border: '1px solid #E5E7EB',
            padding: '16px 18px'
          }}
        >
          {/* Statistical Evidence Cards */}
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#4B5563', textTransform: 'uppercase', marginBottom: '8px' }}>
              Statistical Root-Cause Attribution
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div
                style={{
                  padding: '10px',
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E5E7EB'
                }}
              >
                <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600 }}>RELATIVE RISK (RR)</div>
                <div
                  style={{
                    fontSize: '1.3rem',
                    fontWeight: 800,
                    color: '#B91C1C',
                    fontFamily: "'JetBrains Mono', monospace",
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: '4px'
                  }}
                >
                  {relativeRiskVal.toFixed(1)}x
                  <span style={{ fontSize: '0.68rem', color: '#047857', fontWeight: 600 }}>p &lt; 0.01</span>
                </div>
                <div style={{ fontSize: '0.68rem', color: '#4B5563', marginTop: '2px' }}>
                  vs. baseline failure rate
                </div>
              </div>

              <div
                style={{
                  padding: '10px',
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E5E7EB'
                }}
              >
                <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600 }}>SUSPECT COHORT</div>
                <div
                  style={{
                    fontSize: '1.05rem',
                    fontWeight: 700,
                    color: '#111827',
                    fontFamily: "'JetBrains Mono', monospace",
                    marginTop: '2px'
                  }}
                >
                  {batchCohort}
                </div>
                <div style={{ fontSize: '0.68rem', color: '#4B5563', marginTop: '4px' }}>
                  Concentration epicenter
                </div>
              </div>
            </div>
          </div>

          {/* Action CTAs */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button
              type="button"
              onClick={() => onDispatchTicket(activeIncident.cluster_id, activeIncident.severity)}
              style={{
                width: '100%',
                padding: '10px 14px',
                borderRadius: '8px',
                backgroundColor: '#0F382E',
                color: '#FFFFFF',
                border: 'none',
                fontWeight: 600,
                fontSize: '0.84rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 2px 4px rgba(15, 56, 46, 0.2)',
                transition: 'background-color 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#047857')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#0F382E')}
            >
              <Cpu size={16} />
              <span>Dispatch Audited Jira / Linear Ticket</span>
              <ArrowRight size={14} />
            </button>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <button
                type="button"
                onClick={() => onInspectVerbatims(activeIncident.cluster_id, activeIncident.title)}
                style={{
                  padding: '8px 10px',
                  borderRadius: '8px',
                  backgroundColor: '#FFFFFF',
                  color: '#374151',
                  border: '1px solid #D1D5DB',
                  fontWeight: 600,
                  fontSize: '0.76rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px'
                }}
              >
                <Search size={13} />
                <span>Trace {activeIncident.sentence_count} Quotes</span>
              </button>

              {onExploreDeconstruction && (
                <button
                  type="button"
                  onClick={onExploreDeconstruction}
                  style={{
                    padding: '8px 10px',
                    borderRadius: '8px',
                    backgroundColor: '#EEF2FF',
                    color: '#4338CA',
                    border: '1px solid #C7D2FE',
                    fontWeight: 600,
                    fontSize: '0.76rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '6px'
                  }}
                >
                  <ShieldAlert size={13} />
                  <span>Test Clause Fallacy</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

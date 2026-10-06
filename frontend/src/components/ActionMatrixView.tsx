import { useEffect, useState } from 'react';
import {
  Kanban,
  Zap,
  ShieldAlert,
  Sliders,
  Sparkles,
  Send,
  Loader2,
  CheckCircle2
} from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type { ActionMatrixResponse, ActionMatrixItem } from '../types/telemetry';

interface ActionMatrixViewProps {
  onDispatchTicket?: (item: ActionMatrixItem) => void;
}

export function ActionMatrixView({ onDispatchTicket }: ActionMatrixViewProps) {
  const [data, setData] = useState<ActionMatrixResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [dispatchedIds, setDispatchedIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    setLoading(true);
    apiFetch('/action/matrix')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((matrix: ActionMatrixResponse) => {
        setData(matrix);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load action matrix');
      })
      .finally(() => setLoading(false));
  }, []);

  function handleDispatch(item: ActionMatrixItem) {
    setDispatchedIds((prev) => new Set([...prev, item.id]));
    if (onDispatchTicket) {
      onDispatchTicket(item);
    }
  }

  return (
    <div style={{ paddingTop: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Title */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: '#EEF2FF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Kanban size={20} style={{ color: '#4F46E5' }} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', margin: 0, fontFamily: "'DM Serif Display', Georgia, serif" }}>
              Action &amp; CSAT ROI Prioritization Matrix
            </h2>
            <p style={{ fontSize: '0.84rem', color: '#6B7280', margin: '2px 0 0 0' }}>
              Impact vs Effort 2&times;2 quadrant optimization: translate 10,000 reviews into immediate engineering sprints.
            </p>
          </div>
        </div>
      </div>

      {loading && (
        <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <Loader2 size={32} className="spin" style={{ color: '#0F382E' }} />
          <div style={{ fontSize: '0.86rem', color: '#4B5563' }}>Optimizing defect backlog against CSAT lift…</div>
        </div>
      )}

      {error && (
        <div style={{ padding: '14px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px', color: '#991B1B' }}>
          ⚠️ {error}
        </div>
      )}

      {data && !loading && (
        <>
          {/* Executive CSAT Lift Banner */}
          <div
            style={{
              padding: '20px 24px',
              background: 'linear-gradient(135deg, #0F382E 0%, #164E40 100%)',
              color: '#FFFFFF',
              borderRadius: '18px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '16px',
              boxShadow: '0 4px 14px rgba(15, 56, 46, 0.15)'
            }}
          >
            <div>
              <span
                style={{
                  fontSize: '0.7rem',
                  fontWeight: 700,
                  letterSpacing: '0.05em',
                  backgroundColor: 'rgba(255, 255, 255, 0.15)',
                  padding: '3px 10px',
                  borderRadius: '999px',
                  border: '1px solid rgba(255, 255, 255, 0.25)'
                }}
              >
                PREDICTIVE CSAT OPTIMIZATION
              </span>
              <h3 style={{ fontSize: '1.25rem', fontWeight: 700, margin: '8px 0 2px 0', color: '#FFFFFF' }}>
                Potential CSAT Uplift: <span style={{ color: '#6EE7B7' }}>{data.max_potential_lift}</span>
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#D1FAE5', margin: 0 }}>
                Resolving the prioritized defect backlog elevates product rating from <strong>{data.baseline_csat}★</strong> to <strong>{data.projected_target_csat}★</strong>.
              </p>
            </div>

            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{ padding: '10px 16px', backgroundColor: 'rgba(255, 255, 255, 0.12)', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.2)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: '#A7F3D0', fontWeight: 600 }}>BASELINE</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#FFFFFF', fontFamily: "'JetBrains Mono', monospace" }}>{data.baseline_csat}★</div>
              </div>
              <div style={{ padding: '10px 16px', backgroundColor: 'rgba(16, 185, 129, 0.25)', borderRadius: '12px', border: '1px solid #10B981', textAlign: 'center' }}>
                <div style={{ fontSize: '0.68rem', color: '#D1FAE5', fontWeight: 600 }}>TARGET CSAT</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#6EE7B7', fontFamily: "'JetBrains Mono', monospace" }}>{data.projected_target_csat}★</div>
              </div>
            </div>
          </div>

          {/* 4 Quadrants Summary Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <div style={{ padding: '14px 16px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 700, color: '#065F46' }}>
                <Zap size={14} /> QUICK WINS (HIGH ROI)
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#047857', marginTop: '4px', fontFamily: "'JetBrains Mono', monospace" }}>
                {data.quadrant_counts.quick_wins} Defect Clusters
              </div>
              <div style={{ fontSize: '0.72rem', color: '#064E3B' }}>High CSAT lift, low implementation friction</div>
            </div>

            <div style={{ padding: '14px 16px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 700, color: '#991B1B' }}>
                <ShieldAlert size={14} /> CRITICAL BLOCKERS (P0)
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#DC2626', marginTop: '4px', fontFamily: "'JetBrains Mono', monospace" }}>
                {data.quadrant_counts.critical_blockers} Clusters
              </div>
              <div style={{ fontSize: '0.72rem', color: '#7F1D1D' }}>Severe user churn &amp; brand reputation risk</div>
            </div>

            <div style={{ padding: '14px 16px', backgroundColor: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 700, color: '#3730A3' }}>
                <Sliders size={14} /> STRATEGIC REVAMP
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#4338CA', marginTop: '4px', fontFamily: "'JetBrains Mono', monospace" }}>
                {data.quadrant_counts.strategic_revamp} Clusters
              </div>
              <div style={{ fontSize: '0.72rem', color: '#312E81' }}>Deep architectural or formulation fix</div>
            </div>

            <div style={{ padding: '14px 16px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 700, color: '#4B5563' }}>
                <Sparkles size={14} /> QUALITY OF LIFE
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#374151', marginTop: '4px', fontFamily: "'JetBrains Mono', monospace" }}>
                {data.quadrant_counts.quality_of_life} Clusters
              </div>
              <div style={{ fontSize: '0.72rem', color: '#6B7280' }}>Minor polish &amp; incremental copy tweaks</div>
            </div>
          </div>

          {/* Sprint Prioritization Table */}
          <div style={{ backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #E5E7EB', overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
              <div>
                <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                  Prioritized Engineering Backlog (Ranked by Impact Score)
                </h4>
                <p style={{ fontSize: '0.78rem', color: '#6B7280', margin: '2px 0 0 0' }}>
                  Auto-calculated story points, blast radius, and projected retention ROI.
                </p>
              </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                <thead>
                  <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB', color: '#6B7280', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                    <th style={{ padding: '12px 16px' }}>Defect Pattern</th>
                    <th style={{ padding: '12px 16px' }}>Severity</th>
                    <th style={{ padding: '12px 16px' }}>Quadrant</th>
                    <th style={{ padding: '12px 16px' }}>CSAT Uplift</th>
                    <th style={{ padding: '12px 16px' }}>Story Pts</th>
                    <th style={{ padding: '12px 16px' }}>Retention ROI</th>
                    <th style={{ padding: '12px 16px' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.slice(0, 8).map((item) => (
                    <tr key={item.id} style={{ borderBottom: '1px solid #F3F4F6' }}>
                      <td style={{ padding: '12px 16px' }}>
                        <div style={{ fontWeight: 700, color: '#111827' }}>{item.title}</div>
                        <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                          {item.incident_count} customer citations &bull; {item.recommendation}
                        </div>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '4px',
                            backgroundColor: item.severity === 'P0' || item.severity === 'CRITICAL' ? '#FEF2F2' : (item.severity === 'P1' || item.severity === 'HIGH' ? '#FFFBEB' : '#F3F4F6'),
                            color: item.severity === 'P0' || item.severity === 'CRITICAL' ? '#991B1B' : (item.severity === 'P1' || item.severity === 'HIGH' ? '#92400E' : '#374151')
                          }}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: '999px',
                            backgroundColor: item.quadrant === 'QUICK_WIN' ? '#ECFDF5' : (item.quadrant === 'CRITICAL_BLOCKER' ? '#FEF2F2' : '#EEF2FF'),
                            color: item.quadrant === 'QUICK_WIN' ? '#065F46' : (item.quadrant === 'CRITICAL_BLOCKER' ? '#991B1B' : '#3730A3')
                          }}
                        >
                          {item.quadrant.replace('_', ' ')}
                        </span>
                      </td>
                      <td style={{ padding: '12px 16px', fontWeight: 700, color: '#059669', fontFamily: "'JetBrains Mono', monospace" }}>
                        {item.projected_csat_lift}
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#4B5563' }}>
                        {item.story_points} pts
                      </td>
                      <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 600, color: '#111827' }}>
                        {item.estimated_retention_roi}
                      </td>
                      <td style={{ padding: '12px 16px' }}>
                        <button
                          type="button"
                          onClick={() => handleDispatch(item)}
                          disabled={dispatchedIds.has(item.id)}
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            backgroundColor: dispatchedIds.has(item.id) ? '#ECFDF5' : '#0F382E',
                            color: dispatchedIds.has(item.id) ? '#065F46' : '#FFFFFF',
                            border: dispatchedIds.has(item.id) ? '1px solid #A7F3D0' : 'none',
                            borderRadius: '6px',
                            padding: '5px 10px',
                            fontSize: '0.72rem',
                            fontWeight: 600,
                            cursor: dispatchedIds.has(item.id) ? 'default' : 'pointer'
                          }}
                        >
                          {dispatchedIds.has(item.id) ? (
                            <>
                              <CheckCircle2 size={12} /> Dispatched
                            </>
                          ) : (
                            <>
                              <Send size={12} /> Dispatch Jira
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

import React, { useState } from 'react';
import type { DriftData, BatchTimelineItem } from '../types/telemetry';
import { AlertTriangle, TrendingUp } from 'lucide-react';

interface Props {
  driftData: DriftData | null;
  onSelectBatch?: (batch: string) => void;
}

export const InteractiveTimelineChart: React.FC<Props> = ({ driftData, onSelectBatch }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!driftData || !driftData.timeline.length) return null;

  const timeline = driftData.timeline;
  const maxReviews = Math.max(...timeline.map((t) => t.review_count), 1);

  return (
    <div className="glass-panel" style={{ padding: '24px', marginBottom: '28px' }}>
      {/* Chart Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              TELEMETRY VELOCITY &amp; STABILITY
            </span>
            <span style={{ fontSize: '0.72rem', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', padding: '2px 8px', borderRadius: '12px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              Interactive PSI Engine
            </span>
          </div>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '4px', letterSpacing: '-0.01em' }}>
            Batch Sentiment Flow &amp; Drift Distribution
          </h3>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Hover over any release or batch lot to inspect sentiment ratios and Population Stability Index divergence.
          </p>
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--color-pos)' }} />
            <span>Positive</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--color-neu)' }} />
            <span>Neutral</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--color-neg)' }} />
            <span>Negative</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '14px', height: '2px', background: '#fb7185' }} />
            <span>PSI &gt; 0.25 Alert</span>
          </div>
        </div>
      </div>

      {/* Interactive Bar Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${timeline.length}, 1fr)`, gap: '16px', minHeight: '220px', alignItems: 'flex-end', paddingTop: '30px' }}>
        {timeline.map((item: BatchTimelineItem, idx: number) => {
          const isCrit = item.status === 'CRITICAL_DRIFT';
          const isMod = item.status === 'MODERATE_DRIFT';
          const isHovered = hoveredIdx === idx;
          const heightPct = Math.max(25, (item.review_count / maxReviews) * 100);

          return (
            <div
              key={idx}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
              onClick={() => onSelectBatch && onSelectBatch(item.batch_or_version)}
              style={{
                position: 'relative',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              {/* Tooltip Popup on Hover */}
              {isHovered && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '105%',
                    zIndex: 20,
                    width: '230px',
                    background: '#090d16',
                    border: '1px solid rgba(59, 130, 246, 0.4)',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    boxShadow: '0 10px 25px rgba(0,0,0,0.8), 0 0 15px rgba(59, 130, 246, 0.2)',
                    animation: 'fadeIn 0.15s ease-out',
                    pointerEvents: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #1e293b', paddingBottom: '6px', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.85rem', fontWeight: 800, color: '#60a5fa' }}>{item.batch_or_version}</span>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: isCrit ? '#fb7185' : isMod ? '#fcd34d' : '#34d399'
                      }}
                    >
                      PSI: {item.psi}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.78rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                      <span>Total Volume:</span>
                      <b style={{ color: '#fff' }}>{item.review_count.toLocaleString()}</b>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-pos)' }}>
                      <span>Positive:</span>
                      <b>{item.positive_count.toLocaleString()} ({Math.round(item.positive_count/item.review_count*100)}%)</b>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-neg)' }}>
                      <span>Negative Rate:</span>
                      <b>{item.negative_rate}%</b>
                    </div>
                  </div>

                  {isCrit && (
                    <div style={{ marginTop: '8px', paddingTop: '6px', borderTop: '1px solid rgba(225, 29, 72, 0.3)', color: '#fb7185', fontSize: '0.72rem', fontWeight: 600 }}>
                      ⚠️ Critical Regression Detected!
                    </div>
                  )}
                </div>
              )}

              {/* Top Drift Score Tag */}
              <div style={{ marginBottom: '8px', textAlign: 'center' }}>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '6px',
                    background: isCrit ? 'rgba(225, 29, 72, 0.2)' : isMod ? 'rgba(245, 158, 11, 0.2)' : 'rgba(30, 41, 59, 0.6)',
                    color: isCrit ? '#fb7185' : isMod ? '#fcd34d' : '#94a3b8',
                    border: isCrit ? '1px solid rgba(225, 29, 72, 0.5)' : '1px solid transparent'
                  }}
                >
                  PSI {item.psi}
                </span>
              </div>

              {/* Segmented Volume Stack Bar */}
              <div
                style={{
                  width: '100%',
                  maxWidth: '120px',
                  height: `${heightPct * 1.5}px`,
                  borderRadius: '10px',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column-reverse',
                  boxShadow: isCrit ? '0 0 20px rgba(225, 29, 72, 0.25)' : isHovered ? '0 0 15px rgba(59, 130, 246, 0.3)' : 'none',
                  border: isCrit ? '2px solid #e11d48' : isHovered ? '2px solid #3b82f6' : '1px solid var(--border-subtle)',
                  transition: 'all 0.2s ease',
                  background: '#101625'
                }}
              >
                {/* Positive segment */}
                <div
                  style={{
                    height: `${(item.positive_count / item.review_count) * 100}%`,
                    background: 'linear-gradient(180deg, #10b981, #059669)',
                    transition: 'height 0.3s ease'
                  }}
                />
                {/* Neutral segment */}
                <div
                  style={{
                    height: `${(item.neutral_count / item.review_count) * 100}%`,
                    background: 'linear-gradient(180deg, #f59e0b, #d97706)',
                    transition: 'height 0.3s ease'
                  }}
                />
                {/* Negative segment */}
                <div
                  style={{
                    height: `${(item.negative_count / item.review_count) * 100}%`,
                    background: isCrit
                      ? 'linear-gradient(180deg, #e11d48, #be123c)'
                      : 'linear-gradient(180deg, #f43f5e, #e11d48)',
                    transition: 'height 0.3s ease'
                  }}
                />
              </div>

              {/* Batch label footer */}
              <div style={{ marginTop: '12px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.82rem', fontWeight: 800, color: isHovered ? '#60a5fa' : 'var(--text-primary)' }}>
                  {item.batch_or_version}
                </span>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {item.review_count.toLocaleString()} revs
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Insights Footnote */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <TrendingUp size={14} color="var(--accent-blue)" />
          <span>Formula and release shifts automatically evaluated against baseline via Population Stability Index.</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fb7185' }}>
          <AlertTriangle size={14} />
          <span>PSI &ge; 0.25 triggers mandatory regression alerts.</span>
        </div>
      </div>
    </div>
  );
};

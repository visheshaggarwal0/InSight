import React, { useState } from 'react';
import type { DriftData, BatchTimelineItem } from '../types/telemetry';
import { AlertCircle, TrendingUp } from 'lucide-react';

interface Props {
  driftData: DriftData | null;
  onSelectBatch?: (batch: string) => void;
}

export const InteractiveTimelineChart: React.FC<Props> = ({ driftData, onSelectBatch }) => {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  if (!driftData || !driftData.timeline.length) return null;

  const timeline = driftData.timeline;
  const maxReviews = Math.max(...timeline.map((t) => t.review_count), 1);
  const PLOT_HEIGHT_PX = 180;
  const MIN_BAR_PX = 32;

  return (
    <div className="glass-panel" style={{ padding: '22px 24px', marginBottom: '24px' }}>
      {/* Chart Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              DISTRIBUTION &amp; STABILITY
            </span>
            <span style={{ fontSize: '0.7rem', background: '#202026', color: 'var(--text-secondary)', padding: '2px 7px', borderRadius: '5px', border: '1px solid var(--border-card)' }}>
              PSI Drift Engine
            </span>
          </div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: '4px', letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
            Batch Sentiment Flow &amp; Drift Timeline
          </h3>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Chronological progression of review volume and sentiment distribution across releases.
          </p>
        </div>

        {/* Muted Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--color-pos)' }} />
            <span>Positive</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--color-neu)' }} />
            <span>Neutral</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '2px', background: 'var(--color-neg)' }} />
            <span>Negative</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ width: '10px', height: '2px', background: 'var(--color-crit)' }} />
            <span>PSI &ge; 0.25 Alert</span>
          </div>
        </div>
      </div>

      {/* Bar Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${timeline.length}, 1fr)`, gap: '14px', minHeight: '200px', alignItems: 'flex-end', paddingTop: '24px' }}>
        {timeline.map((item: BatchTimelineItem, idx: number) => {
          const isCrit = item.status === 'CRITICAL_DRIFT';
          const isMod = item.status === 'MODERATE_DRIFT';
          const isHovered = hoveredIdx === idx;
          const reviewCount = item.review_count || 1;
          const barHeightPx = Math.max(MIN_BAR_PX, Math.round((item.review_count / maxReviews) * PLOT_HEIGHT_PX));

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
                cursor: 'pointer'
              }}
            >
              {/* Tooltip Popup */}
              {isHovered && (
                <div
                  style={{
                    position: 'absolute',
                    bottom: '105%',
                    zIndex: 20,
                    width: '210px',
                    background: '#18181b',
                    border: '1px solid #3f3f4e',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
                    animation: 'fadeIn 0.12s ease-out',
                    pointerEvents: 'none'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid #272730', paddingBottom: '5px', marginBottom: '6px' }}>
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#f4f4f5' }}>{item.batch_or_version}</span>
                    <span style={{ fontSize: '0.7rem', fontWeight: 600, color: isCrit ? 'var(--color-crit)' : isMod ? 'var(--color-neu)' : 'var(--color-pos)' }}>
                      PSI: {item.psi}
                    </span>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', fontSize: '0.75rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--text-secondary)' }}>
                      <span>Volume:</span>
                      <b style={{ color: '#fff' }}>{item.review_count.toLocaleString()}</b>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-pos)' }}>
                      <span>Positive:</span>
                      <b>{Math.round((item.positive_count / reviewCount) * 100)}%</b>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--color-neg)' }}>
                      <span>Negative Rate:</span>
                      <b>{item.negative_rate}%</b>
                    </div>
                  </div>

                  {isCrit && (
                    <div style={{ marginTop: '6px', paddingTop: '5px', borderTop: '1px solid rgba(244, 63, 94, 0.2)', color: '#fb7185', fontSize: '0.7rem', fontWeight: 600 }}>
                      ⚠️ Critical Drift Detected
                    </div>
                  )}
                </div>
              )}

              {/* PSI Score Header */}
              <div style={{ marginBottom: '6px', textAlign: 'center' }}>
                <span
                  style={{
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: isCrit ? 'var(--color-crit-bg)' : isMod ? 'var(--color-neu-bg)' : '#1e1e24',
                    color: isCrit ? '#fb7185' : isMod ? '#fcd34d' : 'var(--text-muted)',
                    border: isCrit ? '1px solid var(--color-crit-border)' : '1px solid transparent'
                  }}
                >
                  PSI {item.psi}
                </span>
              </div>

              {/* Segmented Stacked Bar */}
              <div
                style={{
                  width: '100%',
                  maxWidth: '96px',
                  height: `${barHeightPx}px`,
                  borderRadius: '6px',
                  overflow: 'hidden',
                  display: 'flex',
                  flexDirection: 'column-reverse',
                  border: isCrit ? '1px solid var(--color-crit)' : isHovered ? '1px solid #71717a' : '1px solid var(--border-card)',
                  background: '#18181b',
                  transition: 'border-color 0.15s ease'
                }}
              >
                <div style={{ height: `${(item.positive_count / reviewCount) * 100}%`, background: 'var(--color-pos)' }} />
                <div style={{ height: `${(item.neutral_count / reviewCount) * 100}%`, background: 'var(--color-neu)' }} />
                <div style={{ height: `${(item.negative_count / reviewCount) * 100}%`, background: 'var(--color-neg)' }} />
              </div>

              {/* Batch Label Footer */}
              <div style={{ marginTop: '10px', textAlign: 'center' }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: isHovered ? '#fff' : 'var(--text-secondary)' }}>
                  {item.batch_or_version}
                </span>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                  {item.review_count.toLocaleString()} revs
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.75rem', color: 'var(--text-muted)', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <TrendingUp size={13} color="var(--text-secondary)" />
          <span>Continuous Population Stability Index baseline analysis.</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', color: '#fb7185' }}>
          <AlertCircle size={13} />
          <span>PSI &ge; 0.25 indicates significant population shift.</span>
        </div>
      </div>
    </div>
  );
};

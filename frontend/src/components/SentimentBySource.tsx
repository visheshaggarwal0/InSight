import { memo } from 'react';
import { EmptyState, fmtPct } from './EmptyState';
import type { SentimentSourceItem } from '../types/telemetry';

interface SentimentBySourceProps {
  sources?: SentimentSourceItem[];
}

const BAR_HEIGHT = 170;
const SEGMENT_COLORS = ['#10B981', '#E2E8F0', '#F87171'] as const;
const SEGMENT_LABELS = ['Positive', 'Neutral', 'Negative'] as const;

function ComponentSentimentBySource({ sources }: SentimentBySourceProps) {
  const displaySources = sources ?? [];

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em', marginBottom: '8px' }}>
        Sentiment by Source
      </h3>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '22px' }}>
        {SEGMENT_LABELS.map((label, i) => (
          <span key={label} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.74rem', color: '#4B5563', fontWeight: 500 }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: SEGMENT_COLORS[i] }} />
            {label}
          </span>
        ))}
      </div>

      {/* Stacked Bars Container */}
      {displaySources.length === 0 ? (
        <EmptyState
          label="No source breakdown data."
          hint="The active dataset returned no channel attribution."
        />
      ) : (
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          height: '210px',
          padding: '0 8px'
        }}>
          {displaySources.map((src) => {
            // pos/neu/neg are independently rounded server-side, so they can sum to
            // 98-102%. Normalize against their own total so the column always fills
            // the container exactly — no gap, no clipping.
            const raw = [src.pos || 0, src.neu || 0, src.neg || 0];
            const total = raw.reduce((a, b) => a + b, 0) || 1;
            const heights = raw.map((v) => (v / total) * BAR_HEIGHT);

            return (
              <div
                key={src.label}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  flex: 1,
                  height: '100%',
                  justifyContent: 'flex-end'
                }}
              >
                {/* Stacked Column */}
                <div
                  title={`${src.label} — ${fmtPct(src.pos, 0)} positive, ${fmtPct(src.neu, 0)} neutral, ${fmtPct(src.neg, 0)} negative`}
                  style={{
                    width: '42px',
                    height: `${BAR_HEIGHT}px`,
                    display: 'flex',
                    flexDirection: 'column-reverse',
                    borderRadius: '8px',
                    overflow: 'hidden',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                  }}
                >
                  {heights.map((h, i) => (
                    <div
                      key={SEGMENT_LABELS[i]}
                      style={{
                        height: `${h}px`,
                        backgroundColor: SEGMENT_COLORS[i],
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        color: i === 1 ? '#475569' : '#FFFFFF'
                      }}
                    >
                      {h > 18 ? `${Math.round((h / BAR_HEIGHT) * 100)}%` : ''}
                    </div>
                  ))}
                </div>

                {/* Source Label */}
                <span style={{
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  color: '#6B7280',
                  marginTop: '10px',
                  textAlign: 'center'
                }}>
                  {src.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export const SentimentBySource = memo(ComponentSentimentBySource);

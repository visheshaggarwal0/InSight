import { memo } from 'react';
import { EmptyState, fmtPct } from './EmptyState';
import type { RatingDistributionItem } from '../types/telemetry';

interface RatingDistributionCardProps {
  ratings?: RatingDistributionItem[];
}

function ComponentRatingDistributionCard({ ratings }: RatingDistributionCardProps) {
  const displayRatings = ratings ?? [];
  // Normalize against the data's own max so the tallest bar is always full height.
  const maxPercent = Math.max(...displayRatings.map((r) => r.percent || 0), 0) || 1;

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 0.8 }}>
      <h3 style={{
        fontSize: '1.05rem',
        fontWeight: 700,
        color: '#111827',
        letterSpacing: '-0.01em',
        marginBottom: '20px'
      }}>
        Rating Distribution
      </h3>

      {displayRatings.length === 0 ? (
        <EmptyState
          label="No rating distribution data."
          hint="The active dataset returned no ratings."
        />
      ) : (
        <div style={{
          display: 'flex',
          alignItems: 'flex-end',
          justifyContent: 'space-between',
          height: '180px',
          padding: '0 10px',
          position: 'relative'
        }}>
          {displayRatings.map((r) => {
            const barHeight = Math.max(14, ((r.percent || 0) / maxPercent) * 130);

            return (
              <div
                key={r.star}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '8px',
                  flex: 1
                }}
              >
                {/* Percentage label */}
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  color: '#374151'
                }}>
                  {fmtPct(r.percent, 0)}
                </span>

                {/* Vertical Bar */}
                <div
                  title={`${r.star}: ${fmtPct(r.percent, 1)} (${r.count?.toLocaleString() ?? '—'} reviews)`}
                  style={{
                    width: '38px',
                    height: `${barHeight}px`,
                    backgroundColor: r.color,
                    borderRadius: '8px 8px 4px 4px',
                    transition: 'height 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.15s ease',
                    cursor: 'pointer'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = 'scaleY(1.04)';
                    e.currentTarget.style.opacity = '0.9';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'scaleY(1)';
                    e.currentTarget.style.opacity = '1';
                  }}
                />

                {/* Star label */}
                <span style={{
                  fontSize: '0.76rem',
                  fontWeight: 600,
                  color: '#6B7280',
                  marginTop: '4px'
                }}>
                  {r.star}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export const RatingDistributionCard = memo(ComponentRatingDistributionCard);

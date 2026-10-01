import { memo } from 'react';
import { ArrowRight, ArrowUpRight } from 'lucide-react';
import { EmptyState } from './EmptyState';
import { fmtPsi } from '../lib/formatters';
import type { DriftData, DynamicInsightItem } from '../types/telemetry';

interface RecentInsightsProps {
  driftData?: DriftData | null;
  insights?: DynamicInsightItem[];
  onViewDrift?: () => void;
}

const PSI_PATTERN = /([0-9]*\.?[0-9]+)/;

interface RenderItem {
  key: string;
  title: string;
  isWarning: boolean;
  /** Raw PSI index, unitless — never rendered as a percentage. */
  psi?: number;
  /** Backend-supplied non-PSI metric text (e.g. "412 reviews", "72%"). */
  metric?: string;
  period?: string;
}

function ComponentRecentInsights({ driftData, insights, onViewDrift }: RecentInsightsProps) {
  const alerts = driftData?.alerts ?? [];

  // Only real data: /overview insights, or real drift alerts when none were returned.
  const items: RenderItem[] = (insights ?? []).map((item, idx) => {
    const match = item.psiAlert ? item.psiAlert.match(PSI_PATTERN) : null;
    return {
      key: `insight-${idx}-${item.title}`,
      title: item.title,
      isWarning: item.isWarning,
      psi: match ? Number(match[1]) : undefined,
      metric: match ? undefined : (item.metric?.value ?? ''),
      period: match ? `in ${item.period.replace(/^in\s+/, '')}` : item.period
    };
  });

  const fallbackItems: RenderItem[] =
    items.length === 0
      ? alerts.map((a, idx) => ({
          key: `alert-${a.batch_or_version}-${idx}`,
          title: a.message,
          isWarning: a.severity === 'CRITICAL',
          psi: a.psi_score,
          period: `in ${a.batch_or_version}`
        }))
      : [];

  const displayItems = items.length > 0 ? items : fallbackItems;

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px'
      }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
          Recent Insights
        </h3>
        <button
          onClick={onViewDrift}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            background: 'none',
            border: 'none',
            color: '#10B981',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
          title="Inspect Statistical Drift (PSI) & Batch Breakdown"
        >
          <span>View all</span>
          <ArrowRight size={13} />
        </button>
      </div>

      {/* Insight Items */}
      {displayItems.length === 0 ? (
        <EmptyState
          label="No insights available."
          hint="No drift alerts were raised for the active dataset."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {displayItems.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={onViewDrift}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                gap: '12px',
                padding: '8px 10px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: 'transparent',
                textAlign: 'left',
                cursor: 'pointer',
                transition: 'background 0.15s ease'
              }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#F9FAFB')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
            >
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', flex: 1 }}>
                <ArrowUpRight
                  size={16}
                  strokeWidth={2.4}
                  style={{
                    color: item.isWarning ? '#EF4444' : '#10B981',
                    flexShrink: 0,
                    marginTop: '2px'
                  }}
                />
                <div>
                  <p style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: '#111827',
                    lineHeight: 1.35,
                    margin: 0
                  }}>
                    {item.title}
                  </p>
                  {item.psi !== undefined && (
                    <span style={{
                      fontSize: '0.68rem',
                      backgroundColor: '#FEF2F2',
                      color: '#991B1B',
                      padding: '1px 6px',
                      borderRadius: '4px',
                      fontWeight: 700,
                      marginTop: '4px',
                      display: 'inline-block'
                    }}>
                      PSI {fmtPsi(item.psi)} Critical Drift Alert
                    </span>
                  )}
                </div>
              </div>

              {/* Metrics */}
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                {item.psi !== undefined ? (
                  <>
                    <div style={{
                      fontSize: '0.86rem',
                      fontWeight: 700,
                      color: item.isWarning ? '#EF4444' : '#059669',
                      lineHeight: 1.1,
                      fontFamily: "'JetBrains Mono', monospace"
                    }}>
                      {fmtPsi(item.psi)}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: '#9CA3AF', marginTop: '2px', fontWeight: 700 }}>
                      PSI
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{
                      fontSize: '0.86rem',
                      fontWeight: 700,
                      color: item.isWarning ? '#EF4444' : '#059669',
                      lineHeight: 1.1
                    }}>
                      {item.metric ?? '—'}
                    </div>
                    {item.period && (
                      <div style={{ fontSize: '0.7rem', color: '#9CA3AF', marginTop: '2px' }}>
                        {item.period}
                      </div>
                    )}
                  </>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export const RecentInsights = memo(ComponentRecentInsights);

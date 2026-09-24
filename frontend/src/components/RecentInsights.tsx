import { ArrowRight, ArrowUpRight } from 'lucide-react';
import type { DriftData, DynamicInsightItem } from '../types/telemetry';

interface RecentInsightsProps {
  driftData?: DriftData | null;
  insights?: DynamicInsightItem[];
  onViewDrift?: () => void;
}

export function RecentInsights({ driftData, insights, onViewDrift }: RecentInsightsProps) {
  const firstAlert = driftData?.alerts && driftData.alerts.length > 0 ? driftData.alerts[0] : null;
  const alertPsiScore = firstAlert ? `PSI ${firstAlert.psi_score.toFixed(2)}` : null;

  const displayInsights = insights && insights.length > 0 ? insights : [
    {
      title: firstAlert ? firstAlert.message : 'Spike in skin irritation complaints in Batch-24C',
      percent: firstAlert ? `+${Math.round(firstAlert.psi_score * 100)}%` : '+48%',
      period: firstAlert ? `in ${firstAlert.batch_or_version}` : 'in Batch-24C',
      isWarning: true,
      psiAlert: alertPsiScore
    },
    {
      title: 'Packaging defect: dropper pipettes leaking on delivery',
      percent: '62 reviews',
      period: 'critical QA alert',
      isWarning: true,
      psiAlert: null
    },
    {
      title: 'Overall customer satisfaction at 72% positive sentiment',
      percent: '72%',
      period: 'across all SKUs',
      isWarning: false,
      psiAlert: null
    },
  ];

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
      <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
        {displayInsights.map((item, idx) => (
          <div
            key={idx}
            onClick={onViewDrift}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              justifyContent: 'space-between',
              gap: '12px',
              padding: '8px 10px',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'background 0.15s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#F9FAFB'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
          >
            {/* Arrow & Title */}
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
                  lineHeight: 1.35
                }}>
                  {item.title}
                </p>
                {item.psiAlert && (
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
                    {item.psiAlert} Critical Drift Alert
                  </span>
                )}
              </div>
            </div>

            {/* Metrics */}
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{
                fontSize: '0.92rem',
                fontWeight: 700,
                color: item.isWarning ? '#EF4444' : '#059669',
                lineHeight: 1.1
              }}>
                {item.percent}
              </div>
              <div style={{
                fontSize: '0.7rem',
                color: '#9CA3AF',
                marginTop: '2px'
              }}>
                {item.period}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

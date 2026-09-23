import React from 'react';
import { MessageCircle, Smile, Meh, Frown, ArrowUp, ArrowDown } from 'lucide-react';
import type { OverviewMetrics } from '../types/telemetry';

interface Props {
  metrics: OverviewMetrics | null;
  onOpenGovernance?: () => void;
}

export const OverviewCards: React.FC<Props> = ({ metrics }) => {
  if (!metrics) return null;

  const neutralRate = Math.max(0, 100 - metrics.positive_rate - metrics.negative_rate);

  const cards = [
    {
      title: 'Total Reviews',
      value: metrics.total_reviews.toLocaleString(),
      change: '12%',
      isPositive: true,
      arrow: ArrowUp,
      icon: MessageCircle,
      iconBg: '#ECFDF5',
      iconColor: '#10B981',
      changeText: 'vs. previous period'
    },
    {
      title: 'Positive Sentiment',
      value: `${metrics.positive_rate}%`,
      change: '8%',
      isPositive: true,
      arrow: ArrowUp,
      icon: Smile,
      iconBg: '#ECFDF5',
      iconColor: '#059669',
      changeText: 'vs. previous period'
    },
    {
      title: 'Neutral',
      value: `${neutralRate}%`,
      change: '4%',
      isPositive: false,
      arrow: ArrowDown,
      icon: Meh,
      iconBg: '#F3F4F6',
      iconColor: '#6B7280',
      changeText: 'vs. previous period'
    },
    {
      title: 'Negative',
      value: `${metrics.negative_rate}%`,
      change: '4%',
      isPositive: false,
      arrow: ArrowDown,
      icon: Frown,
      iconBg: '#FEF2F2',
      iconColor: '#EF4444',
      changeText: 'vs. previous period'
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
      gap: '16px',
      marginBottom: '28px'
    }}>
      {cards.map((c, i) => {
        const Icon = c.icon;
        const Arrow = c.arrow;
        return (
          <div
            key={i}
            className="dashboard-card"
            style={{
              padding: '20px 22px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between'
            }}
          >
            {/* Top Icon */}
            <div style={{
              width: '38px',
              height: '38px',
              borderRadius: '50%',
              backgroundColor: c.iconBg,
              color: c.iconColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginBottom: '14px'
            }}>
              <Icon size={20} strokeWidth={2} />
            </div>

            {/* Metric Value & Label */}
            <div>
              <div style={{
                fontSize: '1.95rem',
                fontWeight: 700,
                color: '#111827',
                letterSpacing: '-0.02em',
                lineHeight: 1.1
              }}>
                {c.value}
              </div>
              <div style={{
                fontSize: '0.82rem',
                fontWeight: 500,
                color: '#4B5563',
                marginTop: '4px',
                marginBottom: '14px'
              }}>
                {c.title}
              </div>
            </div>

            {/* Trend Indicator */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: c.isPositive ? '#059669' : '#EF4444'
            }}>
              <Arrow size={14} strokeWidth={2.5} />
              <span>{c.change}</span>
              <span style={{ color: '#9CA3AF', fontWeight: 400, marginLeft: '2px' }}>
                {c.changeText}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

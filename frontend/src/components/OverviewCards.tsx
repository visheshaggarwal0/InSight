import { memo, type FC } from 'react';
import { MessageCircle, Smile, Meh, Frown } from 'lucide-react';
import { fmtNum, fmtPct } from '../lib/formatters';
import type { OverviewMetrics } from '../types/telemetry';

interface Props {
  metrics: OverviewMetrics | null;
}

export const OverviewCards: FC<Props> = memo(({ metrics }) => {
  const formatRate = (rate: number) => fmtPct(rate, 1);

  const neutralRate = metrics
    ? Math.max(0, Math.round((100 - metrics.positive_rate - metrics.negative_rate) * 10) / 10)
    : 0;

  // The API exposes no period-over-period deltas, so no trend arrows are rendered.
  const cards = metrics
    ? [
        {
          key: 'total',
          title: 'Total Reviews',
          value: fmtNum(metrics.total_reviews),
          icon: MessageCircle,
          iconBg: '#ECFDF5',
          iconColor: '#10B981'
        },
        {
          key: 'positive',
          title: 'Positive Sentiment',
          value: formatRate(metrics.positive_rate),
          icon: Smile,
          iconBg: '#ECFDF5',
          iconColor: '#059669'
        },
        {
          key: 'neutral',
          title: 'Neutral',
          value: formatRate(neutralRate),
          icon: Meh,
          iconBg: '#F3F4F6',
          iconColor: '#6B7280'
        },
        {
          key: 'negative',
          title: 'Negative',
          value: formatRate(metrics.negative_rate),
          icon: Frown,
          iconBg: '#FEF2F2',
          iconColor: '#EF4444'
        }
      ]
    : [
        { key: 'total', title: 'Total Reviews', value: '—', icon: MessageCircle, iconBg: '#ECFDF5', iconColor: '#10B981' },
        { key: 'positive', title: 'Positive Sentiment', value: '—', icon: Smile, iconBg: '#ECFDF5', iconColor: '#059669' },
        { key: 'neutral', title: 'Neutral', value: '—', icon: Meh, iconBg: '#F3F4F6', iconColor: '#6B7280' },
        { key: 'negative', title: 'Negative', value: '—', icon: Frown, iconBg: '#FEF2F2', iconColor: '#EF4444' }
      ];

  return (
    <div className="responsive-grid-4">
      {cards.map((c) => {
        const Icon = c.icon;
        return (
          <div
            key={c.key}
            className="dashboard-card"
            style={{
              padding: '16px 18px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              minWidth: 0,
              minHeight: metrics ? undefined : '140px'
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
                marginTop: '4px'
              }}>
                {c.title}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
});

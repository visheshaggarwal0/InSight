import { memo } from 'react';
import { Eye, FileText, Quote, AlertOctagon, Star } from 'lucide-react';
import type { ThemeCluster } from '../types/telemetry';

interface Props {
  theme: ThemeCluster;
  onInspectVerbatims: (clusterId: number, themeTitle: string) => void;
  onGenerateTicket: (clusterId: number) => void;
}

export const ThemeCard = memo(function ThemeCard({
  theme,
  onInspectVerbatims,
  onGenerateTicket
}: Props) {
  const isCritical = theme.severity === 'CRITICAL';
  const isHigh = theme.severity === 'HIGH';

  const { POSITIVE, NEUTRAL, NEGATIVE } = theme.sentiment_distribution;
  const distTotal = POSITIVE + NEUTRAL + NEGATIVE;
  const share = (value: number) => (distTotal > 0 ? (value / distTotal) * 100 : 0);
  const negShare = share(NEGATIVE);
  const neuShare = share(NEUTRAL);
  const posShare = share(POSITIVE);

  const severityClass = isCritical
    ? 'badge-critical'
    : isHigh
      ? 'badge-high'
      : theme.severity === 'MEDIUM'
        ? 'badge-medium'
        : 'badge-low';

  return (
    <div
      className="dashboard-card"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '12px',
        borderLeft: isCritical
          ? '3px solid var(--color-crit)'
          : isHigh
            ? '3px solid var(--color-neg-border)'
            : '1px solid var(--border-card)'
      }}
    >
      <div>
        {/* Header: Title & Severity */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <span className={`badge ${severityClass}`}>
                {isCritical && <AlertOctagon size={11} aria-hidden="true" />}
                {theme.severity}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                &bull; Cluster #{theme.cluster_id}
              </span>
            </div>

            <h3 style={{ margin: 0, fontSize: '1.02rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: '1.35' }}>
              {theme.title}
            </h3>
          </div>

          {/* Negative Ratio Badge */}
          <div
            style={{
              textAlign: 'right',
              padding: '4px 8px',
              borderRadius: '6px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-subtle)'
            }}
          >
            <div style={{ fontSize: '1rem', fontWeight: 700, color: theme.negative_rate > 50 ? 'var(--color-neg-text)' : 'var(--text-primary)' }}>
              {theme.negative_rate}%
            </div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 500 }}>
              Negative
            </div>
          </div>
        </div>

        {/* Volume & Distribution Micro-bar */}
        <div style={{ margin: '12px 0 10px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.74rem', color: 'var(--text-muted)', marginBottom: '5px' }}>
            <span><b>{theme.review_count.toLocaleString()}</b> Verbatims</span>
            <span>
              {NEGATIVE} Neg / {NEUTRAL} Neu / {POSITIVE} Pos
            </span>
          </div>
          <div
            role="img"
            aria-label={`Sentiment split: ${NEGATIVE} negative, ${NEUTRAL} neutral, ${POSITIVE} positive`}
            style={{ display: 'flex', height: '4px', width: '100%', borderRadius: '2px', overflow: 'hidden', background: 'var(--bg-elevated)' }}
          >
            <div style={{ width: `${negShare}%`, background: 'var(--color-neg)' }} />
            <div style={{ width: `${neuShare}%`, background: 'var(--color-neu)' }} />
            <div style={{ width: `${posShare}%`, background: 'var(--color-pos)' }} />
          </div>
        </div>

        {/* c-TF-IDF Keyword Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '14px' }}>
          {theme.keywords.map((kw, i) => (
            <span
              key={`${kw}-${i}`}
              style={{
                fontSize: '0.7rem',
                fontFamily: "'JetBrains Mono', monospace",
                background: 'var(--bg-elevated)',
                color: 'var(--text-secondary)',
                padding: '2px 7px',
                borderRadius: '4px',
                border: '1px solid var(--border-subtle)'
              }}
            >
              #{kw}
            </span>
          ))}
        </div>

        {/* Masked Verbatim Quote */}
        {theme.sample_verbatims && theme.sample_verbatims.length > 0 && (() => {
          const sample = theme.sample_verbatims[0];
          return (
            <blockquote
              style={{
                margin: '0 0 16px 0',
                background: 'var(--bg-page)',
                borderLeft: '2px solid var(--border-hover)',
                padding: '10px 12px',
                borderRadius: '0 6px 6px 0'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Quote size={11} color="var(--text-muted)" aria-hidden="true" />
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                    {sample.batch_or_version} &bull; {sample.sku_or_module}
                  </span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', color: 'var(--color-amber-text)', fontSize: '0.7rem', fontWeight: 600 }}>
                  <Star size={10} fill="var(--color-amber)" aria-hidden="true" style={{ marginRight: '2px' }} />
                  {sample.rating}&star;
                </div>
              </div>

              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.45', fontStyle: 'italic' }}>
                &ldquo;{sample.text.length > 140
                  ? sample.text.substring(0, 140) + '...'
                  : sample.text}&rdquo;
              </p>
            </blockquote>
          );
        })()}
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
        <button
          type="button"
          onClick={() => onInspectVerbatims(theme.cluster_id, theme.title)}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '5px',
            padding: '7px 12px',
            borderRadius: '6px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-card)',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <Eye size={13} color="var(--text-secondary)" aria-hidden="true" />
          Trace {theme.review_count} Reviews
        </button>

        <button
          type="button"
          onClick={() => onGenerateTicket(theme.cluster_id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '5px',
            padding: '7px 12px',
            borderRadius: '6px',
            background: 'var(--color-crit-bg)',
            border: '1px solid var(--color-crit-border)',
            color: 'var(--color-crit-text)',
            fontSize: '0.78rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <FileText size={13} aria-hidden="true" />
          Draft Ticket
        </button>
      </div>
    </div>
  );
});

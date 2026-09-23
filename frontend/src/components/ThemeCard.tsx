import React from 'react';
import { Eye, FileText, Quote, AlertOctagon, Star } from 'lucide-react';
import type { ThemeCluster } from '../types/telemetry';

interface Props {
  theme: ThemeCluster;
  onInspectVerbatims: (clusterId: number, themeTitle: string) => void;
  onGenerateTicket: (clusterId: number) => void;
}

export const ThemeCard: React.FC<Props> = ({
  theme,
  onInspectVerbatims,
  onGenerateTicket
}) => {
  const isCritical = theme.severity === 'CRITICAL';
  const isHigh = theme.severity === 'HIGH';

  return (
    <div
      className="glass-card"
      style={{
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderLeft: isCritical ? '3px solid var(--color-crit)' : isHigh ? '3px solid var(--color-neg)' : '1px solid var(--border-card)'
      }}
    >
      <div>
        {/* Header: Title & Severity */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
              <span
                className={`badge ${
                  isCritical
                    ? 'badge-critical'
                    : isHigh
                    ? 'badge-high'
                    : theme.severity === 'MEDIUM'
                    ? 'badge-medium'
                    : 'badge-low'
                }`}
              >
                {isCritical && <AlertOctagon size={11} />}
                {theme.severity}
              </span>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                &bull; Cluster #{theme.cluster_id}
              </span>
            </div>

            <h3 style={{ fontSize: '1.02rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: '1.35' }}>
              {theme.title}
            </h3>
          </div>

          {/* Negative Ratio Badge */}
          <div
            style={{
              textAlign: 'right',
              padding: '4px 8px',
              borderRadius: '6px',
              background: '#1a1a22',
              border: '1px solid var(--border-subtle)'
            }}
          >
            <div style={{ fontSize: '1rem', fontWeight: 700, color: theme.negative_rate > 50 ? 'var(--color-neg)' : 'var(--text-secondary)' }}>
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
            <span>{theme.sentiment_distribution.NEGATIVE} Neg / {theme.sentiment_distribution.POSITIVE} Pos</span>
          </div>
          <div style={{ display: 'flex', height: '3px', width: '100%', borderRadius: '2px', overflow: 'hidden', background: '#202026' }}>
            <div style={{ width: `${theme.negative_rate}%`, background: 'var(--color-neg)' }} />
            <div style={{ width: `${100 - theme.negative_rate}%`, background: 'var(--color-pos)' }} />
          </div>
        </div>

        {/* c-TF-IDF Keyword Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '14px' }}>
          {theme.keywords.map((kw, i) => (
            <span
              key={i}
              style={{
                fontSize: '0.7rem',
                fontFamily: "'JetBrains Mono', monospace",
                background: '#191920',
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
        {theme.sample_verbatims.length > 0 && (
          <div
            style={{
              background: '#101015',
              borderLeft: '2px solid var(--border-hover)',
              padding: '10px 12px',
              borderRadius: '0 6px 6px 0',
              marginBottom: '16px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                <Quote size={11} color="var(--text-muted)" />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 500 }}>
                  {theme.sample_verbatims[0].batch_or_version} &bull; {theme.sample_verbatims[0].sku_or_module}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.7rem', fontWeight: 600 }}>
                <Star size={10} fill="#fbbf24" style={{ marginRight: '2px' }} />
                {theme.sample_verbatims[0].rating}★
              </div>
            </div>

            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.45', fontStyle: 'italic' }}>
              "{theme.sample_verbatims[0].text.length > 140
                ? theme.sample_verbatims[0].text.substring(0, 140) + '...'
                : theme.sample_verbatims[0].text}"
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
        <button
          onClick={() => onInspectVerbatims(theme.cluster_id, theme.title)}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '5px',
            padding: '7px 12px',
            borderRadius: '6px',
            background: '#1a1a22',
            border: '1px solid var(--border-card)',
            color: 'var(--text-primary)',
            fontSize: '0.78rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <Eye size={13} color="var(--text-secondary)" />
          Trace {theme.review_count} Reviews
        </button>

        <button
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
            color: '#fb7185',
            fontSize: '0.78rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <FileText size={13} />
          Draft Ticket
        </button>
      </div>
    </div>
  );
};

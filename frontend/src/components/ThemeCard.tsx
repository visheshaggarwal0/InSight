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

  const severityColor = isCritical ? 'var(--color-crit)' : isHigh ? 'var(--color-neg)' : theme.severity === 'MEDIUM' ? 'var(--color-neu)' : 'var(--color-pos)';

  return (
    <div
      className="glass-card"
      style={{
        padding: '22px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        borderLeft: `4px solid ${severityColor}`
      }}
    >
      <div>
        {/* Header: Title & Severity */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
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
                {isCritical && <AlertOctagon size={12} />}
                {theme.severity} SEVERITY
              </span>
              <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                • Cluster #{theme.cluster_id}
              </span>
            </div>

            <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fff', letterSpacing: '-0.01em', lineHeight: '1.3' }}>
              {theme.title}
            </h3>
          </div>

          {/* Negative Ratio Dial */}
          <div
            style={{
              textAlign: 'right',
              padding: '6px 10px',
              borderRadius: '8px',
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid var(--border-subtle)'
            }}
          >
            <div style={{ fontSize: '1.15rem', fontWeight: 800, color: theme.negative_rate > 50 ? '#fb7185' : 'var(--text-secondary)' }}>
              {theme.negative_rate}%
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Negative
            </div>
          </div>
        </div>

        {/* Volume & Distribution Micro-bar */}
        <div style={{ margin: '14px 0 12px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.76rem', color: 'var(--text-secondary)', marginBottom: '5px' }}>
            <span><b>{theme.review_count.toLocaleString()}</b> Customer Verbatims</span>
            <span>{theme.sentiment_distribution.NEGATIVE} Neg / {theme.sentiment_distribution.POSITIVE} Pos</span>
          </div>
          <div style={{ display: 'flex', height: '5px', width: '100%', borderRadius: '3px', overflow: 'hidden', background: '#111827' }}>
            <div style={{ width: `${theme.negative_rate}%`, background: 'var(--color-neg)' }} />
            <div style={{ width: `${100 - theme.negative_rate}%`, background: 'var(--color-pos)' }} />
          </div>
        </div>

        {/* c-TF-IDF Keyword Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '16px' }}>
          {theme.keywords.map((kw, i) => (
            <span
              key={i}
              style={{
                fontSize: '0.72rem',
                fontFamily: "'JetBrains Mono', monospace",
                background: 'rgba(30, 41, 59, 0.6)',
                color: '#93c5fd',
                padding: '2px 8px',
                borderRadius: '5px',
                border: '1px solid rgba(59, 130, 246, 0.2)'
              }}
            >
              #{kw}
            </span>
          ))}
        </div>

        {/* Representative Masked Verbatim Quote */}
        {theme.sample_verbatims.length > 0 && (
          <div
            style={{
              background: 'rgba(9, 13, 22, 0.7)',
              borderLeft: `3px solid ${severityColor}`,
              padding: '12px 14px',
              borderRadius: '0 8px 8px 0',
              marginBottom: '18px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Quote size={12} color="var(--accent-blue)" />
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                  {theme.sample_verbatims[0].batch_or_version} • {theme.sample_verbatims[0].sku_or_module}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.72rem', fontWeight: 700 }}>
                <Star size={11} fill="#fbbf24" style={{ marginRight: '2px' }} />
                {theme.sample_verbatims[0].rating}★
              </div>
            </div>

            <p style={{ fontSize: '0.82rem', color: '#cbd5e1', lineHeight: '1.45', fontStyle: 'italic' }}>
              "{theme.sample_verbatims[0].text.length > 150
                ? theme.sample_verbatims[0].text.substring(0, 150) + '...'
                : theme.sample_verbatims[0].text}"
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
        <button
          onClick={() => onInspectVerbatims(theme.cluster_id, theme.title)}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '9px 14px',
            borderRadius: '8px',
            background: 'rgba(59, 130, 246, 0.12)',
            border: '1px solid rgba(59, 130, 246, 0.35)',
            color: '#60a5fa',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <Eye size={15} />
          Trace {theme.review_count} Reviews
        </button>

        <button
          onClick={() => onGenerateTicket(theme.cluster_id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '9px 14px',
            borderRadius: '8px',
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.35)',
            color: '#fb7185',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
        >
          <FileText size={15} />
          Draft Ticket
        </button>
      </div>
    </div>
  );
};

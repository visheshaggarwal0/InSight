import React from 'react';
import { Eye, FileText, Quote } from 'lucide-react';
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
  const getBadgeClass = (severity: string) => {
    switch (severity) {
      case 'CRITICAL': return 'badge badge-critical';
      case 'HIGH': return 'badge badge-high';
      case 'MEDIUM': return 'badge badge-medium';
      default: return 'badge badge-low';
    }
  };

  return (
    <div className="glass-card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
      <div>
        {/* Header: Title & Severity */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {theme.title}
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '6px' }}>
              <span className={getBadgeClass(theme.severity)}>
                {theme.severity} SEVERITY
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                • {theme.review_count.toLocaleString()} customer verbatims
              </span>
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '1.2rem', fontWeight: 800, color: theme.negative_rate > 50 ? 'var(--status-neg)' : 'var(--text-secondary)' }}>
              {theme.negative_rate}%
            </span>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Negative Rate
            </div>
          </div>
        </div>

        {/* Semantic Keyword Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', margin: '14px 0' }}>
          {theme.keywords.map((kw, i) => (
            <span
              key={i}
              style={{
                fontSize: '0.74rem',
                background: 'rgba(30, 41, 59, 0.7)',
                color: '#94a3b8',
                padding: '2px 8px',
                borderRadius: '4px',
                border: '1px solid #2d3748'
              }}
            >
              #{kw}
            </span>
          ))}
        </div>

        {/* Sample Customer Verbatim */}
        {theme.sample_verbatims.length > 0 && (
          <div
            style={{
              background: 'rgba(10, 14, 23, 0.6)',
              borderLeft: `3px solid ${theme.severity === 'CRITICAL' ? 'var(--status-crit)' : 'var(--accent-blue)'}`,
              padding: '10px 12px',
              borderRadius: '0 6px 6px 0',
              marginBottom: '16px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <Quote size={12} color="var(--text-muted)" />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                {theme.sample_verbatims[0].batch_or_version} • {theme.sample_verbatims[0].rating}★
              </span>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: '1.4', fontStyle: 'italic' }}>
              "{theme.sample_verbatims[0].text.length > 140
                ? theme.sample_verbatims[0].text.substring(0, 140) + '...'
                : theme.sample_verbatims[0].text}"
            </p>
          </div>
        )}
      </div>

      {/* Action Footer */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
        <button
          onClick={() => onInspectVerbatims(theme.cluster_id, theme.title)}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '8px 12px',
            borderRadius: '6px',
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            color: '#60a5fa',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <Eye size={14} />
          Trace Reviews
        </button>

        <button
          onClick={() => onGenerateTicket(theme.cluster_id)}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '6px',
            padding: '8px 12px',
            borderRadius: '6px',
            background: 'rgba(244, 63, 94, 0.1)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            color: '#fb7185',
            fontSize: '0.8rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          <FileText size={14} />
          Draft Ticket
        </button>
      </div>
    </div>
  );
};

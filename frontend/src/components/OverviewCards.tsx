import React from 'react';
import { MessageSquare, ShieldCheck, TrendingUp, BarChart2 } from 'lucide-react';
import type { OverviewMetrics } from '../types/telemetry';

interface Props {
  metrics: OverviewMetrics | null;
  onOpenGovernance: () => void;
}

export const OverviewCards: React.FC<Props> = ({ metrics, onOpenGovernance }) => {
  if (!metrics) return null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', marginBottom: '24px' }}>
      {/* 1. Total Volume */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>TOTAL TELEMETRY</span>
          <MessageSquare size={18} color="var(--accent-blue)" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '8px', color: 'var(--text-primary)' }}>
          {metrics.total_reviews.toLocaleString()}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          100% indexed & clustered
        </div>
      </div>

      {/* 2. Sentiment Polarity */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>SENTIMENT POLARITY</span>
          <TrendingUp size={18} color="var(--status-pos)" />
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '8px' }}>
          <span style={{ fontSize: '1.8rem', fontWeight: 800, color: 'var(--status-pos)' }}>
            {metrics.positive_rate}%
          </span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            / {metrics.negative_rate}% neg
          </span>
        </div>
        <div style={{ display: 'flex', height: '6px', width: '100%', borderRadius: '3px', overflow: 'hidden', marginTop: '10px', background: '#1e293b' }}>
          <div style={{ width: `${metrics.positive_rate}%`, background: 'var(--status-pos)' }} />
          <div style={{ width: `${100 - metrics.positive_rate - metrics.negative_rate}%`, background: 'var(--status-neu)' }} />
          <div style={{ width: `${metrics.negative_rate}%`, background: 'var(--status-neg)' }} />
        </div>
      </div>

      {/* 3. PII Scrubbing Compliance */}
      <div className="glass-card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>PII PRIVACY GATE</span>
          <ShieldCheck size={18} color="#a78bfa" />
        </div>
        <div style={{ fontSize: '1.8rem', fontWeight: 800, marginTop: '8px', color: '#c4b5fd' }}>
          {metrics.pii_redacted_count.toLocaleString()}
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          {metrics.pii_redacted_rate}% masked (GDPR/CCPA compliant)
        </div>
      </div>

      {/* 4. Model Governance & Accuracy Button */}
      <div
        className="glass-card"
        onClick={onOpenGovernance}
        style={{ padding: '20px', cursor: 'pointer', border: '1px solid rgba(59, 130, 246, 0.4)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-blue)' }}>MODEL GOVERNANCE</span>
          <BarChart2 size={18} color="var(--accent-blue)" />
        </div>
        <div style={{ fontSize: '1.2rem', fontWeight: 800, marginTop: '10px', color: 'var(--text-primary)' }}>
          View Validation Suite ↗
        </div>
        <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
          Confusion matrix & calibrated F1 proof
        </div>
      </div>
    </div>
  );
};

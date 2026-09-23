import React from 'react';
import { MessageSquare, ShieldCheck, TrendingUp, Award, ArrowUpRight } from 'lucide-react';
import type { OverviewMetrics } from '../types/telemetry';

interface Props {
  metrics: OverviewMetrics | null;
  onOpenGovernance: () => void;
}

export const OverviewCards: React.FC<Props> = ({ metrics, onOpenGovernance }) => {
  if (!metrics) return null;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', marginBottom: '24px' }}>
      {/* 1. Total Telemetry */}
      <div className="glass-card" style={{ padding: '18px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            TOTAL REVIEWS
          </span>
          <MessageSquare size={15} color="var(--text-muted)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '10px' }}>
          <span style={{ fontSize: '1.9rem', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary)' }}>
            {metrics.total_reviews.toLocaleString()}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--color-pos)', display: 'flex', alignItems: 'center', fontWeight: 500 }}>
            <ArrowUpRight size={11} /> 100% Indexed
          </span>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
          Real-time semantic vector space
        </div>
      </div>

      {/* 2. Sentiment Polarity */}
      <div className="glass-card" style={{ padding: '18px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            SENTIMENT RATIO
          </span>
          <TrendingUp size={15} color="var(--color-pos)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '10px' }}>
          <span style={{ fontSize: '1.9rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            {metrics.positive_rate}%
          </span>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            positive &bull; <span style={{ color: 'var(--color-neg)' }}>{metrics.negative_rate}%</span> negative
          </span>
        </div>

        {/* Micro-bar */}
        <div style={{ display: 'flex', height: '4px', width: '100%', borderRadius: '2px', overflow: 'hidden', marginTop: '10px', background: '#202026' }}>
          <div style={{ width: `${metrics.positive_rate}%`, background: 'var(--color-pos)' }} />
          <div style={{ width: `${100 - metrics.positive_rate - metrics.negative_rate}%`, background: 'var(--color-neu)' }} />
          <div style={{ width: `${metrics.negative_rate}%`, background: 'var(--color-neg)' }} />
        </div>
      </div>

      {/* 3. PII Redacted */}
      <div className="glass-card" style={{ padding: '18px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            PII REDACTION GATE
          </span>
          <ShieldCheck size={15} color="var(--text-muted)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '10px' }}>
          <span style={{ fontSize: '1.9rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            {metrics.pii_redacted_count.toLocaleString()}
          </span>
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>
            ({metrics.pii_redacted_rate}% masked)
          </span>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
          Addresses, cards, phones &amp; order IDs
        </div>
      </div>

      {/* 4. Model Governance */}
      <div
        className="glass-card"
        onClick={onOpenGovernance}
        style={{
          padding: '18px 20px',
          cursor: 'pointer',
          border: '1px solid var(--border-active)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            MODEL GOVERNANCE
          </span>
          <Award size={15} color="var(--text-secondary)" />
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '10px' }}>
          <span style={{ fontSize: '1.9rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
            88.2%
          </span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 500 }}>
            Test Accuracy (0.89 F1)
          </span>
        </div>

        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '6px' }}>
          View Confusion Matrix &amp; Calibration &rarr;
        </div>
      </div>
    </div>
  );
};

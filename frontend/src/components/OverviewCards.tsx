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
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px', marginBottom: '24px' }}>
      {/* 1. Total Telemetry Ingestion */}
      <div className="glass-card glow-effect" style={{ padding: '20px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            TOTAL TELEMETRY
          </span>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <MessageSquare size={16} color="var(--accent-blue)" />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '12px' }}>
          <span style={{ fontSize: '2.1rem', fontWeight: 800, letterSpacing: '-0.03em', color: '#fff' }}>
            {metrics.total_reviews.toLocaleString()}
          </span>
          <span style={{ fontSize: '0.75rem', color: '#34d399', display: 'flex', alignItems: 'center', fontWeight: 600 }}>
            <ArrowUpRight size={12} /> 100% Index
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#3b82f6', display: 'inline-block' }} />
          <span>Real-time semantic vector space</span>
        </div>
      </div>

      {/* 2. Sentiment Polarity & Distribution */}
      <div className="glass-card glow-effect" style={{ padding: '20px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            SENTIMENT POLARITY
          </span>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={16} color="var(--color-pos)" />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '12px' }}>
          <span style={{ fontSize: '2.1rem', fontWeight: 800, color: 'var(--color-pos)', letterSpacing: '-0.03em' }}>
            {metrics.positive_rate}%
          </span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            positive • <b style={{ color: 'var(--color-neg)' }}>{metrics.negative_rate}%</b> neg
          </span>
        </div>

        {/* Segmented Gradient Micro-bar */}
        <div style={{ display: 'flex', height: '6px', width: '100%', borderRadius: '4px', overflow: 'hidden', marginTop: '12px', background: '#111827' }}>
          <div style={{ width: `${metrics.positive_rate}%`, background: 'var(--color-pos)' }} />
          <div style={{ width: `${100 - metrics.positive_rate - metrics.negative_rate}%`, background: 'var(--color-neu)' }} />
          <div style={{ width: `${metrics.negative_rate}%`, background: 'var(--color-neg)' }} />
        </div>
      </div>

      {/* 3. Enterprise PII Redaction Compliance */}
      <div className="glass-card glow-effect" style={{ padding: '20px 22px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            PII PRIVACY ENGINE
          </span>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(139, 92, 246, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <ShieldCheck size={16} color="#a78bfa" />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '12px' }}>
          <span style={{ fontSize: '2.1rem', fontWeight: 800, color: '#c4b5fd', letterSpacing: '-0.03em' }}>
            {metrics.pii_redacted_count.toLocaleString()}
          </span>
          <span style={{ fontSize: '0.75rem', color: '#a78bfa', fontWeight: 600 }}>
            ({metrics.pii_redacted_rate}% of corpus)
          </span>
        </div>

        <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
          Order IDs, cards, emails &amp; phones scrubbed
        </div>
      </div>

      {/* 4. Model Governance & Mathematical Validation */}
      <div
        className="glass-card glow-effect"
        onClick={onOpenGovernance}
        style={{
          padding: '20px 22px',
          cursor: 'pointer',
          border: '1px solid rgba(59, 130, 246, 0.45)',
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.8), rgba(30, 58, 138, 0.15))'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            MODEL GOVERNANCE
          </span>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'rgba(59, 130, 246, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Award size={16} color="#60a5fa" />
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '12px' }}>
          <span style={{ fontSize: '2.1rem', fontWeight: 800, color: '#60a5fa', letterSpacing: '-0.03em' }}>
            88.2%
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 600 }}>
            Test Accuracy (0.89 F1)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', color: '#93c5fd', marginTop: '8px' }}>
          <span>Inspect Confusion Matrix &amp; Calibration &rarr;</span>
        </div>
      </div>
    </div>
  );
};

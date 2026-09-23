import React from 'react';
import { X, Award, CheckCircle, Activity, BarChart2 } from 'lucide-react';
import type { ModelGovernanceData } from '../types/telemetry';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  governanceData: ModelGovernanceData | null;
}

export const ModelGovernanceModal: React.FC<Props> = ({
  isOpen,
  onClose,
  governanceData
}) => {
  if (!isOpen || !governanceData) return null;

  const { evaluation, model_architecture } = governanceData;
  const classes = evaluation.classes;
  const cm = evaluation.confusion_matrix;

  return (
    <div className="overlay-backdrop">
      <div
        className="glass-panel"
        style={{
          width: '90%',
          maxWidth: '820px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          background: '#101014',
          borderRadius: '14px',
          border: '1px solid #272730',
          boxShadow: '0 20px 50px rgba(0,0,0,0.8)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '28px', height: '28px', borderRadius: '6px', background: '#202026', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Award size={15} color="var(--text-secondary)" />
              </div>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-primary)' }}>
                Model Governance &amp; Ground-Truth Validation
              </h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
              Empirical evaluation on <b>{evaluation.sample_size} human-annotated gold-standard reviews</b>.
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '5px'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Model Spec Tag */}
        <div style={{ margin: '18px 0', padding: '10px 14px', background: '#16161c', borderRadius: '8px', border: '1px solid #22222a', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={14} color="var(--text-muted)" />
            <span style={{ fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
              Architecture: <span style={{ color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{model_architecture}</span>
            </span>
          </div>
          <span style={{ fontSize: '0.68rem', background: 'var(--color-pos-bg)', color: 'var(--color-pos)', padding: '2px 7px', borderRadius: '4px', border: '1px solid var(--color-pos-border)', fontWeight: 600 }}>
            PLATT SCALED &bull; CALIBRATED
          </span>
        </div>

        {/* Metric Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>TEST ACCURACY</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--color-pos)', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {Math.round(evaluation.accuracy * 1000) / 10}%
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>1,000 Verified Samples</span>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO F1</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.macro_f1}
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Balanced Class Metric</span>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO RECALL</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.macro_recall}
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Defect Sensitivity</span>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>BRIER CALIBRATION</span>
            <div style={{ fontSize: '1.6rem', fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.brier_score}
            </div>
            <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Low Brier = True Probs</span>
          </div>
        </div>

        {/* Confusion Matrix Section */}
        <div style={{ marginBottom: '24px', background: '#141418', padding: '18px', borderRadius: '10px', border: '1px solid var(--border-card)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BarChart2 size={14} color="var(--text-muted)" />
              Empirical Confusion Matrix ($3 \times 3$)
            </h4>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              Diagonal shows True Positives across sentiment tiers
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center', fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '10px', color: 'var(--text-muted)', textAlign: 'left', fontWeight: 500 }}>Ground Truth \ Predicted</th>
                  {classes.map((cls, i) => (
                    <th key={i} style={{ padding: '10px', color: 'var(--text-secondary)', fontWeight: 600 }}>
                      Pred {cls}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {classes.map((trueCls, rowIdx) => (
                  <tr key={rowIdx} style={{ borderTop: '1px solid #1f1f26' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 600, color: 'var(--text-primary)', textAlign: 'left' }}>
                      True {trueCls}
                    </td>
                    {cm[rowIdx].map((count, colIdx) => {
                      const isDiagonal = rowIdx === colIdx;
                      return (
                        <td
                          key={colIdx}
                          style={{
                            padding: '12px',
                            fontWeight: isDiagonal ? 700 : 400,
                            borderRadius: '4px',
                            background: isDiagonal
                              ? 'var(--color-pos-bg)'
                              : count > 0
                              ? 'var(--color-neg-bg)'
                              : 'transparent',
                            color: isDiagonal ? 'var(--color-pos)' : count > 0 ? '#f87171' : 'var(--text-dim)',
                            border: isDiagonal ? '1px solid var(--color-pos-border)' : '1px solid transparent',
                            fontSize: isDiagonal ? '0.95rem' : '0.82rem',
                            fontFamily: "'JetBrains Mono', monospace"
                          }}
                        >
                          {count}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Per-Class Table */}
        <div style={{ marginBottom: '20px' }}>
          <h4 style={{ fontSize: '0.88rem', fontWeight: 600, marginBottom: '10px', color: 'var(--text-primary)' }}>
            Class-Level Precision &amp; Recall Breakdown
          </h4>

          <div style={{ background: '#141418', borderRadius: '10px', border: '1px solid var(--border-card)', overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-card)', background: '#121216', color: 'var(--text-muted)', textAlign: 'left' }}>
                  <th style={{ padding: '10px 14px' }}>Class</th>
                  <th style={{ padding: '10px 14px' }}>Precision</th>
                  <th style={{ padding: '10px 14px' }}>Recall</th>
                  <th style={{ padding: '10px 14px' }}>F1-Score</th>
                  <th style={{ padding: '10px 14px' }}>Support</th>
                </tr>
              </thead>
              <tbody>
                {classes.map((cls) => {
                  const item = evaluation.per_class[cls];
                  return (
                    <tr key={cls} style={{ borderBottom: '1px solid #1a1a20' }}>
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--text-primary)' }}>{cls}</td>
                      <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{item.precision}</td>
                      <td style={{ padding: '10px 14px', color: 'var(--text-secondary)', fontFamily: "'JetBrains Mono', monospace" }}>{item.recall}</td>
                      <td style={{ padding: '10px 14px', fontWeight: 600, color: 'var(--color-pos)', fontFamily: "'JetBrains Mono', monospace" }}>{item.f1_score}</td>
                      <td style={{ padding: '10px 14px', color: 'var(--text-muted)' }}>{item.support} reviews</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: 'var(--color-pos)' }}>
            <CheckCircle size={13} />
            <span>Calibrated against held-out ground truth test set</span>
          </div>

          <button
            onClick={onClose}
            style={{
              padding: '7px 16px',
              borderRadius: '6px',
              background: '#272730',
              color: '#f4f4f5',
              border: '1px solid var(--border-hover)',
              fontWeight: 500,
              fontSize: '0.8rem',
              cursor: 'pointer'
            }}
          >
            Close Audit
          </button>
        </div>
      </div>
    </div>
  );
};

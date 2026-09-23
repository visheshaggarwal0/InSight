import React from 'react';
import { X, Award } from 'lucide-react';
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
          maxWidth: '800px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          background: 'var(--bg-surface)',
          borderRadius: '16px',
          boxShadow: '0 20px 40px rgba(0,0,0,0.8)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Award size={20} color="var(--accent-blue)" />
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>
                Model Governance & Ground-Truth Validation
              </h2>
            </div>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Rigorously benchmarked against {evaluation.sample_size} human-annotated ground-truth test reviews.
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Model Architecture Badge */}
        <div style={{ margin: '18px 0', padding: '10px 14px', background: 'rgba(30, 41, 59, 0.5)', borderRadius: '8px', border: '1px solid #334155' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase' }}>
            Serving Architecture:
          </span>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginLeft: '8px' }}>
            {model_architecture}
          </span>
        </div>

        {/* High-Level Score Cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>ACCURACY</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--status-pos)', marginTop: '4px' }}>
              {Math.round(evaluation.accuracy * 1000) / 10}%
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>MACRO F1</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#60a5fa', marginTop: '4px' }}>
              {evaluation.macro_f1}
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>MACRO RECALL</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#c4b5fd', marginTop: '4px' }}>
              {evaluation.macro_recall}
            </div>
          </div>

          <div className="glass-card" style={{ padding: '14px', textAlign: 'center' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontWeight: 600 }}>BRIER CALIBRATION</span>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#34d399', marginTop: '4px' }}>
              {evaluation.brier_score}
            </div>
          </div>
        </div>

        {/* Confusion Matrix Section */}
        <div style={{ marginBottom: '24px' }}>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-primary)' }}>
            Empirical Confusion Matrix ($3 \times 3$)
          </h4>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center', fontSize: '0.82rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '10px', color: 'var(--text-muted)', textAlign: 'left' }}>True \ Predicted</th>
                  {classes.map((cls, i) => (
                    <th key={i} style={{ padding: '10px', color: '#93c5fd', fontWeight: 700 }}>
                      Pred {cls}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {classes.map((trueCls, rowIdx) => (
                  <tr key={rowIdx} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                    <td style={{ padding: '10px', fontWeight: 700, color: '#cbd5e1', textAlign: 'left' }}>
                      True {trueCls}
                    </td>
                    {cm[rowIdx].map((count, colIdx) => {
                      const isDiagonal = rowIdx === colIdx;
                      return (
                        <td
                          key={colIdx}
                          style={{
                            padding: '12px',
                            fontWeight: isDiagonal ? 800 : 500,
                            background: isDiagonal ? 'rgba(59, 130, 246, 0.18)' : 'transparent',
                            color: isDiagonal ? '#60a5fa' : 'var(--text-muted)'
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

        {/* Per-Class Breakdown Table */}
        <div>
          <h4 style={{ fontSize: '0.92rem', fontWeight: 700, marginBottom: '12px', color: 'var(--text-primary)' }}>
            Per-Class Performance Metrics
          </h4>

          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)', textAlign: 'left' }}>
                <th style={{ padding: '8px' }}>Class</th>
                <th style={{ padding: '8px' }}>Precision</th>
                <th style={{ padding: '8px' }}>Recall</th>
                <th style={{ padding: '8px' }}>F1-Score</th>
                <th style={{ padding: '8px' }}>Support</th>
              </tr>
            </thead>
            <tbody>
              {classes.map((cls) => {
                const item = evaluation.per_class[cls];
                return (
                  <tr key={cls} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '10px 8px', fontWeight: 700, color: 'var(--text-primary)' }}>{cls}</td>
                    <td style={{ padding: '10px 8px', color: '#60a5fa' }}>{item.precision}</td>
                    <td style={{ padding: '10px 8px', color: '#c4b5fd' }}>{item.recall}</td>
                    <td style={{ padding: '10px 8px', fontWeight: 700, color: 'var(--status-pos)' }}>{item.f1_score}</td>
                    <td style={{ padding: '10px 8px', color: 'var(--text-muted)' }}>{item.support}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div style={{ marginTop: '24px', textAlign: 'right' }}>
          <button
            onClick={onClose}
            style={{
              padding: '8px 18px',
              borderRadius: '6px',
              background: 'var(--accent-blue)',
              color: '#fff',
              border: 'none',
              fontWeight: 700,
              fontSize: '0.85rem',
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

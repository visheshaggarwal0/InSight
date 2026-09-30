import React from 'react';
import { X, Award, Activity, BarChart2 } from 'lucide-react';
import { Dialog } from './Dialog';
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
    <Dialog
      open={isOpen}
      onClose={onClose}
      labelledBy="governance-dialog-title"
      panelClassName="responsive-modal-body"
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '16px', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div aria-hidden="true" style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#ECFDF5', color: '#047857', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
              <Award size={18} />
            </div>
            <h2 id="governance-dialog-title" style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.01em', color: '#111827', margin: 0 }}>
              Model Governance &amp; Ground-Truth Validation
            </h2>
          </div>
          <p style={{ fontSize: '0.82rem', color: '#6B7280', marginTop: '6px' }}>
            Empirical evaluation on <b>{evaluation.sample_size} human-annotated gold-standard reviews</b>.
          </p>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close model governance report"
          style={{
            background: '#F3F4F6',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            flexShrink: 0
          }}
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      {/* Model Spec Tag */}
      <div style={{ margin: '18px 0', padding: '12px 16px', backgroundColor: '#F9FAFB', borderRadius: '10px', border: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={15} aria-hidden="true" style={{ color: '#047857', flexShrink: 0 }} />
          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
            Architecture: <strong style={{ color: '#111827', fontFamily: "'JetBrains Mono', monospace" }}>{model_architecture}</strong>
          </span>
        </div>
        <span style={{ fontSize: '0.75rem', backgroundColor: '#ECFDF5', color: '#065F46', padding: '3px 8px', borderRadius: '999px', border: '1px solid #A7F3D0', fontWeight: 700 }}>
          PLATT SCALED &bull; CALIBRATED
        </span>
      </div>

      {/* Metric Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px', marginBottom: '24px' }}>
        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>TEST ACCURACY</span>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#047857', marginTop: '4px', letterSpacing: '-0.02em' }}>
            {Math.round(evaluation.accuracy * 1000) / 10}%
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>1,000 Verified Samples</span>
        </div>

        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO F1</span>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
            {evaluation.macro_f1}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Balanced Class Metric</span>
        </div>

        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO RECALL</span>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
            {evaluation.macro_recall}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Defect Sensitivity</span>
        </div>

        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>BRIER CALIBRATION</span>
          <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
            {evaluation.brier_score}
          </div>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Low Brier = True Probs</span>
        </div>
      </div>

      {/* Confusion Matrix Section */}
      <div style={{ marginBottom: '24px', backgroundColor: '#F9FAFB', padding: '18px', borderRadius: '12px', border: '1px solid #E5E7EB' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', gap: '12px', flexWrap: 'wrap' }}>
          <h4 id="confusion-matrix-title" style={{ fontSize: '0.9rem', fontWeight: 700, color: '#111827', display: 'flex', alignItems: 'center', gap: '6px', margin: 0 }}>
            <BarChart2 size={16} aria-hidden="true" style={{ color: '#047857' }} />
            Empirical Confusion Matrix (3 &times; 3)
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Diagonal shows True Positives across sentiment tiers
          </span>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table
            aria-labelledby="confusion-matrix-title"
            style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center', fontSize: '0.84rem' }}
          >
            <thead>
              <tr>
                <th scope="col" style={{ padding: '10px', color: '#6B7280', textAlign: 'left', fontWeight: 600 }}>
                  Ground Truth \ Predicted
                </th>
                {classes.map((cls, i) => (
                  <th key={i} scope="col" style={{ padding: '10px', color: '#374151', fontWeight: 700 }}>
                    Pred {cls}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {classes.map((trueCls, rowIdx) => (
                <tr key={rowIdx} style={{ borderTop: '1px solid #E5E7EB' }}>
                  <th scope="row" style={{ padding: '12px 10px', fontWeight: 700, color: '#111827', textAlign: 'left' }}>
                    True {trueCls}
                  </th>
                  {cm[rowIdx].map((count, colIdx) => {
                    const isDiagonal = rowIdx === colIdx;
                    return (
                      <td
                        key={colIdx}
                        style={{
                          padding: '12px 10px',
                          backgroundColor: isDiagonal ? '#ECFDF5' : 'transparent',
                          color: isDiagonal ? '#065F46' : '#6B7280',
                          fontWeight: isDiagonal ? 700 : 500,
                          borderRadius: isDiagonal ? '6px' : '0'
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

      {/* Footer info */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', paddingTop: '16px', borderTop: '1px solid #E5E7EB' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', maxWidth: '58ch' }}>
          Platt Scaling ensures class probabilities match actual empirical accuracy.
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            padding: '8px 18px',
            borderRadius: '999px',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            border: 'none',
            fontSize: '0.82rem',
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          Close
        </button>
      </div>
    </Dialog>
  );
};

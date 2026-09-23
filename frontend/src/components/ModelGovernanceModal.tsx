import React from 'react';
import { X, Award, Activity, BarChart2 } from 'lucide-react';
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
        style={{
          width: '90%',
          maxWidth: '820px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 20px 50px rgba(0,0,0,0.15)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#ECFDF5', color: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Award size={18} />
              </div>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-0.01em', color: '#111827' }}>
                Model Governance &amp; Ground-Truth Validation
              </h2>
            </div>
            <p style={{ fontSize: '0.82rem', color: '#6B7280', marginTop: '6px' }}>
              Empirical evaluation on <b>{evaluation.sample_size} human-annotated gold-standard reviews</b>.
            </p>
          </div>

          <button
            onClick={onClose}
            style={{
              background: '#F3F4F6',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              color: '#6B7280',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Model Spec Tag */}
        <div style={{ margin: '18px 0', padding: '12px 16px', backgroundColor: '#F9FAFB', borderRadius: '10px', border: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={15} style={{ color: '#10B981' }} />
            <span style={{ fontSize: '0.78rem', color: '#4B5563' }}>
              Architecture: <strong style={{ color: '#111827', fontFamily: "'JetBrains Mono', monospace" }}>{model_architecture}</strong>
            </span>
          </div>
          <span style={{ fontSize: '0.7rem', backgroundColor: '#ECFDF5', color: '#065F46', padding: '3px 8px', borderRadius: '999px', border: '1px solid #A7F3D0', fontWeight: 700 }}>
            PLATT SCALED &bull; CALIBRATED
          </span>
        </div>

        {/* Metric Cards Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
          <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>TEST ACCURACY</span>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#059669', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {Math.round(evaluation.accuracy * 1000) / 10}%
            </div>
            <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>1,000 Verified Samples</span>
          </div>

          <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO F1</span>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.macro_f1}
            </div>
            <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>Balanced Class Metric</span>
          </div>

          <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>MACRO RECALL</span>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.macro_recall}
            </div>
            <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>Defect Sensitivity</span>
          </div>

          <div style={{ padding: '16px', textAlign: 'center', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
            <span style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>BRIER CALIBRATION</span>
            <div style={{ fontSize: '1.7rem', fontWeight: 700, color: '#111827', marginTop: '4px', letterSpacing: '-0.02em' }}>
              {evaluation.brier_score}
            </div>
            <span style={{ fontSize: '0.7rem', color: '#9CA3AF' }}>Low Brier = True Probs</span>
          </div>
        </div>

        {/* Confusion Matrix Section */}
        <div style={{ marginBottom: '24px', backgroundColor: '#F9FAFB', padding: '18px', borderRadius: '12px', border: '1px solid #E5E7EB' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
            <h4 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#111827', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <BarChart2 size={16} style={{ color: '#10B981' }} />
              Empirical Confusion Matrix (3 × 3)
            </h4>
            <span style={{ fontSize: '0.72rem', color: '#6B7280' }}>
              Diagonal shows True Positives across sentiment tiers
            </span>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'center', fontSize: '0.84rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '10px', color: '#6B7280', textAlign: 'left', fontWeight: 600 }}>Ground Truth \ Predicted</th>
                  {classes.map((cls, i) => (
                    <th key={i} style={{ padding: '10px', color: '#374151', fontWeight: 700 }}>
                      Pred {cls}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {classes.map((trueCls, rowIdx) => (
                  <tr key={rowIdx} style={{ borderTop: '1px solid #E5E7EB' }}>
                    <td style={{ padding: '12px 10px', fontWeight: 700, color: '#111827', textAlign: 'left' }}>
                      True {trueCls}
                    </td>
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
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '16px', borderTop: '1px solid #E5E7EB' }}>
          <span style={{ fontSize: '0.74rem', color: '#6B7280' }}>
            Platt Scaling ensures class probabilities match actual empirical accuracy.
          </span>
          <button
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
      </div>
    </div>
  );
};

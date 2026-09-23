import React from 'react';
import { AlertCircle, ShieldAlert } from 'lucide-react';
import type { DriftData } from '../types/telemetry';

interface Props {
  driftData: DriftData | null;
}

export const DriftTimeline: React.FC<Props> = ({ driftData }) => {
  if (!driftData) return null;

  const { alerts } = driftData;

  return (
    <div style={{ marginBottom: '24px' }}>
      {/* Critical Regression Alert Banners */}
      {alerts.map((alert, i) => (
        <div
          key={i}
          style={{
            background: alert.severity === 'CRITICAL' ? 'var(--color-crit-bg)' : 'var(--color-neu-bg)',
            border: alert.severity === 'CRITICAL' ? '1px solid var(--color-crit-border)' : '1px solid var(--color-neu-border)',
            borderLeft: alert.severity === 'CRITICAL' ? '4px solid var(--color-crit)' : '4px solid var(--color-neu)',
            borderRadius: '8px',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '14px'
          }}
        >
          {alert.severity === 'CRITICAL' ? (
            <AlertCircle size={20} color="#fb7185" />
          ) : (
            <ShieldAlert size={20} color="#fbbf24" />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: alert.severity === 'CRITICAL' ? '#fb7185' : '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {alert.severity} STATISTICAL REGRESSION
              </span>
              <span style={{ fontSize: '0.72rem', background: '#1c1917', padding: '1px 6px', borderRadius: '4px', color: '#a8a29e' }}>
                {alert.batch_or_version}
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginTop: '2px', fontWeight: 500 }}>
              {alert.message}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '1rem', fontWeight: 700, color: '#fb7185', fontFamily: "'JetBrains Mono', monospace" }}>
              PSI: {alert.psi_score}
            </span>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Threshold &gt; 0.25</div>
          </div>
        </div>
      ))}
    </div>
  );
};

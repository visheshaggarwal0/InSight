import React from 'react';
import { AlertCircle, ShieldAlert } from 'lucide-react';
import type { DriftData } from '../types/telemetry';

interface Props {
  driftData: DriftData | null;
}

/**
 * DriftTimeline - Visualizes Population Stability Index (PSI) drift across product cohorts.
 *
 * Displays:
 * - High-priority regression alert banners when batch/version PSI exceeds thresholds
 * - Statistical severity badges (CRITICAL vs WARNING)
 * - Affected cohort identifiers (e.g. Batch numbers, software releases)
 */
export const DriftTimeline: React.FC<Props> = ({ driftData }) => {
  if (!driftData) return null;

  const { alerts } = driftData;

  return (
    <div style={{ marginBottom: '24px' }}>
      {/* Critical Regression Alert Banners */}
      {alerts.map((alert, i) => (
        <div
          key={alert.batch_or_version || i}
          role="status"
          aria-label={`${alert.severity} statistical regression for ${alert.batch_or_version}, PSI ${alert.psi_score.toFixed(2)}`}
          style={{
            background: alert.severity === 'CRITICAL' ? 'var(--color-crit-bg)' : 'var(--color-neu-bg)',
            border: alert.severity === 'CRITICAL' ? '1px solid var(--color-crit-border)' : '1px solid var(--color-neu-border)',
            borderLeft: alert.severity === 'CRITICAL' ? '4px solid var(--color-crit)' : '4px solid var(--color-amber)',
            borderRadius: '8px',
            padding: '12px 18px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '14px'
          }}
        >
          {alert.severity === 'CRITICAL' ? (
            <AlertCircle size={20} color="var(--color-crit)" aria-hidden="true" />
          ) : (
            <ShieldAlert size={20} color="var(--color-amber-text)" aria-hidden="true" />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, color: alert.severity === 'CRITICAL' ? 'var(--color-crit-text)' : 'var(--color-amber-text)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                {alert.severity} STATISTICAL REGRESSION
              </span>
              <span style={{ fontSize: '0.72rem', background: 'var(--bg-surface)', border: '1px solid var(--border-card)', padding: '1px 6px', borderRadius: '4px', color: 'var(--text-secondary)' }}>
                {alert.batch_or_version}
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginTop: '2px', fontWeight: 500 }}>
              {alert.message}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '1rem', fontWeight: 700, color: alert.severity === 'CRITICAL' ? 'var(--color-crit-text)' : 'var(--color-amber-text)', fontFamily: "'JetBrains Mono', monospace" }}>
              PSI: {alert.psi_score.toFixed(2)}
            </span>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>Threshold &gt; 0.25</div>
          </div>
        </div>
      ))}
    </div>
  );
};

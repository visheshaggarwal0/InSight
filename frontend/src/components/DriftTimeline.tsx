import React from 'react';
import { AlertOctagon, ShieldAlert } from 'lucide-react';
import type { DriftData } from '../types/telemetry';

interface Props {
  driftData: DriftData | null;
}

export const DriftTimeline: React.FC<Props> = ({ driftData }) => {
  if (!driftData) return null;

  const { timeline, alerts } = driftData;

  return (
    <div style={{ marginBottom: '28px' }}>
      {/* 1. Critical Anomaly Alert Banners */}
      {alerts.map((alert, i) => (
        <div
          key={i}
          style={{
            background: alert.severity === 'CRITICAL' ? 'rgba(225, 29, 72, 0.15)' : 'rgba(245, 158, 11, 0.15)',
            border: alert.severity === 'CRITICAL' ? '1px solid rgba(225, 29, 72, 0.4)' : '1px solid rgba(245, 158, 11, 0.4)',
            borderRadius: '10px',
            padding: '14px 20px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            marginBottom: '16px'
          }}
        >
          {alert.severity === 'CRITICAL' ? (
            <AlertOctagon size={24} color="#f43f5e" />
          ) : (
            <ShieldAlert size={24} color="#f59e0b" />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: alert.severity === 'CRITICAL' ? '#fb7185' : '#fbbf24', textTransform: 'uppercase' }}>
                {alert.severity} STATISTICAL REGRESSION ALERT
              </span>
              <span style={{ fontSize: '0.75rem', background: '#00000044', padding: '1px 6px', borderRadius: '4px', color: '#cbd5e1' }}>
                {alert.batch_or_version}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', marginTop: '2px', fontWeight: 500 }}>
              {alert.message}
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <span style={{ fontSize: '1.1rem', fontWeight: 800, color: '#fb7185' }}>
              PSI: {alert.psi_score}
            </span>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Threshold &gt; 0.25</div>
          </div>
        </div>
      ))}

      {/* 2. Chronological Batch Timeline */}
      <div className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Release & Batch Drift Progression
            </h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
              Tracks categorical Population Stability Index (PSI) and negative sentiment velocity across manufacturing lots or app versions.
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px' }}>
          {timeline.map((item, idx) => {
            const isCrit = item.status === 'CRITICAL_DRIFT';
            const isMod = item.status === 'MODERATE_DRIFT';

            return (
              <div
                key={idx}
                className="glass-card"
                style={{
                  padding: '16px',
                  border: isCrit
                    ? '1px solid rgba(225, 29, 72, 0.5)'
                    : isMod
                    ? '1px solid rgba(245, 158, 11, 0.4)'
                    : '1px solid var(--border-subtle)',
                  background: isCrit
                    ? 'rgba(225, 29, 72, 0.08)'
                    : 'var(--bg-card)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {item.batch_or_version}
                  </span>
                  {isCrit ? (
                    <span className="badge badge-critical">Critical Drift</span>
                  ) : isMod ? (
                    <span className="badge badge-medium">Moderate Drift</span>
                  ) : (
                    <span className="badge badge-low">Stable</span>
                  )}
                </div>

                <div style={{ marginTop: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                    <span>Negative Rate:</span>
                    <b style={{ color: item.negative_rate > 35 ? 'var(--status-neg)' : 'var(--text-primary)' }}>
                      {item.negative_rate}%
                    </b>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    <span>Volume:</span>
                    <b>{item.review_count.toLocaleString()} reviews</b>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    <span>PSI Score:</span>
                    <b style={{ color: isCrit ? 'var(--status-crit)' : 'var(--text-primary)' }}>
                      {item.psi}
                    </b>
                  </div>
                </div>

                {/* Sentiment Mini Bar */}
                <div style={{ display: 'flex', height: '5px', width: '100%', borderRadius: '2px', overflow: 'hidden', marginTop: '12px', background: '#1e293b' }}>
                  <div style={{ width: `${100 - item.negative_rate}%`, background: 'var(--status-pos)' }} />
                  <div style={{ width: `${item.negative_rate}%`, background: 'var(--status-neg)' }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

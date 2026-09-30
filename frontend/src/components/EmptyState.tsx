import React from 'react';

export function fmtNum(value: number | null | undefined, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return value.toLocaleString();
}

export function fmtPct(value: number | null | undefined, digits = 1, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return `${value.toFixed(digits)}%`;
}

/** Population Stability Index is a unitless index, never a percentage. */
export function fmtPsi(value: number | null | undefined, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return value.toFixed(3);
}

export const Skeleton: React.FC<{ rows?: number; height?: number; label?: string }> = ({
  rows = 3,
  height = 14,
  label = 'Loading'
}) => (
  <div
    style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <span style={{ fontSize: '0.74rem', color: '#9CA3AF', fontWeight: 600 }}>{label}…</span>
    {Array.from({ length: rows }).map((_, i) => (
      <div
        key={i}
        className="animate-pulse"
        style={{
          height: `${height}px`,
          width: `${100 - (i % 3) * 12}%`,
          borderRadius: '6px',
          backgroundColor: '#E5E7EB'
        }}
      />
    ))}
  </div>
);

export const EmptyState: React.FC<{ label: string; hint?: string }> = ({ label, hint }) => (
  <div
    role="status"
    style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '6px',
      padding: '28px 16px',
      textAlign: 'center'
    }}
  >
    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#6B7280' }}>{label}</span>
    {hint && <span style={{ fontSize: '0.74rem', color: '#9CA3AF' }}>{hint}</span>}
  </div>
);

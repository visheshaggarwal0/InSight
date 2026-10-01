/**
 * formatters.ts
 * Shared display-formatting utilities used across dashboard components.
 *
 * Kept in lib/ (not components/) so they can be imported by any file
 * without triggering the React Fast Refresh "only-export-components" warning.
 */

/** Format a number with locale-aware thousands separators. */
export function fmtNum(value: number | null | undefined, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return value.toLocaleString();
}

/** Format a number as a percentage string (e.g. "72.4%"). */
export function fmtPct(value: number | null | undefined, digits = 1, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return `${value.toFixed(digits)}%`;
}

/**
 * Format a Population Stability Index value.
 * PSI is a unitless divergence index — never rendered with a percent sign.
 */
export function fmtPsi(value: number | null | undefined, fallback = '—'): string {
  if (value === null || value === undefined || typeof value !== 'number' || !Number.isFinite(value)) {
    return fallback;
  }
  return value.toFixed(3);
}

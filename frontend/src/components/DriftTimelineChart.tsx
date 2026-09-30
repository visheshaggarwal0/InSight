import type { BatchTimelineItem } from '../types/telemetry';

/**
 * Population Stability Index over the batch/cohort timeline.
 *
 * PSI is a unitless divergence index, not a percentage. The two reference
 * lines are the conventional decision thresholds used elsewhere in this app
 * (`DriftTimeline`): > 0.10 means "look at it", > 0.25 means "critical".
 */

export interface DriftTimelineChartProps {
  /** `driftData.timeline` — one row per batch/cohort, in server order. */
  timeline: BatchTimelineItem[];
  /** Accessible name for the chart. */
  title?: string;
  height?: number;
}

const PSI_MODERATE = 0.1;
const PSI_CRITICAL = 0.25;

const WIDTH = 760;
const MARGIN = { top: 16, right: 20, bottom: 56, left: 48 };
const PLOT_W = WIDTH - MARGIN.left - MARGIN.right;

function truncate(value: string, max: number): string {
  return value.length <= max ? value : `${value.slice(0, Math.max(1, max - 1))}…`;
}

export function DriftTimelineChart({ timeline, title = 'PSI by batch', height = 300 }: DriftTimelineChartProps) {
  const rows = (timeline ?? []).filter((row) => row && typeof row.psi === 'number' && Number.isFinite(row.psi));

  if (rows.length === 0) {
    return (
      <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
        No batch-level PSI telemetry is available for this dataset.
      </p>
    );
  }

  // Scale above the largest observed value, but never below the critical
  // threshold — a flat, all-stable series should still show where 0.25 sits.
  const maxObserved = rows.reduce((max, row) => Math.max(max, row.psi), 0);
  const yMaxRaw = Math.max(maxObserved, PSI_CRITICAL) * 1.15 || 0.3;
  const plotH = height - MARGIN.top - MARGIN.bottom;

  const x = (index: number) =>
    MARGIN.left + (rows.length === 1 ? PLOT_W / 2 : (index / (rows.length - 1)) * PLOT_W);
  const y = (value: number) => MARGIN.top + plotH - (Math.min(value, yMaxRaw) / yMaxRaw) * plotH;

  const points = rows.map((row, i) => `${x(i).toFixed(2)},${y(row.psi).toFixed(2)}`);
  const linePath = `M ${points.join(' L ')}`;
  const baseline = (MARGIN.top + plotH).toFixed(2);
  const areaPath = `${linePath} L ${x(rows.length - 1).toFixed(2)},${baseline} L ${x(0).toFixed(2)},${baseline} Z`;

  const yTicks = [0, 0.1, 0.25, yMaxRaw].filter(
    (value, index, all) => index === all.findIndex((other) => Math.abs(other - value) < 1e-9)
  );

  const criticalRows = rows.filter((row) => row.psi > PSI_CRITICAL);
  const moderateRows = rows.filter((row) => row.psi > PSI_MODERATE && row.psi <= PSI_CRITICAL);

  const description = [
    `Population Stability Index for ${rows.length} ${rows.length === 1 ? 'batch' : 'batches'}, in order: ${rows
      .map((row) => `${row.batch_or_version} at ${row.psi.toFixed(2)}`)
      .join(', ')}.`,
    `Moderate-drift reference line at ${PSI_MODERATE.toFixed(2)}; critical-drift reference line at ${PSI_CRITICAL.toFixed(2)}.`,
    criticalRows.length > 0
      ? `${criticalRows.length} ${criticalRows.length === 1 ? 'batch exceeds' : 'batches exceed'} the critical threshold: ${criticalRows
          .map((row) => row.batch_or_version)
          .join(', ')}.`
      : `No batch exceeds the critical threshold.`,
    moderateRows.length > 0
      ? `${moderateRows.length} ${moderateRows.length === 1 ? 'batch sits' : 'batches sit'} above the moderate threshold.`
      : `No batch exceeds the moderate threshold.`
  ].join(' ');

  // Skip x tick labels rather than let them overlap on narrow viewports.
  const labelStride = Math.ceil(rows.length / 8);

  return (
    <figure style={{ margin: 0, width: '100%' }}>
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-labelledby="drift-timeline-chart-title drift-timeline-chart-desc"
        style={{ display: 'block', maxWidth: '100%', height: 'auto' }}
      >
        <title id="drift-timeline-chart-title">{title}</title>
        <desc id="drift-timeline-chart-desc">{description}</desc>

        {/* Horizontal gridlines + y labels */}
        {yTicks.map((value) => (
          <g key={`y-${value}`}>
            <line
              x1={MARGIN.left}
              x2={MARGIN.left + PLOT_W}
              y1={y(value)}
              y2={y(value)}
              stroke="var(--border-card)"
              strokeWidth={1}
            />
            <text
              x={MARGIN.left - 8}
              y={y(value) + 4}
              textAnchor="end"
              fontSize={11}
              fill="var(--text-secondary)"
            >
              {value.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Reference thresholds */}
        <g>
          <line
            x1={MARGIN.left}
            x2={MARGIN.left + PLOT_W}
            y1={y(PSI_MODERATE)}
            y2={y(PSI_MODERATE)}
            stroke="var(--color-amber)"
            strokeWidth={1.5}
            strokeDasharray="6 4"
          />
          <text
            x={MARGIN.left + PLOT_W}
            y={y(PSI_MODERATE) - 6}
            textAnchor="end"
            fontSize={11}
            fontWeight={700}
            fill="var(--color-amber-text)"
          >
            moderate {PSI_MODERATE.toFixed(2)}
          </text>

          <line
            x1={MARGIN.left}
            x2={MARGIN.left + PLOT_W}
            y1={y(PSI_CRITICAL)}
            y2={y(PSI_CRITICAL)}
            stroke="var(--color-crit)"
            strokeWidth={1.5}
            strokeDasharray="6 4"
          />
          <text
            x={MARGIN.left + PLOT_W}
            y={y(PSI_CRITICAL) - 6}
            textAnchor="end"
            fontSize={11}
            fontWeight={700}
            fill="var(--color-crit-text)"
          >
            critical {PSI_CRITICAL.toFixed(2)}
          </text>
        </g>

        {/* Area under the PSI series, then the line itself */}
        <path d={areaPath} fill="var(--brand-mint)" opacity={0.5} />
        <path
          d={linePath}
          fill="none"
          stroke="var(--brand-primary-hover)"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Per-batch points, coloured by the band they fall in */}
        {rows.map((row, i) => {
          const tone = row.psi > PSI_CRITICAL ? 'var(--color-crit)' : row.psi > PSI_MODERATE ? 'var(--color-amber)' : 'var(--color-pos-text)';
          return (
            <circle
              key={row.batch_or_version}
              cx={x(i)}
              cy={y(row.psi)}
              r={rows.length > 20 ? 2.5 : 4}
              fill={tone}
            >
              <title>{`${row.batch_or_version}: PSI ${row.psi.toFixed(2)} (${row.status})`}</title>
            </circle>
          );
        })}

        {/* X axis */}
        <line
          x1={MARGIN.left}
          x2={MARGIN.left + PLOT_W}
          y1={MARGIN.top + plotH}
          y2={MARGIN.top + plotH}
          stroke="var(--border-hover)"
          strokeWidth={1}
        />
        {rows.map((row, i) =>
          i % labelStride === 0 ? (
            <text
              key={`x-${row.batch_or_version}`}
              x={x(i)}
              y={MARGIN.top + plotH + 18}
              textAnchor="middle"
              fontSize={11}
              fill="var(--text-secondary)"
            >
              {truncate(row.batch_or_version, 12)}
            </text>
          ) : null
        )}

        <text
          x={MARGIN.left}
          y={height - 10}
          fontSize={11}
          fill="var(--text-secondary)"
        >
          PSI (unitless index)
        </text>
      </svg>

      {/* Same numbers as a real table, for anyone who cannot use the chart. */}
      <details style={{ marginTop: '12px' }}>
        <summary style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', cursor: 'pointer' }}>
          View PSI values as a table
        </summary>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', marginTop: '10px' }}>
          <caption
            style={{
              textAlign: 'left',
              fontSize: '0.75rem',
              color: 'var(--text-secondary)',
              paddingBottom: '6px'
            }}
          >
            Population Stability Index by batch, with drift status.
          </caption>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-card)' }}>
              <th scope="col" style={{ textAlign: 'left', padding: '6px 8px 6px 0' }}>
                Batch
              </th>
              <th scope="col" style={{ textAlign: 'right', padding: '6px 8px' }}>
                PSI
              </th>
              <th scope="col" style={{ textAlign: 'right', padding: '6px 0 6px 8px' }}>
                Reviews
              </th>
              <th scope="col" style={{ textAlign: 'right', padding: '6px 0 6px 8px' }}>
                Status
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.batch_or_version} style={{ borderBottom: '1px solid var(--border-card)' }}>
                <th scope="row" style={{ textAlign: 'left', padding: '6px 8px 6px 0', fontWeight: 500 }}>
                  {row.batch_or_version}
                </th>
                <td style={{ textAlign: 'right', padding: '6px 8px', fontVariantNumeric: 'tabular-nums' }}>
                  {row.psi.toFixed(3)}
                </td>
                <td style={{ textAlign: 'right', padding: '6px 0 6px 8px', fontVariantNumeric: 'tabular-nums' }}>
                  {row.review_count.toLocaleString()}
                </td>
                <td style={{ textAlign: 'right', padding: '6px 0 6px 8px' }}>{row.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

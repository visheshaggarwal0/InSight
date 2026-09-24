import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { SentimentTrendPoint } from '../types/telemetry';

interface SentimentTrendCardProps {
  trendPoints?: SentimentTrendPoint[];
}

export function SentimentTrendCard({ trendPoints }: SentimentTrendCardProps) {
  const [granularity, setGranularity] = useState('By Batch');
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  // Dynamic curve points or fallback
  const dataPoints: SentimentTrendPoint[] = trendPoints && trendPoints.length > 1
    ? trendPoints
    : [
        { label: 'Batch-24A', pos: 72, neu: 18, neg: 10 },
        { label: 'Batch-24B', pos: 70, neu: 20, neg: 10 },
        { label: 'Batch-24C', pos: 35, neu: 15, neg: 50 },
        { label: 'Batch-24D', pos: 68, neu: 21, neg: 11 },
      ];

  // SVG dimensions
  const width = 540;
  const height = 180;
  const paddingX = 40;
  const paddingY = 20;
  const innerW = width - paddingX * 2;
  const innerH = height - paddingY * 2;

  // Convert points to SVG coordinates
  const getX = (i: number) => paddingX + (i / (dataPoints.length - 1)) * innerW;
  const getY = (val: number) => paddingY + (1 - val / 100) * innerH;

  // Create smooth bezier path string
  const createSmoothPath = (key: 'pos' | 'neu' | 'neg') => {
    const points = dataPoints.map((d, i) => ({ x: getX(i), y: getY(d[key]) }));
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cpX = (p0.x + p1.x) / 2;
      d += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
    }
    return d;
  };

  const pathPos = createSmoothPath('pos');
  const pathNeu = createSmoothPath('neu');
  const pathNeg = createSmoothPath('neg');

  // Closed area for positive fill
  const areaPos = `${pathPos} L ${getX(dataPoints.length - 1)} ${height - paddingY} L ${getX(0)} ${height - paddingY} Z`;

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1.2 }}>
      {/* Card Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '12px'
      }}>
        <div>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
            Sentiment Trend
          </h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginTop: '6px' }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#4B5563', fontWeight: 500 }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10B981' }} />
              Positive
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#4B5563', fontWeight: 500 }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#9CA3AF' }} />
              Neutral
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: '#4B5563', fontWeight: 500 }}>
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#EF4444' }} />
              Negative
            </span>
          </div>
        </div>

        {/* Granularity Dropdown */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '8px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#FFFFFF',
              fontSize: '0.78rem',
              fontWeight: 600,
              color: '#374151',
              cursor: 'pointer'
            }}
          >
            <span>{granularity}</span>
            <ChevronDown size={14} style={{ color: '#9CA3AF' }} />
          </button>
          {isDropdownOpen && (
            <div style={{
              position: 'absolute',
              top: '110%',
              right: 0,
              backgroundColor: '#FFFFFF',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
              padding: '4px',
              zIndex: 10,
              minWidth: '100px'
            }}>
              {['Daily', 'Weekly', 'By Batch'].map((g) => (
                <button
                  key={g}
                  onClick={() => {
                    setGranularity(g);
                    setIsDropdownOpen(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '6px 10px',
                    border: 'none',
                    backgroundColor: granularity === g ? '#ECFDF5' : 'transparent',
                    color: granularity === g ? '#065F46' : '#111827',
                    fontSize: '0.78rem',
                    textAlign: 'left',
                    borderRadius: '6px',
                    cursor: 'pointer'
                  }}
                >
                  {g}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* SVG Chart */}
      <div style={{ position: 'relative', width: '100%', overflow: 'hidden' }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', height: 'auto', display: 'block' }}
        >
          <defs>
            <linearGradient id="posGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = getY(val);
            return (
              <g key={val}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#F3F4F6"
                  strokeWidth="1"
                />
                <text
                  x={paddingX - 10}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="10"
                  fill="#9CA3AF"
                  fontWeight="500"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Area fill */}
          <path d={areaPos} fill="url(#posGrad)" />

          {/* Lines */}
          <path d={pathNeu} fill="none" stroke="#9CA3AF" strokeWidth="2" opacity="0.8" />
          <path d={pathNeg} fill="none" stroke="#EF4444" strokeWidth="2" opacity="0.85" />
          <path d={pathPos} fill="none" stroke="#10B981" strokeWidth="2.5" />

          {/* Interactive Data Points */}
          {dataPoints.map((d, i) => {
            const x = getX(i);
            const isHovered = hoverIndex === i;
            return (
              <g
                key={i}
                onMouseEnter={() => setHoverIndex(i)}
                onMouseLeave={() => setHoverIndex(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Invisible hover bar */}
                <rect
                  x={x - 15}
                  y={0}
                  width="30"
                  height={height}
                  fill="transparent"
                />
                {isHovered && (
                  <line
                    x1={x}
                    y1={paddingY}
                    x2={x}
                    y2={height - paddingY}
                    stroke="#CBD5E1"
                    strokeWidth="1"
                    strokeDasharray="2 2"
                  />
                )}
                <circle
                  cx={x}
                  cy={getY(d.pos)}
                  r={isHovered ? 5 : 3.5}
                  fill="#FFFFFF"
                  stroke="#10B981"
                  strokeWidth="2.5"
                />
              </g>
            );
          })}
        </svg>

        {/* X Axis Labels */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          padding: `0 ${paddingX}px`,
          marginTop: '6px'
        }}>
          {dataPoints.map((d, idx) => (
            <span key={idx} style={{ fontSize: '0.72rem', color: '#9CA3AF', fontWeight: 500 }}>
              {d.label}
            </span>
          ))}
        </div>

        {/* Hover Tooltip */}
        {hoverIndex !== null && (
          <div style={{
            position: 'absolute',
            top: '10px',
            left: `${(getX(hoverIndex) / width) * 100}%`,
            transform: 'translateX(-50%)',
            backgroundColor: '#111827',
            color: '#FFFFFF',
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '0.72rem',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            pointerEvents: 'none',
            zIndex: 10,
            whiteSpace: 'nowrap'
          }}>
            <div style={{ fontWeight: 700, marginBottom: '2px' }}>{dataPoints[hoverIndex].label}</div>
            <div>Pos: <strong style={{ color: '#34D399' }}>{dataPoints[hoverIndex].pos}%</strong> &bull; Neu: {dataPoints[hoverIndex].neu}% &bull; Neg: <strong style={{ color: '#F87171' }}>{dataPoints[hoverIndex].neg}%</strong></div>
          </div>
        )}
      </div>
    </div>
  );
}

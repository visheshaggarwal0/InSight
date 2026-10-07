import { memo, useMemo, useState } from 'react';
import { ArrowRight, Smartphone, ShieldCheck, Sparkles, Layout, AlertCircle, Headphones, Tag, Layers, ChevronDown, ChevronUp } from 'lucide-react';
import { EmptyState } from './EmptyState';
import type { ThemeCluster } from '../types/telemetry';

interface TopThemesListProps {
  themes: ThemeCluster[];
  selectedClusterId: number | null;
  onSelectCluster: (id: number, title: string) => void;
  onViewAll: () => void;
}

const ICONS = [Smartphone, ShieldCheck, Sparkles, Layout, AlertCircle, Headphones, Tag, Layers];
const COLORS = ['#0F382E', '#10B981', '#14B8A6', '#34D399', '#6EE7B7', '#A7F3D0', '#A7F3D0', '#D1FAE5'];

function ComponentTopThemesList({ themes, selectedClusterId, onSelectCluster, onViewAll }: TopThemesListProps) {
  const [showAll, setShowAll] = useState(false);

  const { rows, totalCount } = useMemo(() => {
    const total = themes.reduce((acc, t) => acc + (t.review_count || 0), 0);
    const sliceCount = showAll ? themes.length : 8;
    const mapped = themes.slice(0, sliceCount).map((t, idx) => ({
      id: t.cluster_id,
      title: t.title,
      count: t.review_count ?? 0,
      percent: total > 0 ? (t.review_count / total) * 100 : 0,
      color: COLORS[idx % COLORS.length],
      icon: ICONS[idx % ICONS.length]
    }));
    return { rows: mapped, totalCount: total };
  }, [themes, showAll]);

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
            Themes
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#6B7280', backgroundColor: '#F3F4F6', padding: '2px 6px', borderRadius: '4px' }}>
            {themes.length} total
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {themes.length > 8 && (
            <button
              onClick={() => setShowAll(!showAll)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'none',
                border: 'none',
                color: '#4B5563',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <span>{showAll ? 'Show top 8' : `Show all (${themes.length})`}</span>
              {showAll ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          )}
          <button
            onClick={onViewAll}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              background: 'none',
              border: 'none',
              color: '#10B981',
              fontSize: '0.8rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            <span>Explorer</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>

      {/* Theme List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {rows.length === 0 ? (
          <EmptyState
            label="No themes to display."
            hint={totalCount === 0 ? 'The active dataset produced no clusters.' : undefined}
          />
        ) : (
          rows.map((item, idx) => {
            const Icon = item.icon;
            const isSelected = selectedClusterId === item.id;
            const pctText = item.percent.toFixed(1);

            return (
              <button
                type="button"
                key={item.id}
                onClick={() => onSelectCluster(item.id, item.title)}
                aria-pressed={isSelected}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: isSelected ? '#ECFDF5' : 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  transition: 'background 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) e.currentTarget.style.backgroundColor = '#F9FAFB';
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {/* Rank Number */}
                <span style={{
                  width: '14px',
                  fontSize: '0.78rem',
                  fontWeight: 700,
                  color: '#9CA3AF',
                  textAlign: 'right'
                }}>
                  {idx + 1}
                </span>

                {/* Icon Circle */}
                <span style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '50%',
                  backgroundColor: '#ECFDF5',
                  color: '#10B981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  <Icon size={14} />
                </span>

                {/* Title */}
                <span style={{
                  flex: 1,
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: '#111827',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}>
                  {item.title}
                </span>

                {/* Count */}
                <span style={{
                  fontSize: '0.78rem',
                  color: '#6B7280',
                  fontWeight: 500,
                  minWidth: '48px',
                  textAlign: 'right'
                }}>
                  {item.count.toLocaleString()}
                </span>

                {/* Percentage */}
                <span style={{
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  color: '#374151',
                  minWidth: '42px',
                  textAlign: 'right'
                }}>
                  {pctText}%
                </span>

                {/* Progress Bar — width is the same number printed next to it */}
                <span style={{
                  width: '80px',
                  height: '8px',
                  backgroundColor: '#F3F4F6',
                  borderRadius: '999px',
                  overflow: 'hidden',
                  flexShrink: 0,
                  display: 'block'
                }}>
                  <span
                    style={{
                      display: 'block',
                      width: `${Math.max(0, Math.min(100, item.percent))}%`,
                      height: '100%',
                      backgroundColor: item.color,
                      borderRadius: '999px',
                      transition: 'width 0.4s ease'
                    }}
                  />
                </span>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

export const TopThemesList = memo(ComponentTopThemesList);

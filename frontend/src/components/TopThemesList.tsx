import { ArrowRight, Smartphone, ShieldCheck, Sparkles, Layout, AlertCircle, Headphones, Tag, Layers } from 'lucide-react';
import type { ThemeCluster } from '../types/telemetry';

interface TopThemesListProps {
  themes: ThemeCluster[];
  selectedClusterId: number | null;
  onSelectCluster: (id: number, title: string) => void;
  onViewAll: () => void;
}

export function TopThemesList({ themes, selectedClusterId, onSelectCluster, onViewAll }: TopThemesListProps) {
  // Fallback themes matching the exact ChatGPT mockup if backend themes haven't loaded yet
  const defaultThemes = [
    { id: 1, title: 'App Performance', count: 2341, percent: 23, color: '#0F382E', icon: Smartphone },
    { id: 2, title: 'Login & Authentication', count: 1842, percent: 18, color: '#10B981', icon: ShieldCheck },
    { id: 3, title: 'Feature Requests', count: 1276, percent: 12, color: '#14B8A6', icon: Sparkles },
    { id: 4, title: 'UI / UX', count: 1201, percent: 11, color: '#34D399', icon: Layout },
    { id: 5, title: 'Bugs & Crashes', count: 980, percent: 9, color: '#6EE7B7', icon: AlertCircle },
    { id: 6, title: 'Customer Support', count: 742, percent: 7, color: '#A7F3D0', icon: Headphones },
    { id: 7, title: 'Pricing', count: 532, percent: 5, color: '#A7F3D0', icon: Tag },
    { id: 8, title: 'Other', count: 430, percent: 4, color: '#D1FAE5', icon: Layers },
  ];

  // If backend themes are present, map them to this beautiful structure
  const displayThemes = themes.length > 0 ? themes.slice(0, 8).map((t, idx) => {
    const totalCount = themes.reduce((acc, curr) => acc + curr.review_count, 0) || 10000;
    const percent = Math.round((t.review_count / totalCount) * 100) || defaultThemes[idx]?.percent || 5;
    const icons = [Smartphone, ShieldCheck, Sparkles, Layout, AlertCircle, Headphones, Tag, Layers];
    const colors = ['#0F382E', '#10B981', '#14B8A6', '#34D399', '#6EE7B7', '#A7F3D0', '#A7F3D0', '#D1FAE5'];
    
    return {
      id: t.cluster_id,
      title: t.title,
      count: t.review_count,
      percent,
      color: colors[idx % colors.length],
      icon: icons[idx % icons.length]
    };
  }) : defaultThemes;

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px'
      }}>
        <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
          Top Themes
        </h3>
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
          <span>View all</span>
          <ArrowRight size={13} />
        </button>
      </div>

      {/* Theme List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {displayThemes.map((item, idx) => {
          const Icon = item.icon;
          const isSelected = selectedClusterId === item.id;

          return (
            <div
              key={item.id}
              onClick={() => onSelectCluster(item.id, item.title)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '8px 10px',
                borderRadius: '8px',
                backgroundColor: isSelected ? '#ECFDF5' : 'transparent',
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
              <div style={{
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
              </div>

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
                minWidth: '42px',
                textAlign: 'right'
              }}>
                {item.count.toLocaleString()}
              </span>

              {/* Percentage */}
              <span style={{
                fontSize: '0.78rem',
                fontWeight: 600,
                color: '#374151',
                minWidth: '32px',
                textAlign: 'right'
              }}>
                {item.percent}%
              </span>

              {/* Progress Bar */}
              <div style={{
                width: '80px',
                height: '8px',
                backgroundColor: '#F3F4F6',
                borderRadius: '999px',
                overflow: 'hidden',
                flexShrink: 0
              }}>
                <div
                  style={{
                    width: `${Math.min(100, item.percent * 3.5)}%`,
                    height: '100%',
                    backgroundColor: item.color,
                    borderRadius: '999px',
                    transition: 'width 0.4s ease'
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

import { useState } from 'react';
import {
  LayoutDashboard,
  Award,
  GitCompare,
  Settings,
  Sparkles,
  ShieldAlert,
  Lightbulb,
  SplitSquareVertical,
  Filter,
  Kanban,
  LineChart,
  X
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenGovernance?: () => void;
  onOpenCopilot?: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: typeof LayoutDashboard;
  badge?: string;
  /**
   * Present for entries that open something instead of switching tabs. Those
   * must never carry `aria-current`, which means "you are on this page".
   */
  action?: () => void;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

export function Sidebar({
  currentTab,
  onSelectTab,
  onOpenGovernance,
  onOpenCopilot: _onOpenCopilot,
  isOpen = false,
  onClose
}: SidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const navSections: NavSection[] = [
    {
      title: 'Core Telemetry',
      items: [
        { id: 'dashboard', label: 'Executive Dashboard', icon: LayoutDashboard },
        { id: 'clause-deconstruction', label: 'Clause Fallacy Solver', icon: SplitSquareVertical, badge: 'Demo' },
      ],
    },
    {
      title: 'Intent Streams',
      items: [
        { id: 'complaints', label: 'Complaint Radar', icon: ShieldAlert, badge: 'P0-P3' },
        { id: 'strengths', label: 'Product Strengths', icon: Sparkles, badge: 'Delight' },
        { id: 'features', label: 'Feature Requests', icon: Lightbulb, badge: 'Wishlist' },
        { id: 'noise', label: 'Noise Quarantine', icon: Filter },
      ],
    },
    {
      title: 'Analytics & Strategy',
      items: [
        { id: 'analytics', label: 'Analytics & Visual BI', icon: LineChart },
        { id: 'actionmatrix', label: 'Action & ROI Matrix', icon: Kanban },
        { id: 'compare', label: 'Head-to-Head Compare', icon: GitCompare },
      ],
    },
    {
      title: 'Platform',
      items: [
        { id: 'governance', label: 'Model Governance', icon: Award, action: onOpenGovernance, badge: 'Audit ↗' },
        { id: 'settings', label: 'Data & Ingestion', icon: Settings },
      ],
    },
  ];

  const getBadgeColors = (id: string) => {
    switch (id) {
      case 'complaints':
        return { bg: '#FEE2E2', color: '#B91C1C' };
      case 'strengths':
        return { bg: '#DCFCE7', color: '#15803D' };
      case 'features':
        return { bg: '#EEF2FF', color: '#4338CA' };
      case 'clause-deconstruction':
        return { bg: '#FEF3C7', color: '#B45309' };
      case 'governance':
        return { bg: '#F3F4F6', color: '#374151' };
      default:
        return { bg: '#F3F4F6', color: '#4B5563' };
    }
  };

  return (
    <aside className={`sidebar-desktop ${isOpen ? 'sidebar-open' : ''}`}>
      <div>
        {/* Brand Logo & Mobile Close Button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 6px 18px 6px' }}>
          <img
            src="/insight-logo.png"
            alt="InSight — Real Feedback. Real Insights."
            style={{ height: '28px', width: 'auto', display: 'block', objectFit: 'contain' }}
          />
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="mobile-menu-btn"
              style={{ padding: '4px', border: 'none', background: 'transparent', cursor: 'pointer' }}
              aria-label="Close navigation"
            >
              <X size={20} aria-hidden="true" style={{ color: '#6B7280' }} />
            </button>
          )}
        </div>

        {/* Grouped Navigation List */}
        <nav aria-label="Primary" style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {navSections.map((section) => (
            <div key={section.title} style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              <div
                style={{
                  fontSize: '0.64rem',
                  fontWeight: 700,
                  letterSpacing: '0.06em',
                  color: '#9CA3AF',
                  textTransform: 'uppercase',
                  padding: '4px 10px 4px 10px',
                }}
              >
                {section.title}
              </div>

              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  currentTab === item.id ||
                  (item.id === 'analytics' && ['visual-analytics', 'powerbi', 'trends'].includes(currentTab));
                const isHovered = hoveredId === item.id;
                const badgeStyle = getBadgeColors(item.id);

                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-current={isActive ? 'page' : undefined}
                    onClick={() => {
                      if (item.action) {
                        item.action();
                      } else {
                        onSelectTab(item.id);
                      }
                      onClose?.();
                    }}
                    onMouseEnter={() => setHoveredId(item.id)}
                    onMouseLeave={() => setHoveredId((current) => (current === item.id ? null : current))}
                    onFocus={() => setHoveredId(item.id)}
                    onBlur={() => setHoveredId((current) => (current === item.id ? null : current))}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '9px',
                      width: '100%',
                      padding: '7px 10px',
                      borderRadius: '8px',
                      border: 'none',
                      boxShadow: isActive ? 'inset 3px 0 0 #0F382E' : 'none',
                      backgroundColor: isActive ? '#E6F7F0' : isHovered ? '#F3F4F6' : 'transparent',
                      color: isActive ? '#065F46' : '#4B5563',
                      fontSize: '0.82rem',
                      fontWeight: isActive ? 700 : 500,
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'background-color 0.15s ease, color 0.15s ease',
                    }}
                  >
                    <Icon
                      size={16}
                      aria-hidden="true"
                      strokeWidth={isActive ? 2.2 : 1.8}
                      style={{ color: isActive ? '#047857' : '#6B7280', flexShrink: 0 }}
                    />
                    <span style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {item.label}
                    </span>
                    {item.badge && (
                      <span
                        style={{
                          fontSize: '0.63rem',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '999px',
                          backgroundColor: badgeStyle.bg,
                          color: badgeStyle.color,
                          flexShrink: 0,
                        }}
                      >
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Bottom CTA Card */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{
          backgroundColor: '#F0FDF4',
          border: '1px solid #D1FAE5',
          borderRadius: '12px',
          padding: '14px',
          position: 'relative'
        }}>
          <div
            aria-hidden="true"
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '26px',
              height: '26px',
              borderRadius: '6px',
              backgroundColor: '#DCFCE7',
              color: '#047857',
              marginBottom: '8px'
            }}
          >
            <Sparkles size={15} />
          </div>
          <p style={{
            fontSize: '0.78rem',
            fontWeight: 700,
            color: '#065F46',
            lineHeight: 1.35,
            marginBottom: '8px'
          }}>
            Turn feedback into better products.
          </p>
          <div
            aria-hidden="true"
            style={{
              width: '20px',
              height: '3px',
              borderRadius: '999px',
              backgroundColor: '#047857'
            }}
          />
        </div>
      </div>
    </aside>
  );
}

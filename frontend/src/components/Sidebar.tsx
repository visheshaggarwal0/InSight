import { useState } from 'react';
import {
  LayoutDashboard,
  MessageSquare,
  Layers,
  Smile,
  Award,
  TrendingUp,
  GitCompare,
  Settings,
  Sparkles,
  ShieldAlert,
  Lightbulb,
  SplitSquareVertical,
  Filter,
  X
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenGovernance?: () => void;
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

export function Sidebar({
  currentTab,
  onSelectTab,
  onOpenGovernance,
  isOpen = false,
  onClose
}: SidebarProps) {
  // Hover is React state rather than `e.currentTarget.style.backgroundColor = …`.
  // Direct style mutation writes an inline value that no stylesheet rule can
  // override afterwards, and it had no keyboard equivalent.
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'clause-deconstruction', label: 'Clause Fallacy Solver', icon: SplitSquareVertical, badge: 'AI Core' },
    { id: 'complaints', label: 'Complaint Radar', icon: ShieldAlert, badge: 'P0-P3' },
    { id: 'strengths', label: 'Product Strengths', icon: Sparkles, badge: 'Delight' },
    { id: 'features', label: 'Feature Requests', icon: Lightbulb, badge: 'New' },
    { id: 'noise', label: 'Noise Quarantine', icon: Filter, badge: 'Filtered' },
    { id: 'reviews', label: 'Reviews', icon: MessageSquare },
    { id: 'themes', label: 'Themes', icon: Layers },
    { id: 'sentiment', label: 'Sentiment', icon: Smile },
    // Wired to the real handler. It used to be declared on the props and then
    // silently dropped, so the governance report was unreachable from the nav.
    { id: 'governance', label: 'Model Governance', icon: Award, action: onOpenGovernance },
    { id: 'trends', label: 'Trends', icon: TrendingUp },
    { id: 'compare', label: 'Compare', icon: GitCompare },
    { id: 'settings', label: 'Data & Settings', icon: Settings }
  ];

  return (
    <aside className={`sidebar-desktop ${isOpen ? 'sidebar-open' : ''}`}>
      <div>
        {/* Brand Logo & Mobile Close Button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 6px 22px 6px' }}>
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

        {/* Navigation List */}
        <nav aria-label="Primary" style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            const isHovered = hoveredId === item.id;
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
                  gap: '10px',
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: 'none',
                  // Non-colour cue for the active item. Colour alone failed WCAG
                  // 1.4.1; the inset bar survives greyscale and forced colours.
                  boxShadow: isActive ? 'inset 3px 0 0 #0F382E' : 'none',
                  backgroundColor: isActive ? '#E6F7F0' : isHovered ? '#F3F4F6' : 'transparent',
                  color: isActive ? '#065F46' : '#4B5563',
                  fontSize: '0.84rem',
                  fontWeight: isActive ? 700 : 500,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'background-color 0.15s ease, color 0.15s ease'
                }}
              >
                <Icon
                  size={17}
                  aria-hidden="true"
                  strokeWidth={isActive ? 2.2 : 1.8}
                  style={{ color: isActive ? '#047857' : '#6B7280', flexShrink: 0 }}
                />
                <span style={{ flex: 1 }}>{item.label}</span>
                {item.badge && (
                  <span style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    padding: '1px 6px',
                    borderRadius: '999px',
                    backgroundColor: item.id === 'complaints' ? '#FEE2E2' : '#E0E7FF',
                    color: item.id === 'complaints' ? '#B91C1C' : '#4338CA',
                  }}>
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
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

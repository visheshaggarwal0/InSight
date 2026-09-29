import { 
  LayoutDashboard, 
  MessageSquare, 
  Layers, 
  Smile, 
  TrendingUp, 
  GitCompare, 
  Settings, 
  Sparkles,
  X
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenGovernance?: () => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ currentTab, onSelectTab, isOpen = false, onClose }: SidebarProps) {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'reviews', label: 'Reviews', icon: MessageSquare },
    { id: 'themes', label: 'Themes', icon: Layers },
    { id: 'sentiment', label: 'Sentiment', icon: Smile },
    { id: 'trends', label: 'Trends', icon: TrendingUp },
    { id: 'compare', label: 'Compare', icon: GitCompare },
    { id: 'settings', label: 'Data & Settings', icon: Settings },
  ];

  return (
    <aside className={`sidebar-desktop ${isOpen ? 'sidebar-open' : ''}`}>
      <div>
        {/* Brand Logo & Mobile Close Button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '4px 6px 22px 6px' }}>
          <img 
            src="/insight-logo.png" 
            alt="InSight - Real Feedback. Real Insights." 
            style={{ height: '28px', width: 'auto', display: 'block', objectFit: 'contain' }}
          />
          {onClose && (
            <button
              onClick={onClose}
              className="mobile-menu-btn"
              style={{ padding: '4px', border: 'none', background: 'transparent' }}
              aria-label="Close navigation"
            >
              <X size={20} style={{ color: '#6B7280' }} />
            </button>
          )}
        </div>

        {/* Navigation List */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onClose?.();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  width: '100%',
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: 'none',
                  backgroundColor: isActive ? '#E6F7F0' : 'transparent',
                  color: isActive ? '#065F46' : '#4B5563',
                  fontSize: '0.84rem',
                  fontWeight: isActive ? 600 : 500,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = '#F9FAFB';
                    e.currentTarget.style.color = '#111827';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = '#4B5563';
                  }
                }}
              >
                <Icon size={17} strokeWidth={isActive ? 2.2 : 1.8} style={{ color: isActive ? '#10B981' : '#6B7280' }} />
                <span>{item.label}</span>
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
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '26px',
            height: '26px',
            borderRadius: '6px',
            backgroundColor: '#DCFCE7',
            color: '#10B981',
            marginBottom: '8px'
          }}>
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
          <div style={{
            width: '20px',
            height: '3px',
            borderRadius: '999px',
            backgroundColor: '#10B981'
          }} />
        </div>
      </div>
    </aside>
  );
}

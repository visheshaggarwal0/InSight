import { 
  LayoutDashboard, 
  MessageSquare, 
  Layers, 
  Smile, 
  TrendingUp, 
  GitCompare, 
  Settings, 
  Sparkles 
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  onSelectTab: (tab: string) => void;
  onOpenGovernance?: () => void;
}

export function Sidebar({ currentTab, onSelectTab }: SidebarProps) {
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
    <aside style={{
      width: '240px',
      minWidth: '240px',
      backgroundColor: '#FFFFFF',
      borderRight: '1px solid #E8ECE9',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
      padding: '24px 16px',
      height: '100vh',
      position: 'sticky',
      top: 0,
      zIndex: 20
    }}>
      <div>
        {/* Brand Logo */}
        <div style={{ padding: '4px 10px 24px 10px' }}>
          <img 
            src="/insight-logo.png" 
            alt="InSight - Real Feedback. Real Insights." 
            style={{ height: '32px', width: 'auto', display: 'block', objectFit: 'contain' }}
          />
        </div>

        {/* Navigation List */}
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '10px',
                  border: 'none',
                  backgroundColor: isActive ? '#E6F7F0' : 'transparent',
                  color: isActive ? '#065F46' : '#4B5563',
                  fontSize: '0.86rem',
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
                <Icon size={18} strokeWidth={isActive ? 2.2 : 1.8} style={{ color: isActive ? '#10B981' : '#6B7280' }} />
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
          padding: '16px',
          position: 'relative'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '28px',
            height: '28px',
            borderRadius: '8px',
            backgroundColor: '#DCFCE7',
            color: '#10B981',
            marginBottom: '10px'
          }}>
            <Sparkles size={16} />
          </div>
          <p style={{
            fontSize: '0.82rem',
            fontWeight: 700,
            color: '#065F46',
            lineHeight: 1.35,
            marginBottom: '8px'
          }}>
            Turn feedback into better products.
          </p>
          <div style={{
            width: '24px',
            height: '4px',
            borderRadius: '999px',
            backgroundColor: '#10B981'
          }} />
        </div>
      </div>
    </aside>
  );
}

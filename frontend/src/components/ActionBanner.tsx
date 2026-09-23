import { Download, RefreshCw } from 'lucide-react';

interface ActionBannerProps {
  onExportReport: () => void;
}

export function ActionBanner({ onExportReport }: ActionBannerProps) {
  return (
    <div style={{
      backgroundColor: '#F0FDF4',
      border: '1px solid #D1FAE5',
      borderRadius: '16px',
      padding: '24px 32px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '24px',
      marginTop: '28px',
      marginBottom: '36px',
      flexWrap: 'wrap'
    }}>
      {/* Left Icon & Text */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{
          width: '46px',
          height: '46px',
          borderRadius: '50%',
          backgroundColor: '#DCFCE7',
          color: '#10B981',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0
        }}>
          <RefreshCw size={22} strokeWidth={2.2} />
        </div>

        <div>
          <h4 style={{
            fontSize: '1.15rem',
            fontWeight: 700,
            color: '#0F382E',
            letterSpacing: '-0.01em',
            marginBottom: '4px'
          }}>
            From feedback to action.
          </h4>
          <p style={{
            fontSize: '0.86rem',
            color: '#4B5563',
            fontWeight: 450
          }}>
            Spot issues early. Prioritise what matters. Build a better product.
          </p>
        </div>
      </div>

      {/* Right Export Button */}
      <button
        onClick={onExportReport}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '11px 22px',
          borderRadius: '999px',
          backgroundColor: '#0F382E',
          color: '#FFFFFF',
          border: 'none',
          fontSize: '0.86rem',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'all 0.18s ease',
          boxShadow: '0 2px 8px rgba(15, 56, 46, 0.2)'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = '#164E40';
          e.currentTarget.style.transform = 'translateY(-1px)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = '#0F382E';
          e.currentTarget.style.transform = 'translateY(0)';
        }}
      >
        <Download size={16} />
        <span>Export Report</span>
      </button>
    </div>
  );
}

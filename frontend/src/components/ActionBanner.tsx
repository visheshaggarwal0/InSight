import { useState } from 'react';
import { FileText, RefreshCw } from 'lucide-react';

interface ActionBannerProps {
  /**
   * Named for what App.tsx used to call it. The handler does NOT export
   * anything: it POSTs to `/ticket/generate` and opens the incident-ticket
   * modal. The label below was corrected to match the behaviour; the prop
   * name still lies and should be renamed to `onCreateIncidentTicket` in
   * App.tsx.
   */
  onExportReport: () => void;
}

export function ActionBanner({ onExportReport }: ActionBannerProps) {
  // React state instead of `e.currentTarget.style.backgroundColor = …`.
  // Mutating inline styles bypasses the stylesheet, wins over every rule that
  // comes later, and had no `:focus`/`:active` counterpart at all.
  const [isHovered, setIsHovered] = useState(false);

  return (
    <section className="action-banner-container" aria-labelledby="action-banner-heading">
      {/* Left Icon & Text */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flex: '1 1 auto', minWidth: 0 }}>
        <div
          aria-hidden="true"
          style={{
            width: '46px',
            height: '46px',
            borderRadius: '50%',
            backgroundColor: '#DCFCE7',
            color: '#047857',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}
        >
          <RefreshCw size={22} strokeWidth={2.2} />
        </div>

        <div>
          <h4
            id="action-banner-heading"
            style={{
              fontSize: '1.15rem',
              fontWeight: 700,
              color: '#0F382E',
              letterSpacing: '-0.01em',
              marginBottom: '4px'
            }}
          >
            From feedback to action.
          </h4>
          <p style={{ fontSize: '0.86rem', color: '#4B5563', fontWeight: 450 }}>
            Spot issues early. Prioritise what matters. Build a better product.
          </p>
        </div>
      </div>

      {/* Primary action. Relabelled from "Export Report" because nothing is
          exported: the handler generates an incident ticket. */}
      <button
        type="button"
        onClick={onExportReport}
        className="action-banner-button"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onFocus={() => setIsHovered(true)}
        onBlur={() => setIsHovered(false)}
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          padding: '11px 22px',
          borderRadius: '999px',
          backgroundColor: isHovered ? '#164E40' : '#0F382E',
          color: '#FFFFFF',
          border: 'none',
          fontSize: '0.86rem',
          fontWeight: 600,
          cursor: 'pointer',
          transition: 'background-color 0.18s ease, box-shadow 0.18s ease',
          boxShadow: isHovered ? '0 4px 14px rgba(15, 56, 46, 0.28)' : '0 2px 8px rgba(15, 56, 46, 0.2)'
        }}
      >
        <FileText size={16} aria-hidden="true" />
        <span>Create Incident Ticket</span>
      </button>
    </section>
  );
}

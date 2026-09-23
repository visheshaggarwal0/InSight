import { ChevronRight } from 'lucide-react';

interface HeroBannerProps {
  totalReviews?: number;
}

export function HeroBanner({ totalReviews = 10000 }: HeroBannerProps) {
  const formattedCount = totalReviews.toLocaleString() + '+ reviews';

  return (
    <section style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '36px 0 28px 0',
      gap: '32px',
      position: 'relative'
    }}>
      {/* Editorial Headline */}
      <div style={{ maxWidth: '580px' }}>
        <h1 style={{
          fontFamily: "'Playfair Display', Georgia, serif",
          fontSize: '3.1rem',
          lineHeight: 1.15,
          fontWeight: 700,
          color: '#111827',
          letterSpacing: '-0.02em',
          marginBottom: '14px'
        }}>
          Your users are talking.<br />
          <span style={{ color: '#059669' }}>We help you listen.</span>
        </h1>
        <p style={{
          fontSize: '1.05rem',
          color: '#6B7280',
          fontWeight: 400,
          letterSpacing: '0.01em'
        }}>
          Summarise. Understand. Act.
        </p>
      </div>

      {/* SVG Narrative Flow Widget */}
      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        padding: '16px 24px',
        borderRadius: '24px',
        background: 'radial-gradient(ellipse at 80% 50%, rgba(209, 250, 229, 0.45), transparent 70%)',
      }}>
        {/* Left Source Card */}
        <div style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 4px 14px -2px rgba(16, 185, 129, 0.08)',
          padding: '12px 18px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '8px',
          zIndex: 2
        }}>
          <span style={{
            fontSize: '0.75rem',
            fontWeight: 700,
            color: '#065F46',
            backgroundColor: '#ECFDF5',
            padding: '3px 10px',
            borderRadius: '999px',
            border: '1px solid #A7F3D0'
          }}>
            {formattedCount}
          </span>
          <div style={{
            width: '46px',
            height: '32px',
            borderRadius: '6px',
            backgroundColor: '#F9FAFB',
            border: '1px solid #E5E7EB',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            padding: '4px 6px',
            gap: '4px'
          }}>
            <div style={{ height: '3px', width: '80%', backgroundColor: '#10B981', borderRadius: '2px' }} />
            <div style={{ height: '3px', width: '100%', backgroundColor: '#CBD5E1', borderRadius: '2px' }} />
            <div style={{ height: '3px', width: '60%', backgroundColor: '#CBD5E1', borderRadius: '2px' }} />
          </div>
        </div>

        {/* Curved Flow Lines SVG */}
        <svg width="60" height="90" viewBox="0 0 60 90" fill="none" style={{ margin: '0 4px', zIndex: 1 }}>
          <path d="M 0 45 C 30 45, 30 18, 60 18" stroke="#10B981" strokeWidth="1.8" strokeDasharray="3 3" opacity="0.8" />
          <path d="M 0 45 L 60 45" stroke="#10B981" strokeWidth="1.8" opacity="0.9" />
          <path d="M 0 45 C 30 45, 30 72, 60 72" stroke="#10B981" strokeWidth="1.8" strokeDasharray="3 3" opacity="0.8" />
        </svg>

        {/* Right Output Pillars */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          zIndex: 2
        }}>
          {[
            { label: 'Key themes', bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' },
            { label: 'Real insights', bg: '#F0FDF4', text: '#065F46', border: '#BBF7D0' },
            { label: 'Happier users', bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' }
          ].map((pill, i) => (
            <div
              key={i}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '999px',
                backgroundColor: pill.bg,
                color: pill.text,
                border: `1px solid ${pill.border}`,
                fontSize: '0.78rem',
                fontWeight: 700,
                boxShadow: '0 1px 3px rgba(0,0,0,0.02)'
              }}
            >
              <ChevronRight size={14} style={{ color: '#10B981' }} />
              <span>{pill.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

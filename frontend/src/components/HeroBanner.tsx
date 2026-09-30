import { ChevronRight } from 'lucide-react';

interface HeroBannerProps {
  totalReviews?: number;
}

const OUTPUT_PILLARS = [
  { label: 'Key themes', bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' },
  { label: 'Real insights', bg: '#F0FDF4', text: '#065F46', border: '#BBF7D0' },
  { label: 'Happier users', bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' }
];

export function HeroBanner({ totalReviews = 10000 }: HeroBannerProps) {
  const formattedCount = totalReviews.toLocaleString() + '+ reviews';

  return (
    <section className="hero-section">
      {/* Editorial Headline */}
      <div style={{ maxWidth: '580px', width: '100%' }}>
        <h1 className="hero-title">
          Your users are talking.<br />
          {/* #059669 is only 3.4:1 on white — enough for large text, not for
              anything smaller. #047857 clears 4.5:1 at every size. */}
          <span style={{ color: '#047857' }}>We help you listen.</span>
        </h1>
        <p className="hero-subtitle">
          Summarise. Understand. Act.
        </p>
      </div>

      {/* SVG Narrative Flow Widget.
          The connectors, the fake "document" bars and the chevrons are pure
          decoration that repeats information already in the text, so they are
          hidden from assistive tech rather than announced as noise. The two
          content groups stay in the tree as a labelled list. */}
      <div
        className="hero-svg-widget"
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          padding: '16px 20px',
          borderRadius: '24px',
          background: 'radial-gradient(ellipse at 80% 50%, rgba(209, 250, 229, 0.45), transparent 70%)',
          maxWidth: '100%'
        }}
      >
        {/* Left Source Card */}
        <div
          style={{
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
          }}
        >
          <span
            style={{
              fontSize: '0.75rem',
              fontWeight: 700,
              color: '#065F46',
              backgroundColor: '#ECFDF5',
              padding: '3px 10px',
              borderRadius: '999px',
              border: '1px solid #A7F3D0',
              whiteSpace: 'nowrap'
            }}
          >
            {formattedCount}
          </span>
          <div
            aria-hidden="true"
            style={{
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
            }}
          >
            <div style={{ height: '3px', width: '80%', backgroundColor: '#047857', borderRadius: '2px' }} />
            <div style={{ height: '3px', width: '100%', backgroundColor: '#CBD5E1', borderRadius: '2px' }} />
            <div style={{ height: '3px', width: '60%', backgroundColor: '#CBD5E1', borderRadius: '2px' }} />
          </div>
        </div>

        {/* Curved Flow Lines SVG — decorative connector, no information of its own. */}
        <svg
          width="60"
          height="90"
          viewBox="0 0 60 90"
          fill="none"
          style={{ margin: '0 4px', zIndex: 1 }}
          aria-hidden="true"
          focusable="false"
        >
          <path d="M 0 45 C 30 45, 30 18, 60 18" stroke="#059669" strokeWidth="1.8" strokeDasharray="3 3" opacity="0.8" />
          <path d="M 0 45 L 60 45" stroke="#059669" strokeWidth="1.8" opacity="0.9" />
          <path d="M 0 45 C 30 45, 30 72, 60 72" stroke="#059669" strokeWidth="1.8" strokeDasharray="3 3" opacity="0.8" />
        </svg>

        {/* Right Output Pillars */}
        <ul
          aria-label="What InSight produces from that feedback"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            margin: 0,
            padding: 0,
            listStyle: 'none',
            zIndex: 2
          }}
        >
          {OUTPUT_PILLARS.map((pill) => (
            <li
              key={pill.label}
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
                boxShadow: '0 1px 3px rgba(0,0,0,0.02)',
                whiteSpace: 'nowrap'
              }}
            >
              <ChevronRight size={14} aria-hidden="true" style={{ color: '#047857' }} />
              <span>{pill.label}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

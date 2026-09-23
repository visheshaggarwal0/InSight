import { ArrowRight } from 'lucide-react';

interface KeywordCloudProps {
  onSelectWord?: (word: string) => void;
  onViewAll?: () => void;
}

export function KeywordCloud({ onSelectWord, onViewAll }: KeywordCloudProps) {
  const keywords = [
    { text: 'barcode', size: '0.85rem', color: '#6EE7B7', weight: 600, top: '12%', left: '16%' },
    { text: 'dark', size: '1.25rem', color: '#D97706', weight: 700, top: '8%', left: '48%' },
    { text: 'dark mode', size: '0.88rem', color: '#475569', weight: 500, top: '14%', left: '72%' },
    { text: 'update', size: '1.2rem', color: '#334155', weight: 600, top: '32%', left: '6%' },
    { text: 'love', size: '2.5rem', color: '#0F382E', weight: 800, top: '24%', left: '42%' },
    { text: 'price', size: '1.1rem', color: '#16A34A', weight: 600, top: '34%', left: '80%' },
    { text: 'login', size: '1.35rem', color: '#065F46', weight: 700, top: '48%', left: '12%' },
    { text: 'crash', size: '2.4rem', color: '#EF4444', weight: 800, top: '50%', left: '40%' },
    { text: 'slow', size: '1.4rem', color: '#DC2626', weight: 700, top: '46%', left: '78%' },
    { text: 'ui', size: '1.3rem', color: '#059669', weight: 700, top: '68%', left: '10%' },
    { text: 'great', size: '1.25rem', color: '#64748B', weight: 600, top: '60%', left: '78%' },
    { text: 'feature', size: '1.35rem', color: '#0F766E', weight: 700, top: '74%', left: '26%' },
    { text: 'payment', size: '1.15rem', color: '#94A3B8', weight: 500, top: '72%', left: '56%' },
    { text: 'amazing', size: '0.85rem', color: '#94A3B8', weight: 500, top: '88%', left: '14%' },
    { text: 'suggestion', size: '0.82rem', color: '#94A3B8', weight: 500, top: '88%', left: '46%' },
    { text: 'premium', size: '0.82rem', color: '#94A3B8', weight: 500, top: '88%', left: '76%' },
  ];

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
          Keyword Cloud
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

      {/* Cloud Canvas */}
      <div style={{
        position: 'relative',
        height: '240px',
        backgroundColor: '#FAFCFA',
        borderRadius: '12px',
        border: '1px dashed #E5E8E5',
        overflow: 'hidden'
      }}>
        {keywords.map((kw, i) => (
          <span
            key={i}
            onClick={() => onSelectWord && onSelectWord(kw.text)}
            style={{
              position: 'absolute',
              top: kw.top,
              left: kw.left,
              fontSize: kw.size,
              fontWeight: kw.weight,
              color: kw.color,
              cursor: 'pointer',
              userSelect: 'none',
              transition: 'transform 0.15s ease, filter 0.15s ease',
              lineHeight: 1
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'scale(1.15)';
              e.currentTarget.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.filter = 'none';
            }}
            title={`Filter reviews for "${kw.text}"`}
          >
            {kw.text}
          </span>
        ))}
      </div>
    </div>
  );
}

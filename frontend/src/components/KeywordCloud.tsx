import { ArrowRight } from 'lucide-react';
import type { KeywordCloudItem } from '../types/telemetry';

interface KeywordCloudProps {
  keywords?: KeywordCloudItem[];
  onSelectWord?: (word: string) => void;
  onViewAll?: () => void;
}

const DEFAULT_SLOTS = [
  { top: '12%', left: '16%' },
  { top: '8%', left: '48%' },
  { top: '14%', left: '72%' },
  { top: '32%', left: '6%' },
  { top: '24%', left: '42%' },
  { top: '34%', left: '80%' },
  { top: '48%', left: '12%' },
  { top: '50%', left: '40%' },
  { top: '46%', left: '78%' },
  { top: '68%', left: '10%' },
  { top: '60%', left: '78%' },
  { top: '74%', left: '26%' },
  { top: '72%', left: '56%' },
  { top: '88%', left: '14%' },
  { top: '88%', left: '46%' },
  { top: '88%', left: '76%' },
];

const FALLBACK_KEYWORDS = [
  { text: 'irritation', size: '1.25rem', color: '#EF4444', weight: 800 },
  { text: 'dropper', size: '1.4rem', color: '#D97706', weight: 700 },
  { text: 'hydrating', size: '2.4rem', color: '#0F382E', weight: 800 },
  { text: 'texture', size: '1.2rem', color: '#334155', weight: 600 },
  { text: 'glowing', size: '1.8rem', color: '#059669', weight: 700 },
  { text: 'cracked', size: '1.3rem', color: '#DC2626', weight: 700 },
  { text: 'delivery', size: '1.15rem', color: '#475569', weight: 500 },
  { text: 'sunscreen', size: '1.35rem', color: '#0F766E', weight: 700 },
  { text: 'burning', size: '1.5rem', color: '#EF4444', weight: 800 },
  { text: 'gentle', size: '1.1rem', color: '#16A34A', weight: 600 },
  { text: 'fragrance', size: '0.9rem', color: '#94A3B8', weight: 500 },
  { text: 'packaging', size: '1.35rem', color: '#065F46', weight: 700 },
  { text: 'dermatitis', size: '1.1rem', color: '#EF4444', weight: 700 },
  { text: 'fast shipping', size: '0.85rem', color: '#6EE7B7', weight: 600 },
  { text: 'repurchase', size: '0.88rem', color: '#475569', weight: 500 },
  { text: 'formula', size: '0.82rem', color: '#94A3B8', weight: 500 },
];

export function KeywordCloud({ keywords, onSelectWord, onViewAll }: KeywordCloudProps) {
  const activeKeywords = keywords && keywords.length > 0
    ? keywords.slice(0, 16).map((k, i) => ({
        text: k.text,
        size: k.size || '1.1rem',
        color: k.color || '#0F382E',
        weight: k.weight || 600,
        top: DEFAULT_SLOTS[i % DEFAULT_SLOTS.length].top,
        left: DEFAULT_SLOTS[i % DEFAULT_SLOTS.length].left
      }))
    : FALLBACK_KEYWORDS.map((k, i) => ({
        ...k,
        top: DEFAULT_SLOTS[i].top,
        left: DEFAULT_SLOTS[i].left
      }));

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
        {activeKeywords.map((kw, i) => (
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

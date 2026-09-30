import { memo, useMemo } from 'react';
import { ArrowRight } from 'lucide-react';
import { EmptyState } from './EmptyState';
import type { KeywordCloudItem } from '../types/telemetry';

interface KeywordCloudProps {
  keywords?: KeywordCloudItem[];
  onSelectWord?: (word: string) => void;
  onViewAll?: () => void;
}

const SLOTS = [
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
  { top: '88%', left: '76%' }
];

function ComponentKeywordCloud({ keywords, onSelectWord, onViewAll }: KeywordCloudProps) {
  const activeKeywords = useMemo(
    () =>
      (keywords ?? []).slice(0, SLOTS.length).map((k, i) => ({
        text: k.text,
        size: k.size || '1.1rem',
        color: k.color || '#0F382E',
        weight: k.weight ?? 600,
        top: SLOTS[i % SLOTS.length].top,
        left: SLOTS[i % SLOTS.length].left
      })),
    [keywords]
  );

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
      {activeKeywords.length === 0 ? (
        <EmptyState
          label="No keywords extracted."
          hint="The active dataset produced no keyphrases."
        />
      ) : (
        <div style={{
          position: 'relative',
          height: '240px',
          backgroundColor: '#FAFCFA',
          borderRadius: '12px',
          border: '1px dashed #E5E8E5',
          overflow: 'hidden'
        }}>
          {activeKeywords.map((kw) => (
            <span
              key={kw.text}
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
      )}
    </div>
  );
}

export const KeywordCloud = memo(ComponentKeywordCloud);

import { memo } from 'react';
import { ArrowRight, Star, Shield } from 'lucide-react';
import { EmptyState } from './EmptyState';
import type { SampleVerbatim, ThemeCluster } from '../types/telemetry';

interface ExampleReviewsListProps {
  themes: ThemeCluster[];
  selectedClusterId: number | null;
  onViewAll: () => void;
}

interface RenderReview {
  id: string;
  rating: number;
  date: string;
  /** Server-redacted text only. Raw PII is never read client-side. */
  redactedText: string;
  tags: Array<{ label: string; bg: string; text: string }>;
}

const TAG_STYLE_A = { bg: '#ECFDF5', text: '#065F46' };
const TAG_STYLE_B = { bg: '#F3F4F6', text: '#374151' };

function toRenderReview(v: SampleVerbatim, themeTitle: string, fallbackId: string): RenderReview {
  // `/themes` sets `text` to the server-redacted sample. `raw_text` is deliberately
  // never read here, so unredacted PII is not rendered from this payload.
  const redacted = (v.text ?? '').trim();
  return {
    id: v.id || fallbackId,
    rating: v.rating ?? 0,
    date: v.batch_or_version || 'Production',
    redactedText: redacted.length > 0 ? `\u201C${redacted}\u201D` : '',
    tags: [
      { label: themeTitle, ...TAG_STYLE_A },
      { label: v.sku_or_module || 'Standard SKU', ...TAG_STYLE_B }
    ]
  };
}

function ComponentExampleReviewsList({ themes, selectedClusterId, onViewAll }: ExampleReviewsListProps) {
  const selected = themes.find((t) => t.cluster_id === selectedClusterId);
  const displayReviews: RenderReview[] = (() => {
    if (selected && (selected.sample_verbatims?.length ?? 0) > 0) {
      return (selected.sample_verbatims ?? [])
        .slice(0, 3)
        .map((v, i) => toRenderReview(v, selected.title, `sample-${selected.cluster_id}-${i}`));
    }
    for (const theme of themes) {
      const samples = theme.sample_verbatims ?? [];
      if (samples.length > 0) {
        return samples
          .slice(0, 3)
          .map((v, i) => toRenderReview(v, theme.title, `sample-${theme.cluster_id}-${i}`));
      }
    }
    return [];
  })();

  const selectedCluster = selected;

  const renderStars = (count: number) => {
    const safe = Math.max(0, Math.min(5, Math.round(count || 0)));
    return Array.from({ length: 5 }, (_, idx) => {
      const isFilled = idx < safe;
      const starColor = safe >= 4 ? '#10B981' : safe === 3 ? '#F59E0B' : '#EF4444';
      return (
        <Star
          key={idx}
          size={14}
          fill={isFilled ? starColor : '#E5E7EB'}
          stroke="none"
        />
      );
    });
  };

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: '16px',
        flexWrap: 'wrap',
        gap: '8px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em' }}>
            Example Reviews
          </h3>
          {selectedCluster && (
            <span style={{
              fontSize: '0.72rem',
              backgroundColor: '#ECFDF5',
              color: '#065F46',
              padding: '2px 8px',
              borderRadius: '999px',
              fontWeight: 600
            }}>
              Filtered: {selectedCluster.title}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* PII state is enforced server-side; this is a status, not a client toggle. */}
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#F0FDF4',
              color: '#065F46',
              fontSize: '0.72rem',
              fontWeight: 600
            }}
            title="Verbatim text is redacted server-side before it reaches this page. Unredacted text requires a server-authorized auditor request."
          >
            <Shield size={12} style={{ color: '#10B981' }} />
            <span>Server Redacted</span>
          </span>

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
      </div>

      {/* Reviews List */}
      {displayReviews.length === 0 ? (
        <EmptyState
          label="No example reviews available."
          hint="The active dataset returned no sample verbatims."
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {displayReviews.map((rev) => (
            <div
              key={rev.id}
              style={{
                padding: '14px 16px',
                borderRadius: '10px',
                backgroundColor: '#FAFAFA',
                border: '1px solid #F3F4F6',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px'
              }}
            >
              {/* Stars & Date Header */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
                  {renderStars(rev.rating)}
                </div>
                <span style={{ fontSize: '0.74rem', color: '#9CA3AF', fontWeight: 500 }}>
                  {rev.date}
                </span>
              </div>

              {/* Review Verbatim (server-redacted) */}
              <p style={{
                fontSize: '0.83rem',
                color: '#374151',
                lineHeight: 1.45,
                fontWeight: 450,
                margin: 0
              }}>
                {rev.redactedText || '[Redacted]'}
              </p>

              {/* Tag Pills */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                {rev.tags.map((tag) => (
                  <span
                    key={tag.label}
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '6px',
                      backgroundColor: tag.bg,
                      color: tag.text
                    }}
                  >
                    {tag.label}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const ExampleReviewsList = memo(ComponentExampleReviewsList);

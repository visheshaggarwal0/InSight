import { useState } from 'react';
import { ArrowRight, Star, Shield, Eye, EyeOff } from 'lucide-react';
import type { ThemeCluster } from '../types/telemetry';

interface ExampleReviewsListProps {
  themes: ThemeCluster[];
  selectedClusterId: number | null;
  onViewAll: () => void;
}

export function ExampleReviewsList({ themes, selectedClusterId, onViewAll }: ExampleReviewsListProps) {
  const [isPiiMasked, setIsPiiMasked] = useState(true);

  // If a cluster is selected, find its sample verbatims
  const selectedCluster = themes.find(t => t.cluster_id === selectedClusterId);

  // Default reviews matching ChatGPT mockup
  const defaultReviews = [
    {
      id: 'rev-1',
      rating: 5,
      date: 'Sep 21, 2026',
      maskedText: '“Love the new update! The app is so much faster now and the UI feels cleaner. Great work by [REDACTED_NAME]!”',
      rawText: '“Love the new update! The app is so much faster now and the UI feels cleaner. Great work by Rohan Sharma!”',
      tags: [
        { label: 'App Performance', bg: '#EFF6FF', text: '#1D4ED8' },
        { label: 'UI / UX', bg: '#ECFDF5', text: '#065F46' }
      ]
    },
    {
      id: 'rev-2',
      rating: 2,
      date: 'Sep 20, 2026',
      maskedText: '“The app keeps crashing when I try to upload a file from [REDACTED_PHONE]. Really frustrating as this used to work fine earlier.”',
      rawText: '“The app keeps crashing when I try to upload a file from 9876543210. Really frustrating as this used to work fine earlier.”',
      tags: [
        { label: 'Bugs & Crashes', bg: '#FEF2F2', text: '#991B1B' }
      ]
    },
    {
      id: 'rev-3',
      rating: 4,
      date: 'Sep 19, 2026',
      maskedText: '“Would be great to have a dark mode option. Otherwise, loving the product for order [REDACTED_ORDER]!”',
      rawText: '“Would be great to have a dark mode option. Otherwise, loving the product for order #ORD-9912!”',
      tags: [
        { label: 'Feature Request', bg: '#F0FDF4', text: '#065F46' }
      ]
    }
  ];

  // Dynamically map from selected cluster if present
  const displayReviews = selectedCluster && selectedCluster.sample_verbatims?.length > 0
    ? selectedCluster.sample_verbatims.slice(0, 3).map((v, i) => ({
        id: v.id || `sample-${i}`,
        rating: v.rating || 4,
        date: 'Recent',
        maskedText: `“${v.text}”`,
        rawText: `“${v.text}”`,
        tags: [
          { label: selectedCluster.title, bg: '#ECFDF5', text: '#065F46' },
          { label: v.batch_or_version || 'Production', bg: '#F3F4F6', text: '#374151' }
        ]
      }))
    : defaultReviews;

  const renderStars = (count: number) => {
    return Array.from({ length: 5 }, (_, idx) => {
      const isFilled = idx < count;
      const starColor = count >= 4 ? '#10B981' : count === 3 ? '#F59E0B' : '#EF4444';
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
          {/* PII Masking Toggle */}
          <button
            onClick={() => setIsPiiMasked(!isPiiMasked)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              padding: '4px 10px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: isPiiMasked ? '#F0FDF4' : '#FFFBEB',
              color: isPiiMasked ? '#065F46' : '#92400E',
              fontSize: '0.72rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
            title="Toggle Live PII Masking (GDPR compliance verification)"
          >
            <Shield size={12} style={{ color: isPiiMasked ? '#10B981' : '#F59E0B' }} />
            {isPiiMasked ? <EyeOff size={11} /> : <Eye size={11} />}
            <span>{isPiiMasked ? 'GDPR Masked' : 'Raw Text'}</span>
          </button>

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

            {/* Review Verbatim */}
            <p style={{
              fontSize: '0.83rem',
              color: '#374151',
              lineHeight: 1.45,
              fontWeight: 450,
              fontStyle: 'normal'
            }}>
              {isPiiMasked ? rev.maskedText : rev.rawText}
            </p>

            {/* Tag Pills */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
              {rev.tags.map((tag, idx) => (
                <span
                  key={idx}
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
    </div>
  );
}

import { memo, useState } from 'react';
import { Lightbulb, Search, Tag, ThumbsUp } from 'lucide-react';
import type { FeatureRequestItem } from '../types/telemetry';

interface Props {
  featureRequests: FeatureRequestItem[];
  isLoading?: boolean;
}

export const FeatureRequestsView = memo(function FeatureRequestsView({
  featureRequests,
  isLoading = false,
}: Props) {
  const [search, setSearch] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('ALL');

  const filtered = featureRequests.filter((item) => {
    if (priorityFilter !== 'ALL' && item.priority !== priorityFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTitle = (item.title || '').toLowerCase().includes(q);
      const matchQuote = (item.medoid_quote || '').toLowerCase().includes(q);
      const matchKws = (item.feature_themes || item.keywords || []).some((kw) => (kw || '').toLowerCase().includes(q));
      return matchTitle || matchQuote || matchKws;
    }
    return true;
  });

  const totalVotes = featureRequests.reduce((acc, f) => acc + f.vote_count, 0);

  return (
    <div style={{ paddingTop: '32px' }}>
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.72rem',
              fontWeight: 700,
              backgroundColor: '#EEF2FF',
              color: '#4338CA',
              padding: '2px 8px',
              borderRadius: '999px',
              border: '1px solid #C7D2FE'
            }}>
              <Lightbulb size={12} /> AUTOMATED PRD &amp; ROADMAP RADAR
            </span>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              &bull; Sentence Intent: RECOMMENDATION Pool
            </span>
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
            Customer Wishlist &amp; Feature Proposals
          </h2>
          <p style={{ fontSize: '0.88rem', color: '#4B5563', marginTop: '4px', maxWidth: '820px' }}>
            Extracted directly from sentence-level suggestions (&ldquo;wish they had&rdquo;, &ldquo;please add&rdquo;, &ldquo;would love if&rdquo;). Automatically grouped into roadmap candidates for product engineering.
          </p>
        </div>

        <div style={{
          padding: '8px 16px',
          backgroundColor: '#FFFFFF',
          borderRadius: '8px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
        }}>
          <div style={{ fontSize: '0.7rem', color: '#6B7280', textTransform: 'uppercase', fontWeight: 600 }}>Total Suggestion Citations</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#4338CA', fontFamily: "'JetBrains Mono', monospace" }}>
            {totalVotes.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '22px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          backgroundColor: '#FFFFFF',
          border: '1px solid #E5E7EB',
          borderRadius: '8px',
          padding: '6px 12px',
          flex: '1',
          minWidth: '260px'
        }}>
          <Search size={15} style={{ color: '#9CA3AF' }} />
          <input
            type="text"
            placeholder="Search wishlist (e.g. pump, refill, scent)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: 'none',
              outline: 'none',
              fontSize: '0.82rem',
              width: '100%',
              backgroundColor: 'transparent'
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px' }}>
          {['ALL', 'HIGH', 'MEDIUM', 'LOW'].map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setPriorityFilter(p)}
              style={{
                padding: '6px 12px',
                fontSize: '0.76rem',
                fontWeight: priorityFilter === p ? 700 : 500,
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: priorityFilter === p ? '#4338CA' : '#F3F4F6',
                color: priorityFilter === p ? '#FFFFFF' : '#4B5563',
                transition: 'all 0.15s ease'
              }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Proposals Grid */}
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
          Loading customer feature proposals...
        </div>
      ) : filtered.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid #E5E7EB' }}>
          <p style={{ color: '#6B7280', fontSize: '0.9rem' }}>No feature proposals found matching your criteria.</p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {[...filtered]
            .sort((a, b) => b.vote_count - a.vote_count)
            .map((item, index) => {
              const rank = index + 1;
              const maxVotes = Math.max(...featureRequests.map((f) => f.vote_count), 1);
              const ratio = item.vote_count / maxVotes;
              const isTopRank = index === 0;

              return (
                <div
                  key={item.request_id}
                  className="dashboard-card"
                  style={{
                    padding: '22px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    borderRadius: '12px',
                    backgroundColor: isTopRank ? '#F5F3FF' : '#FFFFFF',
                    border: isTopRank ? '1.5px solid #C4B5FD' : '1px solid #E5E7EB',
                    borderLeft: isTopRank
                      ? '5px solid #6D28D9'
                      : item.priority === 'HIGH'
                      ? '4px solid #4F46E5'
                      : '4px solid #93C5FD',
                    boxShadow: isTopRank ? '0 4px 12px rgba(109, 40, 217, 0.08)' : '0 1px 3px rgba(0,0,0,0.03)',
                    opacity: isTopRank ? 1.0 : Math.max(0.85, 0.8 + 0.2 * ratio),
                    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                    gap: '14px'
                  }}
                >
                  <div>
                    {/* Meta */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 800,
                          padding: '2px 7px',
                          borderRadius: '4px',
                          backgroundColor: isTopRank ? '#5B21B6' : '#F3F4F6',
                          color: isTopRank ? '#FFFFFF' : '#374151',
                          fontFamily: "'JetBrains Mono', monospace"
                        }}>
                          #{rank} {isTopRank ? 'TOP WISHLIST' : ''}
                        </span>
                        <span style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          backgroundColor: item.priority === 'HIGH' ? '#EEF2FF' : '#EFF6FF',
                          color: item.priority === 'HIGH' ? '#4338CA' : '#1D4ED8'
                        }}>
                          {item.priority} PRIORITY
                        </span>
                      </div>

                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                        fontSize: '0.78rem',
                        fontWeight: 700,
                        color: '#111827',
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                        <ThumbsUp size={12} style={{ color: '#4338CA' }} />
                        {item.vote_count} customer votes
                      </span>
                    </div>

                    {/* Relative Vote Share Bar */}
                    <div style={{ marginBottom: '10px' }}>
                      <div style={{ width: '100%', height: '4px', backgroundColor: '#F3F4F6', borderRadius: '999px', overflow: 'hidden' }}>
                        <div style={{
                          width: `${Math.round(ratio * 100)}%`,
                          height: '100%',
                          backgroundColor: isTopRank ? '#6D28D9' : '#4F46E5',
                          borderRadius: '999px'
                        }} />
                      </div>
                    </div>

                {/* Title */}
                <h3 style={{
                  fontSize: '1.2rem',
                  fontWeight: 700,
                  color: '#111827',
                  margin: '0 0 10px 0',
                  fontFamily: "'DM Serif Display', Georgia, serif"
                }}>
                  {item.title}
                </h3>

                {/* Keywords / Feature Themes */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '14px' }}>
                  {(item.feature_themes || item.keywords || []).map((kw, i) => (
                    <span
                      key={i}
                      style={{
                        fontSize: '0.68rem',
                        backgroundColor: '#F3F4F6',
                        color: '#374151',
                        padding: '2px 7px',
                        borderRadius: '4px',
                        fontWeight: 500,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '3px'
                      }}
                    >
                      <Tag size={9} style={{ color: '#9CA3AF' }} />
                      {kw}
                    </span>
                  ))}
                </div>

                {/* Representative Medoid Customer Proposal */}
                <div style={{
                  padding: '12px 14px',
                  borderRadius: '8px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  fontSize: '0.8rem',
                  color: '#1E293B',
                  lineHeight: '1.45',
                  fontStyle: 'italic'
                }}>
                  &ldquo;{item.medoid_quote}&rdquo;
                </div>
              </div>

              {/* Sample Citations Count Footer */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                paddingTop: '10px',
                borderTop: '1px solid #F1F5F9',
                fontSize: '0.72rem',
                color: '#64748B'
              }}>
                <span>Source: {item.sample_quotes.length} sample quotes indexed</span>
                <span style={{ fontWeight: 600, color: '#4338CA' }}>PRD Candidate #{item.request_id + 1}</span>
              </div>
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
});

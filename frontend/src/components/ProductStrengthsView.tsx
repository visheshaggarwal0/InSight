import { memo, useState } from 'react';
import { Sparkles, Search, Eye, Quote, Tag } from 'lucide-react';
import type { PraiseClusterItem } from '../types/telemetry';

interface Props {
  clusters: PraiseClusterItem[];
  isLoading?: boolean;
  onInspectVerbatims: (clusterId: number, title: string) => void;
}

export const ProductStrengthsView = memo(function ProductStrengthsView({
  clusters,
  isLoading = false,
  onInspectVerbatims,
}: Props) {
  const [search, setSearch] = useState('');
  const [tierFilter, setTierFilter] = useState('ALL');

  const filtered = clusters.filter((item) => {
    if (tierFilter !== 'ALL' && item.delight_tier !== tierFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchTitle = (item.title || '').toLowerCase().includes(q);
      const matchQuote = (item.medoid_verbatim || '').toLowerCase().includes(q);
      const matchDrivers = (item.strength_drivers || item.keywords || []).some((kw) =>
        (kw || '').toLowerCase().includes(q)
      );
      return matchTitle || matchQuote || matchDrivers;
    }
    return true;
  });

  const totalPraise = clusters.reduce((acc, c) => acc + (c.praise_count || c.sentence_count || 0), 0);
  const avgDelight = clusters.length
    ? Math.round(clusters.reduce((acc, c) => acc + (c.delight_score || 85), 0) / clusters.length)
    : 0;

  return (
    <div style={{ paddingTop: '32px' }}>
      {/* Header */}
      <div
        style={{
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontSize: '0.72rem',
                fontWeight: 700,
                backgroundColor: '#ECFDF5',
                color: '#065F46',
                padding: '2px 8px',
                borderRadius: '999px',
                border: '1px solid #A7F3D0',
              }}
            >
              <Sparkles size={12} /> DELIGHT &amp; PRODUCT STRENGTHS RADAR
            </span>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              &bull; Sentence Intent: PRAISE Pool &bull; MiniLM + c-TF-IDF
            </span>
          </div>
          <h2
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: '#111827',
              fontFamily: "'DM Serif Display', Georgia, serif",
            }}
          >
            Product Strengths &amp; Delight Drivers
          </h2>
          <p style={{ fontSize: '0.88rem', color: '#4B5563', marginTop: '4px', maxWidth: '820px' }}>
            Unsupervised semantic clustering over positive customer sentences. Surfaces core product strengths,
            sensory satisfaction, and hero qualities directly from verified telemetry.
          </p>
        </div>

        {/* Metric Badges */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <div
            style={{
              padding: '8px 14px',
              backgroundColor: '#FFFFFF',
              borderRadius: '8px',
              border: '1px solid #E5E7EB',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: '#6B7280', textTransform: 'uppercase', fontWeight: 600 }}>
              Total Praise Citations
            </div>
            <div
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#065F46',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {totalPraise.toLocaleString()}
            </div>
          </div>

          <div
            style={{
              padding: '8px 14px',
              backgroundColor: '#ECFDF5',
              borderRadius: '8px',
              border: '1px solid #A7F3D0',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: '#065F46', textTransform: 'uppercase', fontWeight: 600 }}>
              Average Delight Index
            </div>
            <div
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#047857',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {avgDelight}%
            </div>
          </div>

          <div
            style={{
              padding: '8px 14px',
              backgroundColor: '#F0FDF4',
              borderRadius: '8px',
              border: '1px solid #BBF7D0',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
            }}
          >
            <div style={{ fontSize: '0.7rem', color: '#166534', textTransform: 'uppercase', fontWeight: 600 }}>
              Strength Themes
            </div>
            <div
              style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: '#15803D',
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              {clusters.length}
            </div>
          </div>
        </div>
      </div>

      {/* Search & Filter Bar */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '22px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
            padding: '6px 12px',
            flex: '1',
            minWidth: '260px',
          }}
        >
          <Search size={15} style={{ color: '#9CA3AF' }} />
          <input
            type="text"
            placeholder="Search strengths (e.g. hydration, glowing, texture, gentle)..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              border: 'none',
              outline: 'none',
              fontSize: '0.82rem',
              width: '100%',
              color: '#111827',
              backgroundColor: 'transparent',
            }}
          />
        </div>

        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          {(['ALL', 'EXCEPTIONAL', 'STRONG', 'NOTABLE'] as const).map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => setTierFilter(tier)}
              style={{
                padding: '4px 10px',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '6px',
                border: '1px solid',
                borderColor: tierFilter === tier ? '#059669' : '#E5E7EB',
                backgroundColor: tierFilter === tier ? '#ECFDF5' : '#FFFFFF',
                color: tierFilter === tier ? '#065F46' : '#4B5563',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
            >
              {tier}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '60px 0', color: '#6B7280', fontSize: '0.9rem' }}>
          Analyzing customer praise telemetry &amp; clustering strength drivers...
        </div>
      )}

      {/* Empty State */}
      {!isLoading && filtered.length === 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '48px 24px',
            backgroundColor: '#FFFFFF',
            borderRadius: '12px',
            border: '1px dashed #D1D5DB',
          }}
        >
          <Sparkles size={32} style={{ color: '#10B981', margin: '0 auto 12px' }} />
          <div style={{ fontSize: '1rem', fontWeight: 600, color: '#111827' }}>No strength themes match your criteria</div>
          <div style={{ fontSize: '0.82rem', color: '#6B7280', marginTop: '4px' }}>
            Try adjusting your search query or reset the delight tier filter.
          </div>
        </div>
      )}

      {/* Grid of Product Strength Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
          gap: '18px',
        }}
      >
        {[...filtered]
          .sort((a, b) => (b.praise_count || b.sentence_count || 0) - (a.praise_count || a.sentence_count || 0))
          .map((cluster, index) => {
            const drivers = cluster.strength_drivers || cluster.keywords || [];
            const count = cluster.praise_count || cluster.sentence_count || 0;
            const score = cluster.delight_score || 85;
            const rank = index + 1;
            const maxPraise = Math.max(...clusters.map((c) => c.praise_count || c.sentence_count || 0), 1);
            const ratio = count / maxPraise;
            const isTopRank = index === 0;

            const tierBg =
              cluster.delight_tier === 'EXCEPTIONAL'
                ? '#ECFDF5'
                : cluster.delight_tier === 'STRONG'
                ? '#F0FDF4'
                : '#F8FAFC';
            const tierColor =
              cluster.delight_tier === 'EXCEPTIONAL'
                ? '#065F46'
                : cluster.delight_tier === 'STRONG'
                ? '#166534'
                : '#475569';
            const tierBorder =
              cluster.delight_tier === 'EXCEPTIONAL'
                ? '#A7F3D0'
                : cluster.delight_tier === 'STRONG'
                ? '#BBF7D0'
                : '#E2E8F0';

            return (
              <div
                key={cluster.cluster_id}
                style={{
                  backgroundColor: isTopRank ? '#F0FDF4' : '#FFFFFF',
                  borderRadius: '12px',
                  border: isTopRank ? '1.5px solid #86EFAC' : '1px solid #E5E7EB',
                  borderLeft: isTopRank ? '5px solid #059669' : '4px solid #10B981',
                  padding: '20px',
                  boxShadow: isTopRank ? '0 4px 12px rgba(16, 185, 129, 0.08)' : '0 1px 3px rgba(0,0,0,0.03)',
                  opacity: isTopRank ? 1.0 : Math.max(0.85, 0.8 + 0.2 * ratio),
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease',
                }}
              >
                <div>
                  {/* Card Top: Rank, Title & Tier Badge */}
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '10px',
                      gap: '10px',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                        <span
                          style={{
                            fontSize: '0.68rem',
                            fontWeight: 800,
                            padding: '2px 7px',
                            borderRadius: '4px',
                            backgroundColor: isTopRank ? '#065F46' : '#F3F4F6',
                            color: isTopRank ? '#FFFFFF' : '#374151',
                            fontFamily: "'JetBrains Mono', monospace",
                          }}
                        >
                          #{rank} {isTopRank ? 'TOP STRENGTH' : ''}
                        </span>
                      </div>
                      <h3
                        style={{
                          fontSize: isTopRank ? '1.15rem' : '1.05rem',
                          fontWeight: 700,
                          color: '#111827',
                          margin: 0,
                          lineHeight: 1.3,
                        }}
                      >
                        {cluster.title}
                      </h3>
                    </div>
                    <span
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '999px',
                        backgroundColor: tierBg,
                        color: tierColor,
                        border: `1px solid ${tierBorder}`,
                        letterSpacing: '0.04em',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {cluster.delight_tier}
                    </span>
                  </div>

                {/* Metrics Row: Citations & Delight Index Bar */}
                <div style={{ marginBottom: '14px' }}>
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '0.78rem',
                      color: '#4B5563',
                      marginBottom: '5px',
                    }}
                  >
                    <span>
                      <strong style={{ color: '#065F46', fontWeight: 700 }}>{count.toLocaleString()}</strong> clauses
                      cited
                    </span>
                    <span style={{ fontWeight: 600, color: '#047857' }}>{score}% Delight</span>
                  </div>
                  <div
                    style={{
                      height: '5px',
                      width: '100%',
                      backgroundColor: '#E5E7EB',
                      borderRadius: '999px',
                      overflow: 'hidden',
                    }}
                  >
                    <div
                      style={{
                        height: '100%',
                        width: `${Math.min(100, Math.max(10, score))}%`,
                        backgroundColor: '#10B981',
                        borderRadius: '999px',
                      }}
                    />
                  </div>
                </div>

                {/* c-TF-IDF Strength Drivers Tags */}
                <div style={{ marginBottom: '14px' }}>
                  <div
                    style={{
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      color: '#6B7280',
                      textTransform: 'uppercase',
                      marginBottom: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                    }}
                  >
                    <Tag size={10} /> c-TF-IDF Strength Drivers
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                    {drivers.map((driver) => (
                      <span
                        key={driver}
                        style={{
                          fontSize: '0.72rem',
                          backgroundColor: '#F0FDF4',
                          color: '#166534',
                          border: '1px solid #BBF7D0',
                          padding: '2px 7px',
                          borderRadius: '4px',
                          fontWeight: 500,
                        }}
                      >
                        {driver}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Representative Medoid Quote */}
                <div
                  style={{
                    backgroundColor: '#F9FAFB',
                    border: '1px solid #F3F4F6',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    marginBottom: '16px',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', gap: '6px', alignItems: 'flex-start' }}>
                    <Quote size={13} style={{ color: '#10B981', flexShrink: 0, marginTop: '2px' }} />
                    <p
                      style={{
                        margin: 0,
                        fontSize: '0.8rem',
                        fontStyle: 'italic',
                        color: '#374151',
                        lineHeight: 1.4,
                      }}
                    >
                      &ldquo;{cluster.medoid_verbatim}&rdquo;
                    </p>
                  </div>
                </div>
              </div>

              {/* Card Footer: Action button */}
              <div
                style={{
                  borderTop: '1px solid #F3F4F6',
                  paddingTop: '12px',
                  display: 'flex',
                  justifyContent: 'flex-end',
                }}
              >
                <button
                  type="button"
                  onClick={() => onInspectVerbatims(cluster.cluster_id, cluster.title)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#065F46',
                    backgroundColor: '#ECFDF5',
                    border: '1px solid #A7F3D0',
                    borderRadius: '6px',
                    padding: '6px 12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  <Eye size={13} />
                  Inspect Verbatims ({cluster.verbatims?.length || 0})
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
});

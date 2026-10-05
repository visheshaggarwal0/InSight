import { memo, useState, useMemo } from 'react';
import { Eye, FileText, Quote, ShieldAlert, Zap, Tag, Search, ChevronLeft, ChevronRight } from 'lucide-react';
import type { ComplaintClusterItem } from '../types/telemetry';

interface Props {
  clusters: ComplaintClusterItem[];
  isLoading?: boolean;
  onInspectVerbatims: (clusterId: number, title: string) => void;
  onDispatchTicket: (clusterId: number) => void;
}

export const ComplaintClusterDashboard = memo(function ComplaintClusterDashboard({
  clusters,
  isLoading = false,
  onInspectVerbatims,
  onDispatchTicket,
}: Props) {
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(6);

  const filteredClusters = useMemo(() => {
    return clusters.filter((c) => {
      if (severityFilter !== 'ALL' && c.severity !== severityFilter) {
        return false;
      }
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      const inTitle = c.title.toLowerCase().includes(q);
      const inKeywords = (c.keywords || []).some((k) => k.toLowerCase().includes(q));
      const inMedoid = (c.medoid_verbatim || '').toLowerCase().includes(q);
      const inBatch = (c.affected_batch || '').toLowerCase().includes(q);
      return inTitle || inKeywords || inMedoid || inBatch;
    });
  }, [clusters, severityFilter, searchQuery]);

  const totalCitations = clusters.reduce((acc, c) => acc + c.sentence_count, 0);
  const criticalCount = clusters.filter((c) => c.severity === 'CRITICAL').length;
  const outlierCluster = clusters.find((c) => c.cluster_id === -1);
  const maxCitations = Math.max(...clusters.map((c) => c.sentence_count), 1);
  const sortedClusters = useMemo(() => {
    return [...filteredClusters].sort((a, b) => b.sentence_count - a.sentence_count);
  }, [filteredClusters]);

  const totalPages = pageSize === -1 ? 1 : Math.max(1, Math.ceil(sortedClusters.length / pageSize));
  const safePage = Math.min(currentPage, totalPages);

  const displayedClusters = useMemo(() => {
    if (pageSize === -1) return sortedClusters;
    const start = (safePage - 1) * pageSize;
    return sortedClusters.slice(start, start + pageSize);
  }, [sortedClusters, safePage, pageSize]);

  return (
    <div style={{ paddingTop: '32px' }}>
      {/* Top Header & Context */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              fontSize: '0.72rem',
              fontWeight: 700,
              backgroundColor: '#FEF2F2',
              color: '#B91C1C',
              padding: '2px 8px',
              borderRadius: '999px',
              border: '1px solid #FCA5A5'
            }}>
              <ShieldAlert size={12} /> SENTENCE-LEVEL DEEP DEFECT RADAR
            </span>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              &bull; 384-d MiniLM + c-TF-IDF Complaint Drivers
            </span>
          </div>
          <h2 style={{ fontSize: '1.75rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
            Complaint Cluster Intelligence &amp; Driver Analysis
          </h2>
          <p style={{ fontSize: '0.88rem', color: '#4B5563', marginTop: '4px', maxWidth: '820px' }}>
            Unsupervised clause-level complaint clustering. Bypasses the &ldquo;Whole-Document Fallacy&rdquo; by extracting defect propositions directly from raw verbatims regardless of positive star ratings.
          </p>
        </div>

        {/* Metric Badges */}
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{
            padding: '8px 14px',
            backgroundColor: '#FFFFFF',
            borderRadius: '8px',
            border: '1px solid #E5E7EB',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#6B7280', textTransform: 'uppercase', fontWeight: 600 }}>Total Defect Citations</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', fontFamily: "'JetBrains Mono', monospace" }}>
              {totalCitations.toLocaleString()}
            </div>
          </div>

          <div style={{
            padding: '8px 14px',
            backgroundColor: '#FEF2F2',
            borderRadius: '8px',
            border: '1px solid #FCA5A5',
            boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#991B1B', textTransform: 'uppercase', fontWeight: 600 }}>Critical (P0) Clusters</div>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#B91C1C', fontFamily: "'JetBrains Mono', monospace" }}>
              {criticalCount}
            </div>
          </div>

          {outlierCluster && (
            <div style={{
              padding: '8px 14px',
              backgroundColor: '#FFFBEB',
              borderRadius: '8px',
              border: '1px solid #FCD34D',
              boxShadow: '0 1px 2px rgba(0,0,0,0.04)'
            }}>
              <div style={{ fontSize: '0.7rem', color: '#92400E', textTransform: 'uppercase', fontWeight: 600 }}>Zero-Day Outliers</div>
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#B45309', fontFamily: "'JetBrains Mono', monospace" }}>
                {outlierCluster.sentence_count.toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Filter Tabs & Search Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '22px', borderBottom: '1px solid #E5E7EB', paddingBottom: '14px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((tier) => (
            <button
              key={tier}
              type="button"
              onClick={() => {
                setSeverityFilter(tier);
                setCurrentPage(1);
              }}
              style={{
                padding: '6px 14px',
                fontSize: '0.78rem',
                fontWeight: severityFilter === tier ? 700 : 500,
                borderRadius: '6px',
                border: 'none',
                cursor: 'pointer',
                backgroundColor: severityFilter === tier ? '#0F382E' : '#F3F4F6',
                color: severityFilter === tier ? '#FFFFFF' : '#4B5563',
                transition: 'all 0.15s ease'
              }}
            >
              {tier === 'ALL' ? 'All Tiers' : tier}
            </button>
          ))}
        </div>

        {/* Search input & pagination display options */}
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', color: '#9CA3AF' }} />
            <input
              type="text"
              placeholder="Filter defect titles or keywords..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              style={{
                padding: '6px 12px 6px 30px',
                fontSize: '0.8rem',
                borderRadius: '6px',
                border: '1px solid #D1D5DB',
                backgroundColor: '#FFFFFF',
                color: '#1F2937',
                outline: 'none',
                width: '240px',
                transition: 'border-color 0.15s ease'
              }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: '#F3F4F6', padding: '3px', borderRadius: '6px' }}>
            {[6, 12, -1].map((sz) => (
              <button
                key={sz}
                type="button"
                onClick={() => {
                  setPageSize(sz);
                  setCurrentPage(1);
                }}
                style={{
                  padding: '4px 8px',
                  fontSize: '0.72rem',
                  fontWeight: pageSize === sz ? 700 : 500,
                  borderRadius: '4px',
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: pageSize === sz ? '#FFFFFF' : 'transparent',
                  color: pageSize === sz ? '#111827' : '#6B7280',
                  boxShadow: pageSize === sz ? '0 1px 2px rgba(0,0,0,0.05)' : 'none'
                }}
              >
                {sz === -1 ? 'All' : `${sz}/page`}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Clusters Grid */}
      {isLoading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
          Loading complaint cluster telemetry...
        </div>
      ) : filteredClusters.length === 0 ? (
        <div style={{ padding: '40px', textAlign: 'center', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid #E5E7EB' }}>
          <p style={{ color: '#6B7280', fontSize: '0.9rem' }}>
            No complaint clusters found matching your criteria.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: '20px' }}>
          {displayedClusters.map((cluster, index) => {
            const isZeroDay = cluster.cluster_id === -1;
            const isCrit = cluster.severity === 'CRITICAL';
            const isHigh = cluster.severity === 'HIGH';
            const rank = index + 1;
            const ratio = cluster.sentence_count / maxCitations;
            const isTopRank = index === 0;

            return (
              <div
                key={cluster.cluster_id}
                className="dashboard-card"
                style={{
                  padding: '22px',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between',
                  borderRadius: '12px',
                  backgroundColor: isZeroDay ? '#FFFDF8' : isTopRank ? '#FEF2F2' : '#FFFFFF',
                  border: isZeroDay
                    ? '1.5px solid #FCD34D'
                    : isTopRank
                    ? '1.5px solid #FCA5A5'
                    : '1px solid #E5E7EB',
                  boxShadow: isTopRank ? '0 4px 12px rgba(220, 38, 38, 0.08)' : '0 1px 3px rgba(0,0,0,0.03)',
                  borderLeft: isZeroDay
                    ? '5px solid #F59E0B'
                    : isCrit
                    ? '5px solid #DC2626'
                    : isHigh
                    ? '5px solid #EA580C'
                    : '5px solid #3B82F6',
                  opacity: isTopRank ? 1.0 : Math.max(0.85, 0.8 + 0.2 * ratio),
                  gap: '14px',
                  position: 'relative',
                  transition: 'transform 0.15s ease, box-shadow 0.15s ease'
                }}
              >
                <div>
                  {/* Top Bar: Rank, Cluster ID & Severity Badge */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        padding: '2px 7px',
                        borderRadius: '4px',
                        backgroundColor: isTopRank ? '#991B1B' : '#F3F4F6',
                        color: isTopRank ? '#FFFFFF' : '#374151',
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                        #{rank} {isTopRank ? 'TOP DEFECT' : ''}
                      </span>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '999px',
                        backgroundColor: isZeroDay
                          ? '#FEF3C7'
                          : isCrit
                          ? '#FEE2E2'
                          : isHigh
                          ? '#FFEDD5'
                          : '#EFF6FF',
                        color: isZeroDay
                          ? '#92400E'
                          : isCrit
                          ? '#991B1B'
                          : isHigh
                          ? '#C2410C'
                          : '#1D4ED8'
                      }}>
                        {isZeroDay ? 'ZERO-DAY RADAR' : cluster.severity}
                      </span>
                    </div>

                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#111827', fontFamily: "'JetBrains Mono', monospace" }}>
                      {cluster.sentence_count} citations
                    </span>
                  </div>

                  {/* Volume Relative Bar */}
                  <div style={{ marginBottom: '10px' }}>
                    <div style={{ width: '100%', height: '4px', backgroundColor: '#F3F4F6', borderRadius: '999px', overflow: 'hidden' }}>
                      <div style={{
                        width: `${Math.round(ratio * 100)}%`,
                        height: '100%',
                        backgroundColor: isCrit ? '#DC2626' : isHigh ? '#EA580C' : '#3B82F6',
                        borderRadius: '999px'
                      }} />
                    </div>
                  </div>

                  {/* Title */}
                  <h3 style={{
                    fontSize: isTopRank ? '1.25rem' : '1.15rem',
                    fontWeight: 700,
                    color: '#111827',
                    margin: '0 0 8px 0',
                    fontFamily: "'DM Serif Display', Georgia, serif"
                  }}>
                    {cluster.title}
                  </h3>

                  {/* Relative Risk & Causal Attribution Pill */}
                  {cluster.affected_batch && (
                    <div style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      backgroundColor: cluster.is_statistically_significant ? '#FFF1F2' : '#F9FAFB',
                      color: cluster.is_statistically_significant ? '#9F1239' : '#4B5563',
                      border: cluster.is_statistically_significant ? '1px solid #FECDD3' : '1px solid #E5E7EB',
                      padding: '3px 8px',
                      borderRadius: '6px',
                      marginBottom: '10px'
                    }}>
                      <Zap size={12} style={{ color: cluster.is_statistically_significant ? '#E11D48' : '#9CA3AF' }} />
                      <span>Cohort: <strong>{cluster.affected_batch}</strong></span>
                      {cluster.relative_risk && cluster.relative_risk > 1.0 && (
                        <span>&bull; <strong>{cluster.relative_risk}x</strong> Relative Risk</span>
                      )}
                    </div>
                  )}

                  {/* c-TF-IDF Complaint Drivers */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px', marginBottom: '14px' }}>
                    {(cluster.complaint_drivers || cluster.keywords || []).slice(0, 6).map((kw, i) => (
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

                  {/* Representative Medoid Quote */}
                  <div style={{
                    padding: '10px 12px',
                    borderRadius: '8px',
                    backgroundColor: '#F9FAFB',
                    border: '1px solid #F3F4F6',
                    fontSize: '0.78rem',
                    color: '#374151',
                    fontStyle: 'italic',
                    lineHeight: '1.4',
                    position: 'relative'
                  }}>
                    <Quote size={12} style={{ color: '#9CA3AF', marginRight: '4px', verticalAlign: 'middle' }} />
                    &ldquo;{cluster.medoid_verbatim}&rdquo;
                  </div>
                </div>

                {/* Card Actions */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px', paddingTop: '12px', borderTop: '1px solid #F3F4F6' }}>
                  <button
                    type="button"
                    onClick={() => onInspectVerbatims(cluster.cluster_id, cluster.title)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      color: '#065F46',
                      backgroundColor: '#ECFDF5',
                      border: '1px solid #A7F3D0',
                      borderRadius: '6px',
                      padding: '5px 10px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Eye size={13} />
                    Inspect Verbatims
                  </button>

                  <button
                    type="button"
                    onClick={() => onDispatchTicket(cluster.cluster_id)}
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '5px',
                      fontSize: '0.76rem',
                      fontWeight: 600,
                      color: '#374151',
                      backgroundColor: '#F3F4F6',
                      border: '1px solid #E5E7EB',
                      borderRadius: '6px',
                      padding: '5px 10px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <FileText size={13} />
                    Dispatch Jira Ticket
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Pagination Controls */}
      {!isLoading && sortedClusters.length > 0 && totalPages > 1 && (
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '28px',
          paddingTop: '16px',
          borderTop: '1px solid #E5E7EB',
          flexWrap: 'wrap',
          gap: '12px'
        }}>
          <div style={{ fontSize: '0.82rem', color: '#6B7280' }}>
            Showing <strong>{(safePage - 1) * pageSize + 1}</strong> &ndash; <strong>{Math.min(safePage * pageSize, sortedClusters.length)}</strong> of <strong>{sortedClusters.length}</strong> defect clusters
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <button
              type="button"
              disabled={safePage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: safePage <= 1 ? '#9CA3AF' : '#374151',
                backgroundColor: safePage <= 1 ? '#F3F4F6' : '#FFFFFF',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                cursor: safePage <= 1 ? 'not-allowed' : 'pointer'
              }}
            >
              <ChevronLeft size={14} /> Previous
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setCurrentPage(p)}
                style={{
                  minWidth: '32px',
                  height: '32px',
                  fontSize: '0.78rem',
                  fontWeight: safePage === p ? 700 : 500,
                  borderRadius: '6px',
                  border: safePage === p ? '1px solid #0F382E' : '1px solid #E5E7EB',
                  backgroundColor: safePage === p ? '#0F382E' : '#FFFFFF',
                  color: safePage === p ? '#FFFFFF' : '#374151',
                  cursor: 'pointer'
                }}
              >
                {p}
              </button>
            ))}

            <button
              type="button"
              disabled={safePage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.78rem',
                fontWeight: 600,
                color: safePage >= totalPages ? '#9CA3AF' : '#374151',
                backgroundColor: safePage >= totalPages ? '#F3F4F6' : '#FFFFFF',
                border: '1px solid #D1D5DB',
                borderRadius: '6px',
                cursor: safePage >= totalPages ? 'not-allowed' : 'pointer'
              }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
});

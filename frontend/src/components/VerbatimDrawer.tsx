import React, { useCallback, useEffect, useRef, useState } from 'react';
import { X, Search, Shield, Star, Filter, Eye, ArrowUp, Loader2 } from 'lucide-react';
import { EmptyState } from './EmptyState';
import type { VerbatimItem } from '../types/telemetry';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const INITIAL_LIMIT = 10;
const SUBSEQUENT_LIMIT = 20;

interface Props {
  isOpen: boolean;
  onClose: () => void;
  clusterId?: number | null;
  clusterTitle?: string | null;
  /** Externally-driven search term (e.g. a keyword-cloud click). */
  search?: string;
  isComplaintCluster?: boolean;
  isPraiseCluster?: boolean;
  isSilentDefects?: boolean;
}

export const VerbatimDrawer: React.FC<Props> = ({
  isOpen,
  onClose,
  clusterId,
  clusterTitle,
  search: externalSearch,
  isComplaintCluster = false,
  isPraiseCluster = false,
  isSilentDefects = false
}) => {
  const [reviews, setReviews] = useState<VerbatimItem[]>([]);
  const [total, setTotal] = useState(0);
  const [showRawPii, setShowRawPii] = useState(false);
  const [search, setSearch] = useState('');
  const [searchDraft, setSearchDraft] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const listContainerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const generationRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);

  // Reset all paging/filter state when the drawer is re-opened for a different scope.
  const scopeKey = isOpen
    ? `${isSilentDefects ? 'silent' : isComplaintCluster ? 'complaint' : isPraiseCluster ? 'praise' : 'verbatim'}|${clusterId ?? 'all'}|${externalSearch ?? ''}`
    : 'closed';
  const [lastScopeKey, setLastScopeKey] = useState<string>('closed');
  if (scopeKey !== lastScopeKey) {
    setLastScopeKey(scopeKey);
    setSentimentFilter('');
    setShowRawPii(false);
    setSearch(externalSearch ?? '');
    setSearchDraft(externalSearch ?? '');
  }

  const fetchChunk = useCallback(async (
    offset: number,
    limit: number,
    signal?: AbortSignal
  ): Promise<{ items: VerbatimItem[]; total: number; hasMore: boolean }> => {
    if (isSilentDefects) {
      const res = await fetch(`${API_BASE}/reviews/silent-defects?limit=200`, { signal });
      if (!res.ok) throw new Error(`Silent defects query failed (HTTP ${res.status}).`);
      const data = await res.json();
      const all: VerbatimItem[] = ((data.silent_defects || []) as Array<{
        id?: string;
        display_text?: string;
        rating?: number;
        sentiment_pred?: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
        batch_or_version?: string;
        product_name?: string;
        sku_or_module?: string;
        highlight_span?: { text: string; start: number; end: number };
      }>).map((s) => ({
        id: s.id || 'REV-DEFECT',
        domain: 'd2c',
        raw_text: s.display_text || '',
        redacted_text: s.display_text || '',
        display_text: s.display_text || '',
        rating: s.rating ?? 4,
        sentiment_pred: s.sentiment_pred || 'POSITIVE',
        sentiment_confidence: 0.95,
        cluster_id: 0,
        theme_title: 'Silent Defect (Trojan Horse)',
        channel: 'Trojan Horse 4-5★ Review',
        batch_or_version: s.batch_or_version || 'Production',
        product_name: s.product_name || 'Verified Product',
        sku_or_module: s.sku_or_module || 'Standard SKU',
        highlight_span: s.highlight_span?.text ? s.highlight_span : undefined
      }));
      const sliced = all.slice(offset, offset + limit);
      return {
        items: sliced,
        total: all.length,
        hasMore: offset + limit < all.length
      };
    }

    if (isComplaintCluster && clusterId !== null && clusterId !== undefined) {
      const res = await fetch(`${API_BASE}/complaint-clusters/${clusterId}/verbatims?offset=${offset}&limit=${limit}`, {
        signal
      });
      if (!res.ok) throw new Error(`Complaint verbatims query failed (HTTP ${res.status}).`);
      const data = await res.json();
      const items: VerbatimItem[] = ((data.verbatims || []) as Array<{
        sentence_id?: string;
        review_id?: string;
        sentence_text?: string;
        start?: number;
        end?: number;
        confidence?: number;
      }>).map((v) => {
        const txt = v.sentence_text || '';
        return {
          id: v.sentence_id || v.review_id || 'SENT-COMPLAINT',
          domain: 'd2c',
          raw_text: txt,
          redacted_text: txt,
          display_text: txt,
          rating: 1,
          sentiment_pred: 'NEGATIVE' as const,
          sentiment_confidence: v.confidence ?? 0.95,
          cluster_id: clusterId ?? 0,
          theme_title: (data.title as string) || 'Complaint Driver',
          channel: 'Sentence Deconstructor',
          batch_or_version: (data.affected_batch as string) || 'Extracted Sentence',
          product_name: (data.title as string) || 'Complaint Driver',
          sku_or_module: `Offset [${v.start ?? 0}:${v.end ?? 0}]`,
          highlight_span: {
            text: txt,
            start: 0,
            end: txt.length
          }
        };
      });
      const tot = typeof data.total === 'number' ? data.total : items.length;
      return {
        items,
        total: tot,
        hasMore: Boolean(data.has_more ?? (offset + items.length < tot))
      };
    }

    if (isPraiseCluster && clusterId !== null && clusterId !== undefined) {
      const res = await fetch(`${API_BASE}/praise-clusters/${clusterId}/verbatims?offset=${offset}&limit=${limit}`, {
        signal
      });
      if (!res.ok) throw new Error(`Product strength verbatims query failed (HTTP ${res.status}).`);
      const data = await res.json();
      const items: VerbatimItem[] = ((data.verbatims || []) as Array<{
        sentence_id?: string;
        review_id?: string;
        sentence_text?: string;
        start?: number;
        end?: number;
        confidence?: number;
      }>).map((v) => {
        const txt = v.sentence_text || '';
        return {
          id: v.sentence_id || v.review_id || 'SENT-PRAISE',
          domain: 'd2c',
          raw_text: txt,
          redacted_text: txt,
          display_text: txt,
          rating: 5,
          sentiment_pred: 'POSITIVE' as const,
          sentiment_confidence: v.confidence ?? 0.95,
          cluster_id: clusterId ?? 0,
          theme_title: (data.title as string) || 'Product Strength',
          channel: 'Praise Medoid',
          batch_or_version: 'Extracted Sentence',
          product_name: (data.title as string) || 'Product Strength',
          sku_or_module: `Offset [${v.start ?? 0}:${v.end ?? 0}]`,
          highlight_span: {
            text: txt,
            start: 0,
            end: txt.length
          }
        };
      });
      const tot = typeof data.total === 'number' ? data.total : items.length;
      return {
        items,
        total: tot,
        hasMore: Boolean(data.has_more ?? (offset + items.length < tot))
      };
    }

    const params = new URLSearchParams({
      offset: offset.toString(),
      limit: limit.toString(),
      show_raw_pii: showRawPii ? 'true' : 'false'
    });
    if (clusterId !== null && clusterId !== undefined) {
      params.append('cluster_id', clusterId.toString());
    }
    if (sentimentFilter) {
      params.append('sentiment', sentimentFilter);
    }
    if (search) {
      params.append('search', search);
    }

    const res = await fetch(`${API_BASE}/verbatims?${params.toString()}`, { signal });
    if (!res.ok) throw new Error(`Verbatim query failed (HTTP ${res.status}).`);
    const data = await res.json();
    const items = Array.isArray(data.verbatims) ? data.verbatims : [];
    const tot = typeof data.total === 'number' ? data.total : 0;
    return {
      items,
      total: tot,
      hasMore: Boolean(data.has_more ?? (offset + items.length < tot))
    };
  }, [isSilentDefects, isComplaintCluster, isPraiseCluster, clusterId, showRawPii, sentimentFilter, search]);

  // Initial load: 10 items
  useEffect(() => {
    if (!isOpen) return;
    const generation = ++generationRef.current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const loadInitial = async () => {
      setLoading(true);
      setError(null);
      try {
        const result = await fetchChunk(0, INITIAL_LIMIT, controller.signal);
        if (generation !== generationRef.current) return;
        setReviews(result.items);
        setTotal(result.total);
        setHasMore(result.hasMore);
      } catch (err) {
        if ((err as Error)?.name === 'AbortError') return;
        if (generation !== generationRef.current) return;
        setError((err as Error).message);
      } finally {
        if (generation === generationRef.current) setLoading(false);
      }
    };

    void loadInitial();
  }, [isOpen, scopeKey, showRawPii, sentimentFilter, search, fetchChunk]);

  // Load more: 20 items appended
  const loadMore = useCallback(async () => {
    if (loading || loadingMore || !hasMore) return;
    const generation = generationRef.current;
    setLoadingMore(true);
    try {
      const currentOffset = reviews.length;
      const result = await fetchChunk(currentOffset, SUBSEQUENT_LIMIT);
      if (generation !== generationRef.current) return;
      setReviews((prev) => [...prev, ...result.items]);
      setHasMore(result.hasMore);
    } catch (err) {
      console.error('Failed to load more verbatims:', err);
    } finally {
      if (generation === generationRef.current) setLoadingMore(false);
    }
  }, [loading, loadingMore, hasMore, reviews.length, fetchChunk]);

  // IntersectionObserver on sentinel at the end of the list
  useEffect(() => {
    const target = sentinelRef.current;
    if (!target || !hasMore || loading || loadingMore) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          void loadMore();
        }
      },
      { root: listContainerRef.current, threshold: 0.1 }
    );

    observer.observe(target);
    return () => observer.disconnect();
  }, [hasMore, loading, loadingMore, loadMore]);

  // Unmount cleanup: abort any in-flight request so no response lands after teardown.
  useEffect(() => {
    const controller = abortRef.current;
    return () => controller?.abort();
  }, []);

  const handleSearchSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchDraft);
  }, [searchDraft]);

  const handleClearSearch = useCallback(() => {
    setSearchDraft('');
    setSearch('');
  }, []);

  if (!isOpen) return null;

  return (
    <div className="overlay-backdrop" style={{ justifyContent: 'flex-end' }}>
      <div
        className="verbatim-drawer-panel"
        style={{
          width: '100%',
          maxWidth: '740px',
          height: '100vh',
          borderRadius: '16px 0 0 16px',
          display: 'flex',
          flexDirection: 'column',
          backgroundColor: '#FFFFFF',
          borderLeft: '1px solid #E5E7EB',
          boxShadow: '-10px 0 40px rgba(0,0,0,0.12)',
          animation: 'slideInRight 0.18s ease-out'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '20px 24px',
          borderBottom: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#FFFFFF'
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Eye size={14} style={{ color: '#10B981' }} />
              <span style={{ fontSize: '0.7rem', fontWeight: 700, color: '#10B981', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                TRACEABLE VERBATIMS
              </span>
            </div>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: '3px', color: '#111827' }}>
              {clusterTitle ? clusterTitle : 'All Customer Verbatims'}
            </h2>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              Showing {reviews.length.toLocaleString()} of <b>{total.toLocaleString()} matched quotes</b>
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: '#F3F4F6',
              border: '1px solid #E5E7EB',
              color: '#4B5563',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '8px'
            }}
            aria-label="Close verbatim drawer"
          >
            <X size={16} />
          </button>
        </div>

        {/* Filter Controls Bar */}
        <div style={{
          padding: '12px 24px',
          backgroundColor: '#F9FAFB',
          borderBottom: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          {/* Search */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '200px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <input
                type="text"
                value={searchDraft}
                onChange={(e) => setSearchDraft(e.target.value)}
                placeholder="Search quotes, order IDs, errors..."
                aria-label="Search verbatims"
                style={{
                  width: '100%',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  padding: '7px 10px 7px 32px',
                  color: '#111827',
                  fontSize: '0.8rem',
                  outline: 'none'
                }}
              />
              <Search size={14} style={{ color: '#9CA3AF', position: 'absolute', left: '10px', top: '9px' }} />
            </div>
            {searchDraft !== search && (
              <button
                type="button"
                onClick={handleClearSearch}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#6B7280',
                  fontSize: '0.74rem',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap'
                }}
              >
                Clear
              </button>
            )}
          </form>

          {/* Sentiment Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Filter size={13} style={{ color: '#6B7280' }} />
            <select
              value={sentimentFilter}
              onChange={(e) => setSentimentFilter(e.target.value)}
              aria-label="Filter by sentiment"
              style={{
                backgroundColor: '#FFFFFF',
                border: '1px solid #E5E7EB',
                color: '#374151',
                fontSize: '0.78rem',
                borderRadius: '8px',
                padding: '6px 8px',
                outline: 'none'
              }}
            >
              <option value="">All Sentiments</option>
              <option value="NEGATIVE">Negative Only</option>
              <option value="NEUTRAL">Neutral Only</option>
              <option value="POSITIVE">Positive Only</option>
            </select>
          </div>

          {/* PII request toggle — the server decides what is actually returned. */}
          <button
            type="button"
            onClick={() => setShowRawPii(!showRawPii)}
            aria-pressed={showRawPii}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '999px',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: showRawPii ? '1px solid #FDE68A' : '1px solid #A7F3D0',
              backgroundColor: showRawPii ? '#FFFBEB' : '#ECFDF5',
              color: showRawPii ? '#92400E' : '#065F46',
              transition: 'all 0.15s ease'
            }}
            title="Requests raw text from the server. Whether unredacted PII is returned depends entirely on server-side authorization."
          >
            <Shield size={13} />
            {showRawPii ? 'Raw requested (server-gated)' : 'PII Scrubbed'}
          </button>
        </div>

        {/* Verbatims List */}
        <div ref={listContainerRef} style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {error ? (
            <EmptyState label={error} hint="Retry by changing a filter or reopening the drawer." />
          ) : loading ? (
            <div style={{ textAlign: 'center', padding: '50px', color: '#6B7280' }}>
              Querying reviews...
            </div>
          ) : reviews.length === 0 ? (
            <EmptyState
              label="No reviews match the current filters."
              hint={search ? `No quotes matched "${search}".` : undefined}
            />
          ) : (
            reviews.map((r) => (
              <div
                key={r.id}
                style={{
                  padding: '16px',
                  borderRadius: '10px',
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E5E7EB',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                  borderLeft: `4px solid ${
                    r.sentiment_pred === 'NEGATIVE'
                      ? '#EF4444'
                      : r.sentiment_pred === 'NEUTRAL'
                      ? '#F59E0B'
                      : '#10B981'
                  }`
                }}
              >
                {/* Meta details */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, color: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}>
                      {r.id}
                    </span>
                    <span style={{ fontSize: '0.7rem', backgroundColor: '#F3F4F6', padding: '2px 6px', borderRadius: '4px', color: '#374151', fontWeight: 500 }}>
                      {r.batch_or_version}
                    </span>
                    <span style={{ fontSize: '0.74rem', color: '#4B5563' }}>
                      {r.product_name} &bull; {r.sku_or_module}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', color: '#D97706', fontSize: '0.74rem', fontWeight: 600 }}>
                      <Star size={11} fill="#D97706" style={{ marginRight: '2px' }} />
                      {r.rating}★
                    </span>
                    <span style={{ fontSize: '0.7rem', color: '#6B7280' }}>
                      &bull; {r.channel}
                    </span>
                  </div>
                </div>

                {/* Review Text with Clause Span Highlighting (server-provided display_text only) */}
                <div style={{ fontSize: '0.84rem', color: '#1F2937', lineHeight: '1.5', fontWeight: 450 }}>
                  {r.highlight_span && r.highlight_span.text && r.display_text.includes(r.highlight_span.text) ? (
                    (() => {
                      const text = r.display_text;
                      const spanText = r.highlight_span.text;
                      const idx = text.indexOf(spanText);
                      const before = text.slice(0, idx);
                      const after = text.slice(idx + spanText.length);
                      const isNegative = r.sentiment_pred === 'NEGATIVE';
                      return (
                        <p style={{ margin: 0 }}>
                          {before}
                          <mark
                            style={{
                              backgroundColor: isNegative ? '#FEE2E2' : '#FEF3C7',
                              color: isNegative ? '#991B1B' : '#92400E',
                              padding: '2px 4px',
                              borderRadius: '4px',
                              fontWeight: 600,
                              borderBottom: `2px solid ${isNegative ? '#EF4444' : '#F59E0B'}`
                            }}
                            title="Linguistic Defect Span (Contrastive Clause)"
                          >
                            {spanText}
                          </mark>
                          {after}
                        </p>
                      );
                    })()
                  ) : (
                    <p style={{ margin: 0 }}>{r.display_text}</p>
                  )}
                </div>

                {/* Footer */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #F3F4F6' }}>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {r.pii_detected && r.pii_detected.length > 0 ? (
                      r.pii_detected.map((p, idx) => (
                        <span key={`${r.id}-pii-${idx}`} style={{
                          fontSize: '0.66rem',
                          backgroundColor: '#FEF3C7',
                          color: '#92400E',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          fontWeight: 600
                        }}>
                          SCRUBBED: {p}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.66rem', color: '#10B981', display: 'flex', alignItems: 'center', gap: '3px' }}>
                        <Shield size={10} /> Clean (No PII)
                      </span>
                    )}
                  </div>

                  <span style={{
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '999px',
                    backgroundColor: r.sentiment_pred === 'NEGATIVE' ? '#FEF2F2' : r.sentiment_pred === 'NEUTRAL' ? '#FFFBEB' : '#ECFDF5',
                    color: r.sentiment_pred === 'NEGATIVE' ? '#991B1B' : r.sentiment_pred === 'NEUTRAL' ? '#92400E' : '#065F46'
                  }}>
                    {r.sentiment_pred}
                  </span>
                </div>
              </div>
            ))
          )}

          {/* Infinite Scroll Sentinel */}
          {hasMore && (
            <div
              ref={sentinelRef}
              style={{
                padding: '16px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#6B7280',
                fontSize: '0.8rem',
                gap: '8px'
              }}
            >
              {loadingMore ? (
                <>
                  <Loader2 size={16} className="animate-spin" style={{ color: '#10B981' }} />
                  <span>Loading 20 more verbatims...</span>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => void loadMore()}
                  style={{
                    background: '#F3F4F6',
                    border: '1px solid #D1D5DB',
                    borderRadius: '8px',
                    padding: '8px 16px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#374151',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}
                >
                  Load 20 More Quotes &darr;
                </button>
              )}
            </div>
          )}
        </div>

        {/* Dynamic Continuous Scroll Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#FAFAFA'
        }}>
          <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
            Loaded <b>{reviews.length.toLocaleString()}</b> of <b>{total.toLocaleString()}</b> matched verbatims
            {hasMore ? ` (${total - reviews.length} more available)` : ' (All quotes loaded)'}
          </span>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {hasMore && (
              <button
                type="button"
                disabled={loadingMore}
                onClick={() => void loadMore()}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  padding: '6px 14px',
                  borderRadius: '6px',
                  border: '1px solid #10B981',
                  backgroundColor: '#ECFDF5',
                  color: '#065F46',
                  fontSize: '0.78rem',
                  fontWeight: 600,
                  cursor: loadingMore ? 'not-allowed' : 'pointer'
                }}
              >
                {loadingMore ? 'Loading 20 more...' : 'Load 20 More Quotes ↓'}
              </button>
            )}
            <button
              type="button"
              onClick={() => listContainerRef.current?.scrollTo({ top: 0, behavior: 'smooth' })}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #E5E7EB',
                backgroundColor: '#FFFFFF',
                color: '#374151',
                fontSize: '0.76rem',
                cursor: 'pointer'
              }}
              title="Scroll to top of verbatim list"
            >
              <ArrowUp size={13} /> Top
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

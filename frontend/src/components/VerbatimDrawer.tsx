import React, { useState, useEffect } from 'react';
import { X, Search, Shield, ShieldAlert, Star, Filter, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import type { VerbatimItem } from '../types/telemetry';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  clusterId?: number | null;
  clusterTitle?: string | null;
}

export const VerbatimDrawer: React.FC<Props> = ({
  isOpen,
  onClose,
  clusterId,
  clusterTitle
}) => {
  const [reviews, setReviews] = useState<VerbatimItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [showRawPii, setShowRawPii] = useState(false);
  const [search, setSearch] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const fetchVerbatims = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: '20',
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

      const res = await fetch(`http://localhost:8000/api/verbatims?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        setReviews(data.verbatims);
        setTotal(data.total);
      }
    } catch (err) {
      console.error("Failed to load verbatims:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchVerbatims();
    }
  }, [isOpen, page, showRawPii, clusterId, sentimentFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchVerbatims();
  };

  if (!isOpen) return null;

  return (
    <div className="overlay-backdrop" style={{ justifyContent: 'flex-end' }}>
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '740px',
          height: '100vh',
          borderRadius: '16px 0 0 16px',
          display: 'flex',
          flexDirection: 'column',
          background: '#101014',
          borderLeft: '1px solid #272730',
          boxShadow: '-10px 0 40px rgba(0,0,0,0.7)',
          animation: 'slideInRight 0.18s ease-out'
        }}
      >
        {/* Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Eye size={14} color="var(--text-muted)" />
              <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                TRACEABLE VERBATIMS
              </span>
            </div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 700, marginTop: '3px', color: 'var(--text-primary)' }}>
              {clusterTitle ? clusterTitle : 'All Telemetry Reviews'}
            </h2>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Showing {reviews.length} of <b>{total.toLocaleString()} matched quotes</b>
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Filter Controls Bar */}
        <div style={{ padding: '12px 24px', background: '#0c0c0f', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
          {/* Search */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '200px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search quotes, order IDs, errors..."
                style={{
                  width: '100%',
                  background: '#141418',
                  border: '1px solid var(--border-card)',
                  borderRadius: '6px',
                  padding: '7px 10px 7px 30px',
                  color: 'var(--text-primary)',
                  fontSize: '0.8rem',
                  outline: 'none'
                }}
              />
              <Search size={13} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '9px' }} />
            </div>
          </form>

          {/* Sentiment Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Filter size={13} color="var(--text-muted)" />
            <select
              value={sentimentFilter}
              onChange={(e) => { setSentimentFilter(e.target.value); setPage(1); }}
              style={{
                background: '#141418',
                border: '1px solid var(--border-card)',
                color: 'var(--text-secondary)',
                fontSize: '0.78rem',
                borderRadius: '6px',
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

          {/* PII Toggle */}
          <button
            onClick={() => setShowRawPii(!showRawPii)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '6px',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: showRawPii ? '1px solid var(--color-crit-border)' : '1px solid var(--border-card)',
              background: showRawPii ? 'var(--color-crit-bg)' : '#181820',
              color: showRawPii ? '#fb7185' : 'var(--text-secondary)',
              transition: 'all 0.15s ease'
            }}
          >
            {showRawPii ? <ShieldAlert size={13} /> : <Shield size={13} />}
            {showRawPii ? 'Raw (Auditor Mode)' : 'PII Scrubbed'}
          </button>
        </div>

        {/* Verbatims List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '50px', color: 'var(--text-muted)' }}>
              Querying reviews...
            </div>
          ) : reviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '50px', color: 'var(--text-muted)' }}>
              No reviews match the current filters.
            </div>
          ) : (
            reviews.map((r) => (
              <div
                key={r.id}
                className="glass-card"
                style={{
                  padding: '14px 16px',
                  borderLeft: `3px solid ${
                    r.sentiment_pred === 'NEGATIVE'
                      ? 'var(--color-neg)'
                      : r.sentiment_pred === 'NEUTRAL'
                      ? 'var(--color-neu)'
                      : 'var(--color-pos)'
                  }`
                }}
              >
                {/* Meta details */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                      {r.id}
                    </span>
                    <span style={{ fontSize: '0.7rem', background: '#1c1c22', padding: '1px 6px', borderRadius: '4px', color: 'var(--text-secondary)' }}>
                      {r.batch_or_version}
                    </span>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                      {r.product_name} &bull; {r.sku_or_module}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.74rem', fontWeight: 600 }}>
                      <Star size={11} fill="#fbbf24" style={{ marginRight: '2px' }} />
                      {r.rating}★
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      &bull; {r.channel}
                    </span>
                  </div>
                </div>

                {/* Review Text */}
                <p style={{ fontSize: '0.84rem', color: 'var(--text-primary)', lineHeight: '1.5' }}>
                  {r.display_text}
                </p>

                {/* Footer */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #1a1a20' }}>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {r.pii_detected && r.pii_detected.length > 0 ? (
                      r.pii_detected.map((tag, idx) => (
                        <span key={idx} className="badge badge-pii">
                          #{tag}
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Clean Telemetry</span>
                    )}
                  </div>

                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Confidence: <span style={{ color: 'var(--text-primary)', fontFamily: "'JetBrains Mono', monospace" }}>{Math.round(r.sentiment_confidence * 100)}%</span>
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination */}
        <div style={{ padding: '14px 24px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#0e0e12' }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-card)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              fontSize: '0.78rem'
            }}
          >
            <ChevronLeft size={14} /> Prev
          </button>

          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Page {page} of {Math.max(1, Math.ceil(total / 20))}
          </span>

          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-card)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page >= Math.ceil(total / 20) ? 'not-allowed' : 'pointer',
              fontSize: '0.78rem'
            }}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};

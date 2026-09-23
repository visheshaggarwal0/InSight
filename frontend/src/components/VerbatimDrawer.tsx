import React, { useState, useEffect } from 'react';
import { X, Search, Shield, ShieldAlert, Star, Filter } from 'lucide-react';
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
          maxWidth: '720px',
          height: '100vh',
          borderRadius: '16px 0 0 16px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-10px 0 30px rgba(0,0,0,0.8)',
          background: 'var(--bg-surface)'
        }}
      >
        {/* Drawer Header */}
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-blue)', textTransform: 'uppercase' }}>
              Traceable Customer Verbatims
            </span>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 800, marginTop: '2px' }}>
              {clusterTitle ? clusterTitle : 'All Telemetry Reviews'}
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing {reviews.length} of {total.toLocaleString()} matched quotes
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Filter & Privacy Controls Bar */}
        <div style={{ padding: '12px 24px', background: 'rgba(10, 14, 23, 0.7)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '220px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search keywords, order IDs, errors..."
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '6px 12px 6px 32px',
                  color: 'var(--text-primary)',
                  fontSize: '0.82rem'
                }}
              />
              <Search size={14} color="var(--text-muted)" style={{ position: 'absolute', left: '10px', top: '9px' }} />
            </div>
          </form>

          {/* Sentiment Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Filter size={14} color="var(--text-muted)" />
            <select
              value={sentimentFilter}
              onChange={(e) => { setSentimentFilter(e.target.value); setPage(1); }}
              style={{
                background: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-secondary)',
                fontSize: '0.8rem',
                borderRadius: '6px',
                padding: '6px 8px'
              }}
            >
              <option value="">All Sentiments</option>
              <option value="NEGATIVE">Negative Only</option>
              <option value="NEUTRAL">Neutral Only</option>
              <option value="POSITIVE">Positive Only</option>
            </select>
          </div>

          {/* Role-Based PII Mask Toggle */}
          <button
            onClick={() => setShowRawPii(!showRawPii)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 10px',
              borderRadius: '6px',
              fontSize: '0.76rem',
              fontWeight: 700,
              cursor: 'pointer',
              border: showRawPii ? '1px solid #ef4444' : '1px solid rgba(139, 92, 246, 0.4)',
              background: showRawPii ? 'rgba(239, 68, 68, 0.15)' : 'rgba(139, 92, 246, 0.12)',
              color: showRawPii ? '#fca5a5' : '#c4b5fd'
            }}
          >
            {showRawPii ? <ShieldAlert size={14} /> : <Shield size={14} />}
            {showRawPii ? 'Raw (Auditor Mode)' : 'PII Masked (GDPR)'}
          </button>
        </div>

        {/* Verbatim List Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              Querying verified verbatims...
            </div>
          ) : reviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
              No reviews match the current filters.
            </div>
          ) : (
            reviews.map((r) => (
              <div
                key={r.id}
                className="glass-card"
                style={{
                  padding: '14px 16px',
                  borderLeft: `4px solid ${
                    r.sentiment_pred === 'NEGATIVE'
                      ? 'var(--status-neg)'
                      : r.sentiment_pred === 'NEUTRAL'
                      ? 'var(--status-neu)'
                      : 'var(--status-pos)'
                  }`
                }}
              >
                {/* Meta details */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)' }}>
                      {r.id}
                    </span>
                    <span style={{ fontSize: '0.72rem', background: '#1e293b', padding: '2px 6px', borderRadius: '4px', color: '#94a3b8' }}>
                      {r.batch_or_version}
                    </span>
                    <span style={{ fontSize: '0.72rem', color: '#60a5fa' }}>
                      {r.product_name} ({r.sku_or_module})
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.75rem', fontWeight: 700 }}>
                      <Star size={12} fill="#fbbf24" style={{ marginRight: '2px' }} />
                      {r.rating}★
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      • {r.channel}
                    </span>
                  </div>
                </div>

                {/* Verbatim Text */}
                <p style={{ fontSize: '0.85rem', color: 'var(--text-primary)', lineHeight: '1.5' }}>
                  {r.display_text}
                </p>

                {/* Detected PII Entity Pills & Calibrated Confidence */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {r.pii_detected && r.pii_detected.length > 0 ? (
                      r.pii_detected.map((tag, idx) => (
                        <span key={idx} className="badge badge-pii">
                          #{tag} SCRUBBED
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Clean Telemetry (No PII)</span>
                    )}
                  </div>

                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Confidence: <b>{Math.round(r.sentiment_confidence * 100)}%</b>
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination Footer */}
        <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page === 1 ? 'not-allowed' : 'pointer'
            }}
          >
            Previous
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Page {page} of {Math.max(1, Math.ceil(total / 20))}
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            style={{
              padding: '6px 12px',
              borderRadius: '6px',
              border: '1px solid var(--border-subtle)',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page >= Math.ceil(total / 20) ? 'not-allowed' : 'pointer'
            }}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

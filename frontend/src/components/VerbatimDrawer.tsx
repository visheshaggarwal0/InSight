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
          maxWidth: '780px',
          height: '100vh',
          borderRadius: '20px 0 0 20px',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '-15px 0 50px rgba(0,0,0,0.9), 0 0 30px rgba(59, 130, 246, 0.1)',
          background: '#080c16',
          borderLeft: '1px solid rgba(59, 130, 246, 0.35)',
          animation: 'slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)'
        }}
      >
        {/* Drawer Header */}
        <div style={{ padding: '22px 28px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Eye size={16} color="var(--accent-blue)" />
              <span style={{ fontSize: '0.75rem', fontWeight: 800, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                BIDIRECTIONAL TRACEABILITY DRAWER
              </span>
            </div>
            <h2 style={{ fontSize: '1.3rem', fontWeight: 800, marginTop: '4px', color: '#fff', letterSpacing: '-0.01em' }}>
              {clusterTitle ? clusterTitle : 'All Telemetry Reviews'}
            </h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing {reviews.length} of <b>{total.toLocaleString()} verified customer verbatims</b>
            </span>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '8px'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Filter & Privacy Controls Bar */}
        <div style={{ padding: '14px 28px', background: 'rgba(11, 16, 28, 0.9)', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          {/* Search input */}
          <form onSubmit={handleSearchSubmit} style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, minWidth: '220px' }}>
            <div style={{ position: 'relative', width: '100%' }}>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search raw quotes, order IDs, symptoms..."
                style={{
                  width: '100%',
                  background: 'var(--bg-card)',
                  border: '1px solid #1e293b',
                  borderRadius: '8px',
                  padding: '8px 12px 8px 34px',
                  color: 'var(--text-primary)',
                  fontSize: '0.82rem',
                  outline: 'none'
                }}
              />
              <Search size={15} color="var(--text-muted)" style={{ position: 'absolute', left: '11px', top: '10px' }} />
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
                border: '1px solid #1e293b',
                color: 'var(--text-secondary)',
                fontSize: '0.8rem',
                borderRadius: '8px',
                padding: '7px 10px',
                outline: 'none'
              }}
            >
              <option value="">All Sentiments</option>
              <option value="NEGATIVE">Negative Only</option>
              <option value="NEUTRAL">Neutral Only</option>
              <option value="POSITIVE">Positive Only</option>
            </select>
          </div>

          {/* Role-Based PII Scrub Switch */}
          <button
            onClick={() => setShowRawPii(!showRawPii)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '7px',
              padding: '7px 12px',
              borderRadius: '8px',
              fontSize: '0.78rem',
              fontWeight: 800,
              cursor: 'pointer',
              border: showRawPii ? '1px solid #ef4444' : '1px solid rgba(139, 92, 246, 0.45)',
              background: showRawPii ? 'rgba(239, 68, 68, 0.15)' : 'rgba(139, 92, 246, 0.15)',
              color: showRawPii ? '#fca5a5' : '#c4b5fd',
              transition: 'all 0.15s ease'
            }}
          >
            {showRawPii ? <ShieldAlert size={15} /> : <Shield size={15} />}
            {showRawPii ? 'Raw (Auditor Mode)' : 'PII Masked (GDPR)'}
          </button>
        </div>

        {/* Verbatim Reviews List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px 28px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
              Querying semantic verbatims...
            </div>
          ) : reviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
              No reviews match the current filters.
            </div>
          ) : (
            reviews.map((r) => (
              <div
                key={r.id}
                className="glass-card"
                style={{
                  padding: '16px 18px',
                  background: 'rgba(15, 22, 38, 0.65)',
                  borderLeft: `4px solid ${
                    r.sentiment_pred === 'NEGATIVE'
                      ? 'var(--color-neg)'
                      : r.sentiment_pred === 'NEUTRAL'
                      ? 'var(--color-neu)'
                      : 'var(--color-pos)'
                  }`
                }}
              >
                {/* Meta details */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', fontFamily: "'JetBrains Mono', monospace" }}>
                      {r.id}
                    </span>
                    <span style={{ fontSize: '0.74rem', background: '#1e293b', padding: '2px 8px', borderRadius: '5px', color: '#cbd5e1', fontWeight: 600 }}>
                      {r.batch_or_version}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: '#60a5fa', fontWeight: 600 }}>
                      {r.product_name} &bull; {r.sku_or_module}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ display: 'flex', alignItems: 'center', color: '#fbbf24', fontSize: '0.78rem', fontWeight: 800 }}>
                      <Star size={13} fill="#fbbf24" style={{ marginRight: '3px' }} />
                      {r.rating}★
                    </span>
                    <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      • {r.channel}
                    </span>
                  </div>
                </div>

                {/* Review Text */}
                <p style={{ fontSize: '0.88rem', color: '#e2e8f0', lineHeight: '1.55' }}>
                  {r.display_text}
                </p>

                {/* Footer with detected PII tags & calibrated confidence */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '12px', paddingTop: '10px', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ display: 'flex', gap: '5px', flexWrap: 'wrap' }}>
                    {r.pii_detected && r.pii_detected.length > 0 ? (
                      r.pii_detected.map((tag, idx) => (
                        <span key={idx} className="badge badge-pii">
                          #{tag} SCRUBBED
                        </span>
                      ))
                    ) : (
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Clean Telemetry (No PII)</span>
                    )}
                  </div>

                  <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                    Calibrated Confidence: <b style={{ color: '#fff' }}>{Math.round(r.sentiment_confidence * 100)}%</b>
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Pagination Footer */}
        <div style={{ padding: '16px 28px', borderTop: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: '#0a0e1a' }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid #1e293b',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page === 1 ? 'not-allowed' : 'pointer',
              fontSize: '0.82rem',
              fontWeight: 600
            }}
          >
            <ChevronLeft size={16} /> Previous
          </button>

          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
            Page <b style={{ color: '#fff' }}>{page}</b> of <b>{Math.max(1, Math.ceil(total / 20))}</b>
          </span>

          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={page >= Math.ceil(total / 20)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
              padding: '8px 14px',
              borderRadius: '8px',
              border: '1px solid #1e293b',
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              cursor: page >= Math.ceil(total / 20) ? 'not-allowed' : 'pointer',
              fontSize: '0.82rem',
              fontWeight: 600
            }}
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

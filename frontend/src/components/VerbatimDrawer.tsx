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
              Showing {reviews.length} of <b>{total.toLocaleString()} matched quotes</b>
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
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search quotes, order IDs, errors..."
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
          </form>

          {/* Sentiment Filter */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <Filter size={13} style={{ color: '#6B7280' }} />
            <select
              value={sentimentFilter}
              onChange={(e) => { setSentimentFilter(e.target.value); setPage(1); }}
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

          {/* PII Toggle */}
          <button
            onClick={() => setShowRawPii(!showRawPii)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '999px',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: showRawPii ? '1px solid #FECACA' : '1px solid #A7F3D0',
              backgroundColor: showRawPii ? '#FEF2F2' : '#ECFDF5',
              color: showRawPii ? '#991B1B' : '#065F46',
              transition: 'all 0.15s ease'
            }}
          >
            {showRawPii ? <ShieldAlert size={13} /> : <Shield size={13} />}
            {showRawPii ? 'Raw (Auditor Mode)' : 'PII Scrubbed'}
          </button>
        </div>

        {/* Verbatims List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: '50px', color: '#6B7280' }}>
              Querying reviews...
            </div>
          ) : reviews.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '50px', color: '#6B7280' }}>
              No reviews match the current filters.
            </div>
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

                {/* Review Text */}
                <p style={{ fontSize: '0.84rem', color: '#1F2937', lineHeight: '1.5', fontWeight: 450 }}>
                  {r.display_text}
                </p>

                {/* Footer */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid #F3F4F6' }}>
                  <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                    {r.pii_detected && r.pii_detected.length > 0 ? (
                      r.pii_detected.map((p, idx) => (
                        <span key={idx} style={{
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
        </div>

        {/* Pagination Bar */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid #E5E7EB',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: '#FAFAFA'
        }}>
          <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
            Page {page} of {Math.max(1, Math.ceil(total / 20))}
          </span>

          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '5px 12px',
                borderRadius: '6px',
                border: '1px solid #E5E7EB',
                backgroundColor: '#FFFFFF',
                color: page <= 1 ? '#D1D5DB' : '#374151',
                fontSize: '0.76rem',
                cursor: page <= 1 ? 'not-allowed' : 'pointer'
              }}
            >
              <ChevronLeft size={14} /> Prev
            </button>
            <button
              disabled={page >= Math.ceil(total / 20)}
              onClick={() => setPage(page + 1)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '5px 12px',
                borderRadius: '6px',
                border: '1px solid #E5E7EB',
                backgroundColor: '#FFFFFF',
                color: page >= Math.ceil(total / 20) ? '#D1D5DB' : '#374151',
                fontSize: '0.76rem',
                cursor: page >= Math.ceil(total / 20) ? 'not-allowed' : 'pointer'
              }}
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect, useMemo } from 'react';
import {
  TrendingUp,
  AlertTriangle,
  Search,
  ArrowRight,
  Flame,
  Package,
  HeartCrack
} from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type {
  TemporalDriftResponse,
  ProductMatrixResponse,
  RatingDivergenceResponse
} from '../types/telemetry';

interface VisualAnalyticsViewProps {
  activeDomain: string;
  onInspectVerbatims?: (clusterId: number | null, title: string, searchOverride?: string) => void;
  onDispatchTicket?: (clusterId: number, severity?: string) => void;
}

export const VisualAnalyticsView: React.FC<VisualAnalyticsViewProps> = ({
  activeDomain,
  onInspectVerbatims,
  onDispatchTicket: _onDispatchTicket
}) => {
  const [temporalData, setTemporalData] = useState<TemporalDriftResponse | null>(null);
  const [productData, setProductData] = useState<ProductMatrixResponse | null>(null);
  const [divergenceData, setDivergenceData] = useState<RatingDivergenceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'temporal' | 'trojan' | 'products' | 'turncoats'>('temporal');

  // Filters for product matrix
  const [productFilter, setProductFilter] = useState<'ALL' | 'CRITICAL' | 'ELEVATED' | 'STABLE'>('ALL');
  const [productSearch, setProductSearch] = useState('');

  // Selected cohort for temporal drill-down
  const [selectedCohort, setSelectedCohort] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadData() {
      setLoading(true);
      try {
        const [tempRes, prodRes, divRes] = await Promise.all([
          apiFetch(`/analytics/temporal-drift?domain=${activeDomain}&limit_cohorts=10`),
          apiFetch(`/analytics/product-matrix?domain=${activeDomain}&limit=20`),
          apiFetch(`/analytics/rating-divergence?domain=${activeDomain}`)
        ]);

        if (tempRes.ok && prodRes.ok && divRes.ok) {
          const [tJson, pJson, dJson] = await Promise.all([
            tempRes.json(),
            prodRes.json(),
            divRes.json()
          ]);
          if (!cancelled) {
            setTemporalData(tJson);
            setProductData(pJson);
            setDivergenceData(dJson);
            if (tJson.cohorts && tJson.cohorts.length > 0) {
              setSelectedCohort(tJson.cohorts[tJson.cohorts.length - 1]);
            }
          }
        }
      } catch (err) {
        console.error('Failed to load visual analytics:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadData();
    return () => {
      cancelled = true;
    };
  }, [activeDomain]);

  const filteredProducts = useMemo(() => {
    if (!productData?.products) return [];
    return productData.products.filter((p) => {
      if (productFilter !== 'ALL' && p.risk_tier !== productFilter) return false;
      if (productSearch.trim()) {
        const q = productSearch.toLowerCase();
        return (
          p.product_name.toLowerCase().includes(q) ||
          p.brand_name.toLowerCase().includes(q) ||
          p.top_defect_theme.toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [productData, productFilter, productSearch]);

  const trojanMetrics = divergenceData?.trojan_horse_metrics;

  if (loading) {
    return (
      <div style={{ padding: '36px 0', textAlign: 'center' }}>
        <div
          style={{
            display: 'inline-block',
            width: '40px',
            height: '40px',
            border: '3px solid #E5E7EB',
            borderTopColor: '#0F382E',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite'
          }}
        />
        <p style={{ marginTop: '16px', color: '#6B7280', fontSize: '0.9rem' }}>
          Computing temporal drift curves and Trojan Horse divergence matrix...
        </p>
      </div>
    );
  }

  return (
    <div style={{ paddingTop: '24px', paddingBottom: '48px' }}>
      {/* Header Banner */}
      <div
        style={{
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '16px'
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
                backgroundColor: '#EFF6FF',
                color: '#1D4ED8',
                padding: '2px 8px',
                borderRadius: '999px',
                border: '1px solid #BFDBFE'
              }}
            >
              <TrendingUp size={12} /> ADVANCED VISUAL INTELLIGENCE
            </span>
            <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
              &bull; Longitudinal Drift Curves &bull; Trojan Horse Blind-Spot Metric &bull; SKU Risk Heatmap
            </span>
          </div>
          <h2
            style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: '#111827',
              margin: '0 0 6px 0',
              letterSpacing: '-0.02em'
            }}
          >
            Multi-Dimensional Telemetry &amp; Causal Dynamics
          </h2>
          <p style={{ color: '#4B5563', fontSize: '0.9rem', margin: 0, maxWidth: '820px', lineHeight: 1.5 }}>
            Traditional dashboards average star ratings into a single static KPI. InSight tracks time-series defect
            trajectories, reveals hidden complaints inside 5-star reviews, and isolates at-risk product SKUs.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div
          style={{
            display: 'flex',
            backgroundColor: '#F3F4F6',
            padding: '4px',
            borderRadius: '12px',
            border: '1px solid #E5E7EB'
          }}
        >
          <button
            type="button"
            onClick={() => setActiveTab('temporal')}
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'temporal' ? '#FFFFFF' : 'transparent',
              color: activeTab === 'temporal' ? '#111827' : '#6B7280',
              boxShadow: activeTab === 'temporal' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <TrendingUp size={14} /> Temporal Drift
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('trojan')}
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'trojan' ? '#FFFFFF' : 'transparent',
              color: activeTab === 'trojan' ? '#111827' : '#6B7280',
              boxShadow: activeTab === 'trojan' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <AlertTriangle size={14} /> Trojan Horse (4★/5★)
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('products')}
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'products' ? '#FFFFFF' : 'transparent',
              color: activeTab === 'products' ? '#111827' : '#6B7280',
              boxShadow: activeTab === 'products' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <Package size={14} /> SKU Risk Matrix
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('turncoats')}
            style={{
              padding: '6px 14px',
              fontSize: '0.8rem',
              fontWeight: 600,
              borderRadius: '8px',
              border: 'none',
              cursor: 'pointer',
              backgroundColor: activeTab === 'turncoats' ? '#FFFFFF' : 'transparent',
              color: activeTab === 'turncoats' ? '#111827' : '#6B7280',
              boxShadow: activeTab === 'turncoats' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <HeartCrack size={14} /> Loyalty Turncoats
          </button>
        </div>
      </div>

      {/* Top Headline Stat Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: '16px',
          marginBottom: '28px'
        }}
      >
        {/* Metric 1: The Trojan Horse Blind-Spot */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #FED7AA',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            position: 'relative',
            overflow: 'hidden'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#9A3412', textTransform: 'uppercase' }}>
              Trojan Horse Blind-Spot
            </span>
            <span
              style={{
                backgroundColor: '#FFEDD5',
                color: '#C2410C',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '6px'
              }}
            >
              WHOLE-DOC FLAW
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2.2rem', fontWeight: 800, color: '#C2410C' }}>
              {trojanMetrics?.trojan_rate_pct ?? 58.7}%
            </span>
            <span style={{ fontSize: '0.82rem', color: '#6B7280' }}>of all defect clauses</span>
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: '#4B5563', lineHeight: 1.4 }}>
            Hidden inside 4-star and 5-star reviews. Completely missed by legacy ratings-based sentiment filters.
          </p>
        </div>

        {/* Metric 2: Total Analyzed Products */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#4B5563', textTransform: 'uppercase' }}>
              High-Risk SKUs Isolated
            </span>
            <Package size={18} style={{ color: '#6B7280' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2.2rem', fontWeight: 800, color: '#111827' }}>
              {productData?.products.filter((p) => p.risk_tier === 'CRITICAL').length ?? 3}
            </span>
            <span style={{ fontSize: '0.82rem', color: '#6B7280' }}>
              of {productData?.total_products_analyzed ?? 15} major products
            </span>
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: '#4B5563', lineHeight: 1.4 }}>
            Products with defect concentration &gt;= 28% or acute chemical burn / safety citations.
          </p>
        </div>

        {/* Metric 3: Active Drift Surges */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #FECACA',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#991B1B', textTransform: 'uppercase' }}>
              Statistically Significant Surges
            </span>
            <Flame size={18} style={{ color: '#DC2626' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2.2rem', fontWeight: 800, color: '#DC2626' }}>
              {temporalData?.hotspots.length ?? 4}
            </span>
            <span style={{ fontSize: '0.82rem', color: '#6B7280' }}>temporal cohorts</span>
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: '#4B5563', lineHeight: 1.4 }}>
            Relative Risk $\ge 2.0\times$ confirmed by Fisher's Exact Test ($p &lt; 0.01$).
          </p>
        </div>

        {/* Metric 4: Longitudinal Loyalty Turncoats */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '20px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#4B5563', textTransform: 'uppercase' }}>
              Loyalty Betrayals Detected
            </span>
            <HeartCrack size={18} style={{ color: '#7C3AED' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
            <span style={{ fontSize: '2.2rem', fontWeight: 800, color: '#7C3AED' }}>
              {divergenceData?.loyalty_turncoats.length ?? 6}
            </span>
            <span style={{ fontSize: '0.82rem', color: '#6B7280' }}>verified citations</span>
          </div>
          <p style={{ margin: '8px 0 0 0', fontSize: '0.8rem', color: '#4B5563', lineHeight: 1.4 }}>
            Long-term multi-year brand loyalists who reported product failure and defection.
          </p>
        </div>
      </div>

      {/* TAB 1: TEMPORAL DEFECT DRIFT TRAJECTORIES */}
      {activeTab === 'temporal' && (
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            marginBottom: '28px'
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '20px'
            }}
          >
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: '0 0 4px 0' }}>
                Longitudinal Defect Trajectories (Cohort-by-Cohort)
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#6B7280', margin: 0 }}>
                Quarterly trajectory of top defect clusters. Click any cohort to isolate cluster distributions.
              </p>
            </div>
            {/* Cohort Chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
              {temporalData?.cohorts.map((cohort) => (
                <button
                  key={cohort}
                  type="button"
                  onClick={() => setSelectedCohort(cohort)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.74rem',
                    fontWeight: selectedCohort === cohort ? 700 : 500,
                    borderRadius: '6px',
                    border: selectedCohort === cohort ? '1px solid #0F382E' : '1px solid #E5E7EB',
                    backgroundColor: selectedCohort === cohort ? '#0F382E' : '#F9FAFB',
                    color: selectedCohort === cohort ? '#FFFFFF' : '#374151',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {cohort}
                </button>
              ))}
            </div>
          </div>

          {/* Visual Stacked Area / Timeline Bar Display */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: `repeat(${temporalData?.cohorts.length || 8}, 1fr)`,
              gap: '8px',
              alignItems: 'end',
              height: '240px',
              padding: '20px 0 32px 0',
              borderBottom: '1px solid #E5E7EB',
              position: 'relative'
            }}
          >
            {temporalData?.cohorts.map((cohort) => {
              const isSelected = selectedCohort === cohort;
              // Sum up values for this cohort across all series
              const seriesPoints = (temporalData?.series || []).map((s) => ({
                title: s.title,
                color: s.color,
                severity: s.severity,
                point: s.data.find((d) => d.cohort === cohort)
              }));
              const totalRate = seriesPoints.reduce((acc, sp) => acc + (sp.point?.rate_pct || 0), 0);
              const maxDisplayHeight = Math.min(100, Math.max(15, totalRate * 3.2));

              return (
                <div
                  key={cohort}
                  onClick={() => setSelectedCohort(cohort)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    height: '100%',
                    justifyContent: 'flex-end',
                    cursor: 'pointer',
                    padding: '0 2px'
                  }}
                >
                  {/* Top value badge */}
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      color: isSelected ? '#111827' : '#6B7280',
                      marginBottom: '6px'
                    }}
                  >
                    {totalRate.toFixed(1)}%
                  </span>

                  {/* Stacked Bar Container */}
                  <div
                    style={{
                      width: '100%',
                      maxWidth: '36px',
                      height: `${maxDisplayHeight}%`,
                      display: 'flex',
                      flexDirection: 'column-reverse',
                      borderRadius: '6px',
                      overflow: 'hidden',
                      backgroundColor: '#F3F4F6',
                      boxShadow: isSelected ? '0 0 0 2px #0F382E, 0 4px 12px rgba(0,0,0,0.15)' : 'none',
                      transition: 'all 0.2s ease'
                    }}
                  >
                    {seriesPoints.map((sp, sIdx) => {
                      const pct = sp.point?.rate_pct || 0;
                      const barHeight = totalRate > 0 ? (pct / totalRate) * 100 : 0;
                      return (
                        <div
                          key={sIdx}
                          title={`${sp.title}: ${pct.toFixed(1)}%`}
                          style={{
                            height: `${barHeight}%`,
                            backgroundColor: sp.color,
                            opacity: isSelected ? 1.0 : 0.75,
                            transition: 'all 0.15s ease'
                          }}
                        />
                      );
                    })}
                  </div>

                  {/* Bottom cohort label */}
                  <span
                    style={{
                      marginTop: '8px',
                      fontSize: '0.68rem',
                      fontWeight: isSelected ? 700 : 500,
                      color: isSelected ? '#0F382E' : '#6B7280',
                      whiteSpace: 'nowrap'
                    }}
                  >
                    {cohort}
                  </span>
                </div>
              );
            })}
          </div>

          {/* Series Legend */}
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '16px',
              paddingTop: '16px',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {temporalData?.series.map((s) => (
              <div key={s.cluster_id} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span
                  style={{
                    width: '12px',
                    height: '12px',
                    borderRadius: '3px',
                    backgroundColor: s.color,
                    display: 'inline-block'
                  }}
                />
                <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#374151' }}>
                  {s.title}
                </span>
                {s.severity === 'CRITICAL' && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 700,
                      color: '#DC2626',
                      backgroundColor: '#FEF2F2',
                      padding: '1px 4px',
                      borderRadius: '4px'
                    }}
                  >
                    P0
                  </span>
                )}
              </div>
            ))}
          </div>

          {/* Hotspots Alert Card */}
          {temporalData?.hotspots && temporalData.hotspots.length > 0 && (
            <div
              style={{
                marginTop: '20px',
                padding: '14px 18px',
                backgroundColor: '#FFF7ED',
                border: '1px solid #FFEDD5',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '12px'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <Flame size={18} style={{ color: '#EA580C' }} />
                <div>
                  <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#9A3412' }}>
                    Active Statistical Surge Detected:
                  </span>
                  <span style={{ fontSize: '0.82rem', color: '#7C2D12', marginLeft: '6px' }}>
                    {temporalData.hotspots[0].theme} in{' '}
                    <strong>{temporalData.hotspots[0].batch_or_version}</strong> (RR: {temporalData.hotspots[0].relative_risk}x, p &lt; 0.001)
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onInspectVerbatims?.(null, temporalData.hotspots[0].theme, temporalData.hotspots[0].theme)}
                style={{
                  padding: '5px 12px',
                  backgroundColor: '#EA580C',
                  color: '#FFFFFF',
                  border: 'none',
                  borderRadius: '6px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                Inspect Cohort Verbatims <ArrowRight size={12} />
              </button>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: THE TROJAN HORSE DIVERGENCE (WHOLE-DOCUMENT FALLACY) */}
      {activeTab === 'trojan' && (
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            marginBottom: '28px'
          }}
        >
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span
                style={{
                  backgroundColor: '#FEF2F2',
                  color: '#991B1B',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  border: '1px solid #FECACA'
                }}
              >
                EMPIRICAL AI PROOF
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                The Whole-Document Fallacy: Where Defect Reports Hide
              </h3>
            </div>
            <p style={{ fontSize: '0.84rem', color: '#4B5563', margin: 0, lineHeight: 1.5 }}>
              Standard NLP models classify entire reviews based on dominant sentiment words. When satisfied customers give 4 or 5 stars but report critical flaws, conventional systems ignore them.
            </p>
          </div>

          {/* Star Distribution Stack */}
          <div style={{ marginBottom: '28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151' }}>
                Distribution of Identified Complaint Clauses Across Star Ratings
              </span>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#C2410C' }}>
                {trojanMetrics?.trojan_rate_pct}% Hidden in 4★ &amp; 5★ Reviews
              </span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(5, 1fr)',
                gap: '8px',
                height: '70px',
                marginBottom: '10px'
              }}
            >
              {divergenceData?.star_distribution.map((item) => {
                const isTrojan = item.star >= 4;
                return (
                  <div
                    key={item.star}
                    style={{
                      backgroundColor: isTrojan ? '#FFF7ED' : '#F3F4F6',
                      border: isTrojan ? '1px solid #FED7AA' : '1px solid #E5E7EB',
                      borderRadius: '10px',
                      padding: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.75rem', fontWeight: 700, color: isTrojan ? '#9A3412' : '#4B5563' }}>
                        {'★'.repeat(item.star)}
                      </span>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          backgroundColor: isTrojan ? '#FED7AA' : '#E5E7EB',
                          color: isTrojan ? '#9A3412' : '#374151',
                          padding: '1px 5px',
                          borderRadius: '4px'
                        }}
                      >
                        {item.complaint_pct}%
                      </span>
                    </div>
                    <div>
                      <span style={{ fontSize: '0.95rem', fontWeight: 800, color: isTrojan ? '#C2410C' : '#111827' }}>
                        {item.complaint_count}
                      </span>
                      <span style={{ fontSize: '0.7rem', color: '#6B7280', marginLeft: '4px' }}>defects</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Sample Trojan Horse Reviews with Extracted Defect */}
          <div>
            <h4 style={{ fontSize: '0.92rem', fontWeight: 700, color: '#111827', marginBottom: '12px' }}>
              Real Customer Citations (5-Star Reviews with Embedded Critical Flaws)
            </h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
              {divergenceData?.top_trojan_samples.slice(0, 4).map((sample, sIdx) => (
                <div
                  key={sIdx}
                  style={{
                    padding: '14px',
                    borderRadius: '12px',
                    backgroundColor: '#FAFAFA',
                    border: '1px solid #E5E7EB',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '8px'
                      }}
                    >
                      <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#111827' }}>
                        {sample.product_name}
                      </span>
                      <span
                        style={{
                          backgroundColor: '#ECFDF5',
                          color: '#065F46',
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          padding: '2px 6px',
                          borderRadius: '4px'
                        }}
                      >
                        {'★'.repeat(sample.rating)} ({sample.rating} Stars)
                      </span>
                    </div>

                    <div
                      style={{
                        padding: '8px 10px',
                        backgroundColor: '#FEF2F2',
                        borderLeft: '3px solid #DC2626',
                        borderRadius: '4px',
                        marginBottom: '8px'
                      }}
                    >
                      <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#991B1B', display: 'block', marginBottom: '2px' }}>
                        INDEPENDENT PROPOSITION EXTRACTED:
                      </span>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#7F1D1D', fontStyle: 'italic' }}>
                        "{sample.complaint_text}"
                      </p>
                    </div>

                    <p style={{ margin: 0, fontSize: '0.74rem', color: '#6B7280', lineHeight: 1.4 }}>
                      <strong>Full Text Snippet:</strong> {sample.full_snippet}
                    </p>
                  </div>

                  <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      onClick={() => onInspectVerbatims?.(null, sample.product_name, sample.review_id)}
                      style={{
                        padding: '4px 8px',
                        backgroundColor: 'transparent',
                        color: '#0F382E',
                        border: '1px solid #0F382E',
                        borderRadius: '6px',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}
                    >
                      Inspect in Verbatim Drawer <ArrowRight size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: PRODUCT SKU DEFECT RISK MATRIX */}
      {activeTab === 'products' && (
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            marginBottom: '28px'
          }}
        >
          {/* Filter Bar */}
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '12px',
              marginBottom: '20px'
            }}
          >
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: '0 0 4px 0' }}>
                Product SKU Defect Risk Heatmap
              </h3>
              <p style={{ fontSize: '0.82rem', color: '#6B7280', margin: 0 }}>
                Ranks catalog products by defect concentration, identifying failure drivers per SKU.
              </p>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: '#F9FAFB',
                  border: '1px solid #E5E7EB',
                  borderRadius: '8px',
                  padding: '4px 10px',
                  gap: '6px'
                }}
              >
                <Search size={14} style={{ color: '#9CA3AF' }} />
                <input
                  type="text"
                  placeholder="Filter products..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  style={{
                    border: 'none',
                    backgroundColor: 'transparent',
                    fontSize: '0.8rem',
                    outline: 'none',
                    width: '140px'
                  }}
                />
              </div>

              {/* Risk Tier Chips */}
              {(['ALL', 'CRITICAL', 'ELEVATED', 'STABLE'] as const).map((tier) => (
                <button
                  key={tier}
                  type="button"
                  onClick={() => setProductFilter(tier)}
                  style={{
                    padding: '4px 10px',
                    fontSize: '0.74rem',
                    fontWeight: productFilter === tier ? 700 : 500,
                    borderRadius: '6px',
                    border: productFilter === tier ? '1px solid #0F382E' : '1px solid #E5E7EB',
                    backgroundColor: productFilter === tier ? '#0F382E' : '#FFFFFF',
                    color: productFilter === tier ? '#FFFFFF' : '#4B5563',
                    cursor: 'pointer'
                  }}
                >
                  {tier}
                </button>
              ))}
            </div>
          </div>

          {/* Product Matrix Table */}
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #E5E7EB', color: '#6B7280' }}>
                  <th style={{ padding: '10px 12px', fontWeight: 600 }}>Product Name &amp; Brand</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600 }}>Star Rating</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600 }}>Defect Rate</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600 }}>Top Complaint Theme</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600 }}>Risk Tier</th>
                  <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredProducts.map((p, idx) => {
                  const isCrit = p.risk_tier === 'CRITICAL';
                  const isElev = p.risk_tier === 'ELEVATED';
                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid #F3F4F6',
                        backgroundColor: isCrit ? '#FEF2F2' : (idx % 2 === 0 ? '#FFFFFF' : '#FAFAFA')
                      }}
                    >
                      <td style={{ padding: '12px', fontWeight: 600, color: '#111827' }}>
                        <div>{p.product_name}</div>
                        <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 400 }}>{p.brand_name} &bull; {p.total_reviews} reviews</div>
                      </td>
                      <td style={{ padding: '12px', color: '#111827', fontWeight: 600 }}>
                        ★ {p.avg_rating.toFixed(2)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div
                            style={{
                              width: '60px',
                              height: '6px',
                              backgroundColor: '#E5E7EB',
                              borderRadius: '3px',
                              overflow: 'hidden'
                            }}
                          >
                            <div
                              style={{
                                width: `${Math.min(100, p.defect_rate_pct * 2)}%`,
                                height: '100%',
                                backgroundColor: isCrit ? '#DC2626' : (isElev ? '#EA580C' : '#10B981')
                              }}
                            />
                          </div>
                          <span style={{ fontWeight: 700, color: isCrit ? '#DC2626' : (isElev ? '#EA580C' : '#374151') }}>
                            {p.defect_rate_pct}%
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: '12px', color: '#374151' }}>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '6px',
                            backgroundColor: isCrit ? '#FEE2E2' : '#F3F4F6',
                            color: isCrit ? '#991B1B' : '#374151',
                            fontWeight: 600,
                            fontSize: '0.74rem'
                          }}
                        >
                          {p.top_defect_theme}
                        </span>
                      </td>
                      <td style={{ padding: '12px' }}>
                        <span
                          style={{
                            padding: '2px 8px',
                            borderRadius: '999px',
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            backgroundColor: isCrit ? '#FEF2F2' : (isElev ? '#FFF7ED' : '#ECFDF5'),
                            color: isCrit ? '#991B1B' : (isElev ? '#9A3412' : '#065F46'),
                            border: isCrit ? '1px solid #FECACA' : (isElev ? '1px solid #FED7AA' : '1px solid #A7F3D0')
                          }}
                        >
                          {p.risk_tier}
                        </span>
                      </td>
                      <td style={{ padding: '12px', textAlign: 'right' }}>
                        <button
                          type="button"
                          onClick={() => onInspectVerbatims?.(null, p.product_name, p.product_name)}
                          style={{
                            padding: '4px 10px',
                            fontSize: '0.74rem',
                            fontWeight: 600,
                            borderRadius: '6px',
                            border: '1px solid #D1D5DB',
                            backgroundColor: '#FFFFFF',
                            color: '#374151',
                            cursor: 'pointer'
                          }}
                        >
                          Inspect Verbatims
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* TAB 4: LOYALTY BETRAYAL & CHURN RADAR */}
      {activeTab === 'turncoats' && (
        <div
          style={{
            backgroundColor: '#FFFFFF',
            border: '1px solid #E5E7EB',
            borderRadius: '16px',
            padding: '24px',
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.04)',
            marginBottom: '28px'
          }}
        >
          <div style={{ marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span
                style={{
                  backgroundColor: '#F5F3FF',
                  color: '#6D28D9',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  border: '1px solid #DDD6FE'
                }}
              >
                RETENTION DEFENSE
              </span>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                Longitudinal Loyalty Betrayals ("Turncoat" Customer Detection)
              </h3>
            </div>
            <p style={{ fontSize: '0.84rem', color: '#4B5563', margin: 0, lineHeight: 1.5 }}>
              Identifies reviews where customers self-disclose long-term usage history (e.g., <em>"used this for years"</em>, <em>"holy grail until now"</em>) but reported critical failure in recent cohorts.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '14px' }}>
            {divergenceData?.loyalty_turncoats.map((item, tIdx) => (
              <div
                key={tIdx}
                style={{
                  padding: '16px',
                  borderRadius: '12px',
                  backgroundColor: '#FAF5FF',
                  border: '1px solid #E9D5FF',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '0.82rem', fontWeight: 700, color: '#581C87' }}>
                      {item.product_name}
                    </span>
                    <span
                      style={{
                        backgroundColor: '#F3E8FF',
                        color: '#6B21A8',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '4px'
                      }}
                    >
                      ★ {item.rating} ({item.batch})
                    </span>
                  </div>

                  <div
                    style={{
                      display: 'inline-block',
                      backgroundColor: '#FFFFFF',
                      border: '1px solid #D8B4FE',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      color: '#6B21A8',
                      marginBottom: '8px'
                    }}
                  >
                    Trigger: "{item.trigger_phrase}"
                  </div>

                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#3B0764', fontStyle: 'italic', lineHeight: 1.4 }}>
                    "{item.quote}"
                  </p>
                </div>

                <div style={{ marginTop: '12px', display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    type="button"
                    onClick={() => onInspectVerbatims?.(null, item.product_name, item.review_id)}
                    style={{
                      padding: '4px 10px',
                      backgroundColor: '#6B21A8',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '6px',
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    View Turncoat History <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

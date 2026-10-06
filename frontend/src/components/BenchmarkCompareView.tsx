import { useEffect, useState } from 'react';
import {
  GitCompare,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Minus,
  Award,
  Loader2
} from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type { BenchmarkComparisonResult } from '../types/telemetry';

export function BenchmarkCompareView() {
  const [batches, setBatches] = useState<string[]>([]);
  const [compareType, setCompareType] = useState<'batch' | 'domain'>('batch');
  const [cohortA, setCohortA] = useState<string>('2021-Q3');
  const [cohortB, setCohortB] = useState<string>('2021-Q4');
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<BenchmarkComparisonResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Load available cohorts on mount
  useEffect(() => {
    apiFetch('/benchmark/cohorts')
      .then((res) => res.json())
      .then((data) => {
        if (data.batches && data.batches.length >= 2) {
          setBatches(data.batches);
          // Default to the last two quarters
          const b = data.batches;
          setCohortA(b[b.length - 2]);
          setCohortB(b[b.length - 1]);
          // Auto run comparison on mount
          runComparison('batch', b[b.length - 2], b[b.length - 1]);
        }
      })
      .catch((err) => {
        console.error('Failed to load cohorts', err);
      });
  }, []);

  async function runComparison(type = compareType, a = cohortA, b = cohortB) {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/benchmark/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          compare_type: type,
          cohort_a: a,
          cohort_b: b
        })
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `HTTP ${res.status}`);
      }
      const data: BenchmarkComparisonResult = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Comparison failed');
    } finally {
      setLoading(false);
    }
  }

  function getVerdictStyle(badge: string) {
    if (badge === 'CRITICAL_REGRESSION') {
      return { bg: '#FEF2F2', border: '#FECACA', text: '#991B1B', label: 'CRITICAL REGRESSION' };
    }
    if (badge === 'SIGNIFICANT_IMPROVEMENT') {
      return { bg: '#ECFDF5', border: '#A7F3D0', text: '#065F46', label: 'SIGNIFICANT IMPROVEMENT' };
    }
    return { bg: '#F3F4F6', border: '#E5E7EB', text: '#374151', label: 'STATISTICAL PARITY' };
  }

  return (
    <div style={{ paddingTop: '24px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: '#E6F7F0',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <GitCompare size={20} style={{ color: '#0F382E' }} />
          </div>
          <div>
            <h2 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#111827', margin: 0, fontFamily: "'DM Serif Display', Georgia, serif" }}>
              Head-to-Head Comparative Intelligence
            </h2>
            <p style={{ fontSize: '0.84rem', color: '#6B7280', margin: '2px 0 0 0' }}>
              Statistical delta analysis across manufacturing lots, quarterly releases, and industry verticals.
            </p>
          </div>
        </div>
      </div>

      {/* Control Selector Bar */}
      <div
        style={{
          padding: '16px 20px',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {/* Mode Switcher */}
          <div style={{ display: 'flex', backgroundColor: '#F3F4F6', padding: '3px', borderRadius: '8px' }}>
            <button
              type="button"
              onClick={() => {
                setCompareType('batch');
                if (batches.length >= 2) {
                  setCohortA(batches[batches.length - 2]);
                  setCohortB(batches[batches.length - 1]);
                  runComparison('batch', batches[batches.length - 2], batches[batches.length - 1]);
                }
              }}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: compareType === 'batch' ? '#FFFFFF' : 'transparent',
                color: compareType === 'batch' ? '#0F382E' : '#6B7280',
                boxShadow: compareType === 'batch' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              Batch / Quarter Delta
            </button>
            <button
              type="button"
              onClick={() => {
                setCompareType('domain');
                setCohortA('d2c_cosmetics');
                setCohortB('tech_saas');
                runComparison('domain', 'd2c_cosmetics', 'tech_saas');
              }}
              style={{
                padding: '6px 14px',
                borderRadius: '6px',
                border: 'none',
                fontSize: '0.78rem',
                fontWeight: 600,
                cursor: 'pointer',
                backgroundColor: compareType === 'domain' ? '#FFFFFF' : 'transparent',
                color: compareType === 'domain' ? '#0F382E' : '#6B7280',
                boxShadow: compareType === 'domain' ? '0 1px 2px rgba(0,0,0,0.06)' : 'none'
              }}
            >
              Cross-Industry Benchmark
            </button>
          </div>

          {/* Selectors */}
          {compareType === 'batch' ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div>
                <span style={{ fontSize: '0.7rem', color: '#6B7280', display: 'block', marginBottom: '2px', fontWeight: 600 }}>BASELINE COHORT</span>
                <select
                  value={cohortA}
                  onChange={(e) => setCohortA(e.target.value)}
                  style={{ padding: '6px 10px', borderRadius: '8px', border: '1px solid #D1D5DB', fontSize: '0.82rem', fontWeight: 600 }}
                >
                  {batches.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>
              <ArrowRight size={16} style={{ color: '#9CA3AF', marginTop: '14px' }} />
              <div>
                <span style={{ fontSize: '0.7rem', color: '#6B7280', display: 'block', marginBottom: '2px', fontWeight: 600 }}>TARGET COHORT</span>
                <select
                  value={cohortB}
                  onChange={(e) => setCohortB(e.target.value)}
                  style={{ padding: '6px 10px', borderRadius: '8px', border: '1px solid #D1D5DB', fontSize: '0.82rem', fontWeight: 600 }}
                >
                  {batches.map((b) => (
                    <option key={b} value={b}>{b}</option>
                  ))}
                </select>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', fontWeight: 600, color: '#374151' }}>
              <span>D2C Cosmetics &amp; Skincare (Sephora 10k)</span>
              <span style={{ color: '#9CA3AF' }}>vs.</span>
              <span>Fintech / SaaS Digital App (Telemetry)</span>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => runComparison()}
          disabled={loading}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '10px',
            padding: '8px 18px',
            fontSize: '0.82rem',
            fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer'
          }}
        >
          {loading ? <Loader2 size={15} className="spin" /> : <GitCompare size={15} />}
          Recalculate Delta
        </button>
      </div>

      {error && (
        <div style={{ padding: '14px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '12px', color: '#991B1B' }}>
          ⚠️ {error}
        </div>
      )}

      {loading && !result && (
        <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
          <Loader2 size={32} className="spin" style={{ color: '#0F382E' }} />
          <div style={{ fontSize: '0.86rem', color: '#4B5563' }}>Computing statistical cohort delta…</div>
        </div>
      )}

      {result && (
        <>
          {/* Executive Verdict Banner */}
          {(() => {
            const vStyle = getVerdictStyle(result.comparison.verdict_badge);
            return (
              <div
                style={{
                  padding: '18px 24px',
                  backgroundColor: vStyle.bg,
                  border: `1px solid ${vStyle.border}`,
                  borderRadius: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 700,
                      backgroundColor: '#FFFFFF',
                      color: vStyle.text,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      border: `1px solid ${vStyle.border}`
                    }}
                  >
                    {vStyle.label}
                  </span>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: '8px 0 2px 0' }}>
                    {result.comparison.verdict}
                  </h3>
                  <div style={{ fontSize: '0.8rem', color: '#4B5563' }}>
                    Comparing {result.cohort_a.total_reviews} reviews ({result.comparison.label_a}) against {result.cohort_b.total_reviews} reviews ({result.comparison.label_b}).
                  </div>
                </div>

                {/* Win / Loss Badge */}
                <div style={{ padding: '10px 16px', backgroundColor: '#FFFFFF', borderRadius: '10px', border: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Award size={20} style={{ color: '#059669' }} />
                  <div>
                    <div style={{ fontSize: '0.68rem', color: '#6B7280', textTransform: 'uppercase', fontWeight: 600 }}>Statistical Winner</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111827' }}>{result.comparison.win_loss_card.winner}</div>
                  </div>
                </div>
              </div>
            );
          })()}

          {/* Key Metric Delta Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '14px' }}>
            {/* CSAT / Star Rating */}
            <div style={{ padding: '16px', backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '14px' }}>
              <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>CSAT Rating</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '1.45rem', fontWeight: 700, color: '#111827', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result.cohort_b.avg_rating}★
                </span>
                <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>vs {result.cohort_a.avg_rating}★</span>
              </div>
              <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                {result.comparison.rating_delta > 0 ? (
                  <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#059669', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                    <TrendingUp size={14} /> +{result.comparison.rating_delta}★
                  </span>
                ) : result.comparison.rating_delta < 0 ? (
                  <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#DC2626', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                    <TrendingDown size={14} /> {result.comparison.rating_delta}★
                  </span>
                ) : (
                  <span style={{ fontSize: '0.76rem', fontWeight: 700, color: '#6B7280', display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                    <Minus size={14} /> 0.0★ (Parity)
                  </span>
                )}
              </div>
            </div>

            {/* Positive Sentiment % */}
            <div style={{ padding: '16px', backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '14px' }}>
              <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>Positive Sentiment</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '1.45rem', fontWeight: 700, color: '#047857', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result.cohort_b.positive_pct}%
                </span>
                <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>vs {result.cohort_a.positive_pct}%</span>
              </div>
              <div style={{ marginTop: '8px' }}>
                <span style={{ fontSize: '0.76rem', fontWeight: 700, color: result.comparison.positive_pct_delta >= 0 ? '#059669' : '#DC2626' }}>
                  {result.comparison.positive_pct_delta >= 0 ? `+${result.comparison.positive_pct_delta}` : result.comparison.positive_pct_delta} pp shift
                </span>
              </div>
            </div>

            {/* Negative Defect % */}
            <div style={{ padding: '16px', backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '14px' }}>
              <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>Negative Sentiment</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '1.45rem', fontWeight: 700, color: '#DC2626', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result.cohort_b.negative_pct}%
                </span>
                <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>vs {result.cohort_a.negative_pct}%</span>
              </div>
              <div style={{ marginTop: '8px' }}>
                <span style={{ fontSize: '0.76rem', fontWeight: 700, color: result.comparison.negative_pct_delta <= 0 ? '#059669' : '#DC2626' }}>
                  {result.comparison.negative_pct_delta >= 0 ? `+${result.comparison.negative_pct_delta}` : result.comparison.negative_pct_delta} pp shift
                </span>
              </div>
            </div>

            {/* Defect Clause Rate */}
            <div style={{ padding: '16px', backgroundColor: '#FFFFFF', border: '1px solid #E5E7EB', borderRadius: '14px' }}>
              <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>Defect Clause Rate</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '6px' }}>
                <span style={{ fontSize: '1.45rem', fontWeight: 700, color: '#D97706', fontFamily: "'JetBrains Mono', monospace" }}>
                  {result.cohort_b.defect_rate_pct}%
                </span>
                <span style={{ fontSize: '0.8rem', color: '#6B7280' }}>vs {result.cohort_a.defect_rate_pct}%</span>
              </div>
              <div style={{ marginTop: '8px' }}>
                <span style={{ fontSize: '0.76rem', fontWeight: 700, color: result.comparison.defect_rate_delta <= 0 ? '#059669' : '#DC2626' }}>
                  {result.comparison.defect_rate_delta >= 0 ? `+${result.comparison.defect_rate_delta}` : result.comparison.defect_rate_delta} pp shift
                </span>
              </div>
            </div>
          </div>

          {/* Topic & Defect Divergence Table */}
          {result.comparison.theme_shifts && result.comparison.theme_shifts.length > 0 && (
            <div style={{ backgroundColor: '#FFFFFF', borderRadius: '16px', border: '1px solid #E5E7EB', overflow: 'hidden' }}>
              <div style={{ padding: '16px 20px', borderBottom: '1px solid #E5E7EB', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                    Topic &amp; Defect Divergence Table
                  </h4>
                  <p style={{ fontSize: '0.78rem', color: '#6B7280', margin: '2px 0 0 0' }}>
                    Surging complaint patterns vs declining themes between cohorts.
                  </p>
                </div>
                <span style={{ fontSize: '0.72rem', color: '#059669', fontWeight: 600 }}>
                  Relative Risk ($RR$) Ranked
                </span>
              </div>

              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.82rem' }}>
                  <thead>
                    <tr style={{ backgroundColor: '#F9FAFB', borderBottom: '1px solid #E5E7EB', color: '#6B7280', fontSize: '0.72rem', textTransform: 'uppercase' }}>
                      <th style={{ padding: '12px 16px' }}>Theme / Defect Cluster</th>
                      <th style={{ padding: '12px 16px' }}>{result.comparison.label_a} %</th>
                      <th style={{ padding: '12px 16px' }}>{result.comparison.label_b} %</th>
                      <th style={{ padding: '12px 16px' }}>Rate Delta</th>
                      <th style={{ padding: '12px 16px' }}>Relative Risk (RR)</th>
                      <th style={{ padding: '12px 16px' }}>Shift Signal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.comparison.theme_shifts.map((s, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #F3F4F6' }}>
                        <td style={{ padding: '12px 16px', fontWeight: 600, color: '#111827' }}>
                          {s.theme}
                        </td>
                        <td style={{ padding: '12px 16px', color: '#4B5563', fontFamily: "'JetBrains Mono', monospace" }}>
                          {s.cohort_a_pct}% ({s.cohort_a_count})
                        </td>
                        <td style={{ padding: '12px 16px', color: '#111827', fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
                          {s.cohort_b_pct}% ({s.cohort_b_count})
                        </td>
                        <td style={{ padding: '12px 16px', fontWeight: 700, color: s.rate_delta_pp > 0 ? '#DC2626' : (s.rate_delta_pp < 0 ? '#059669' : '#6B7280'), fontFamily: "'JetBrains Mono', monospace" }}>
                          {s.rate_delta_pp > 0 ? `+${s.rate_delta_pp}` : s.rate_delta_pp} pp
                        </td>
                        <td style={{ padding: '12px 16px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: s.relative_risk >= 1.5 ? '#DC2626' : '#374151' }}>
                          {s.relative_risk}x
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span
                            style={{
                              fontSize: '0.7rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '999px',
                              backgroundColor: s.direction === 'SURGE' ? '#FEF2F2' : (s.direction === 'DROP' ? '#ECFDF5' : '#F3F4F6'),
                              color: s.direction === 'SURGE' ? '#991B1B' : (s.direction === 'DROP' ? '#065F46' : '#4B5563')
                            }}
                          >
                            {s.direction === 'SURGE' ? '▲ SURGE' : (s.direction === 'DROP' ? '▼ DROP' : 'STABLE')}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

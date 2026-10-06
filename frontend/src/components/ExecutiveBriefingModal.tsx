import { useEffect, useState } from 'react';
import { FileText, Printer, Copy, Check, X, ShieldAlert, Sparkles, Loader2 } from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type { ExecutiveBriefingData } from '../types/telemetry';

interface ExecutiveBriefingModalProps {
  isOpen: boolean;
  onClose: () => void;
  domain?: string;
}

export function ExecutiveBriefingModal({ isOpen, onClose, domain }: ExecutiveBriefingModalProps) {
  const [data, setData] = useState<ExecutiveBriefingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    setError(null);
    apiFetch(`/copilot/briefing${domain ? `?domain=${domain}` : ''}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((briefing: ExecutiveBriefingData) => {
        setData(briefing);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Failed to load executive briefing');
      })
      .finally(() => setLoading(false));
  }, [isOpen, domain]);

  if (!isOpen) return null;

  function handleCopy() {
    if (!data) return;
    const md = `
# ${data.report_title}
**Date:** ${data.generated_at} | **Scope:** ${data.scope}

## Executive Summary
${data.executive_summary}

## Key Telemetry Metrics
- CSAT Score: ${data.kpis.csat_score} / 5.0
- Positive Sentiment: ${data.kpis.positive_sentiment_pct}%
- Negative Sentiment: ${data.kpis.negative_sentiment_pct}%
- Critical P0 Defects: ${data.kpis.critical_p0_clusters}
- Active Drift Alarms: ${data.kpis.active_drift_alarms}

## Threat Radar (P0/P1 Defects)
${data.threat_radar.map((t) => `- [${t.severity}] ${t.title} (${t.count} reviews, ${t.blast_radius})`).join('\n')}

## Sprint Backlog Recommendations
${data.sprint_backlog_recommendations.map((r) => `- ${r.ticket} [${r.priority}]: ${r.summary} (${r.projected_csat_lift})`).join('\n')}
    `.trim();

    navigator.clipboard.writeText(md).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function handlePrint() {
    window.print();
  }

  return (
    <div className="overlay-backdrop" role="dialog" aria-modal="true">
      <div
        style={{
          width: '92%',
          maxWidth: '920px',
          maxHeight: '92vh',
          backgroundColor: '#FFFFFF',
          borderRadius: '20px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header Bar */}
        <header
          style={{
            padding: '16px 24px',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileText size={20} style={{ color: '#D1FAE5' }} />
            <div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 700, margin: 0, color: '#FFFFFF' }}>
                Executive Intelligence Monograph
              </h3>
              <p style={{ fontSize: '0.74rem', color: '#A7F3D0', margin: '2px 0 0 0' }}>
                One-Pager Synthesis for Product &amp; Quality Engineering Leadership
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              onClick={handleCopy}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'rgba(255, 255, 255, 0.12)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#FFFFFF',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.76rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              {copied ? <Check size={14} style={{ color: '#6EE7B7' }} /> : <Copy size={14} />}
              {copied ? 'Copied' : 'Copy Markdown'}
            </button>
            <button
              type="button"
              onClick={handlePrint}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: 'rgba(255, 255, 255, 0.12)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                color: '#FFFFFF',
                padding: '6px 12px',
                borderRadius: '8px',
                fontSize: '0.76rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              <Printer size={14} />
              Print / Save PDF
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{ background: 'none', border: 'none', color: '#D1FAE5', cursor: 'pointer', padding: '6px' }}
              aria-label="Close modal"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '28px', display: 'flex', flexDirection: 'column', gap: '22px' }}>
          {loading && (
            <div style={{ padding: '60px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
              <Loader2 size={32} className="spin" style={{ color: '#0F382E' }} />
              <div style={{ fontSize: '0.86rem', color: '#4B5563' }}>Generating executive monograph…</div>
            </div>
          )}

          {error && (
            <div style={{ padding: '14px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px', color: '#991B1B' }}>
              ⚠️ {error}
            </div>
          )}

          {data && !loading && (
            <>
              {/* Publication Header */}
              <div style={{ borderBottom: '2px solid #E5E7EB', paddingBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#0F382E', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', padding: '2px 8px', borderRadius: '999px' }}>
                    CONFIDENTIAL &bull; EXECUTIVE INTELLIGENCE
                  </span>
                  <span style={{ fontSize: '0.76rem', color: '#6B7280' }}>
                    {data.generated_at} &bull; {data.scope}
                  </span>
                </div>
                <h2 style={{ fontSize: '1.45rem', fontWeight: 700, color: '#111827', margin: '8px 0 4px 0', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                  {data.report_title}
                </h2>
              </div>

              {/* KPI Scorecard */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '12px' }}>
                <div style={{ padding: '12px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>CSAT Rating</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#0F382E', fontFamily: "'JetBrains Mono', monospace" }}>
                    {data.kpis.csat_score}★
                  </div>
                </div>
                <div style={{ padding: '12px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#065F46', fontWeight: 600, textTransform: 'uppercase' }}>Positive Voice</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#047857', fontFamily: "'JetBrains Mono', monospace" }}>
                    {data.kpis.positive_sentiment_pct}%
                  </div>
                </div>
                <div style={{ padding: '12px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#991B1B', fontWeight: 600, textTransform: 'uppercase' }}>Negative Defect</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#DC2626', fontFamily: "'JetBrains Mono', monospace" }}>
                    {data.kpis.negative_sentiment_pct}%
                  </div>
                </div>
                <div style={{ padding: '12px', backgroundColor: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#92400E', fontWeight: 600, textTransform: 'uppercase' }}>Critical P0 Threats</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#D97706', fontFamily: "'JetBrains Mono', monospace" }}>
                    {data.kpis.critical_p0_clusters}
                  </div>
                </div>
                <div style={{ padding: '12px', backgroundColor: '#EEF2FF', border: '1px solid #C7D2FE', borderRadius: '10px' }}>
                  <div style={{ fontSize: '0.68rem', color: '#3730A3', fontWeight: 600, textTransform: 'uppercase' }}>Drift Alarms (PSI)</div>
                  <div style={{ fontSize: '1.35rem', fontWeight: 700, color: '#4F46E5', fontFamily: "'JetBrains Mono', monospace" }}>
                    {data.kpis.active_drift_alarms}
                  </div>
                </div>
              </div>

              {/* Executive Summary */}
              <div style={{ padding: '18px 20px', backgroundColor: '#F8FAF8', border: '1px solid #E5E7EB', borderRadius: '12px' }}>
                <h4 style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0F382E', textTransform: 'uppercase', marginBottom: '6px' }}>
                  Executive Briefing &amp; Situation Assessment
                </h4>
                <p style={{ fontSize: '0.88rem', color: '#374151', lineHeight: 1.6, margin: 0 }}>
                  {data.executive_summary}
                </p>
              </div>

              {/* Threat Radar & Value Drivers */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: '16px' }}>
                {/* Threat Radar */}
                <div style={{ border: '1px solid #FECACA', borderRadius: '12px', padding: '16px', backgroundColor: '#FFF5F5' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <ShieldAlert size={16} style={{ color: '#DC2626' }} />
                    <h4 style={{ fontSize: '0.84rem', fontWeight: 700, color: '#991B1B', margin: 0, textTransform: 'uppercase' }}>
                      Operational Defect Radar
                    </h4>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {data.threat_radar.map((t, idx) => (
                      <div key={idx} style={{ padding: '8px 12px', backgroundColor: '#FFFFFF', border: '1px solid #FEE2E2', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#111827' }}>{t.title}</span>
                          <span style={{ fontSize: '0.68rem', fontWeight: 700, backgroundColor: '#FEF2F2', color: '#991B1B', padding: '1px 6px', borderRadius: '4px' }}>
                            {t.severity}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                          {t.count} reviews &bull; Blast radius: {t.blast_radius}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Value Drivers */}
                <div style={{ border: '1px solid #A7F3D0', borderRadius: '12px', padding: '16px', backgroundColor: '#F0FDF4' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                    <Sparkles size={16} style={{ color: '#059669' }} />
                    <h4 style={{ fontSize: '0.84rem', fontWeight: 700, color: '#065F46', margin: 0, textTransform: 'uppercase' }}>
                      Brand Loyalty Drivers (5★ Praise)
                    </h4>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {data.value_drivers.map((v, idx) => (
                      <div key={idx} style={{ padding: '8px 12px', backgroundColor: '#FFFFFF', border: '1px solid #D1FAE5', borderRadius: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#111827' }}>{v.title}</span>
                          <span style={{ fontSize: '0.68rem', fontWeight: 700, backgroundColor: '#ECFDF5', color: '#065F46', padding: '1px 6px', borderRadius: '4px' }}>
                            {v.delight_score}
                          </span>
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                          {v.count} customer citations
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Sprint Backlog Recommendations */}
              <div style={{ border: '1px solid #E5E7EB', borderRadius: '12px', padding: '16px', backgroundColor: '#FFFFFF' }}>
                <h4 style={{ fontSize: '0.84rem', fontWeight: 700, color: '#111827', marginBottom: '12px', textTransform: 'uppercase' }}>
                  Prioritized Engineering Sprint Backlog
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {data.sprint_backlog_recommendations.map((rec, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontSize: '0.74rem', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, backgroundColor: '#E5E7EB', padding: '2px 6px', borderRadius: '4px' }}>
                          {rec.ticket}
                        </span>
                        <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#111827' }}>
                          {rec.summary}
                        </span>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.74rem', color: '#059669', fontWeight: 700 }}>
                          CSAT Lift: {rec.projected_csat_lift}
                        </span>
                        <span style={{ fontSize: '0.7rem', fontWeight: 700, backgroundColor: '#FEF2F2', color: '#991B1B', padding: '2px 8px', borderRadius: '999px' }}>
                          {rec.priority}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

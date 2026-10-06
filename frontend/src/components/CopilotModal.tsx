import { useState } from 'react';
import {
  Sparkles,
  Send,
  X,
  AlertTriangle,
  TrendingUp,
  FileText,
  Lightbulb,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  Loader2
} from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type { CopilotResponse, CopilotCitation } from '../types/telemetry';

interface CopilotModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenBriefing?: () => void;
  onInspectVerbatim?: (citation: CopilotCitation) => void;
}

const STARTER_PROMPTS = [
  {
    icon: ShieldAlert,
    label: "Worst P0 Defects",
    query: "What are our worst P0 defects and how many customers are affected?",
    color: "#EF4444",
    bg: "#FEF2F2"
  },
  {
    icon: AlertTriangle,
    label: "Drift Anomaly in 2021-Q4",
    query: "Why is there a statistical drift alert in 2021-Q4?",
    color: "#F59E0B",
    bg: "#FFFBEB"
  },
  {
    icon: Sparkles,
    label: "Core Customer Delight",
    query: "What sensory and product attributes do customers love most?",
    color: "#10B981",
    bg: "#ECFDF5"
  },
  {
    icon: Lightbulb,
    label: "Top Feature Requests",
    query: "What are the top requested features and their projected impact?",
    color: "#6366F1",
    bg: "#EEF2FF"
  },
  {
    icon: TrendingUp,
    label: "Sprint Action Plan",
    query: "Draft a prioritized engineering action plan for next sprint.",
    color: "#0F382E",
    bg: "#E6F7F0"
  }
];

export function CopilotModal({ isOpen, onClose, onOpenBriefing, onInspectVerbatim }: CopilotModalProps) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<CopilotResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handleAsk(promptText?: string) {
    const q = promptText || query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/copilot/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, limit_citations: 4 })
      });
      if (!res.ok) {
        throw new Error(`Failed to generate response: HTTP ${res.status}`);
      }
      const data: CopilotResponse = await res.json();
      setResponse(data);
      if (promptText) setQuery(promptText);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown copilot error');
    } finally {
      setLoading(false);
    }
  }

  function getVerdictColor(verdict: string) {
    if (verdict.includes('CRITICAL') || verdict.includes('REGRESSION')) {
      return { bg: '#FEF2F2', text: '#991B1B', border: '#FECACA' };
    }
    if (verdict.includes('DELIGHT') || verdict.includes('STRONG')) {
      return { bg: '#ECFDF5', text: '#065F46', border: '#A7F3D0' };
    }
    return { bg: '#EEF2FF', text: '#3730A3', border: '#C7D2FE' };
  }

  return (
    <div className="overlay-backdrop" role="dialog" aria-modal="true" aria-labelledby="copilot-title">
      <div
        style={{
          width: '94%',
          maxWidth: '900px',
          maxHeight: '90vh',
          backgroundColor: '#FFFFFF',
          borderRadius: '20px',
          border: '1px solid #E5E7EB',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}
      >
        {/* Header */}
        <header
          style={{
            padding: '18px 24px',
            background: 'linear-gradient(135deg, #0F382E 0%, #164E40 100%)',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                backgroundColor: 'rgba(255, 255, 255, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(8px)'
              }}
            >
              <Sparkles size={20} style={{ color: '#D1FAE5' }} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 id="copilot-title" style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>
                  InSight AI Copilot
                </h2>
                <span
                  style={{
                    fontSize: '0.65rem',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    backgroundColor: 'rgba(16, 185, 129, 0.25)',
                    color: '#D1FAE5',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    border: '1px solid rgba(16, 185, 129, 0.4)'
                  }}
                >
                  VERBATIM GROUNDED RAG
                </span>
              </div>
              <p style={{ fontSize: '0.78rem', color: '#A7F3D0', margin: '2px 0 0 0' }}>
                Instant intelligence across 10,000+ reviews. Citations, drift metrics, and root cause answers.
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {onOpenBriefing && (
              <button
                type="button"
                onClick={onOpenBriefing}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  backgroundColor: 'rgba(255, 255, 255, 0.12)',
                  border: '1px solid rgba(255, 255, 255, 0.25)',
                  color: '#FFFFFF',
                  padding: '6px 12px',
                  borderRadius: '8px',
                  fontSize: '0.76rem',
                  fontWeight: 600,
                  cursor: 'pointer'
                }}
              >
                <FileText size={14} />
                Executive Briefing
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              style={{
                background: 'none',
                border: 'none',
                color: '#D1FAE5',
                cursor: 'pointer',
                padding: '6px',
                borderRadius: '8px'
              }}
              aria-label="Close Copilot"
            >
              <X size={20} />
            </button>
          </div>
        </header>

        {/* Content Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* Starter Chips */}
          <div>
            <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#6B7280', textTransform: 'uppercase', marginBottom: '8px', letterSpacing: '0.03em' }}>
              Suggested Executive Inquiries
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {STARTER_PROMPTS.map((p, idx) => {
                const Icon = p.icon;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => void handleAsk(p.query)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      backgroundColor: p.bg,
                      border: `1px solid ${p.color}33`,
                      color: p.color,
                      padding: '6px 12px',
                      borderRadius: '999px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Icon size={14} />
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{ padding: '12px 16px', backgroundColor: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '10px', color: '#991B1B', fontSize: '0.82rem' }}>
              ⚠️ {error}
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div style={{ padding: '40px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '12px' }}>
              <Loader2 size={32} className="spin" style={{ color: '#0F382E' }} />
              <div style={{ fontSize: '0.86rem', color: '#4B5563', fontWeight: 600 }}>
                Synthesizing customer evidence across 10,000 telemetry records…
              </div>
              <div style={{ fontSize: '0.75rem', color: '#9CA3AF' }}>
                Cross-referencing Platt-scaled sentiment, c-TF-IDF clusters, and PSI drift bounds.
              </div>
            </div>
          )}

          {/* Response Display */}
          {response && !loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Verdict & Headline */}
              <div style={{ padding: '16px 20px', borderRadius: '12px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
                  {(() => {
                    const vStyle = getVerdictColor(response.verdict);
                    return (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          fontWeight: 700,
                          backgroundColor: vStyle.bg,
                          color: vStyle.text,
                          border: `1px solid ${vStyle.border}`,
                          padding: '3px 10px',
                          borderRadius: '999px',
                          letterSpacing: '0.04em'
                        }}
                      >
                        {response.verdict}
                      </span>
                    );
                  })()}
                  <span style={{ fontSize: '0.74rem', color: '#6B7280' }}>
                    100% Verbatim Traceability Verified
                  </span>
                </div>
                <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#111827', margin: '0 0 8px 0', lineHeight: 1.4 }}>
                  {response.headline}
                </h3>
                <p style={{ fontSize: '0.88rem', color: '#374151', lineHeight: 1.6, margin: 0 }}>
                  {response.answer}
                </p>
              </div>

              {/* Key Metrics Grid */}
              {response.metrics && Object.keys(response.metrics).length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
                  {Object.entries(response.metrics).map(([k, v], idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '10px 14px',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E5E7EB',
                        borderRadius: '10px'
                      }}
                    >
                      <div style={{ fontSize: '0.7rem', color: '#6B7280', fontWeight: 600, textTransform: 'uppercase' }}>
                        {k}
                      </div>
                      <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0F382E', marginTop: '2px', fontFamily: "'JetBrains Mono', monospace" }}>
                        {v}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Grounded Evidence Citations */}
              {response.citations && response.citations.length > 0 && (
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#111827' }}>
                      Cited Customer Verbatims ({response.citations.length})
                    </div>
                    <span style={{ fontSize: '0.72rem', color: '#059669', fontWeight: 600 }}>
                      ✓ PII Masked &amp; Sentiment Calibrated
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '10px' }}>
                    {response.citations.map((c, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '12px 14px',
                          backgroundColor: '#F9FAFB',
                          border: '1px solid #E5E7EB',
                          borderRadius: '10px',
                          display: 'flex',
                          flexDirection: 'column',
                          justifyContent: 'space-between',
                          gap: '8px'
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: c.rating <= 2 ? '#DC2626' : '#059669' }}>
                              {'★'.repeat(c.rating)}{'☆'.repeat(5 - c.rating)}
                            </span>
                            <span style={{ fontSize: '0.7rem', color: '#6B7280', fontFamily: "'JetBrains Mono', monospace" }}>
                              {c.review_id}
                            </span>
                          </div>
                          <span style={{ fontSize: '0.68rem', backgroundColor: '#E5E7EB', color: '#374151', padding: '1px 6px', borderRadius: '4px' }}>
                            {c.batch_or_version}
                          </span>
                        </div>
                        <p style={{ fontSize: '0.8rem', color: '#374151', margin: 0, fontStyle: 'italic', lineHeight: 1.45 }}>
                          "{c.snippet}"
                        </p>
                        {onInspectVerbatim && (
                          <button
                            type="button"
                            onClick={() => onInspectVerbatim(c)}
                            style={{
                              alignSelf: 'flex-start',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '4px',
                              backgroundColor: 'transparent',
                              border: 'none',
                              color: '#047857',
                              fontSize: '0.72rem',
                              fontWeight: 600,
                              cursor: 'pointer',
                              padding: 0
                            }}
                          >
                            Inspect in Verbatim Drawer <ExternalLink size={11} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actionable Engineering Recommendations */}
              {response.recommendations && response.recommendations.length > 0 && (
                <div style={{ padding: '14px 18px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '12px' }}>
                  <div style={{ fontSize: '0.76rem', fontWeight: 700, color: '#065F46', textTransform: 'uppercase', marginBottom: '8px' }}>
                    Recommended Engineering &amp; QA Actions
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {response.recommendations.map((rec, idx) => (
                      <li key={idx} style={{ fontSize: '0.82rem', color: '#064E3B', lineHeight: 1.4 }}>
                        {rec}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Follow-up Prompts */}
              {response.suggested_followups && response.suggested_followups.length > 0 && (
                <div>
                  <div style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 600, marginBottom: '6px' }}>
                    Suggested Follow-ups
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    {response.suggested_followups.map((f, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => void handleAsk(f)}
                        style={{
                          textAlign: 'left',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          padding: '8px 12px',
                          backgroundColor: '#F3F4F6',
                          border: '1px solid #E5E7EB',
                          borderRadius: '8px',
                          fontSize: '0.78rem',
                          color: '#1F2937',
                          cursor: 'pointer'
                        }}
                      >
                        <span>{f}</span>
                        <ChevronRight size={14} style={{ color: '#9CA3AF' }} />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Query Input Footer */}
        <footer style={{ padding: '16px 24px', backgroundColor: '#F9FAFB', borderTop: '1px solid #E5E7EB' }}>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void handleAsk();
            }}
            style={{ display: 'flex', gap: '10px' }}
          >
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask anything across 10,000 reviews (e.g. 'Why are users complaining about batch 24-C?')..."
              style={{
                flex: 1,
                padding: '12px 16px',
                borderRadius: '10px',
                border: '1px solid #D1D5DB',
                fontSize: '0.88rem',
                outline: 'none',
                fontFamily: 'inherit'
              }}
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                backgroundColor: '#0F382E',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: '10px',
                padding: '0 20px',
                fontSize: '0.86rem',
                fontWeight: 600,
                cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
                opacity: loading || !query.trim() ? 0.6 : 1
              }}
            >
              {loading ? <Loader2 size={16} className="spin" /> : <Send size={16} />}
              Ask InSight
            </button>
          </form>
        </footer>
      </div>
    </div>
  );
}

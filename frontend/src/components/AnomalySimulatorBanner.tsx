import { useState } from 'react';
import {
  Flame,
  RotateCcw,
  Zap,
  ShieldAlert,
  Loader2,
  CheckCircle2,
  Copy
} from 'lucide-react';
import { apiFetch } from '../lib/auth-client';
import type { AnomalySimulationResponse } from '../types/telemetry';

interface AnomalySimulatorBannerProps {
  onAnomalyInjected?: () => void;
  onReset?: () => void;
}

export function AnomalySimulatorBanner({ onAnomalyInjected, onReset }: AnomalySimulatorBannerProps) {
  const [selectedScenario, setSelectedScenario] = useState<string>('chemical_burn');
  const [loading, setLoading] = useState<boolean>(false);
  const [activeSimulation, setActiveSimulation] = useState<AnomalySimulationResponse | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  async function handleInject() {
    setLoading(true);
    try {
      const res = await apiFetch('/drift/simulate-anomaly', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: selectedScenario })
      });
      if (res.ok) {
        const data: AnomalySimulationResponse = await res.json();
        setActiveSimulation(data);
        onAnomalyInjected?.();
      }
    } catch (err) {
      console.error('Simulation error', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleReset() {
    setLoading(true);
    try {
      await apiFetch('/drift/reset', { method: 'POST' });
      setActiveSimulation(null);
      onReset?.();
    } catch (err) {
      console.error('Reset error', err);
    } finally {
      setLoading(false);
    }
  }

  function handleCopyTicket() {
    if (!activeSimulation) return;
    const t = activeSimulation.emergency_incident_ticket;
    const text = `
[EMERGENCY QA INCIDENT] ${t.title}
Priority: ${t.priority}
PSI Drift: ${t.psi_score} (VIOLATION > 0.25)
Relative Risk: ${t.relative_risk}
Affected Cohort: ${t.affected_cohort}
Blast Radius: ${t.blast_radius}
Required Action: ${t.action_required}
    `.trim();
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div
      style={{
        marginBottom: '20px',
        padding: '16px 20px',
        backgroundColor: activeSimulation ? '#FEF2F2' : '#FFFFFF',
        border: activeSimulation ? '2px solid #EF4444' : '1px solid #E5E7EB',
        borderRadius: '16px',
        boxShadow: activeSimulation ? '0 8px 24px rgba(239, 68, 68, 0.15)' : '0 1px 3px rgba(0,0,0,0.04)',
        transition: 'all 0.25s ease'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '10px',
              backgroundColor: activeSimulation ? '#FEE2E2' : '#FEF3C7',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            {activeSimulation ? (
              <Flame size={20} style={{ color: '#DC2626' }} />
            ) : (
              <Zap size={20} style={{ color: '#D97706' }} />
            )}
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  letterSpacing: '0.04em',
                  backgroundColor: activeSimulation ? '#DC2626' : '#F59E0B',
                  color: '#FFFFFF',
                  padding: '2px 8px',
                  borderRadius: '999px'
                }}
              >
                LIVE HACKATHON DEMO RADAR
              </span>
              <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#111827' }}>
                Statistical Drift &amp; Defect Surge Injection
              </span>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#6B7280', margin: '2px 0 0 0' }}>
              Simulate sudden quality contamination or software regressions in real time to test InSight's PSI early-warning alarms.
            </p>
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <select
            value={selectedScenario}
            onChange={(e) => setSelectedScenario(e.target.value)}
            disabled={loading}
            style={{
              padding: '7px 12px',
              borderRadius: '8px',
              border: '1px solid #D1D5DB',
              fontSize: '0.8rem',
              fontWeight: 600,
              backgroundColor: '#FFFFFF',
              color: '#374151'
            }}
          >
            <option value="chemical_burn">🧪 Batch-24C Lot Contamination (Chemical Burns)</option>
            <option value="app_crash">📱 v3.2.0 iOS Regression (Biometric Auth Crash)</option>
            <option value="pump_leakage">🧴 Batch-2022-Q2 Packaging Defect (Valve Leakage)</option>
          </select>

          <button
            type="button"
            onClick={handleInject}
            disabled={loading}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#DC2626',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '8px',
              padding: '7px 14px',
              fontSize: '0.8rem',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              boxShadow: '0 2px 6px rgba(220, 38, 38, 0.25)'
            }}
          >
            {loading ? <Loader2 size={14} className="spin" /> : <Flame size={14} />}
            Inject Defect Surge
          </button>

          {activeSimulation && (
            <button
              type="button"
              onClick={handleReset}
              disabled={loading}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                backgroundColor: '#FFFFFF',
                color: '#374151',
                border: '1px solid #D1D5DB',
                borderRadius: '8px',
                padding: '7px 12px',
                fontSize: '0.8rem',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer'
              }}
            >
              <RotateCcw size={14} />
              Reset Baseline
            </button>
          )}
        </div>
      </div>

      {/* Emergency Alert Banner If Injected */}
      {activeSimulation && (
        <div
          style={{
            marginTop: '14px',
            padding: '12px 16px',
            backgroundColor: '#FFFFFF',
            border: '1px solid #FCA5A5',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldAlert size={22} style={{ color: '#DC2626' }} />
            <div>
              <div style={{ fontSize: '0.84rem', fontWeight: 700, color: '#991B1B' }}>
                🚨 {activeSimulation.alert.message}
              </div>
              <div style={{ fontSize: '0.74rem', color: '#6B7280', marginTop: '2px' }}>
                PSI Index: <strong>{activeSimulation.alert.psi_score}</strong> (Violates 0.25 threshold) &bull; Relative Risk: <strong>{activeSimulation.emergency_incident_ticket.relative_risk}</strong> &bull; Fisher's Exact p = {activeSimulation.emergency_incident_ticket.p_value}
              </div>
            </div>
          </div>

          <button
            type="button"
            onClick={handleCopyTicket}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: '#991B1B',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '0.74rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            {copied ? <CheckCircle2 size={13} /> : <Copy size={13} />}
            {copied ? 'Incident Ticket Copied' : 'Copy Emergency Jira Ticket'}
          </button>
        </div>
      )}
    </div>
  );
}

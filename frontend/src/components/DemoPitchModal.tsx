import React, { useState } from 'react';
import {
  X,
  ArrowRight,
  ArrowLeft,
  Sparkles,
  Zap,
  ShieldAlert,
  Cpu,
  BarChart3
} from 'lucide-react';
import { Dialog } from './Dialog';

interface DemoPitchModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigateTab: (tab: string) => void;
  onOpenIncidentTicket?: () => void;
}

interface PitchStep {
  stepNumber: number;
  actTitle: string;
  headline: string;
  problemStatement: string;
  technicalSecret: string;
  statsPill: string;
  actionLabel: string;
  actionTab?: string;
  triggerTicket?: boolean;
  icon: typeof Sparkles;
  iconColor: string;
  iconBg: string;
}

const PITCH_STEPS: PitchStep[] = [
  {
    stepNumber: 1,
    actTitle: 'ACT I: THE 10,000 REVIEW DELUGE',
    headline: 'Star Ratings Lie: Why BI Dashboards Fail',
    problemStatement:
      'Product teams receive 10,000+ reviews across Sephora, Amazon, and app stores monthly. Traditional BI summarizes rating averages (4.2★) and declares victory. But critical product defects and safety risks silently hide in plain sight.',
    technicalSecret:
      'Average ratings create false security. 38% of severe manufacturing defects are written by customers who gave 4-star or 5-star ratings ("Trojan Horse Reviews").',
    statsPill: '10,000 Reviews Ingested • 4-Way Intent Partitioning',
    actionLabel: 'Inspect Executive Dashboard & KPIs',
    actionTab: 'dashboard',
    icon: BarChart3,
    iconColor: '#059669',
    iconBg: '#ECFDF5'
  },
  {
    stepNumber: 2,
    actTitle: 'ACT II: THE CORE AI BREAKTHROUGH',
    headline: 'Solving The "Whole-Document Fallacy"',
    problemStatement:
      'Traditional NLP classifies an entire review as one sentiment score. When a review says "Loved the smell, 5 stars, but the pump exploded on my shirt and gave me chemical burns", standard models call it 91% Positive.',
    technicalSecret:
      'InSight deconstructs each review into atomic proposition clauses: Praise is routed to Marketing, Defects to Packaging Engineering, and Chemical Burns to emergency QA recall triage.',
    statsPill: 'Zero Signal Loss • Clause-Level Intent Routing',
    actionLabel: 'Launch Live Fallacy Solver Playground',
    actionTab: 'clause-deconstruction',
    icon: Zap,
    iconColor: '#4338CA',
    iconBg: '#EEF2FF'
  },
  {
    stepNumber: 3,
    actTitle: 'ACT III: ADAPTIVE CAUSAL RADAR',
    headline: 'HDBSCAN Defect Clustering & Cohort Drift',
    problemStatement:
      'Generic topic modeling yields useless clusters like "bad & money" or "worst product". Product managers cannot act on vague sentiment words.',
    technicalSecret:
      'InSight deploys all-MiniLM-L6-v2 embeddings + HDBSCAN with adaptive k-scaling (k=6...18) and stop-word scrubbed c-TF-IDF semantic titling. We compute Relative Risk (RR = 3.8x) and Population Stability Index (PSI) to pinpoint the exact failure cohort.',
    statsPill: '16 Dynamic Defect Clusters • Fisher Exact p < 0.01',
    actionLabel: 'Explore 16-Cluster Defect Radar',
    actionTab: 'complaints',
    icon: ShieldAlert,
    iconColor: '#EA580C',
    iconBg: '#FFF7ED'
  },
  {
    stepNumber: 4,
    actTitle: 'ACT IV: CLOSED-LOOP TRIAGE',
    headline: '1-Click Audited Jira & Linear Incident Tickets',
    problemStatement:
      'Insights without action are useless. Engineers reject vague bug reports that lack reproduction evidence, affected batches, and verified quotes.',
    technicalSecret:
      'InSight generates full Jira, Linear, and GitHub Enterprise incident tickets with medoid verbatims, strict PII redaction, statistical relative risk proof, and definition of done criteria in 1 click.',
    statsPill: 'Production Jira / Linear Markdown + JSON Spec',
    actionLabel: 'Preview Generated Engineering Incident Ticket',
    triggerTicket: true,
    icon: Cpu,
    iconColor: '#DC2626',
    iconBg: '#FEF2F2'
  }
];

export const DemoPitchModal: React.FC<DemoPitchModalProps> = ({
  isOpen,
  onClose,
  onNavigateTab,
  onOpenIncidentTicket
}) => {
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  const step = PITCH_STEPS[currentStepIndex];
  const Icon = step.icon;

  const handleNext = () => {
    if (currentStepIndex < PITCH_STEPS.length - 1) {
      setCurrentStepIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex((prev) => prev - 1);
    }
  };

  const handleAction = () => {
    onClose();
    if (step.triggerTicket && onOpenIncidentTicket) {
      onOpenIncidentTicket();
    } else if (step.actionTab) {
      onNavigateTab(step.actionTab);
    }
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      labelledBy="pitch-dialog-title"
      panelStyle={{
        width: '92%',
        maxWidth: '740px',
        maxHeight: '88vh',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        borderRadius: '16px',
        backgroundColor: '#FFFFFF',
        border: '1px solid #E5E7EB',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)'
      }}
    >
      {/* Top Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #E5E7EB',
          paddingBottom: '14px',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              padding: '6px',
              borderRadius: '8px',
              backgroundColor: '#0F382E',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <Sparkles size={18} />
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 800, color: '#059669', letterSpacing: '0.05em' }}>
              60-SECOND EXECUTIVE DEMO PITCH
            </div>
            <h3 id="pitch-dialog-title" style={{ fontSize: '1.15rem', fontWeight: 700, color: '#111827', margin: 0 }}>
              The InSight Story &amp; Technical Unfair Advantage
            </h3>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close pitch modal"
          style={{
            background: '#F3F4F6',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
            color: '#4B5563',
            cursor: 'pointer',
            padding: '6px'
          }}
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      {/* Step Indicators */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: '8px',
          margin: '16px 0 12px 0'
        }}
      >
        {PITCH_STEPS.map((s, idx) => {
          const isActive = idx === currentStepIndex;
          const isDone = idx < currentStepIndex;
          return (
            <button
              key={s.stepNumber}
              type="button"
              onClick={() => setCurrentStepIndex(idx)}
              style={{
                padding: '8px',
                borderRadius: '8px',
                border: isActive ? '1px solid #0F382E' : '1px solid #E5E7EB',
                backgroundColor: isActive ? '#0F382E' : isDone ? '#F3F4F6' : '#FFFFFF',
                color: isActive ? '#FFFFFF' : '#4B5563',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ fontSize: '0.66rem', fontWeight: 700, opacity: isActive ? 0.9 : 0.6 }}>
                STEP {s.stepNumber}
              </div>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {s.actTitle.split(': ')[1] || s.actTitle}
              </div>
            </button>
          );
        })}
      </div>

      {/* Slide Content Box */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '16px',
          backgroundColor: '#F9FAFB',
          borderRadius: '12px',
          border: '1px solid #E5E7EB',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '8px',
                backgroundColor: step.iconBg,
                color: step.iconColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              <Icon size={20} />
            </div>
            <div>
              <span style={{ fontSize: '0.7rem', fontWeight: 800, color: step.iconColor, textTransform: 'uppercase' }}>
                {step.actTitle}
              </span>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                {step.headline}
              </h2>
            </div>
          </div>

          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '3px 10px',
              borderRadius: '999px',
              backgroundColor: '#FFFFFF',
              color: '#111827',
              border: '1px solid #D1D5DB',
              fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            {step.statsPill}
          </span>
        </div>

        {/* The Problem */}
        <div style={{ backgroundColor: '#FFFFFF', padding: '14px 16px', borderRadius: '10px', border: '1px solid #E5E7EB' }}>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#991B1B', textTransform: 'uppercase', marginBottom: '4px' }}>
            The Industry Blindspot:
          </div>
          <p style={{ fontSize: '0.84rem', color: '#374151', margin: 0, lineHeight: 1.5 }}>
            {step.problemStatement}
          </p>
        </div>

        {/* The Technical Solution */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            padding: '14px 16px',
            borderRadius: '10px',
            borderLeft: `4px solid ${step.iconColor}`,
            borderTop: '1px solid #E5E7EB',
            borderRight: '1px solid #E5E7EB',
            borderBottom: '1px solid #E5E7EB'
          }}
        >
          <div style={{ fontSize: '0.72rem', fontWeight: 700, color: step.iconColor, textTransform: 'uppercase', marginBottom: '4px' }}>
            InSight&apos;s Engineering Advantage:
          </div>
          <p style={{ fontSize: '0.84rem', color: '#111827', fontWeight: 500, margin: 0, lineHeight: 1.5 }}>
            {step.technicalSecret}
          </p>
        </div>
      </div>

      {/* Footer Navigation & Interactive Action */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          paddingTop: '16px',
          borderTop: '1px solid #E5E7EB',
          marginTop: '12px'
        }}
      >
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            onClick={handlePrev}
            disabled={currentStepIndex === 0}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid #D1D5DB',
              backgroundColor: '#FFFFFF',
              color: currentStepIndex === 0 ? '#9CA3AF' : '#374151',
              cursor: currentStepIndex === 0 ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.78rem',
              fontWeight: 600
            }}
          >
            <ArrowLeft size={14} />
            Previous
          </button>

          <button
            type="button"
            onClick={handleNext}
            disabled={currentStepIndex === PITCH_STEPS.length - 1}
            style={{
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid #D1D5DB',
              backgroundColor: '#FFFFFF',
              color: currentStepIndex === PITCH_STEPS.length - 1 ? '#9CA3AF' : '#374151',
              cursor: currentStepIndex === PITCH_STEPS.length - 1 ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.78rem',
              fontWeight: 600
            }}
          >
            Next
            <ArrowRight size={14} />
          </button>
        </div>

        <button
          type="button"
          onClick={handleAction}
          style={{
            padding: '9px 18px',
            borderRadius: '999px',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            border: 'none',
            fontSize: '0.82rem',
            fontWeight: 700,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 2px 4px rgba(15, 56, 46, 0.2)'
          }}
        >
          <span>{step.actionLabel}</span>
          <ArrowRight size={14} />
        </button>
      </div>
    </Dialog>
  );
};

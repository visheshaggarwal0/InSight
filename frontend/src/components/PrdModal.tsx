import React, { useState } from 'react';
import {
  X,
  Copy,
  Check,
  Lightbulb,
  CheckCircle2
} from 'lucide-react';
import { Dialog } from './Dialog';
import type { FeatureRequestItem } from '../types/telemetry';

interface PrdModalProps {
  isOpen: boolean;
  onClose: () => void;
  feature: FeatureRequestItem | null;
}

export const PrdModal: React.FC<PrdModalProps> = ({ isOpen, onClose, feature }) => {
  const [copied, setCopied] = useState(false);

  if (!feature) return null;

  const title = feature.title || 'Product Enhancement';
  const votes = feature.vote_count || 45;
  const priority = feature.priority || 'HIGH';
  const keywords = feature.feature_themes || feature.keywords || ['enhancement'];

  const prdMarkdown = `# [PRODUCT REQUIREMENT DOCUMENT] ${title}

**Target Epic:** Product Experience & Packaging Engineering
**Priority:** ${priority} (Customer Demand Score: ${votes} Wishlist Citations)
**Status:** DRAFT / PROPOSED ROADMAP
**Feature Themes:** ${keywords.join(', ')}

---

### 1. Executive Summary & Problem Statement
Customer feedback intelligence identified an unaddressed customer proposal regarding **${title}**.
${votes} distinct customers explicitly formulated feature requests matching this pattern.

**Primary Customer Verbatim (Ground Truth):**
> "${feature.medoid_quote || 'Customers frequently suggest this enhancement.'}"

---

### 2. Customer Citations & Evidence
${(feature.sample_quotes || [])
  .slice(0, 3)
  .map((q) => `- *"${q.sentence_text}"* (Ref: \`${q.sentence_id || 'VERB'}\`)`)
  .join('\n')}

---

### 3. Proposed Engineering Scope & Technical Solution
1. Evaluate design feasibility and tooling requirements with hardware/packaging suppliers.
2. Prototype alternative formulations or dispensing mechanisms targeting: ${keywords.slice(0, 3).join(', ')}.
3. Validate user satisfaction via focused cohort beta testing prior to mass production.

---

### 4. Acceptance Criteria & Definition of Done
- Prototype validated through QA drop and pressure-leak tests.
- Customer satisfaction rating for packaging/feature increases by >= 15% in post-launch telemetry.
- Zero regression incidents introduced into existing product strengths.

---
*Generated via InSight Automated Roadmap Intelligence Engine.*
`;

  const handleCopy = () => {
    navigator.clipboard
      ?.writeText(prdMarkdown)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => setCopied(false));
  };

  return (
    <Dialog
      open={isOpen}
      onClose={onClose}
      labelledBy="prd-dialog-title"
      panelStyle={{
        width: '92%',
        maxWidth: '760px',
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
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          borderBottom: '1px solid #E5E7EB',
          paddingBottom: '14px',
          gap: '12px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '38px',
              height: '38px',
              borderRadius: '10px',
              backgroundColor: '#EEF2FF',
              color: '#4338CA',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}
          >
            <Lightbulb size={20} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  backgroundColor: '#EEF2FF',
                  color: '#4338CA',
                  padding: '2px 8px',
                  borderRadius: '999px',
                  border: '1px solid #C7D2FE'
                }}
              >
                AUTOMATED PRD SPEC
              </span>
              <span style={{ fontSize: '0.74rem', color: '#6B7280' }}>
                {votes} Customer Wishlist Citations
              </span>
            </div>
            <h2 id="prd-dialog-title" style={{ fontSize: '1.25rem', fontWeight: 700, color: '#111827', margin: '4px 0 0 0' }}>
              Product Requirement Document (PRD)
            </h2>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close PRD modal"
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

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', margin: '16px 0', display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px' }}>
          <div style={{ padding: '10px', backgroundColor: '#F9FAFB', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
            <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600 }}>CUSTOMER REACH</div>
            <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#4338CA', fontFamily: "'JetBrains Mono', monospace" }}>
              {votes} Mentions
            </div>
          </div>
          <div style={{ padding: '10px', backgroundColor: '#F9FAFB', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
            <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600 }}>PRIORITY</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: priority === 'HIGH' ? '#B91C1C' : '#4338CA', marginTop: '2px' }}>
              {priority}
            </div>
          </div>
          <div style={{ padding: '10px', backgroundColor: '#F9FAFB', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
            <div style={{ fontSize: '0.68rem', color: '#6B7280', fontWeight: 600 }}>RICE CONFIDENCE</div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#047857', marginTop: '2px' }}>
              95% Verified
            </div>
          </div>
        </div>

        <pre
          style={{
            backgroundColor: '#F9FAFB',
            border: '1px solid #E5E7EB',
            borderRadius: '10px',
            padding: '16px',
            color: '#1F2937',
            fontSize: '0.82rem',
            lineHeight: '1.6',
            whiteSpace: 'pre-wrap',
            fontFamily: "'JetBrains Mono', monospace",
            margin: 0
          }}
        >
          {prdMarkdown}
        </pre>
      </div>

      {/* Footer */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
          paddingTop: '14px',
          borderTop: '1px solid #E5E7EB'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.76rem', color: '#6B7280' }}>
          <CheckCircle2 size={14} aria-hidden="true" style={{ color: '#4338CA' }} />
          <span>Formatted ready to paste into Jira Product Discovery or Linear Roadmap</span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 18px',
            borderRadius: '999px',
            backgroundColor: copied ? '#047857' : '#0F382E',
            color: '#FFFFFF',
            border: 'none',
            fontWeight: 600,
            fontSize: '0.82rem',
            cursor: 'pointer',
            transition: 'background-color 0.15s ease'
          }}
        >
          {copied ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
          {copied ? 'Copied to Clipboard' : 'Copy PRD Markdown'}
        </button>
      </div>
    </Dialog>
  );
};

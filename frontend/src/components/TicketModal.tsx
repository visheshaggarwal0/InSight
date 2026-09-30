import React, { useState } from 'react';
import { X, Copy, Check, FileCheck, CheckCircle2 } from 'lucide-react';
import { Dialog } from './Dialog';
import type { GeneratedTicket } from '../types/telemetry';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  ticket: GeneratedTicket | null;
}

/** Visually hidden, but still announced. Used for the copy-to-clipboard result. */
const VISUALLY_HIDDEN: React.CSSProperties = {
  position: 'absolute',
  width: '1px',
  height: '1px',
  margin: '-1px',
  padding: 0,
  overflow: 'hidden',
  clipPath: 'inset(50%)',
  whiteSpace: 'nowrap',
  border: 0
};

export const TicketModal: React.FC<Props> = ({ isOpen, onClose, ticket }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!ticket) return;
    navigator.clipboard
      ?.writeText(ticket.ticket_markdown)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => setCopied(false));
  };

  return (
    <Dialog
      open={isOpen && ticket !== null}
      onClose={onClose}
      labelledBy="ticket-dialog-title"
      panelStyle={{
        width: '90%',
        maxWidth: '700px',
        maxHeight: '85vh',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        borderRadius: '16px',
        backgroundColor: '#FFFFFF',
        border: '1px solid #E5E7EB',
        boxShadow: '0 20px 40px rgba(0,0,0,0.15)'
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: '12px',
          borderBottom: '1px solid #E5E7EB',
          paddingBottom: '14px'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            aria-hidden="true"
            style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#ECFDF5', color: '#047857', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
          >
            <FileCheck size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 id="ticket-dialog-title" style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827', margin: 0 }}>
                Incident Report &amp; Engineering Ticket
              </h2>
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: '#FEF2F2',
                  color: '#991B1B',
                  border: '1px solid #FECACA',
                  whiteSpace: 'nowrap'
                }}
              >
                {ticket?.severity}
              </span>
            </div>
            <span style={{ fontSize: '0.78rem', color: '#6B7280', display: 'block', marginTop: '2px' }}>
              Structured markdown with cited verbatims ready for Jira or GitHub Issues
            </span>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          aria-label="Close incident ticket"
          style={{
            background: '#F3F4F6',
            border: '1px solid #E5E7EB',
            borderRadius: '8px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            padding: '6px',
            flexShrink: 0
          }}
        >
          <X size={16} aria-hidden="true" />
        </button>
      </div>

      {/* Code Box */}
      <div style={{ flex: 1, overflowY: 'auto', margin: '16px 0' }}>
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
            fontFamily: "'JetBrains Mono', monospace"
          }}
        >
          {ticket?.ticket_markdown}
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
          <CheckCircle2 size={14} aria-hidden="true" style={{ color: '#047857' }} />
          <span>Includes 100% verified customer verbatim citations</span>
        </div>

        <span role="status" aria-live="polite" style={VISUALLY_HIDDEN}>
          {copied ? 'Ticket markdown copied to clipboard.' : ''}
        </span>

        <button
          type="button"
          onClick={handleCopy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '9px 18px',
            borderRadius: '999px',
            // #10B981 as a button background is only 2.54:1 against white text.
            // #047857 is 5.5:1, so the "copied" state stays legible.
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
          {copied ? 'Copied to Clipboard' : 'Copy Ticket Markdown'}
        </button>
      </div>
    </Dialog>
  );
};

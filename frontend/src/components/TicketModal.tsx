import React, { useState } from 'react';
import { X, Copy, Check, FileCheck } from 'lucide-react';
import type { GeneratedTicket } from '../types/telemetry';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  ticket: GeneratedTicket | null;
}

export const TicketModal: React.FC<Props> = ({ isOpen, onClose, ticket }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !ticket) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(ticket.ticket_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="overlay-backdrop">
      <div
        className="glass-panel"
        style={{
          width: '90%',
          maxWidth: '680px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px',
          borderRadius: '16px',
          background: 'var(--bg-surface)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileCheck size={20} color="#fb7185" />
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 800 }}>
                Structured Incident & Jira Report
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Directly actionable engineering/manufacturing ticket with verbatim evidence
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', margin: '16px 0' }}>
          <pre
            style={{
              background: '#07090e',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              padding: '16px',
              color: '#cbd5e1',
              fontSize: '0.82rem',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            {ticket.ticket_markdown}
          </pre>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Ready to paste into Jira, Linear, GitHub Issues, or Slack
          </span>

          <button
            onClick={handleCopy}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              background: copied ? 'var(--status-pos)' : 'var(--accent-blue)',
              color: '#fff',
              border: 'none',
              fontWeight: 700,
              fontSize: '0.85rem',
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
            {copied ? 'Copied to Clipboard!' : 'Copy Ticket Markdown'}
          </button>
        </div>
      </div>
    </div>
  );
};

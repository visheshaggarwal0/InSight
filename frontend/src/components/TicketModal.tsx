import React, { useState } from 'react';
import { X, Copy, Check, FileCheck, CheckCircle2 } from 'lucide-react';
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
          maxWidth: '700px',
          maxHeight: '85vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px',
          borderRadius: '14px',
          background: '#101014',
          border: '1px solid #272730',
          boxShadow: '0 20px 40px rgba(0,0,0,0.8)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '30px', height: '30px', borderRadius: '6px', background: '#1c1c24', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileCheck size={16} color="var(--text-secondary)" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Incident Report &amp; Engineering Ticket
                </h2>
                <span className="badge badge-critical">
                  {ticket.severity}
                </span>
              </div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Structured markdown with cited verbatims ready for Jira or GitHub Issues
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '5px'
            }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Code Box */}
        <div style={{ flex: 1, overflowY: 'auto', margin: '16px 0' }}>
          <pre
            style={{
              background: '#09090c',
              border: '1px solid #1e1e24',
              borderRadius: '8px',
              padding: '16px',
              color: 'var(--text-primary)',
              fontSize: '0.82rem',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            {ticket.ticket_markdown}
          </pre>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <CheckCircle2 size={13} color="var(--color-pos)" />
            <span>Includes 100% verified customer verbatim citations</span>
          </div>

          <button
            onClick={handleCopy}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              background: copied ? 'var(--color-pos)' : '#fafafa',
              color: copied ? '#fff' : '#09090b',
              border: 'none',
              fontWeight: 600,
              fontSize: '0.82rem',
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
          >
            {copied ? <Check size={14} /> : <Copy size={14} />}
            {copied ? 'Copied to Clipboard' : 'Copy Ticket Markdown'}
          </button>
        </div>
      </div>
    </div>
  );
};

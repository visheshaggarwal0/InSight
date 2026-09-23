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
          width: '92%',
          maxWidth: '720px',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          padding: '28px',
          borderRadius: '18px',
          background: '#090d16',
          border: '1px solid rgba(244, 63, 94, 0.35)',
          boxShadow: '0 25px 50px rgba(0,0,0,0.9), 0 0 30px rgba(244, 63, 94, 0.15)'
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '34px', height: '34px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.18)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileCheck size={18} color="#fb7185" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff' }}>
                  Incident Report &amp; Engineering Ticket
                </h2>
                <span className="badge badge-critical">
                  {ticket.severity} SEVERITY
                </span>
              </div>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Structured markdown with cited verbatims ready for Jira, Linear, or Manufacturing QA
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '8px',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Ticket Content Box */}
        <div style={{ flex: 1, overflowY: 'auto', margin: '20px 0' }}>
          <pre
            style={{
              background: '#05070c',
              border: '1px solid #1e293b',
              borderRadius: '10px',
              padding: '18px',
              color: '#cbd5e1',
              fontSize: '0.84rem',
              lineHeight: '1.65',
              whiteSpace: 'pre-wrap',
              fontFamily: "'JetBrains Mono', monospace"
            }}
          >
            {ticket.ticket_markdown}
          </pre>
        </div>

        {/* Actions Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#34d399' }}>
            <CheckCircle2 size={15} />
            <span>Includes 100% verified customer verbatim citations</span>
          </div>

          <button
            onClick={handleCopy}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 20px',
              borderRadius: '8px',
              background: copied ? 'var(--color-pos)' : 'linear-gradient(135deg, #3b82f6, #2563eb)',
              color: '#fff',
              border: 'none',
              fontWeight: 800,
              fontSize: '0.85rem',
              cursor: 'pointer',
              boxShadow: '0 4px 15px rgba(59, 130, 246, 0.35)',
              transition: 'all 0.2s ease'
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

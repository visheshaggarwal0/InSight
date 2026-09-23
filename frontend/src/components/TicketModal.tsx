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
        style={{
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
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', borderBottom: '1px solid #E5E7EB', paddingBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#ECFDF5', color: '#10B981', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <FileCheck size={18} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>
                  Incident Report &amp; Engineering Ticket
                </h2>
                <span style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '999px',
                  backgroundColor: '#FEF2F2',
                  color: '#991B1B',
                  border: '1px solid #FECACA'
                }}>
                  {ticket.severity}
                </span>
              </div>
              <span style={{ fontSize: '0.78rem', color: '#6B7280' }}>
                Structured markdown with cited verbatims ready for Jira or GitHub Issues
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: '#F3F4F6',
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              color: '#6B7280',
              cursor: 'pointer',
              padding: '6px'
            }}
          >
            <X size={16} />
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
            {ticket.ticket_markdown}
          </pre>
        </div>

        {/* Footer */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '14px', borderTop: '1px solid #E5E7EB' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.76rem', color: '#6B7280' }}>
            <CheckCircle2 size={14} style={{ color: '#10B981' }} />
            <span>Includes 100% verified customer verbatim citations</span>
          </div>

          <button
            onClick={handleCopy}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '9px 18px',
              borderRadius: '999px',
              backgroundColor: copied ? '#10B981' : '#0F382E',
              color: '#FFFFFF',
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

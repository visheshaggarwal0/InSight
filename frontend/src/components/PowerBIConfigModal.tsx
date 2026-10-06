import { useState, useEffect } from 'react';
import { X, Check, Sparkles, HelpCircle, AlertCircle } from 'lucide-react';
import type { PowerBIConfig } from '../types/powerbi';

interface PowerBIConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  config: PowerBIConfig | null;
  onSaveConfig: (embedUrl: string, reportTitle: string) => Promise<void>;
}

export function PowerBIConfigModal({
  isOpen,
  onClose,
  config,
  onSaveConfig
}: PowerBIConfigModalProps) {
  const [embedUrl, setEmbedUrl] = useState('');
  const [reportTitle, setReportTitle] = useState('InSight Executive Review Intelligence');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    if (config) {
      setEmbedUrl(config.embed_url || '');
      setReportTitle(config.report_title || 'InSight Executive Review Intelligence');
    }
  }, [config]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaveSuccess(false);

    const trimmedUrl = embedUrl.trim();
    if (trimmedUrl && !trimmedUrl.startsWith('https://')) {
      setError('Embed URL must begin with https:// for secure browser embedding.');
      return;
    }

    try {
      setIsSaving(true);
      await onSaveConfig(trimmedUrl, reportTitle.trim());
      setSaveSuccess(true);
      setTimeout(() => {
        onClose();
        setSaveSuccess(false);
      }, 700);
    } catch (err) {
      setError((err as Error).message || 'Failed to save configuration.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleUseSample = () => {
    if (config?.demo_url) {
      setEmbedUrl(config.demo_url);
      setReportTitle('Microsoft Customer Profitability Sample');
    }
  };

  const handleClear = () => {
    setEmbedUrl('');
    setReportTitle('InSight Executive Review Intelligence');
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="powerbi-modal-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.08)',
          width: '100%',
          maxWidth: '580px',
          overflow: 'hidden',
          border: '1px solid #E5E7EB',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: '#F59E0B',
                color: '#1E293B',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 800,
                fontSize: '0.85rem'
              }}
            >
              BI
            </div>
            <div>
              <h3 id="powerbi-modal-title" style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, fontFamily: "'DM Serif Display', Georgia, serif" }}>
                Power BI Embed Workspace Setup
              </h3>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: '#A7F3D0' }}>
                Embed real-time executive reports directly into InSight
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#A7F3D0',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px'
            }}
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {error && (
            <div
              style={{
                padding: '12px 14px',
                borderRadius: '8px',
                backgroundColor: '#FEF2F2',
                border: '1px solid #FCA5A5',
                color: '#991B1B',
                fontSize: '0.82rem',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label
              htmlFor="report-title-input"
              style={{ display: 'block', fontSize: '0.82rem', fontWeight: 600, color: '#374151', marginBottom: '6px' }}
            >
              Report Title
            </label>
            <input
              id="report-title-input"
              type="text"
              value={reportTitle}
              onChange={(e) => setReportTitle(e.target.value)}
              placeholder="e.g. Executive Sentiment & Defect Analysis"
              style={{
                width: '100%',
                padding: '9px 12px',
                fontSize: '0.88rem',
                borderRadius: '8px',
                border: '1px solid #D1D5DB',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <label
                htmlFor="embed-url-input"
                style={{ fontSize: '0.82rem', fontWeight: 600, color: '#374151' }}
              >
                Power BI Embed URL
              </label>
              <button
                type="button"
                onClick={handleUseSample}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#059669',
                  fontSize: '0.76rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px'
                }}
              >
                <Sparkles size={12} />
                <span>Load Sample Report</span>
              </button>
            </div>
            <input
              id="embed-url-input"
              type="url"
              value={embedUrl}
              onChange={(e) => setEmbedUrl(e.target.value)}
              placeholder="https://app.powerbi.com/reportEmbed?reportId=... or /view?r=..."
              style={{
                width: '100%',
                padding: '9px 12px',
                fontSize: '0.85rem',
                fontFamily: "'JetBrains Mono', monospace",
                borderRadius: '8px',
                border: '1px solid #D1D5DB',
                outline: 'none',
                boxSizing: 'border-box'
              }}
            />
            <p style={{ margin: '6px 0 0 0', fontSize: '0.74rem', color: '#6B7280' }}>
              Leave empty to use the <strong>InSight Native Interactive BI Simulator</strong>.
            </p>
          </div>

          {/* Helper callout */}
          <div
            style={{
              padding: '14px',
              backgroundColor: '#F8FAFC',
              borderRadius: '10px',
              border: '1px solid #E2E8F0',
              fontSize: '0.78rem',
              color: '#475569'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, color: '#1E293B', marginBottom: '6px' }}>
              <HelpCircle size={14} style={{ color: '#059669' }} />
              <span>How to get your Embed URL from Power BI Service:</span>
            </div>
            <ol style={{ margin: '4px 0 0 16px', padding: 0, lineHeight: 1.6 }}>
              <li>Open your report in Power BI Service (<code>app.powerbi.com</code>)</li>
              <li>Click <strong>File</strong> &rarr; <strong>Embed report</strong> &rarr; <strong>Website or portal</strong> (or <strong>Publish to web</strong>)</li>
              <li>Copy the secure URL link and paste it into the field above</li>
            </ol>
          </div>

          {/* Buttons */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
            <button
              type="button"
              onClick={handleClear}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748B',
                fontSize: '0.8rem',
                cursor: 'pointer',
                textDecoration: 'underline'
              }}
            >
              Reset to Native Simulator
            </button>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                type="button"
                onClick={onClose}
                className="btn-outline"
                style={{ padding: '8px 16px', fontSize: '0.84rem' }}
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSaving}
                className="btn-primary"
                style={{
                  padding: '8px 20px',
                  fontSize: '0.84rem',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {saveSuccess ? (
                  <>
                    <Check size={16} />
                    <span>Saved!</span>
                  </>
                ) : isSaving ? (
                  'Saving…'
                ) : (
                  'Save & Apply'
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

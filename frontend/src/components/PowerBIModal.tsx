import React, { useState } from 'react';
import {
  X,
  Download,
  Copy,
  Check,
  BarChart3,
  FileSpreadsheet,
  FileCode,
  Package,
  Layers,
  HelpCircle,
  TrendingUp,
  ShieldCheck
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

interface PowerBIModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeDomain: string;
}

type TabType = 'overview' | 'live_feed' | 'dax' | 'guide';

export const PowerBIModal: React.FC<PowerBIModalProps> = ({
  isOpen,
  onClose,
  activeDomain
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [copiedUrl, setCopiedUrl] = useState(false);
  const [copiedM, setCopiedM] = useState(false);
  const [copiedDax, setCopiedDax] = useState(false);
  const [downloadingZip, setDownloadingZip] = useState(false);
  const [downloadingCsv, setDownloadingCsv] = useState(false);
  const [downloadingPbids, setDownloadingPbids] = useState(false);

  // Keyboard navigation: Escape closes modal
  React.useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const currentDomain = activeDomain || 'd2c_cosmetics';
  const feedUrl = `${API_BASE}/export/powerbi?domain=${currentDomain}`;
  const pbidsUrl = `${API_BASE}/export/powerbi/pbids?domain=${currentDomain}`;
  const bundleUrl = `${API_BASE}/export/powerbi/bundle?domain=${currentDomain}`;

  const mCodeSnippet = `// ==============================================================================
// InSight AI - Power Query (M) Script for Power BI Desktop
// Paste into Power BI Desktop: Home Ribbon -> Get Data -> Blank Query -> Advanced Editor
// ==============================================================================
let
    Source = Csv.Document(Web.Contents("${feedUrl}"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers",{
        {"Review_ID", type text},
        {"Domain", type text},
        {"Product_Name", type text},
        {"SKU_or_Module", type text},
        {"Batch_or_Version", type text},
        {"Submission_Date", type date},
        {"Channel", type text},
        {"Rating", Int64.Type},
        {"Calibrated_Sentiment", type text},
        {"Sentiment_Confidence", type number},
        {"Theme_Title", type text},
        {"Cluster_ID", Int64.Type},
        {"Sentence_Count", Int64.Type},
        {"Complaint_Clauses", Int64.Type},
        {"Praise_Clauses", Int64.Type},
        {"Recommendation_Clauses", Int64.Type},
        {"Is_Actionable", type logical},
        {"Has_Silent_Defect", type logical},
        {"Is_PII_Scrubbed", type logical},
        {"PII_Entities_Detected", type text},
        {"Sanitized_Verbatim", type text},
        {"Defect_Clause", type text}
    })
in
    #"Changed Type"`;

  const daxSnippet = `// ==============================================================================
// InSight AI - Curated Power BI DAX Measures Reference
// Create these as New Measures on your 'Telemetry' table in Power BI Desktop
// ==============================================================================

// 1. Silent Defect Rate: % of 4★ and 5★ reviews harboring hidden complaints
Silent Defect Rate = 
DIVIDE(
    CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Rating] >= 4, 'Telemetry'[Has_Silent_Defect] = TRUE()),
    CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Rating] >= 4),
    0
)

// 2. Actionable Feedback Volume: Reviews with extracted bugs, praises, or features
Actionable Reviews = 
CALCULATE(
    COUNTROWS('Telemetry'),
    'Telemetry'[Is_Actionable] = TRUE()
)

// 3. Actionability Index: % of feedback providing concrete engineering/product signals
Actionability Index = 
DIVIDE(
    [Actionable Reviews],
    COUNTROWS('Telemetry'),
    0
)

// 4. Net Sentiment Score (NSS) [-100 to +100]
Net Sentiment Score = 
VAR PosCount = CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Calibrated_Sentiment] = "POSITIVE")
VAR NegCount = CALCULATE(COUNTROWS('Telemetry'), 'Telemetry'[Calibrated_Sentiment] = "NEGATIVE")
VAR TotalReviews = COUNTROWS('Telemetry')
RETURN
DIVIDE(PosCount - NegCount, TotalReviews, 0) * 100

// 5. Total Complaint Clauses Discovered
Total Complaints = 
SUM('Telemetry'[Complaint_Clauses])`;

  const handleCopyUrl = async () => {
    try {
      await navigator.clipboard.writeText(feedUrl);
      setCopiedUrl(true);
      setTimeout(() => setCopiedUrl(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const handleCopyM = async () => {
    try {
      await navigator.clipboard.writeText(mCodeSnippet);
      setCopiedM(true);
      setTimeout(() => setCopiedM(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const handleCopyDax = async () => {
    try {
      await navigator.clipboard.writeText(daxSnippet);
      setCopiedDax(true);
      setTimeout(() => setCopiedDax(false), 2000);
    } catch {
      /* ignore */
    }
  };

  const downloadFile = async (url: string, filename: string, setLoading: (s: boolean) => void) => {
    setLoading(true);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const objUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objUrl);
    } catch (err) {
      console.error('Download failed:', err);
      alert(`Download failed: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="overlay-backdrop"
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
        role="dialog"
        aria-modal="true"
        aria-labelledby="powerbi-modal-title"
        style={{
          width: '100%',
          maxWidth: '880px',
          maxHeight: '92vh',
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
          border: '1px solid #E5E7EB',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeInScale 0.18s ease-out'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            backgroundColor: '#FFFBEB',
            borderBottom: '1px solid #FDE68A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div
              style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                backgroundColor: '#F59E0B',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                boxShadow: '0 4px 10px rgba(245, 158, 11, 0.35)'
              }}
            >
              <BarChart3 size={24} />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2
                  id="powerbi-modal-title"
                  style={{
                    margin: 0,
                    fontSize: '1.25rem',
                    fontWeight: 700,
                    color: '#92400E',
                    letterSpacing: '-0.01em'
                  }}
                >
                  Microsoft Power BI Integration Studio
                </h2>
                <span
                  style={{
                    fontSize: '0.72rem',
                    backgroundColor: '#FEF3C7',
                    border: '1px solid #FDE68A',
                    color: '#B45309',
                    padding: '2px 8px',
                    borderRadius: '999px',
                    fontWeight: 700,
                    textTransform: 'uppercase'
                  }}
                >
                  Enterprise Star-Schema
                </span>
              </div>
              <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#B45309' }}>
                Active Domain: <b style={{ textTransform: 'capitalize' }}>{currentDomain.replace(/_/g, ' ')}</b> &bull; Live OData/REST endpoints, Power Query ETL, and executive DAX metrics.
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            aria-label="Close dialog"
            style={{
              background: '#FEF3C7',
              border: '1px solid #FDE68A',
              color: '#92400E',
              cursor: 'pointer',
              padding: '8px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.15s ease'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            borderBottom: '1px solid #E5E7EB',
            backgroundColor: '#F9FAFB',
            padding: '0 24px',
            gap: '8px'
          }}
        >
          {[
            { id: 'overview', label: '1-Click Downloads & Overview', icon: Package },
            { id: 'live_feed', label: 'Live Power Query (M) Script', icon: FileCode },
            { id: 'dax', label: 'Curated DAX Measures', icon: TrendingUp },
            { id: 'guide', label: 'Dashboard Blueprint & Setup', icon: HelpCircle }
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id as TabType)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '12px 14px',
                  fontSize: '0.82rem',
                  fontWeight: isActive ? 700 : 500,
                  color: isActive ? '#D97706' : '#6B7280',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #D97706' : '2px solid transparent',
                  backgroundColor: 'transparent',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={16} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Tab Content Body */}
        <div
          style={{
            padding: '24px',
            overflowY: 'auto',
            flex: '1 1 auto',
            backgroundColor: '#FFFFFF'
          }}
        >
          {/* TAB 1: OVERVIEW & ONE-CLICK DOWNLOADS */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div
                style={{
                  backgroundColor: '#F0FDF4',
                  border: '1px solid #BBF7D0',
                  borderRadius: '12px',
                  padding: '16px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}
              >
                <ShieldCheck size={22} style={{ color: '#16A34A', flexShrink: 0, marginTop: '2px' }} />
                <div>
                  <h4 style={{ margin: '0 0 4px 0', fontSize: '0.92rem', color: '#166534', fontWeight: 700 }}>
                    Enterprise Compliance & PII Safety Guaranteed
                  </h4>
                  <p style={{ margin: 0, fontSize: '0.82rem', color: '#15803D', lineHeight: 1.45 }}>
                    All exported datasets and feeds contain strictly scrubbed, anonymized customer verbatims.
                    Extracted linguistic defect clauses and c-TF-IDF keyword tags are pre-calculated for immediate slicing in Power BI Desktop.
                  </p>
                </div>
              </div>

              {/* Download Action Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
                {/* 1. Complete Kit (.zip) */}
                <div
                  style={{
                    border: '2px solid #F59E0B',
                    borderRadius: '12px',
                    padding: '18px',
                    backgroundColor: '#FFFBEB',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    position: 'relative'
                  }}
                >
                  <span
                    style={{
                      position: 'absolute',
                      top: '-10px',
                      right: '16px',
                      backgroundColor: '#D97706',
                      color: '#FFFFFF',
                      fontSize: '0.66rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '999px',
                      textTransform: 'uppercase'
                    }}
                  >
                    Recommended
                  </span>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <Package size={20} style={{ color: '#D97706' }} />
                      <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700, color: '#92400E' }}>
                        Complete Power BI Kit (.zip)
                      </h3>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#B45309', lineHeight: 1.4 }}>
                      All-in-one bundle containing the full CSV dataset, <code>.pbids</code> connector, Power Query (M) ETL script, DAX measures reference, and setup manual.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void downloadFile(bundleUrl, `insight_${currentDomain}_powerbi_kit.zip`, setDownloadingZip)}
                    disabled={downloadingZip}
                    style={{
                      marginTop: '16px',
                      padding: '10px 16px',
                      backgroundColor: '#D97706',
                      color: '#FFFFFF',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '0.84rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: downloadingZip ? 'wait' : 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <Download size={16} />
                    <span>{downloadingZip ? 'Generating Bundle…' : 'Download Complete Kit (.zip)'}</span>
                  </button>
                </div>

                {/* 2. Official .PBIDS Connector */}
                <div
                  style={{
                    border: '1px solid #E5E7EB',
                    borderRadius: '12px',
                    padding: '18px',
                    backgroundColor: '#FFFFFF',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <FileCode size={20} style={{ color: '#2563EB' }} />
                      <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700, color: '#1E3A8A' }}>
                        Direct Data Source (.pbids)
                      </h3>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#4B5563', lineHeight: 1.4 }}>
                      Official Microsoft Power BI Data Source file. Double-click in Windows to automatically launch Power BI Desktop with the InSight connection pre-loaded.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void downloadFile(pbidsUrl, `insight_${currentDomain}_connector.pbids`, setDownloadingPbids)}
                    disabled={downloadingPbids}
                    style={{
                      marginTop: '16px',
                      padding: '10px 16px',
                      backgroundColor: '#EFF6FF',
                      color: '#1D4ED8',
                      border: '1px solid #BFDBFE',
                      borderRadius: '8px',
                      fontSize: '0.84rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: downloadingPbids ? 'wait' : 'pointer'
                    }}
                  >
                    <Download size={16} />
                    <span>{downloadingPbids ? 'Preparing…' : 'Download Connector (.pbids)'}</span>
                  </button>
                </div>

                {/* 3. CSV Dataset Export */}
                <div
                  style={{
                    border: '1px solid #E5E7EB',
                    borderRadius: '12px',
                    padding: '18px',
                    backgroundColor: '#FFFFFF',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <FileSpreadsheet size={20} style={{ color: '#059669' }} />
                      <h3 style={{ margin: 0, fontSize: '0.98rem', fontWeight: 700, color: '#065F46' }}>
                        Relational Telemetry (.csv)
                      </h3>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.78rem', color: '#4B5563', lineHeight: 1.4 }}>
                      Flat, denormalized 22-column table with customer ratings, sentiment classes, defect spans, cluster IDs, and batch/version tags.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void downloadFile(feedUrl, `insight_${currentDomain}_telemetry.csv`, setDownloadingCsv)}
                    disabled={downloadingCsv}
                    style={{
                      marginTop: '16px',
                      padding: '10px 16px',
                      backgroundColor: '#ECFDF5',
                      color: '#047857',
                      border: '1px solid #A7F3D0',
                      borderRadius: '8px',
                      fontSize: '0.84rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '8px',
                      cursor: downloadingCsv ? 'wait' : 'pointer'
                    }}
                  >
                    <Download size={16} />
                    <span>{downloadingCsv ? 'Streaming…' : 'Download Dataset (.csv)'}</span>
                  </button>
                </div>
              </div>

              {/* Data Schema Specs */}
              <div style={{ marginTop: '10px', border: '1px solid #E5E7EB', borderRadius: '12px', padding: '16px' }}>
                <h4 style={{ margin: '0 0 10px 0', fontSize: '0.88rem', fontWeight: 700, color: '#374151', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Layers size={16} style={{ color: '#6B7280' }} />
                  Included Telemetry Dimensions & Fact Columns (22 Fields)
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {[
                    'Review_ID', 'Domain', 'Product_Name', 'SKU_or_Module', 'Batch_or_Version',
                    'Submission_Date', 'Channel', 'Rating (1-5★)', 'Calibrated_Sentiment',
                    'Sentiment_Confidence', 'Theme_Title', 'Cluster_ID', 'Sentence_Count',
                    'Complaint_Clauses', 'Praise_Clauses', 'Recommendation_Clauses',
                    'Is_Actionable', 'Has_Silent_Defect', 'Is_PII_Scrubbed',
                    'PII_Entities_Detected', 'Sanitized_Verbatim', 'Defect_Clause'
                  ].map((col) => (
                    <span
                      key={col}
                      style={{
                        fontSize: '0.72rem',
                        backgroundColor: '#F3F4F6',
                        color: '#374151',
                        padding: '3px 8px',
                        borderRadius: '6px',
                        fontFamily: "'JetBrains Mono', monospace",
                        border: '1px solid #E5E7EB'
                      }}
                    >
                      {col}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LIVE WEB FEED & M SCRIPT */}
          {activeTab === 'live_feed' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 700, color: '#374151', marginBottom: '6px' }}>
                  Live Web Feed URL (Power BI Web Connector / OData)
                </label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    readOnly
                    value={feedUrl}
                    style={{
                      flex: 1,
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid #D1D5DB',
                      backgroundColor: '#F9FAFB',
                      fontSize: '0.82rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#111827'
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => void handleCopyUrl()}
                    style={{
                      padding: '10px 16px',
                      backgroundColor: copiedUrl ? '#10B981' : '#F3F4F6',
                      color: copiedUrl ? '#FFFFFF' : '#374151',
                      border: '1px solid #D1D5DB',
                      borderRadius: '8px',
                      fontSize: '0.82rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {copiedUrl ? <Check size={16} /> : <Copy size={16} />}
                    <span>{copiedUrl ? 'Copied URL!' : 'Copy Feed URL'}</span>
                  </button>
                </div>
              </div>

              <div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', fontWeight: 700, color: '#374151' }}>
                      Power Query (M) Script for Power BI Desktop
                    </label>
                    <span style={{ fontSize: '0.74rem', color: '#6B7280', display: 'block' }}>
                      Paste this into <b>Home &rarr; Transform Data &rarr; Advanced Editor</b> to auto-configure types, dates, and headers.
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => void handleCopyM()}
                    style={{
                      padding: '6px 12px',
                      backgroundColor: copiedM ? '#10B981' : '#FFFBEB',
                      color: copiedM ? '#FFFFFF' : '#92400E',
                      border: '1px solid #FDE68A',
                      borderRadius: '6px',
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {copiedM ? <Check size={14} /> : <Copy size={14} />}
                    <span>{copiedM ? 'Copied M Code!' : 'Copy Script'}</span>
                  </button>
                </div>

                <pre
                  style={{
                    backgroundColor: '#1E293B',
                    color: '#F8FAFC',
                    padding: '16px',
                    borderRadius: '10px',
                    fontSize: '0.78rem',
                    lineHeight: '1.45',
                    fontFamily: "'JetBrains Mono', monospace",
                    overflowX: 'auto',
                    margin: 0
                  }}
                >
                  {mCodeSnippet}
                </pre>
              </div>
            </div>
          )}

          {/* TAB 3: CURATED DAX MEASURES */}
          {activeTab === 'dax' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ margin: '0 0 4px 0', fontSize: '0.98rem', fontWeight: 700, color: '#111827' }}>
                    Executive DAX Formulas for Power BI
                  </h3>
                  <p style={{ margin: 0, fontSize: '0.8rem', color: '#6B7280' }}>
                    Copy and paste these measures into your Power BI Desktop model to instantly build KPI cards and severity ratios.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => void handleCopyDax()}
                  style={{
                    padding: '8px 14px',
                    backgroundColor: copiedDax ? '#10B981' : '#FFFBEB',
                    color: copiedDax ? '#FFFFFF' : '#92400E',
                    border: '1px solid #FDE68A',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    cursor: 'pointer'
                  }}
                >
                  {copiedDax ? <Check size={14} /> : <Copy size={14} />}
                  <span>{copiedDax ? 'Copied All Measures!' : 'Copy DAX Formulas'}</span>
                </button>
              </div>

              <pre
                style={{
                  backgroundColor: '#0F172A',
                  color: '#38BDF8',
                  padding: '18px',
                  borderRadius: '10px',
                  fontSize: '0.78rem',
                  lineHeight: '1.5',
                  fontFamily: "'JetBrains Mono', monospace",
                  overflowX: 'auto',
                  margin: 0
                }}
              >
                {daxSnippet}
              </pre>
            </div>
          )}

          {/* TAB 4: SETUP GUIDE & DASHBOARD BLUEPRINT */}
          {activeTab === 'guide' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '1rem', fontWeight: 700, color: '#111827' }}>
                  Step-by-Step Power BI Setup
                </h3>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        backgroundColor: '#FEF3C7',
                        color: '#92400E',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      1
                    </div>
                    <div>
                      <h5 style={{ margin: '0 0 2px 0', fontSize: '0.86rem', fontWeight: 700, color: '#1F2937' }}>
                        Import via Connector or Web Feed
                      </h5>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#4B5563' }}>
                        Double click <code>insight_{currentDomain}_connector.pbids</code> to launch Power BI Desktop.
                        Alternatively, open Power BI &rarr; <b>Get Data &rarr; Web</b> and paste the feed URL.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        backgroundColor: '#FEF3C7',
                        color: '#92400E',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      2
                    </div>
                    <div>
                      <h5 style={{ margin: '0 0 2px 0', fontSize: '0.86rem', fontWeight: 700, color: '#1F2937' }}>
                        Apply Power Query Advanced M Script
                      </h5>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#4B5563' }}>
                        Open <b>Transform Data &rarr; Advanced Editor</b> and paste our pre-built M query script to automatically format columns into integer ratings, boolean defect flags, and date hierarchies.
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '26px',
                        height: '26px',
                        borderRadius: '50%',
                        backgroundColor: '#FEF3C7',
                        color: '#92400E',
                        fontWeight: 700,
                        fontSize: '0.82rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0
                      }}
                    >
                      3
                    </div>
                    <div>
                      <h5 style={{ margin: '0 0 2px 0', fontSize: '0.86rem', fontWeight: 700, color: '#1F2937' }}>
                        Create Recommended Dashboard Layout
                      </h5>
                      <p style={{ margin: 0, fontSize: '0.8rem', color: '#4B5563' }}>
                        Add our curated DAX measures to configure executive cards:
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommended Visualizations Grid */}
              <div
                style={{
                  border: '1px solid #E5E7EB',
                  borderRadius: '12px',
                  padding: '16px',
                  backgroundColor: '#F9FAFB'
                }}
              >
                <h4 style={{ margin: '0 0 12px 0', fontSize: '0.9rem', fontWeight: 700, color: '#111827' }}>
                  Recommended Visual Layout Blueprint
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
                  <div style={{ backgroundColor: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#D97706', marginBottom: '4px' }}>
                      Row 1: Executive KPI Cards
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#4B5563' }}>
                      &bull; <code>Net Sentiment Score (NSS)</code><br />
                      &bull; <code>Silent Defect Rate (%)</code><br />
                      &bull; <code>Actionability Index (%)</code>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#2563EB', marginBottom: '4px' }}>
                      Row 2: Root Cause Decomposition
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#4B5563' }}>
                      Decomposition Tree: <b>Domain &rarr; Product_Name &rarr; Theme_Title &rarr; Complaint_Clauses</b>
                    </div>
                  </div>

                  <div style={{ backgroundColor: '#FFFFFF', padding: '12px', borderRadius: '8px', border: '1px solid #E5E7EB' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#059669', marginBottom: '4px' }}>
                      Row 3: Quality Drift Over Batches
                    </div>
                    <div style={{ fontSize: '0.74rem', color: '#4B5563' }}>
                      Ribbon or 100% Stacked Column: <b>Batch_or_Version vs Calibrated_Sentiment</b> to detect defect spikes.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '14px 24px',
            backgroundColor: '#F9FAFB',
            borderTop: '1px solid #E5E7EB',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.76rem', color: '#6B7280' }}>
            <span>Need live real-time refresh?</span>
            <span style={{ color: '#059669', fontWeight: 600 }}>InSight API streams updates automatically</span>
          </div>

          <button
            type="button"
            onClick={onClose}
            style={{
              padding: '8px 20px',
              backgroundColor: '#111827',
              color: '#FFFFFF',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

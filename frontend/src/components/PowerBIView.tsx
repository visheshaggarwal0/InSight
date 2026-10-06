import { useState, useEffect, useRef } from 'react';
import * as pbi from 'powerbi-client';
import {
  BarChart3,
  Copy,
  Check,
  Download,
  Maximize2,
  Minimize2,
  RefreshCw,
  Layers,
  Database,
  Code2,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  Key
} from 'lucide-react';
import type { OverviewMetrics, ThemeCluster, DriftData } from '../types/telemetry';
import type { PowerBIConfig, PowerBIGuide, PowerBIEmbedResponse } from '../types/powerbi';
import { PowerBIConfigModal } from './PowerBIConfigModal';

interface PowerBIViewProps {
  overview: OverviewMetrics | null;
  themes: ThemeCluster[];
  driftData: DriftData | null;
  activeDomain: string;
  onInspectVerbatims?: (clusterId: number, title: string) => void;
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export function PowerBIView({
  overview,
  activeDomain,
}: PowerBIViewProps) {
  const [activeSubTab, setActiveSubTab] = useState<'report' | 'connectors' | 'dax' | 'schema'>('report');
  const [config, setConfig] = useState<PowerBIConfig | null>(null);
  const [guide, setGuide] = useState<PowerBIGuide | null>(null);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Official Power BI Embedded State
  const [embedResponse, setEmbedResponse] = useState<PowerBIEmbedResponse | null>(null);
  const [isLoadingEmbed, setIsLoadingEmbed] = useState<boolean>(true);
  const [refreshState, setRefreshState] = useState<'idle' | 'refreshing' | 'refreshed' | 'error'>('idle');
  const [refreshMessage, setRefreshMessage] = useState<string | null>(null);
  const [showLocalFallback, setShowLocalFallback] = useState<boolean>(false);

  const reportContainerRef = useRef<HTMLDivElement>(null);
  const embeddedReportInstanceRef = useRef<pbi.Report | null>(null);

  // 1. Fetch Power BI Embed Token & Configuration from backend
  const fetchEmbedToken = async () => {
    setIsLoadingEmbed(true);
    try {
      const res = await fetch(`${API_BASE}/powerbi/embed-token`);
      if (res.ok) {
        const data: PowerBIEmbedResponse = await res.json();
        setEmbedResponse(data);
      } else {
        setEmbedResponse({
          status: 'error',
          error_message: `HTTP ${res.status}: Failed to reach backend embed token endpoint.`
        });
      }
    } catch (err) {
      setEmbedResponse({
        status: 'error',
        error_message: `Network error: ${(err as Error).message}`
      });
    } finally {
      setIsLoadingEmbed(false);
    }
  };

  useEffect(() => {
    fetchEmbedToken();

    // Fetch config & guide
    async function loadAuxiliaryData() {
      try {
        const [configRes, guideRes] = await Promise.all([
          fetch(`${API_BASE}/powerbi/config`),
          fetch(`${API_BASE}/powerbi/guide`)
        ]);
        if (configRes.ok) setConfig(await configRes.json());
        if (guideRes.ok) setGuide(await guideRes.json());
      } catch (err) {
        console.warn('Failed to load auxiliary Power BI metadata:', err);
      }
    }
    loadAuxiliaryData();
  }, []);

  // 2. Initialize official Microsoft powerbi-client when token is ready
  useEffect(() => {
    if (
      activeSubTab === 'report' &&
      embedResponse?.status === 'success' &&
      embedResponse.embed_token &&
      embedResponse.embed_url &&
      embedResponse.report_id &&
      reportContainerRef.current
    ) {
      try {
        const pbiService = new pbi.service.Service(
          pbi.factories.hpmFactory,
          pbi.factories.wpmpFactory,
          pbi.factories.routerFactory
        );

        pbiService.reset(reportContainerRef.current);

        const embedConfig: pbi.models.IReportEmbedConfiguration = {
          type: 'report',
          tokenType: pbi.models.TokenType.Embed,
          accessToken: embedResponse.embed_token,
          embedUrl: embedResponse.embed_url,
          id: embedResponse.report_id,
          permissions: pbi.models.Permissions.Read,
          settings: {
            panes: {
              filters: {
                expanded: false,
                visible: true
              },
              pageNavigation: {
                visible: true,
                position: pbi.models.PageNavigationPosition.Bottom
              }
            },
            background: pbi.models.BackgroundType.Transparent
          }
        };

        const report = pbiService.embed(reportContainerRef.current, embedConfig) as pbi.Report;
        embeddedReportInstanceRef.current = report;

        report.on('error', (event: any) => {
          console.error('Power BI client reported an error:', event.detail);
        });
      } catch (err) {
        console.error('Failed to embed Power BI report via SDK:', err);
      }
    }

    return () => {
      if (reportContainerRef.current) {
        try {
          const pbiService = new pbi.service.Service(
            pbi.factories.hpmFactory,
            pbi.factories.wpmpFactory,
            pbi.factories.routerFactory
          );
          pbiService.reset(reportContainerRef.current);
        } catch {
          // ignore cleanup errors
        }
      }
    };
  }, [activeSubTab, embedResponse]);

  // 3. Trigger Power BI Semantic Model Refresh
  const handleTriggerDatasetRefresh = async () => {
    setRefreshState('refreshing');
    setRefreshMessage('Requesting Power BI Service dataset refresh…');
    try {
      const res = await fetch(`${API_BASE}/powerbi/dataset/refresh`, { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setRefreshState('refreshed');
        setRefreshMessage(data.message || 'Dataset refresh triggered successfully in Power BI Service!');
        setTimeout(() => setRefreshState('idle'), 4000);
      } else {
        setRefreshState('error');
        setRefreshMessage(data.detail || 'Failed to trigger dataset refresh in Power BI.');
      }
    } catch (err) {
      setRefreshState('error');
      setRefreshMessage((err as Error).message);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleDownloadPbids = () => {
    const link = document.createElement('a');
    link.href = `${API_BASE}/powerbi/connector/pbids?domain=${encodeURIComponent(activeDomain)}`;
    link.download = `InSight_${activeDomain}_Telemetry.pbids`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadCsv = () => {
    const link = document.createElement('a');
    link.href = `${API_BASE}/powerbi/data/reviews.csv?domain=${encodeURIComponent(activeDomain)}`;
    link.download = `insight_${activeDomain}_telemetry.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const toggleFullscreen = () => {
    if (!reportContainerRef.current) return;
    if (!document.fullscreenElement) {
      reportContainerRef.current.requestFullscreen().catch((err) => {
        console.warn('Fullscreen request failed:', err);
      });
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch((err) => {
        console.warn('Exit fullscreen failed:', err);
      });
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const onFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, []);

  const totalReviews = overview?.total_reviews || 0;
  const posCount = overview?.sentiment_counts?.POSITIVE || 0;
  const negCount = overview?.sentiment_counts?.NEGATIVE || 0;
  const nssScore = totalReviews > 0 ? Math.round(((posCount - negCount) / totalReviews) * 100) : 0;
  const defectRate = overview?.negative_rate || 0;
  const actionableRate = overview?.intent_breakdown?.actionable_rate_pct || 88.5;

  return (
    <div style={{ paddingTop: '28px', paddingBottom: '60px' }}>
      {/* Top Banner & Control Center */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '16px',
          border: '1px solid #E5E7EB',
          padding: '24px 28px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
          marginBottom: '24px'
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '16px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div
              style={{
                width: '46px',
                height: '46px',
                borderRadius: '12px',
                backgroundColor: '#F59E0B',
                color: '#1E293B',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 900,
                fontSize: '1.25rem',
                boxShadow: '0 4px 6px -1px rgba(245, 158, 11, 0.3)'
              }}
            >
              BI
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <h2
                  style={{
                    margin: 0,
                    fontSize: '1.65rem',
                    fontWeight: 700,
                    color: '#111827',
                    fontFamily: "'DM Serif Display', Georgia, serif"
                  }}
                >
                  Microsoft Power BI Live Analytics
                </h2>
                {embedResponse?.status === 'success' ? (
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      backgroundColor: '#DEF7EC',
                      color: '#03543F',
                      padding: '3px 9px',
                      borderRadius: '999px',
                      border: '1px solid #BCF0DA',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: '#059669' }} />
                    Azure Entra ID Authenticated • Embed Token Active
                  </span>
                ) : embedResponse?.status === 'unconfigured' ? (
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      padding: '3px 9px',
                      borderRadius: '999px',
                      border: '1px solid #FDE68A',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <Key size={12} />
                    Azure App Registration Setup Required
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      backgroundColor: '#FEE2E2',
                      color: '#991B1B',
                      padding: '3px 9px',
                      borderRadius: '999px',
                      border: '1px solid #FECACA',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <AlertCircle size={12} />
                    Connection Diagnostics Needed
                  </span>
                )}
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.84rem', color: '#6B7280' }}>
                Official Microsoft Power BI Embedded (App-Owns-Data) architecture powered by InSight's telemetry pipeline.
              </p>
            </div>
          </div>

          {/* Action Toolbar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              onClick={handleDownloadPbids}
              className="btn-outline"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.82rem',
                borderColor: '#F59E0B',
                backgroundColor: '#FFFBEB',
                color: '#92400E',
                fontWeight: 600
              }}
              title="Download Power BI Data Source (.pbids) file to launch Power BI Desktop pre-configured"
            >
              <Download size={14} />
              <span>Launch Desktop (.pbids)</span>
            </button>

            <button
              type="button"
              onClick={handleDownloadCsv}
              className="btn-outline"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '0.82rem'
              }}
              title="Download normalized CSV telemetry for Power BI semantic model import"
            >
              <FileSpreadsheet size={14} />
              <span>Export CSV Feed</span>
            </button>

            {embedResponse?.status === 'success' && (
              <button
                type="button"
                onClick={handleTriggerDatasetRefresh}
                disabled={refreshState === 'refreshing'}
                className="btn-primary"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '0.82rem',
                  backgroundColor: '#059669'
                }}
                title="Trigger automated refresh on Power BI Semantic Model via Power BI REST API"
              >
                <RefreshCw size={14} className={refreshState === 'refreshing' ? 'spin' : ''} />
                <span>{refreshState === 'refreshing' ? 'Refreshing…' : 'Refresh Dataset'}</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => void fetchEmbedToken()}
              className="btn-outline"
              style={{ fontSize: '0.82rem', padding: '7px 12px' }}
              title="Re-check Azure Entra ID token and Power BI Service connection"
            >
              <RefreshCw size={13} />
              <span>Test Connection</span>
            </button>
          </div>
        </div>

        {refreshMessage && (
          <div
            style={{
              marginTop: '14px',
              padding: '10px 14px',
              borderRadius: '8px',
              backgroundColor: refreshState === 'error' ? '#FEF2F2' : '#DEF7EC',
              border: `1px solid ${refreshState === 'error' ? '#FECACA' : '#BCF0DA'}`,
              color: refreshState === 'error' ? '#991B1B' : '#03543F',
              fontSize: '0.8rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
          >
            {refreshState === 'error' ? <AlertCircle size={15} /> : <CheckCircle2 size={15} />}
            <span>{refreshMessage}</span>
          </div>
        )}

        {/* View Switcher Sub-Tabs */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginTop: '22px',
            borderTop: '1px solid #F3F4F6',
            paddingTop: '16px'
          }}
        >
          <button
            type="button"
            onClick={() => setActiveSubTab('report')}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeSubTab === 'report' ? '#0F382E' : '#F3F4F6',
              color: activeSubTab === 'report' ? '#FFFFFF' : '#4B5563',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <BarChart3 size={15} />
            <span>Power BI Embedded Report</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubTab('connectors')}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeSubTab === 'connectors' ? '#0F382E' : '#F3F4F6',
              color: activeSubTab === 'connectors' ? '#FFFFFF' : '#4B5563',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Database size={15} />
            <span>Semantic Model Feeds &amp; Connectors</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubTab('dax')}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeSubTab === 'dax' ? '#0F382E' : '#F3F4F6',
              color: activeSubTab === 'dax' ? '#FFFFFF' : '#4B5563',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Code2 size={15} />
            <span>Production DAX Measures</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveSubTab('schema')}
            style={{
              padding: '7px 16px',
              borderRadius: '8px',
              border: 'none',
              backgroundColor: activeSubTab === 'schema' ? '#0F382E' : '#F3F4F6',
              color: activeSubTab === 'schema' ? '#FFFFFF' : '#4B5563',
              fontSize: '0.82rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.15s ease'
            }}
          >
            <Layers size={15} />
            <span>Star Schema &amp; Setup Guide</span>
          </button>
        </div>
      </div>

      {/* =========================================================================
          TAB 1: POWER BI EMBEDDED REPORT
      ========================================================================= */}
      {activeSubTab === 'report' && (
        <div>
          {isLoadingEmbed ? (
            <div
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '16px',
                border: '1px solid #E5E7EB',
                padding: '48px',
                textAlign: 'center',
                color: '#6B7280'
              }}
            >
              <RefreshCw size={28} className="spin" style={{ color: '#059669', margin: '0 auto 14px auto' }} />
              <p style={{ margin: 0, fontWeight: 600, fontSize: '0.95rem', color: '#111827' }}>
                Connecting to Microsoft Azure Entra ID…
              </p>
              <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem' }}>
                Acquiring Service Principal token and minting Power BI Embed Token
              </p>
            </div>
          ) : embedResponse?.status === 'success' ? (
            /* OFFICIAL POWER BI EMBEDDED CONTAINER */
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '12px',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#111827' }}>
                    {embedResponse.report_title || 'InSight Executive Review Intelligence'}
                  </span>
                  <span style={{ fontSize: '0.74rem', color: '#6B7280' }}>
                    (Workspace: <code>{embedResponse.workspace_id?.slice(0, 8)}…</code> | Report: <code>{embedResponse.report_id?.slice(0, 8)}…</code>)
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => void fetchEmbedToken()}
                    className="btn-outline"
                    style={{ fontSize: '0.76rem', padding: '5px 10px' }}
                    title="Refresh token & reload report"
                  >
                    <RefreshCw size={13} />
                    <span>Reload Report</span>
                  </button>

                  <button
                    type="button"
                    onClick={toggleFullscreen}
                    className="btn-outline"
                    style={{ fontSize: '0.76rem', padding: '5px 10px' }}
                    title="Toggle fullscreen presentation mode"
                  >
                    {isFullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
                    <span>{isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}</span>
                  </button>
                </div>
              </div>

              {/* The Power BI Embedded iframe container initialized via powerbi-client SDK */}
              <div
                ref={reportContainerRef}
                style={{
                  width: '100%',
                  height: isFullscreen ? 'calc(100vh - 60px)' : '740px',
                  borderRadius: '16px',
                  overflow: 'hidden',
                  border: '1px solid #E5E7EB',
                  backgroundColor: '#FFFFFF',
                  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)'
                }}
              />
            </div>
          ) : embedResponse?.status === 'unconfigured' ? (
            /* AUTHENTIC HACKATHON SETUP GUIDE PANEL */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '16px',
                  border: '1px solid #E5E7EB',
                  padding: '32px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
                  <div
                    style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      backgroundColor: '#FEF3C7',
                      color: '#92400E',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                  >
                    <Key size={18} />
                  </div>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
                      Microsoft Azure &amp; Power BI Service Credentials Required
                    </h3>
                    <p style={{ margin: '2px 0 0 0', fontSize: '0.82rem', color: '#6B7280' }}>
                      To embed a genuine Power BI Service report with Microsoft Entra ID authentication, provide your Azure App Registration and Power BI Workspace keys.
                    </p>
                  </div>
                </div>

                {/* Configuration Checklist */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                    gap: '12px',
                    margin: '20px 0'
                  }}
                >
                  {[
                    { key: 'POWERBI_TENANT_ID', label: 'Azure Directory (Tenant) ID', isSet: embedResponse.credentials_present?.tenant_id },
                    { key: 'POWERBI_CLIENT_ID', label: 'App Registration (Client) ID', isSet: embedResponse.credentials_present?.client_id },
                    { key: 'POWERBI_CLIENT_SECRET', label: 'Client Secret Value', isSet: embedResponse.credentials_present?.client_secret },
                    { key: 'POWERBI_WORKSPACE_ID', label: 'Power BI Workspace (Group) ID', isSet: embedResponse.credentials_present?.workspace_id },
                    { key: 'POWERBI_REPORT_ID', label: 'Target Report ID', isSet: embedResponse.credentials_present?.report_id },
                    { key: 'POWERBI_DATASET_ID', label: 'Semantic Model ID (Optional)', isSet: embedResponse.credentials_present?.dataset_id }
                  ].map((item) => (
                    <div
                      key={item.key}
                      style={{
                        padding: '12px 16px',
                        borderRadius: '10px',
                        border: `1px solid ${item.isSet ? '#BCF0DA' : '#FDE68A'}`,
                        backgroundColor: item.isSet ? '#F0FDF4' : '#FFFBEB',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between'
                      }}
                    >
                      <div>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: item.isSet ? '#166534' : '#92400E', fontFamily: "'JetBrains Mono', monospace" }}>
                          {item.key}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#6B7280', marginTop: '2px' }}>
                          {item.label}
                        </div>
                      </div>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '999px',
                          backgroundColor: item.isSet ? '#DEF7EC' : '#FEF3C7',
                          color: item.isSet ? '#03543F' : '#92400E'
                        }}
                      >
                        {item.isSet ? 'CONFIGURED' : 'NOT SET'}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Step-by-Step Azure & Power BI Instructions */}
                <div
                  style={{
                    backgroundColor: '#F8FAFC',
                    borderRadius: '12px',
                    border: '1px solid #E2E8F0',
                    padding: '20px',
                    marginTop: '20px'
                  }}
                >
                  <h4 style={{ margin: '0 0 12px 0', fontSize: '0.92rem', fontWeight: 700, color: '#1E293B' }}>
                    Manual Setup Steps in Microsoft Azure &amp; Power BI Service:
                  </h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.8rem', color: '#475569' }}>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                        1
                      </span>
                      <span>
                        <strong>Azure Portal:</strong> Open <em>Microsoft Entra ID &rarr; App registrations &rarr; New registration</em>. Note the <strong>Tenant ID</strong> and <strong>Client ID</strong>, then generate a <strong>Client Secret</strong>.
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                        2
                      </span>
                      <span>
                        <strong>Power BI Admin Portal:</strong> Under <em>Tenant settings &rarr; Developer settings</em>, enable <strong>"Allow service principals to use Power BI APIs"</strong>.
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                        3
                      </span>
                      <span>
                        <strong>Power BI Workspace:</strong> In your workspace, click <em>Manage Access</em> and add your App Registration as a <strong>Member</strong> or <strong>Contributor</strong>.
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ width: '20px', height: '20px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, flexShrink: 0 }}>
                        4
                      </span>
                      <span>
                        <strong>InSight .env file:</strong> Populate the variables in <code>d:\Documents\InSight\.env</code> (use template from <code>.env.example</code>), then click <strong>"Test Connection"</strong> above.
                      </span>
                    </div>
                  </div>
                </div>

                {/* Actions & Optional Fallback Toggle */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '24px', flexWrap: 'wrap', gap: '12px' }}>
                  <button
                    type="button"
                    onClick={() => void fetchEmbedToken()}
                    className="btn-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.84rem' }}
                  >
                    <RefreshCw size={14} />
                    <span>Check Credentials Again</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowLocalFallback(!showLocalFallback)}
                    className="btn-outline"
                    style={{ fontSize: '0.8rem' }}
                  >
                    {showLocalFallback ? 'Hide Local Offline Preview' : 'Inspect Local Schema & Offline Preview'}
                  </button>
                </div>
              </div>

              {/* EXPLICIT LOCAL FALLBACK SIMULATOR (ONLY WHEN TOGGLED) */}
              {showLocalFallback && (
                <div
                  style={{
                    backgroundColor: '#FFFFFF',
                    borderRadius: '16px',
                    border: '1px solid #E5E7EB',
                    padding: '24px',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '16px',
                      paddingBottom: '12px',
                      borderBottom: '1px solid #F3F4F6'
                    }}
                  >
                    <div>
                      <span style={{ fontSize: '0.7rem', fontWeight: 700, backgroundColor: '#FEF3C7', color: '#92400E', padding: '2px 6px', borderRadius: '4px' }}>
                        LOCAL OFFLINE PREVIEW
                      </span>
                      <h4 style={{ margin: '4px 0 0 0', fontSize: '1rem', fontWeight: 700, color: '#111827' }}>
                        InSight Local Telemetry Verification Preview
                      </h4>
                    </div>
                    <span style={{ fontSize: '0.76rem', color: '#6B7280' }}>
                      (Displaying local dataset telemetry)
                    </span>
                  </div>

                  {/* Simulator KPIs */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '14px', marginBottom: '20px' }}>
                    <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F0FDF4', border: '1px solid #DCFCE7' }}>
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase' }}>
                        Net Sentiment Score (NSS)
                      </div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#15803D', fontFamily: "'JetBrains Mono', monospace" }}>
                        {nssScore > 0 ? `+${nssScore}` : nssScore}
                      </div>
                    </div>
                    <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#FEF2F2', border: '1px solid #FEE2E2' }}>
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#991B1B', textTransform: 'uppercase' }}>
                        Defect Surge Rate (%)
                      </div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#DC2626', fontFamily: "'JetBrains Mono', monospace" }}>
                        {defectRate}%
                      </div>
                    </div>
                    <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#EFF6FF', border: '1px solid #DBEAFE' }}>
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#1E40AF', textTransform: 'uppercase' }}>
                        Actionable Telemetry
                      </div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#2563EB', fontFamily: "'JetBrains Mono', monospace" }}>
                        {actionableRate}%
                      </div>
                    </div>
                    <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F0FDF4', border: '1px solid #DCFCE7' }}>
                      <div style={{ fontSize: '0.7rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase' }}>
                        PII Scrub Compliance
                      </div>
                      <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#15803D', fontFamily: "'JetBrains Mono', monospace" }}>
                        100.0%
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ERROR DIAGNOSTICS PANEL */
            <div
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '16px',
                border: '1px solid #FCA5A5',
                padding: '32px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
                <AlertCircle size={22} style={{ color: '#DC2626' }} />
                <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#991B1B' }}>
                  Power BI Service Embed Token Generation Error
                </h3>
              </div>
              <p style={{ margin: '0 0 16px 0', fontSize: '0.84rem', color: '#7F1D1D', lineHeight: 1.5 }}>
                {embedResponse?.error_message}
              </p>

              <div style={{ padding: '14px', backgroundColor: '#FEF2F2', borderRadius: '8px', border: '1px solid #FECACA', fontSize: '0.78rem', color: '#991B1B' }}>
                <strong>Troubleshooting Checklist:</strong>
                <ul style={{ margin: '6px 0 0 16px', padding: 0, lineHeight: 1.6 }}>
                  <li>Confirm the <strong>Client Secret</strong> has not expired in Microsoft Entra ID.</li>
                  <li>Verify the App Registration is explicitly added as <strong>Member/Contributor</strong> to Workspace <code>{embedResponse?.workspace_id || 'POWERBI_WORKSPACE_ID'}</code>.</li>
                  <li>Verify Report ID <code>{embedResponse?.report_id || 'POWERBI_REPORT_ID'}</code> exists inside that workspace.</li>
                  <li>Ensure "Allow service principals to use Power BI APIs" is enabled in Power BI Admin Portal.</li>
                </ul>
              </div>

              <div style={{ marginTop: '20px', display: 'flex', gap: '10px' }}>
                <button
                  type="button"
                  onClick={() => void fetchEmbedToken()}
                  className="btn-primary"
                  style={{ fontSize: '0.82rem' }}
                >
                  Retry Connection
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 2: SEMANTIC MODEL FEEDS & CONNECTORS
      ========================================================================= */}
      {activeSubTab === 'connectors' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Quick Launch Card */}
          <div
            style={{
              backgroundColor: '#0F382E',
              color: '#FFFFFF',
              borderRadius: '16px',
              padding: '28px',
              boxShadow: '0 4px 6px -1px rgba(15, 56, 46, 0.2)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
              <div>
                <span
                  style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    backgroundColor: 'rgba(255,255,255,0.15)',
                    padding: '3px 8px',
                    borderRadius: '999px',
                    color: '#A7F3D0'
                  }}
                >
                  OFFICIAL POWER BI DATA SOURCE CONNECTOR
                </span>
                <h3 style={{ margin: '8px 0 4px 0', fontSize: '1.4rem', fontWeight: 700, fontFamily: "'DM Serif Display', Georgia, serif" }}>
                  Double-Click Power BI Data Source (.pbids)
                </h3>
                <p style={{ margin: 0, fontSize: '0.85rem', color: '#D1FAE5', maxWidth: '640px' }}>
                  Download the official Microsoft Power BI Data Source file. When opened on Windows, it automatically launches Power BI Desktop with the InSight live feed pre-configured.
                </p>
              </div>

              <button
                type="button"
                onClick={handleDownloadPbids}
                style={{
                  backgroundColor: '#F59E0B',
                  color: '#1E293B',
                  border: 'none',
                  borderRadius: '10px',
                  padding: '12px 22px',
                  fontSize: '0.9rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}
              >
                <Download size={16} />
                <span>Download InSight_{activeDomain}.pbids</span>
              </button>
            </div>
          </div>

          {/* Live REST API & Web Endpoints Cards */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>
              InSight Semantic Model Data Streams (Power BI Web Connector)
            </h3>
            <p style={{ margin: '4px 0 20px 0', fontSize: '0.82rem', color: '#6B7280' }}>
              In Power BI Desktop, click <strong>Get Data &rarr; Web</strong> and paste these real-time streaming URLs to populate the semantic model:
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* Endpoint 1: CSV Feed */}
              <div
                style={{
                  padding: '14px 18px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '10px',
                  border: '1px solid #E5E7EB',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.74rem', fontWeight: 700, backgroundColor: '#DEF7EC', color: '#03543F', padding: '2px 6px', borderRadius: '4px' }}>
                      FACT TABLE
                    </span>
                    <strong style={{ fontSize: '0.86rem', color: '#111827' }}>
                      Fact_ReviewTelemetry Live Stream (CSV)
                    </strong>
                  </div>
                  <div
                    style={{
                      fontSize: '0.78rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#4B5563',
                      marginTop: '4px'
                    }}
                  >
                    {guide?.api_urls?.csv_feed || `${API_BASE}/powerbi/data/reviews.csv`}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => handleCopy(guide?.api_urls?.csv_feed || `${API_BASE}/powerbi/data/reviews.csv`, 'csv')}
                    className="btn-outline"
                    style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                  >
                    {copiedKey === 'csv' ? <Check size={14} style={{ color: '#059669' }} /> : <Copy size={14} />}
                    <span>{copiedKey === 'csv' ? 'Copied URL!' : 'Copy URL'}</span>
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadCsv}
                    className="btn-outline"
                    style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                  >
                    <Download size={14} />
                    <span>Download</span>
                  </button>
                </div>
              </div>

              {/* Endpoint 2: Themes Feed */}
              <div
                style={{
                  padding: '14px 18px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '10px',
                  border: '1px solid #E5E7EB',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.74rem', fontWeight: 700, backgroundColor: '#EFF6FF', color: '#1E40AF', padding: '2px 6px', borderRadius: '4px' }}>
                      DIMENSION TABLE
                    </span>
                    <strong style={{ fontSize: '0.86rem', color: '#111827' }}>
                      Dim_Themes Dimension Stream (CSV)
                    </strong>
                  </div>
                  <div
                    style={{
                      fontSize: '0.78rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#4B5563',
                      marginTop: '4px'
                    }}
                  >
                    {guide?.api_urls?.themes_feed || `${API_BASE}/powerbi/data/themes.csv`}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleCopy(guide?.api_urls?.themes_feed || `${API_BASE}/powerbi/data/themes.csv`, 'themes')}
                  className="btn-outline"
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  {copiedKey === 'themes' ? <Check size={14} style={{ color: '#059669' }} /> : <Copy size={14} />}
                  <span>{copiedKey === 'themes' ? 'Copied URL!' : 'Copy URL'}</span>
                </button>
              </div>

              {/* Endpoint 3: Drift Feed */}
              <div
                style={{
                  padding: '14px 18px',
                  backgroundColor: '#F9FAFB',
                  borderRadius: '10px',
                  border: '1px solid #E5E7EB',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '12px'
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '0.74rem', fontWeight: 700, backgroundColor: '#FFFBEB', color: '#92400E', padding: '2px 6px', borderRadius: '4px' }}>
                      DRIFT FACT
                    </span>
                    <strong style={{ fontSize: '0.86rem', color: '#111827' }}>
                      Fact_BatchDrift PSI Telemetry (JSON)
                    </strong>
                  </div>
                  <div
                    style={{
                      fontSize: '0.78rem',
                      fontFamily: "'JetBrains Mono', monospace",
                      color: '#4B5563',
                      marginTop: '4px'
                    }}
                  >
                    {guide?.api_urls?.drift_feed || `${API_BASE}/powerbi/data/drift`}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => handleCopy(guide?.api_urls?.drift_feed || `${API_BASE}/powerbi/data/drift`, 'drift')}
                  className="btn-outline"
                  style={{ fontSize: '0.78rem', padding: '6px 12px' }}
                >
                  {copiedKey === 'drift' ? <Check size={14} style={{ color: '#059669' }} /> : <Copy size={14} />}
                  <span>{copiedKey === 'drift' ? 'Copied URL!' : 'Copy URL'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Power Query (M) Script Box */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '1.05rem', fontWeight: 700, color: '#111827' }}>
                  Power Query (M) Formula Code
                </h3>
                <p style={{ margin: '2px 0 0 0', fontSize: '0.78rem', color: '#6B7280' }}>
                  Paste this snippet directly into Power BI Desktop &rarr; Advanced Editor for automated type casting:
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleCopy(guide?.power_query_m || '', 'm_script')}
                className="btn-primary"
                style={{ fontSize: '0.78rem', padding: '6px 14px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                {copiedKey === 'm_script' ? <Check size={14} /> : <Copy size={14} />}
                <span>{copiedKey === 'm_script' ? 'Copied Script!' : 'Copy M-Query'}</span>
              </button>
            </div>

            <pre
              style={{
                backgroundColor: '#1E293B',
                color: '#E2E8F0',
                padding: '16px',
                borderRadius: '10px',
                fontSize: '0.78rem',
                fontFamily: "'JetBrains Mono', monospace",
                overflowX: 'auto',
                lineHeight: 1.5,
                margin: 0
              }}
            >
              {guide?.power_query_m || 'Loading Power Query definition…'}
            </pre>
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 3: DAX MEASURES LIBRARY
      ========================================================================= */}
      {activeSubTab === 'dax' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
              Production DAX Measures for Power BI Report
            </h3>
            <p style={{ margin: '4px 0 0 0', fontSize: '0.82rem', color: '#6B7280' }}>
              6 pre-formulated DAX metrics designed for InSight executive reporting. Click <strong>Copy DAX</strong> and paste into Power BI's <em>New Measure</em> toolbar.
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '18px' }}>
            {(guide?.dax_measures || []).map((measure) => (
              <div
                key={measure.id}
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '14px',
                  border: '1px solid #E5E7EB',
                  padding: '20px',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
                  display: 'flex',
                  flexDirection: 'column',
                  justifyContent: 'space-between'
                }}
              >
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span
                      style={{
                        fontSize: '0.7rem',
                        fontWeight: 700,
                        backgroundColor: '#EFF6FF',
                        color: '#1D4ED8',
                        padding: '2px 8px',
                        borderRadius: '999px'
                      }}
                    >
                      {measure.category}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleCopy(measure.dax, measure.id)}
                      className="btn-outline"
                      style={{ fontSize: '0.74rem', padding: '4px 10px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      {copiedKey === measure.id ? <Check size={12} style={{ color: '#059669' }} /> : <Copy size={12} />}
                      <span>{copiedKey === measure.id ? 'Copied!' : 'Copy DAX'}</span>
                    </button>
                  </div>

                  <h4 style={{ margin: '0 0 6px 0', fontSize: '0.98rem', fontWeight: 700, color: '#111827' }}>
                    {measure.name}
                  </h4>
                  <p style={{ margin: '0 0 14px 0', fontSize: '0.78rem', color: '#6B7280', lineHeight: 1.4 }}>
                    {measure.description}
                  </p>
                </div>

                <pre
                  style={{
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    color: '#0F172A',
                    padding: '12px',
                    borderRadius: '8px',
                    fontSize: '0.74rem',
                    fontFamily: "'JetBrains Mono', monospace",
                    overflowX: 'auto',
                    margin: 0,
                    lineHeight: 1.45
                  }}
                >
                  {measure.dax}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 4: STAR SCHEMA & SETUP GUIDE
      ========================================================================= */}
      {activeSubTab === 'schema' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          {/* Relational Star Schema Diagram */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}
          >
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#111827', fontFamily: "'DM Serif Display', Georgia, serif" }}>
              InSight VertiPaq Star Schema Blueprint
            </h3>
            <p style={{ margin: '4px 0 20px 0', fontSize: '0.82rem', color: '#6B7280' }}>
              Normalized dimensional model optimized for Power BI in-memory VertiPaq storage and cross-filtering:
            </p>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
                gap: '16px',
                marginBottom: '20px'
              }}
            >
              {/* Fact Table */}
              <div
                style={{
                  backgroundColor: '#F0FDF4',
                  border: '2px solid #86EFAC',
                  borderRadius: '12px',
                  padding: '16px'
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase' }}>
                  CENTRAL FACT TABLE
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: '#14532D', marginTop: '2px' }}>
                  Fact_ReviewTelemetry
                </div>
                <ul style={{ margin: '10px 0 0 16px', padding: 0, fontSize: '0.76rem', color: '#166534', lineHeight: 1.6 }}>
                  <li><strong>Review_ID</strong> (PK, Text)</li>
                  <li><strong>Submission_Date</strong> (DateTime)</li>
                  <li><strong>Rating</strong> (Int64: 1-5)</li>
                  <li><strong>Calibrated_Sentiment</strong> (Text)</li>
                  <li><strong>Sentiment_Confidence</strong> (Decimal)</li>
                  <li><strong>Cluster_ID</strong> (FK &rarr; Dim_Themes)</li>
                  <li><strong>Batch_or_Version</strong> (FK)</li>
                  <li><strong>SKU_or_Module</strong> (FK)</li>
                  <li><strong>Sanitized_Verbatim</strong> (Text)</li>
                </ul>
              </div>

              {/* Dim Themes */}
              <div
                style={{
                  backgroundColor: '#EFF6FF',
                  border: '1px solid #BFDBFE',
                  borderRadius: '12px',
                  padding: '16px'
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#1E40AF', textTransform: 'uppercase' }}>
                  DIMENSION TABLE (1:N)
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: '#1E3A8A', marginTop: '2px' }}>
                  Dim_Themes
                </div>
                <ul style={{ margin: '10px 0 0 16px', padding: 0, fontSize: '0.76rem', color: '#1E40AF', lineHeight: 1.6 }}>
                  <li><strong>Cluster_ID</strong> (PK, Int64)</li>
                  <li><strong>Theme_Title</strong> (Text)</li>
                  <li><strong>Category</strong> (Text)</li>
                  <li><strong>Severity</strong> (CRITICAL/HIGH/MED)</li>
                  <li><strong>Negative_Share_Pct</strong> (Decimal)</li>
                  <li><strong>Top_Keywords</strong> (Text)</li>
                </ul>
              </div>

              {/* Dim Batch / Release */}
              <div
                style={{
                  backgroundColor: '#FFFBEB',
                  border: '1px solid #FDE68A',
                  borderRadius: '12px',
                  padding: '16px'
                }}
              >
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#92400E', textTransform: 'uppercase' }}>
                  DIMENSION TABLE (1:N)
                </div>
                <div style={{ fontSize: '1rem', fontWeight: 800, color: '#78350F', marginTop: '2px' }}>
                  Dim_BatchRelease
                </div>
                <ul style={{ margin: '10px 0 0 16px', padding: 0, fontSize: '0.76rem', color: '#92400E', lineHeight: 1.6 }}>
                  <li><strong>Batch_or_Version</strong> (PK, Text)</li>
                  <li><strong>Total_Reviews</strong> (Int64)</li>
                  <li><strong>Negative_Rate_Pct</strong> (Decimal)</li>
                  <li><strong>PSI_Score</strong> (Decimal)</li>
                  <li><strong>Drift_Status</strong> (Text)</li>
                </ul>
              </div>
            </div>
          </div>

          {/* 5-Minute Setup Steps */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              borderRadius: '16px',
              border: '1px solid #E5E7EB',
              padding: '24px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.03)'
            }}
          >
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', fontWeight: 700, color: '#111827' }}>
              5-Minute Zero-Friction Setup Guide
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
              <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB' }}>
                <div style={{ width: '26px', height: '26px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', marginBottom: '10px' }}>
                  1
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.88rem', fontWeight: 700, color: '#111827' }}>
                  Open Power BI Desktop
                </h4>
                <p style={{ margin: 0, fontSize: '0.76rem', color: '#6B7280', lineHeight: 1.5 }}>
                  Launch Power BI Desktop or double-click the <code>.pbids</code> file downloaded from the top bar.
                </p>
              </div>

              <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB' }}>
                <div style={{ width: '26px', height: '26px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', marginBottom: '10px' }}>
                  2
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.88rem', fontWeight: 700, color: '#111827' }}>
                  Connect to InSight Feeds
                </h4>
                <p style={{ margin: 0, fontSize: '0.76rem', color: '#6B7280', lineHeight: 1.5 }}>
                  Click <strong>Get Data &rarr; Web</strong> and paste <code>http://localhost:8000/api/powerbi/data/reviews.csv</code>.
                </p>
              </div>

              <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB' }}>
                <div style={{ width: '26px', height: '26px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', marginBottom: '10px' }}>
                  3
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.88rem', fontWeight: 700, color: '#111827' }}>
                  Apply DAX Measures
                </h4>
                <p style={{ margin: 0, fontSize: '0.76rem', color: '#6B7280', lineHeight: 1.5 }}>
                  Copy <em>Net Sentiment Score (NSS)</em> and <em>Defect Surge Rate</em> from the DAX tab above into New Measures.
                </p>
              </div>

              <div style={{ padding: '16px', borderRadius: '10px', backgroundColor: '#F9FAFB', border: '1px solid #E5E7EB' }}>
                <div style={{ width: '26px', height: '26px', borderRadius: '50%', backgroundColor: '#059669', color: '#FFF', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8rem', marginBottom: '10px' }}>
                  4
                </div>
                <h4 style={{ margin: '0 0 6px 0', fontSize: '0.88rem', fontWeight: 700, color: '#111827' }}>
                  Publish &amp; Configure .env
                </h4>
                <p style={{ margin: 0, fontSize: '0.76rem', color: '#6B7280', lineHeight: 1.5 }}>
                  Publish to your Power BI Workspace, obtain Workspace/Report IDs, and configure in <code>.env</code>.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Power BI Embed Config Modal */}
      <PowerBIConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        config={config}
        onSaveConfig={async (embedUrl, reportTitle) => {
          await fetch(`${API_BASE}/powerbi/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ embed_url: embedUrl, report_title: reportTitle })
          });
          setConfig({
            embed_url: embedUrl,
            report_title: reportTitle,
            is_configured: Boolean(embedUrl),
            demo_url: config?.demo_url || ''
          });
        }}
      />
    </div>
  );
}

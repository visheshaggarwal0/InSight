import { useState } from 'react';
import { Search, Calendar, Bell, ChevronDown, Database, Upload, ShieldCheck, BarChart3 } from 'lucide-react';
import type { DatasetInfo } from '../types/telemetry';

interface TopBarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  datasets: DatasetInfo[];
  activeDomain: string;
  onSelectDomain: (domain: string) => void;
  onUploadCsv: (file: File) => void;
  timeRange: string;
  onChangeTimeRange: (range: string) => void;
  onOpenGovernance?: () => void;
}

export function TopBar({
  searchQuery,
  onSearchChange,
  datasets,
  activeDomain,
  onSelectDomain,
  onUploadCsv,
  timeRange,
  onChangeTimeRange,
  onOpenGovernance
}: TopBarProps) {
  const [isDomainOpen, setIsDomainOpen] = useState(false);
  const [isDateOpen, setIsDateOpen] = useState(false);

  const activeDatasetObj = datasets.find(d => d.id === activeDomain);
  const domainDisplayName = activeDatasetObj?.name
    ? (activeDatasetObj.name.includes('(') ? activeDatasetObj.name.split('(')[0].trim() : activeDatasetObj.name)
    : 'Switch Dataset';

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: '16px',
      padding: '14px 36px',
      backgroundColor: '#FFFFFF',
      borderBottom: '1px solid #E8ECE9',
      position: 'sticky',
      top: 0,
      zIndex: 15
    }}>
      {/* Search Input with Ctrl K */}
      <div style={{
        position: 'relative',
        flex: '1 1 220px',
        minWidth: '200px',
        maxWidth: '440px'
      }}>
        <Search 
          size={16} 
          style={{
            position: 'absolute',
            left: '14px',
            top: '50%',
            transform: 'translateY(-50%)',
            color: '#9CA3AF'
          }} 
        />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search feedback, themes, quotes..."
          style={{
            width: '100%',
            padding: '9px 72px 9px 38px',
            borderRadius: '999px',
            border: '1px solid #E5E7EB',
            backgroundColor: '#F9FAFB',
            fontSize: '0.84rem',
            color: '#111827',
            outline: 'none',
            transition: 'all 0.15s ease'
          }}
          onFocus={(e) => {
            e.target.style.backgroundColor = '#FFFFFF';
            e.target.style.borderColor = '#10B981';
            e.target.style.boxShadow = '0 0 0 3px rgba(16, 185, 129, 0.1)';
          }}
          onBlur={(e) => {
            e.target.style.backgroundColor = '#F9FAFB';
            e.target.style.borderColor = '#E5E7EB';
            e.target.style.boxShadow = 'none';
          }}
        />
        <span style={{
          position: 'absolute',
          right: '12px',
          top: '50%',
          transform: 'translateY(-50%)',
          fontSize: '0.68rem',
          color: '#6B7280',
          backgroundColor: '#E5E7EB',
          padding: '2px 6px',
          borderRadius: '4px',
          fontWeight: 600,
          pointerEvents: 'none'
        }}>
          Ctrl K
        </span>
      </div>

      {/* Right Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
        {/* Model Trust Score Pill */}
        {onOpenGovernance && (
          <button
            onClick={onOpenGovernance}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '7px 12px',
              borderRadius: '999px',
              border: '1px solid #A7F3D0',
              backgroundColor: '#ECFDF5',
              color: '#065F46',
              fontSize: '0.78rem',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'all 0.15s ease'
            }}
            title="Inspect Platt Calibration (88.2% Accuracy), 3x3 Confusion Matrix, and PSI Drift"
          >
            <ShieldCheck size={14} style={{ color: '#10B981' }} />
            <span>88.2% Trust</span>
          </button>
        )}

        {/* Power BI Live Connector Bridge */}
        <a
          href="http://localhost:8000/api/export/powerbi"
          download
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '7px 12px',
            borderRadius: '999px',
            border: '1px solid #FDE68A',
            backgroundColor: '#FFFBEB',
            color: '#92400E',
            fontSize: '0.78rem',
            fontWeight: 600,
            textDecoration: 'none',
            cursor: 'pointer',
            transition: 'all 0.15s ease'
          }}
          title="Download live relational telemetry dataset formatted for Microsoft Power BI"
        >
          <BarChart3 size={14} style={{ color: '#D97706' }} />
          <span>Power BI Feed</span>
        </a>

        {/* Domain Switcher */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setIsDomainOpen(!isDomainOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#FFFFFF',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: '#374151',
              cursor: 'pointer'
            }}
          >
            <Database size={15} style={{ color: '#10B981' }} />
            <span>{domainDisplayName}</span>
            <ChevronDown size={14} style={{ color: '#9CA3AF' }} />
          </button>

          {isDomainOpen && (
            <div style={{
              position: 'absolute',
              top: '110%',
              right: 0,
              width: '260px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E5E7EB',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
              padding: '6px',
              zIndex: 30
            }}>
              <div style={{ padding: '6px 8px', fontSize: '0.72rem', fontWeight: 700, color: '#9CA3AF', textTransform: 'uppercase' }}>
                Select Domain
              </div>
              {datasets.map((d) => (
                <button
                  key={d.id}
                  onClick={() => {
                    onSelectDomain(d.id);
                    setIsDomainOpen(false);
                  }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'flex-start',
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: activeDomain === d.id ? '#ECFDF5' : 'transparent',
                    color: activeDomain === d.id ? '#065F46' : '#111827',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                >
                  <span style={{ fontSize: '0.82rem', fontWeight: 600 }}>{d.name}</span>
                  <span style={{ fontSize: '0.72rem', color: '#6B7280' }}>{d.review_count.toLocaleString()} reviews</span>
                </button>
              ))}

              <div style={{ borderTop: '1px solid #E5E7EB', marginTop: '6px', paddingTop: '6px' }}>
                <label style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 10px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: '#4B5563',
                  cursor: 'pointer'
                }}>
                  <Upload size={14} />
                  <span>Upload Custom CSV</span>
                  <input
                    type="file"
                    accept=".csv"
                    style={{ display: 'none' }}
                    onChange={(e) => {
                      if (e.target.files?.[0]) {
                        onUploadCsv(e.target.files[0]);
                        setIsDomainOpen(false);
                      }
                    }}
                  />
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Date Range Selector */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setIsDateOpen(!isDateOpen)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              borderRadius: '999px',
              border: '1px solid #E5E7EB',
              backgroundColor: '#FFFFFF',
              fontSize: '0.82rem',
              fontWeight: 600,
              color: '#374151',
              cursor: 'pointer'
            }}
          >
            <Calendar size={15} style={{ color: '#6B7280' }} />
            <span>{timeRange}</span>
            <ChevronDown size={14} style={{ color: '#9CA3AF' }} />
          </button>

          {isDateOpen && (
            <div style={{
              position: 'absolute',
              top: '110%',
              right: 0,
              width: '180px',
              backgroundColor: '#FFFFFF',
              border: '1px solid #E5E7EB',
              borderRadius: '12px',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1)',
              padding: '6px',
              zIndex: 30
            }}>
              {['Last 7 days', 'Last 30 days', 'Last 90 days', 'All Releases'].map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    onChangeTimeRange(r);
                    setIsDateOpen(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: timeRange === r ? '#ECFDF5' : 'transparent',
                    color: timeRange === r ? '#065F46' : '#111827',
                    fontSize: '0.82rem',
                    fontWeight: timeRange === r ? 600 : 500,
                    textAlign: 'left',
                    cursor: 'pointer'
                  }}
                >
                  {r}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications */}
        <div style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '38px',
          height: '38px',
          borderRadius: '50%',
          backgroundColor: '#F3F4F6',
          cursor: 'pointer'
        }}>
          <Bell size={17} style={{ color: '#4B5563' }} />
          <span style={{
            position: 'absolute',
            top: '8px',
            right: '9px',
            width: '7px',
            height: '7px',
            borderRadius: '50%',
            backgroundColor: '#EF4444'
          }} />
        </div>

        {/* User Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '4px 12px 4px 4px',
          borderRadius: '999px',
          backgroundColor: '#F9FAFB',
          border: '1px solid #E5E7EB'
        }}>
          <div style={{
            width: '30px',
            height: '30px',
            borderRadius: '50%',
            backgroundColor: '#0F382E',
            color: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.82rem',
            fontWeight: 700
          }}>
            V
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: '#111827', lineHeight: 1.1 }}>Vishesh</span>
            <span style={{ fontSize: '0.68rem', color: '#6B7280' }}>Product Team</span>
          </div>
        </div>
      </div>
    </header>
  );
}

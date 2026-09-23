import React, { useRef } from 'react';
import { Sparkles, Smartphone, UploadCloud, CheckCircle } from 'lucide-react';
import type { DatasetInfo } from '../types/telemetry';

interface Props {
  datasets: DatasetInfo[];
  activeDomain: string;
  onSelectDomain: (domainId: string) => void;
  onUploadCsv: (file: File) => void;
  isLoading: boolean;
}

export const DomainSwitcher: React.FC<Props> = ({
  datasets,
  activeDomain,
  onSelectDomain,
  onUploadCsv,
  isLoading
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUploadCsv(e.target.files[0]);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Active Telemetry Domain
            </span>
            {isLoading && (
              <span style={{ fontSize: '0.75rem', color: 'var(--accent-blue)', animation: 'pulse 1.5s infinite' }}>
                • Processing Pipeline...
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Toggle between physical consumer goods (D2C skincare/cosmetics), software app telemetry, or ingest custom CSV.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          {datasets.map((d) => {
            const isSelected = activeDomain === d.id;
            const Icon = d.id === 'd2c_cosmetics' ? Sparkles : d.id === 'tech_saas' ? Smartphone : UploadCloud;
            
            return (
              <button
                key={d.id}
                onClick={() => d.id === 'custom' ? fileInputRef.current?.click() : onSelectDomain(d.id)}
                disabled={isLoading}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 14px',
                  borderRadius: '8px',
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  border: isSelected ? '1px solid var(--accent-blue)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-card)',
                  color: isSelected ? '#60a5fa' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={16} />
                <span>{d.id === 'd2c_cosmetics' ? 'D2C Cosmetics & Beauty' : d.id === 'tech_saas' ? 'Fintech Mobile App' : 'Upload CSV'}</span>
                {isSelected && <CheckCircle size={14} color="#60a5fa" />}
              </button>
            );
          })}

          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept=".csv"
            style={{ display: 'none' }}
          />
        </div>
      </div>
    </div>
  );
};

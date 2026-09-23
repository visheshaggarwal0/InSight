import React, { useRef } from 'react';
import { Sparkles, Smartphone, UploadCloud, Check, RefreshCw } from 'lucide-react';
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
            <span style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
              TELEMETRY SOURCE
            </span>
            {isLoading && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                <RefreshCw size={11} style={{ animation: 'spin 1s linear infinite' }} />
                Indexing corpus...
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: '3px' }}>
            Select an enterprise feedback domain or upload a custom review batch.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
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
                  gap: '7px',
                  padding: '7px 14px',
                  borderRadius: '7px',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  border: isSelected ? '1px solid #3f3f4e' : '1px solid var(--border-subtle)',
                  background: isSelected ? '#202026' : 'var(--bg-card)',
                  color: isSelected ? '#f4f4f5' : 'var(--text-secondary)',
                  transition: 'all 0.15s ease'
                }}
              >
                <Icon size={14} color={isSelected ? '#fafafa' : '#71717a'} />
                <span>
                  {d.id === 'd2c_cosmetics'
                    ? 'D2C Consumer & Cosmetics'
                    : d.id === 'tech_saas'
                    ? 'Fintech / Mobile SaaS'
                    : 'Upload CSV'}
                </span>
                {isSelected && <Check size={13} color="#fafafa" style={{ marginLeft: '2px' }} />}
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

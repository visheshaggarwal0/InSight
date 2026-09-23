import React, { useRef } from 'react';
import { Sparkles, Smartphone, UploadCloud, CheckCircle2, RefreshCw } from 'lucide-react';
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
    <div className="glass-panel" style={{ padding: '18px 24px', marginBottom: '24px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 800, color: 'var(--accent-blue)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              ACTIVE PRODUCT DOMAIN
            </span>
            {isLoading && (
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.72rem', color: '#60a5fa', fontWeight: 600 }}>
                <RefreshCw size={12} className="pulse-indicator" />
                Processing 10,000 telemetry records...
              </span>
            )}
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Switch between physical consumer goods (D2C skincare/cosmetics), mobile app stores, or upload custom review batches.
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
                  padding: '9px 16px',
                  borderRadius: '10px',
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  border: isSelected ? '1px solid #3b82f6' : '1px solid rgba(255, 255, 255, 0.08)',
                  background: isSelected ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.22), rgba(37, 99, 235, 0.12))' : 'rgba(15, 22, 38, 0.6)',
                  color: isSelected ? '#93c5fd' : 'var(--text-secondary)',
                  boxShadow: isSelected ? '0 0 15px rgba(59, 130, 246, 0.25)' : 'none',
                  transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)'
                }}
              >
                <Icon size={16} color={isSelected ? '#60a5fa' : 'currentColor'} />
                <span>
                  {d.id === 'd2c_cosmetics'
                    ? 'D2C Skincare & Beauty'
                    : d.id === 'tech_saas'
                    ? 'Fintech Mobile App'
                    : 'Upload Custom CSV'}
                </span>
                {isSelected && <CheckCircle2 size={15} color="#60a5fa" />}
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

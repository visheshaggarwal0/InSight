export function RatingDistributionCard() {
  const ratings = [
    { star: '1★', percent: 8, color: '#F87171' },
    { star: '2★', percent: 6, color: '#FB923C' },
    { star: '3★', percent: 12, color: '#FBBF24' },
    { star: '4★', percent: 28, color: '#34D399' },
    { star: '5★', percent: 46, color: '#059669' },
  ];

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 0.8 }}>
      <h3 style={{
        fontSize: '1.05rem',
        fontWeight: 700,
        color: '#111827',
        letterSpacing: '-0.01em',
        marginBottom: '20px'
      }}>
        Rating Distribution
      </h3>

      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        height: '180px',
        padding: '0 10px',
        position: 'relative'
      }}>
        {ratings.map((r, i) => {
          // Normalize height relative to max 50%
          const barHeight = Math.max(14, (r.percent / 50) * 130);

          return (
            <div
              key={i}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '8px',
                flex: 1
              }}
            >
              {/* Percentage label */}
              <span style={{
                fontSize: '0.75rem',
                fontWeight: 700,
                color: '#374151'
              }}>
                {r.percent}%
              </span>

              {/* Vertical Bar */}
              <div
                style={{
                  width: '38px',
                  height: `${barHeight}px`,
                  backgroundColor: r.color,
                  borderRadius: '8px 8px 4px 4px',
                  transition: 'height 0.4s cubic-bezier(0.16, 1, 0.3, 1), transform 0.15s ease',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'scaleY(1.04)';
                  e.currentTarget.style.opacity = '0.9';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scaleY(1)';
                  e.currentTarget.style.opacity = '1';
                }}
              />

              {/* Star label */}
              <span style={{
                fontSize: '0.76rem',
                fontWeight: 600,
                color: '#6B7280',
                marginTop: '4px'
              }}>
                {r.star}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

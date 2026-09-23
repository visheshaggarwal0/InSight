export function SentimentBySource() {
  const sources = [
    { label: 'App Store', pos: 68, neu: 20, neg: 12 },
    { label: 'Google Play', pos: 62, neu: 25, neg: 13 },
    { label: 'Survey', pos: 78, neu: 15, neg: 7 },
    { label: 'In-App', pos: 70, neu: 20, neg: 10 },
  ];

  return (
    <div className="dashboard-card" style={{ padding: '22px 24px', flex: 1 }}>
      {/* Header */}
      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827', letterSpacing: '-0.01em', marginBottom: '8px' }}>
        Sentiment by Source
      </h3>

      {/* Legend */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginBottom: '22px' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.74rem', color: '#4B5563', fontWeight: 500 }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#10B981' }} />
          Positive
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.74rem', color: '#4B5563', fontWeight: 500 }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#CBD5E1' }} />
          Neutral
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '0.74rem', color: '#4B5563', fontWeight: 500 }}>
          <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#F87171' }} />
          Negative
        </span>
      </div>

      {/* Stacked Bars Container */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        height: '210px',
        padding: '0 8px'
      }}>
        {sources.map((src, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              flex: 1,
              height: '100%',
              justifyContent: 'flex-end'
            }}
          >
            {/* Stacked Column */}
            <div style={{
              width: '42px',
              height: '170px',
              display: 'flex',
              flexDirection: 'column-reverse',
              borderRadius: '8px',
              overflow: 'hidden',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
            }}>
              {/* Positive segment (bottom) */}
              <div
                style={{
                  height: `${src.pos}%`,
                  backgroundColor: '#10B981',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  color: '#FFFFFF'
                }}
                title={`Positive: ${src.pos}%`}
              >
                {src.pos}%
              </div>

              {/* Neutral segment (middle) */}
              <div
                style={{
                  height: `${src.neu}%`,
                  backgroundColor: '#E2E8F0',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.68rem',
                  fontWeight: 600,
                  color: '#475569'
                }}
                title={`Neutral: ${src.neu}%`}
              >
                {src.neu}%
              </div>

              {/* Negative segment (top) */}
              <div
                style={{
                  height: `${src.neg}%`,
                  backgroundColor: '#F87171',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  color: '#FFFFFF'
                }}
                title={`Negative: ${src.neg}%`}
              >
                {src.neg}%
              </div>
            </div>

            {/* Source Label */}
            <span style={{
              fontSize: '0.74rem',
              fontWeight: 600,
              color: '#6B7280',
              marginTop: '10px',
              textAlign: 'center'
            }}>
              {src.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

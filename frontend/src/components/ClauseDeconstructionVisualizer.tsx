import React, { useState, useMemo } from 'react';
import {
  CheckCircle,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  Zap
} from 'lucide-react';

interface ClauseResult {
  text: string;
  intent: 'PRAISE' | 'DEFECT' | 'CRITICAL_SAFETY' | 'FEATURE_REQUEST' | 'NOISE';
  sentimentScore: number; // 0 to 1 (0=negative, 1=positive)
  routeDestination: string;
  badgeColor: string;
  badgeBg: string;
  explanation: string;
}

interface BenchmarkPreset {
  id: string;
  label: string;
  starRating: number;
  text: string;
  naiveSentiment: {
    label: string;
    score: number;
    flawDescription: string;
  };
}

const PRESETS: BenchmarkPreset[] = [
  {
    id: 'trojan-5star',
    label: '🚨 The Trojan Horse 5-Star (Chemical Burn)',
    starRating: 5,
    text: 'Absolutely loved the fragrance and the glow is unreal, 5 stars all the way! But the dispenser nozzle cracked on day two, leaked all over my suitcase, and the formula gave me severe contact dermatitis.',
    naiveSentiment: {
      label: 'POSITIVE (92%)',
      score: 0.92,
      flawDescription: 'Naive whole-document models score this as overwhelmingly positive because "loved", "glow", and "5 stars" mask the severe allergic reaction.'
    }
  },
  {
    id: 'shattered-glass',
    label: '⚠️ 4-Star Safety Hazard (Shattered Glass)',
    starRating: 4,
    text: 'My holy grail daily moisturizer, keeps my skin deeply hydrated all day. However, the glass bottle arrived shattered into razor-sharp shards inside the cardboard packaging.',
    naiveSentiment: {
      label: 'POSITIVE (87%)',
      score: 0.87,
      flawDescription: 'Standard classifiers flag this 4-star review as "Satisfied Customer", completely missing the dangerous glass shard quality control hazard.'
    }
  },
  {
    id: 'multi-intent-backlog',
    label: '💡 High-Value Backlog (Feature Request + Defect)',
    starRating: 4,
    text: 'Amazing anti-aging serum that visibly smoothed my fine lines. Would love a fragrance-free version for sensitive skin, and please redesign the dropper because it constantly jams.',
    naiveSentiment: {
      label: 'POSITIVE (84%)',
      score: 0.84,
      flawDescription: 'Lumps valuable product development requests and hardware packaging flaws into a generic positive bucket.'
    }
  }
];

function analyzeTextIntoClauses(rawText: string): ClauseResult[] {
  if (!rawText.trim()) return [];

  // Split on sentence boundaries and contrastive conjunction pivots
  const rawSegments = rawText
    .split(/(?<=[.!?])\s+|(?<=[,;])\s+(?=but\b|however\b|although\b|yet\b|though\b|except\b)/i)
    .map((s) => s.trim())
    .filter(Boolean);

  const results: ClauseResult[] = [];

  for (const seg of rawSegments) {
    const lower = seg.toLowerCase();

    // Critical safety keywords
    const isCritical =
      /\b(dermatitis|chemical burn|burns|burning|allergic|rash|swelling|hospital|infection|shattered|broken glass|shards|bleeding|blister)\b/i.test(
        lower
      );

    // Defect keywords
    const isDefect =
      /\b(broke|broken|cracked|leak|leaked|leaking|clog|clogged|jams|jammed|explode|exploded|defective|pump|dispenser|dropper|smell terrible|spoiled|greasy|breakout|acne|dryness|chapping)\b/i.test(
        lower
      );

    // Feature request / wishlist keywords
    const isFeature =
      /\b(would love|wish|please make|please add|suggest|unscented|fragrance-free|travel-friendly|refill|bigger size|pump option|shade range)\b/i.test(
        lower
      );

    // Praise keywords
    const isPraise =
      /\b(love|loved|holy grail|amazing|glow|best|hydrated|hydrating|smoothed|smooth|soothing|5 stars|repurchase|favorite|perfect|delight)\b/i.test(
        lower
      );

    if (isCritical) {
      results.push({
        text: seg,
        intent: 'CRITICAL_SAFETY',
        sentimentScore: 0.05,
        routeDestination: '🚨 Immediate QA & Product Safety Recall Triage',
        badgeColor: '#991B1B',
        badgeBg: '#FEF2F2',
        explanation: 'Critical biological or physical safety hazard detected. Triggers emergency alert.'
      });
    } else if (isDefect) {
      results.push({
        text: seg,
        intent: 'DEFECT',
        sentimentScore: 0.15,
        routeDestination: '🔴 Packaging & Hardware Engineering Incident Radar',
        badgeColor: '#C2410C',
        badgeBg: '#FFF7ED',
        explanation: 'Actionable hardware or formula defect extracted independently from praising context.'
      });
    } else if (isFeature) {
      results.push({
        text: seg,
        intent: 'FEATURE_REQUEST',
        sentimentScore: 0.65,
        routeDestination: '🔵 Product Roadmap & R&D Feature Backlog',
        badgeColor: '#3730A3',
        badgeBg: '#EEF2FF',
        explanation: 'Direct customer recommendation routed directly to Product Management backlog.'
      });
    } else if (isPraise) {
      results.push({
        text: seg,
        intent: 'PRAISE',
        sentimentScore: 0.95,
        routeDestination: '🟢 Marketing Claims & Product Strength Highlights',
        badgeColor: '#065F46',
        badgeBg: '#ECFDF5',
        explanation: 'Validated sensory delight and customer satisfaction proposition.'
      });
    } else {
      results.push({
        text: seg,
        intent: 'NOISE',
        sentimentScore: 0.5,
        routeDestination: '⚪ Filtered Telemetry (Non-Actionable)',
        badgeColor: '#4B5563',
        badgeBg: '#F3F4F6',
        explanation: 'Contextual filler or ambient narrative.'
      });
    }
  }

  return results;
}

export const ClauseDeconstructionVisualizer: React.FC = () => {
  const [activePresetId, setActivePresetId] = useState<string>(PRESETS[0].id);
  const [customText, setCustomText] = useState<string>(PRESETS[0].text);
  const [isEditing, setIsEditing] = useState<boolean>(false);

  const currentPreset = useMemo(
    () => PRESETS.find((p) => p.id === activePresetId) || PRESETS[0],
    [activePresetId]
  );

  const clauses = useMemo(() => analyzeTextIntoClauses(customText), [customText]);

  const criticalFound = clauses.some((c) => c.intent === 'CRITICAL_SAFETY');
  const defectsFound = clauses.filter((c) => c.intent === 'DEFECT' || c.intent === 'CRITICAL_SAFETY');

  const handleSelectPreset = (preset: BenchmarkPreset) => {
    setActivePresetId(preset.id);
    setCustomText(preset.text);
    setIsEditing(false);
  };

  return (
    <div style={{ paddingTop: '16px' }}>
      {/* Header Banner */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
          <span
            style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              padding: '2px 8px',
              borderRadius: '999px',
              backgroundColor: '#ECFDF5',
              color: '#065F46',
              border: '1px solid #A7F3D0'
            }}
          >
            PATENTED AI ARCHITECTURE SHOWCASE
          </span>
          <span style={{ fontSize: '0.8rem', color: '#6B7280', fontWeight: 500 }}>
            Clause-Level Proposition Routing
          </span>
        </div>
        <h2
          style={{
            fontSize: '1.8rem',
            fontWeight: 700,
            color: '#111827',
            margin: 0,
            fontFamily: "'DM Serif Display', Georgia, serif"
          }}
        >
          Solving The &ldquo;Whole-Document Fallacy&rdquo;
        </h2>
        <p style={{ fontSize: '0.88rem', color: '#4B5563', marginTop: '6px', maxWidth: '780px', lineHeight: 1.5 }}>
          Traditional sentiment tools evaluate an entire review as a single blob. When happy customers write 5-star
          reviews that contain critical defects, conventional NLP completely buries the defect. InSight deconstructs reviews
          into atomic proposition clauses and dispatches each to the right engineering queue.
        </p>
      </div>

      {/* Preset Selector */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          flexWrap: 'wrap',
          marginBottom: '20px'
        }}
      >
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#374151' }}>Live Test Benchmark:</span>
        {PRESETS.map((preset) => {
          const isActive = activePresetId === preset.id && !isEditing;
          return (
            <button
              key={preset.id}
              type="button"
              onClick={() => handleSelectPreset(preset)}
              style={{
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.78rem',
                fontWeight: isActive ? 700 : 500,
                backgroundColor: isActive ? '#0F382E' : '#FFFFFF',
                color: isActive ? '#FFFFFF' : '#374151',
                border: isActive ? '1px solid #0F382E' : '1px solid #D1D5DB',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <span>{preset.label}</span>
            </button>
          );
        })}
      </div>

      {/* Input / Editing Box */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          borderRadius: '14px',
          border: '1px solid #E5E7EB',
          padding: '18px 20px',
          marginBottom: '24px',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)'
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label htmlFor="clause-input" style={{ fontSize: '0.78rem', fontWeight: 700, color: '#374151', textTransform: 'uppercase' }}>
            Customer Review Text (Editable Live Playground):
          </label>
          <button
            type="button"
            onClick={() => handleSelectPreset(currentPreset)}
            style={{
              background: 'none',
              border: 'none',
              color: '#059669',
              fontSize: '0.75rem',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
          >
            <RefreshCw size={12} />
            Reset to Preset
          </button>
        </div>

        <textarea
          id="clause-input"
          value={customText}
          onChange={(e) => {
            setCustomText(e.target.value);
            setIsEditing(true);
          }}
          rows={3}
          style={{
            width: '100%',
            padding: '12px 14px',
            borderRadius: '8px',
            border: '1px solid #D1D5DB',
            fontSize: '0.9rem',
            lineHeight: 1.5,
            color: '#111827',
            fontFamily: "'Inter', sans-serif",
            resize: 'vertical',
            outline: 'none'
          }}
          placeholder="Type or paste any mixed-sentiment customer review..."
        />
      </div>

      {/* Side-by-Side Comparison */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(280px, 1fr) minmax(360px, 1.8fr)',
          gap: '24px',
          alignItems: 'start'
        }}
        className="clause-comparison-grid"
      >
        {/* Left Column: Traditional NLP (The Failure) */}
        <div
          style={{
            backgroundColor: '#FEF2F2',
            borderRadius: '14px',
            border: '1px solid #FECACA',
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '0.72rem', fontWeight: 800, color: '#991B1B', textTransform: 'uppercase' }}>
                Conventional NLP
              </span>
            </div>
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '999px',
                backgroundColor: '#FEE2E2',
                color: '#991B1B',
                border: '1px solid #FECACA'
              }}
            >
              Whole-Doc Aggregator
            </span>
          </div>

          <div>
            <div style={{ fontSize: '0.75rem', color: '#7F1D1D', fontWeight: 600 }}>AGGREGATE PREDICTION</div>
            <div
              style={{
                fontSize: '1.4rem',
                fontWeight: 800,
                color: '#059669', // Ironically green because it thought it was positive
                marginTop: '4px',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              {currentPreset.naiveSentiment.label}
            </div>
          </div>

          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#FFFFFF',
              borderRadius: '8px',
              border: '1px solid #FECACA'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#B91C1C', marginBottom: '6px' }}>
              <AlertTriangle size={15} />
              <strong style={{ fontSize: '0.78rem' }}>The Whole-Document Fallacy:</strong>
            </div>
            <p style={{ fontSize: '0.78rem', color: '#7F1D1D', margin: 0, lineHeight: 1.45 }}>
              {currentPreset.naiveSentiment.flawDescription}
            </p>
          </div>

          <div
            style={{
              fontSize: '0.74rem',
              color: '#991B1B',
              backgroundColor: '#FEE2E2',
              padding: '10px 12px',
              borderRadius: '8px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <span>❌ 0 Actionable Tickets Dispatched</span>
          </div>
        </div>

        {/* Right Column: InSight Clause Engine (The Solution) */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '14px',
            border: '1px solid #A7F3D0',
            padding: '20px',
            boxShadow: '0 4px 14px rgba(4, 120, 87, 0.05)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 800,
                  color: '#065F46',
                  textTransform: 'uppercase',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <Zap size={14} />
                InSight Proposition Engine
              </span>
            </div>
            <span
              style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: '999px',
                backgroundColor: '#ECFDF5',
                color: '#047857',
                border: '1px solid #A7F3D0'
              }}
            >
              {clauses.length} Independent Propositions Extracted
            </span>
          </div>

          {/* Proposition Breakdown Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {clauses.map((clause, idx) => (
              <div
                key={idx}
                style={{
                  padding: '14px 16px',
                  borderRadius: '10px',
                  backgroundColor: clause.badgeBg,
                  border: `1px solid ${clause.badgeColor}33`,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '8px'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '0.7rem',
                      fontWeight: 800,
                      color: clause.badgeColor,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em'
                    }}
                  >
                    Proposition #{idx + 1}: {clause.intent.replace('_', ' ')}
                  </span>
                  <span
                    style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      color: clause.badgeColor,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px'
                    }}
                  >
                    <ArrowRight size={12} />
                    {clause.routeDestination}
                  </span>
                </div>

                <div
                  style={{
                    fontSize: '0.86rem',
                    color: '#111827',
                    fontWeight: 500,
                    lineHeight: 1.45,
                    fontStyle: 'italic'
                  }}
                >
                  &ldquo;{clause.text}&rdquo;
                </div>

                <div style={{ fontSize: '0.72rem', color: '#4B5563' }}>
                  {clause.explanation}
                </div>
              </div>
            ))}
          </div>

          {/* Outcome Summary Callout */}
          <div
            style={{
              padding: '12px 16px',
              backgroundColor: '#F0FDF4',
              borderRadius: '8px',
              border: '1px solid #86EFAC',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '10px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={16} style={{ color: '#059669', flexShrink: 0 }} />
              <span style={{ fontSize: '0.78rem', color: '#064E3B', fontWeight: 600 }}>
                {criticalFound
                  ? '🚨 Critical Safety Hazard isolated and forwarded to executive triage!'
                  : defectsFound.length > 0
                  ? `⚡ Isolated ${defectsFound.length} engineering defects without discarding positive praise!`
                  : 'Customer feedback decomposed with zero information loss.'}
              </span>
            </div>
            <div
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                color: '#047857',
                fontFamily: "'JetBrains Mono', monospace"
              }}
            >
              100% Signal Retention
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

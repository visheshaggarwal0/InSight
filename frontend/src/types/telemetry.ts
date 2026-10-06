export interface DatasetInfo {
  id: string;
  name: string;
  category: string;
  focus: string;
  review_count: number;
}

export interface RatingDistributionItem {
  star: string;
  count: number;
  percent: number;
  color: string;
}

export interface SentimentSourceItem {
  label: string;
  pos: number;
  neu: number;
  neg: number;
}

export interface SentimentTrendPoint {
  label: string;
  pos: number;
  neu: number;
  neg: number;
}

export interface KeywordCloudItem {
  text: string;
  size?: string;
  color?: string;
  weight?: number;
  count?: number;
}

/**
 * What kind of number a `DynamicInsightItem.metric` actually holds.
 *
 * The backend used to send all three of these through one stringly-typed
 * `percent` field (see `backend/app/api/routes.py`):
 *   - `percentage` — `"72%"`, `"+48%"`
 *   - `count`      — `"412 reviews"`
 *   - `index`      — a drift magnitude derived from PSI
 * The field name claimed the first and delivered all three, so consumers had
 * to re-derive the meaning from the shape of the string.
 */
export type InsightMetricKind = 'percentage' | 'count' | 'index';

export interface InsightMetric {
  /** Display string exactly as the backend formatted it, e.g. `"72%"`. */
  value: string;
  kind: InsightMetricKind;
}

export interface DynamicInsightItem {
  title: string;
  /**
   * The headline figure for this insight. `kind` says what the number is, so
   * a count is never rendered with a percent sign and a PSI index is never
   * rendered as a percentage.
   */
  metric: InsightMetric;
  period: string;
  isWarning: boolean;
  psiAlert: string | null;
}

export interface OverviewMetrics {
  domain: string;
  total_reviews: number;
  sentiment_counts: {
    POSITIVE: number;
    NEUTRAL: number;
    NEGATIVE: number;
  };
  positive_rate: number;
  negative_rate: number;
  pii_redacted_count: number;
  pii_redacted_rate: number;
  critical_themes_count: number;
  active_alerts: number;
  rating_distribution?: RatingDistributionItem[];
  sentiment_by_source?: SentimentSourceItem[];
  sentiment_trend?: SentimentTrendPoint[];
  keyword_cloud?: KeywordCloudItem[];
  recent_insights?: DynamicInsightItem[];
  intent_breakdown?: IntentBreakdown;
}

export interface SampleVerbatim {
  id: string;
  rating: number;
  text: string;
  raw_text?: string;
  batch_or_version: string;
  /** Composed as `"{brand_name} - {product_name}"` by the backend. */
  sku_or_module: string;
  highlight_span?: {
    text: string;
    start: number;
    end: number;
  };
}

export interface ThemeCluster {
  cluster_id: number;
  title: string;
  keywords: string[];
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  review_count: number;
  sentiment_distribution: {
    POSITIVE: number;
    NEUTRAL: number;
    NEGATIVE: number;
  };
  negative_rate: number;
  /**
   * Optional: a cluster with no representative rows (or a payload that
   * omitted the key) has nothing to show, and consumers already guard for it.
   */
  sample_verbatims?: SampleVerbatim[];
}

export interface VerbatimItem {
  id: string;
  domain: string;
  product_name: string;
  /**
   * NOT a stock-keeping unit or a module path. The backend builds it as
   * `"{brand_name} - {product_name}"` (see `real_loader.py`), which is why
   * `brand_name` and `product_id` are surfaced separately below.
   */
  sku_or_module: string;
  /** d2c domain only; absent for other domains. */
  brand_name?: string;
  /** d2c domain only; absent for other domains. */
  product_id?: string;
  batch_or_version: string;
  channel: string;
  rating: number;
  raw_text: string;
  redacted_text: string;
  display_text: string;
  /** Optional: the backend omits the key when no PII was detected. */
  pii_detected?: string[];
  sentiment_pred: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  sentiment_confidence: number;
  cluster_id: number;
  theme_title: string;
  highlight_span?: {
    text: string;
    start: number;
    end: number;
  };
}

export interface DriftAlert {
  severity: 'CRITICAL' | 'WARNING';
  batch_or_version: string;
  psi_score: number;
  surging_theme?: string;
  message: string;
}

export interface BatchTimelineItem {
  batch_or_version: string;
  review_count: number;
  negative_count: number;
  neutral_count: number;
  positive_count: number;
  negative_rate: number;
  /** Population Stability Index: unitless, NOT a percentage. */
  psi: number;
  status: 'STABLE' | 'MODERATE_DRIFT' | 'CRITICAL_DRIFT';
  themes: Record<string, number>;
}

export interface DriftData {
  timeline: BatchTimelineItem[];
  alerts: DriftAlert[];
  batches_analyzed: number;
}

export interface PerClassMetrics {
  precision: number;
  recall: number;
  f1_score: number;
  support: number;
}

export interface ModelGovernanceData {
  model_architecture: string;
  evaluation: {
    sample_size: number;
    accuracy: number;
    macro_precision: number;
    macro_recall: number;
    macro_f1: number;
    brier_score: number;
    classes: string[];
    confusion_matrix: number[][];
    per_class: Record<string, PerClassMetrics>;
  };
}

export interface GeneratedTicket {
  cluster_id: number;
  /** Null when the backend failed to persist the ticket. */
  ticket_id?: string | number | null;
  title: string;
  severity: string;
  ticket_markdown: string;
  incident_volume?: number;
  affected_batch?: string;
  relative_risk?: number;
}

export interface ComplaintVerbatim {
  sentence_id: string;
  review_id: string;
  source_row_index: number;
  sentence_text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface ComplaintClusterItem {
  cluster_id: number;
  title: string;
  label_provenance: string;
  keywords: string[];
  complaint_drivers?: string[];
  sentence_count: number;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  medoid_verbatim: string;
  affected_batch?: string | null;
  relative_risk?: number;
  is_statistically_significant?: boolean;
  verbatims?: ComplaintVerbatim[];
  is_provisional?: boolean;
}

export interface FeatureRequestQuote {
  sentence_id: string;
  review_id: string;
  sentence_text: string;
  start: number;
  end: number;
}

export interface FeatureRequestItem {
  request_id: number;
  title: string;
  keywords: string[];
  feature_themes?: string[];
  vote_count: number;
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  medoid_quote: string;
  sample_quotes: FeatureRequestQuote[];
}

export interface PraiseVerbatim {
  sentence_id: string;
  review_id: string;
  source_row_index: number;
  sentence_text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface PraiseClusterItem {
  cluster_id: number;
  title: string;
  strength_drivers: string[];
  keywords: string[];
  sentence_count?: number;
  praise_count: number;
  delight_score: number;
  delight_tier: 'EXCEPTIONAL' | 'STRONG' | 'NOTABLE';
  medoid_verbatim: string;
  verbatims?: PraiseVerbatim[];
  is_provisional?: boolean;
}

export interface IntentBreakdown {
  total_sentences: number;
  complaints: number;
  praise: number;
  recommendations: number;
  noise: number;
  actionable_count: number;
  actionable_rate_pct: number;
}

export interface CopilotCitation {
  review_id: string;
  rating: number;
  sentiment: string;
  batch_or_version: string;
  channel: string;
  product_name: string;
  snippet: string;
  highlight_span: string;
  full_text: string;
}

export interface CopilotResponse {
  query: string;
  headline: string;
  answer: string;
  verdict: string;
  metrics: Record<string, string>;
  citations: CopilotCitation[];
  recommendations: string[];
  suggested_followups: string[];
}

export interface ExecutiveBriefingData {
  report_title: string;
  generated_at: string;
  scope: string;
  kpis: {
    total_reviews: number;
    csat_score: number;
    positive_sentiment_pct: number;
    negative_sentiment_pct: number;
    neutral_sentiment_pct: number;
    critical_p0_clusters: number;
    active_drift_alarms: number;
  };
  executive_summary: string;
  threat_radar: Array<{
    severity: string;
    title: string;
    count: number;
    blast_radius: string;
    action: string;
  }>;
  value_drivers: Array<{
    title: string;
    count: number;
    delight_score: string;
  }>;
  drift_overview: Array<{
    batch: string;
    psi: number;
    theme: string;
    relative_risk: string;
    significance: string;
  }>;
  sprint_backlog_recommendations: Array<{
    ticket: string;
    priority: string;
    summary: string;
    projected_csat_lift: string;
  }>;
}

export interface BenchmarkCohortStats {
  label: string;
  total_reviews: number;
  avg_rating: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  defect_count: number;
  defect_rate_pct: number;
  praise_count: number;
  praise_rate_pct: number;
  rating_distribution: Record<string, number>;
}

export interface TopicShiftItem {
  theme: string;
  cohort_a_count: number;
  cohort_b_count: number;
  cohort_a_pct: number;
  cohort_b_pct: number;
  rate_delta_pp: number;
  relative_risk: number;
  direction: 'SURGE' | 'DROP' | 'STABLE';
}

export interface BenchmarkComparisonResult {
  cohort_a: BenchmarkCohortStats;
  cohort_b: BenchmarkCohortStats;
  comparison: {
    label_a: string;
    label_b: string;
    rating_delta: number;
    positive_pct_delta: number;
    negative_pct_delta: number;
    defect_rate_delta: number;
    verdict: string;
    verdict_badge: 'CRITICAL_REGRESSION' | 'SIGNIFICANT_IMPROVEMENT' | 'STABLE_PARITY';
    theme_shifts: TopicShiftItem[];
    win_loss_card: {
      winner: string;
      key_advantage: string;
      primary_headwind: string;
    };
  };
}

export interface ActionMatrixItem {
  id: number;
  title: string;
  severity: string;
  incident_count: number;
  blast_radius_pct: number;
  impact_score: number;
  effort: 'LOW' | 'MEDIUM' | 'HIGH';
  story_points: number;
  quadrant: 'QUICK_WIN' | 'CRITICAL_BLOCKER' | 'STRATEGIC_REVAMP' | 'QUALITY_OF_LIFE';
  projected_csat_lift: string;
  csat_lift_val: number;
  recommendation: string;
  estimated_retention_roi: string;
}

export interface ActionMatrixResponse {
  baseline_csat: number;
  projected_target_csat: number;
  max_potential_lift: string;
  items: ActionMatrixItem[];
  quadrant_counts: {
    quick_wins: number;
    critical_blockers: number;
    strategic_revamp: number;
    quality_of_life: number;
  };
}

export interface AnomalySimulationResponse {
  status: string;
  scenario: string;
  alert: DriftAlert;
  emergency_incident_ticket: {
    title: string;
    priority: string;
    psi_score: number;
    relative_risk: string;
    p_value: number;
    affected_cohort: string;
    blast_radius: string;
    action_required: string;
  };
}




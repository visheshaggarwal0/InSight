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
}

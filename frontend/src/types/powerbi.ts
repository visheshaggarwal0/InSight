export interface PowerBIEmbedResponse {
  status: 'success' | 'unconfigured' | 'error';
  embed_token?: string;
  embed_url?: string;
  report_id?: string;
  report_title?: string;
  workspace_id?: string;
  dataset_id?: string;
  expiration?: string;
  message?: string;
  missing_keys?: string[];
  credentials_present?: {
    tenant_id: boolean;
    client_id: boolean;
    client_secret: boolean;
    workspace_id: boolean;
    report_id: boolean;
    dataset_id: boolean;
  };
  setup_guide?: {
    step_1: string;
    step_2: string;
    step_3: string;
    step_4: string;
  };
  error_message?: string;
  diagnostics?: Record<string, boolean>;
}

export interface PowerBIConfig {
  embed_url: string;
  report_title: string;
  is_configured: boolean;
  demo_url: string;
  last_updated?: string | null;
}

export interface PowerBISummary {
  domain: string;
  total_reviews: number;
  net_sentiment_score: number;
  positive_rate_pct: number;
  negative_rate_pct: number;
  neutral_rate_pct: number;
  defect_surge_rate_pct: number;
  silent_defects_count: number;
  actionable_rate_pct: number;
  pii_compliance_rate_pct: number;
  total_themes: number;
  critical_themes: number;
}

export interface DAXMeasure {
  id: string;
  name: string;
  category: string;
  description: string;
  dax: string;
}

export interface PowerBIGuide {
  api_urls: {
    csv_feed: string;
    json_feed: string;
    themes_feed: string;
    drift_feed: string;
    pbids_file: string;
  };
  power_query_m: string;
  dax_measures: DAXMeasure[];
  star_schema: {
    fact_table: string;
    dimension_tables: string[];
  };
}

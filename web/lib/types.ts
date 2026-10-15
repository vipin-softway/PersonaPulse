// Mirrors api/app/services/aggregate.py. Keep the two in sync.

export type Product = {
  name: string;
  description: string;
  price_inr: number;
  pack_size: string;
  channel: string;
  image_url?: string | null;
};

export type SegmentResult = {
  segment_id: string;
  segment_name: string;
  share: number | null;
  n: number;
  would_buy_pct: number;
  avg_intent: number | null;
  avg_wtp_inr: number | null;
};

export type CountedText = { text: string; count: number; pct: number };

export type Quote = {
  persona_id: string;
  persona_name: string;
  age: number | null;
  city: string | null;
  segment_name: string;
  would_buy: boolean;
  purchase_intent: number | null;
  main_reason: string | null;
  quote: string;
};

export type Insights = {
  headline: string;
  summary: string;
  key_findings: string[];
  recommendations: string[];
};

export type PriceInsight = {
  price_inr: number;
  median_wtp_inr: number | null;
  pct_wtp_at_or_above_price: number | null;
  buckets: { from_inr: number; to_inr: number; count: number }[];
};

export type VariantResult = {
  variant: string;
  product: Product;
  n_personas: number;
  overall: { would_buy_pct: number; avg_intent: number | null; avg_wtp_inr: number | null };
  segments: SegmentResult[];
  price: PriceInsight;
  top_objections: CountedText[];
  top_likes: CountedText[];
  quotes: Quote[];
  insights: Insights | null;
};

export type Suggestion = {
  variant_id: string;
  title: string;
  changes: string[];
  rationale: string;
  product: Product;
};

export type TestResult = {
  test_id: string;
  label: string;
  created_at: string;
  is_demo: boolean;
  is_placeholder: boolean;
  variants: VariantResult[];
  suggestions: Suggestion[];
};

export type NewTestInput = {
  name: string;
  description: string;
  price_inr: number;
  pack_size: string;
  channel: string;
  image_base64?: string;
  image_mime?: string;
};

export type BacktestProduct = {
  product_id: string;
  product_name: string;
  price_inr: number;
  actual_rating: number;
  predicted_rating: number;
  baseline_rating: number;
};

export type Backtest = {
  label: string;
  is_placeholder: boolean;
  category: string;
  n_holdout: number;
  baseline_description: string;
  metrics: { mae_model: number; mae_baseline: number };
  products: BacktestProduct[];
};

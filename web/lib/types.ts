// Mirrors api/app/services/aggregate.py. Keep the two in sync.

export type Product = {
  name: string;
  description: string;
  price_inr: number;
  pack_size: string;
  channel: string;
  competitors?: string | null;
  has_image?: boolean;
};

export type SegmentResult = {
  segment_id: string;
  segment_name: string;
  share: number | null;
  n: number;
  would_buy_pct: number; // % answering "yes"
  maybe_pct: number;
  no_pct: number;
  avg_intent: number | null;
  avg_wtp_inr: number | null;
  median_wtp_inr: number | null;
};

export type WouldBuy = "yes" | "maybe" | "no";

export type CountedText = { text: string; count: number; pct: number };

export type Quote = {
  persona_id: string;
  persona_name: string;
  age: number | null;
  city: string | null;
  segment_name: string;
  would_buy: WouldBuy;
  purchase_intent: number | null;
  main_reason: string | null;
  quote: string;
};

// Prompt 6 output.
export type Insights = {
  headline: string;
  overall_verdict: "launch" | "launch_with_changes" | "rethink";
  best_segments: { segment_name: string; why: string }[];
  weakest_segments: { segment_name: string; why: string }[];
  price_insight: string;
  top_3_objections: { objection: string; segments_affected: string[] }[];
  top_3_strengths: string[];
  standout_quotes: string[];
  recommended_target_segment: string;
  caveat: string;
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
  overall: { would_buy_pct: number; maybe_pct: number; avg_intent: number | null; avg_wtp_inr: number | null };
  segments: SegmentResult[];
  price: PriceInsight;
  top_objections: CountedText[];
  top_likes: CountedText[];
  quotes: Quote[];
  insights: Insights | null;
  insights_pending?: boolean; // Prompt 6 is still running in the background
};

// One of Prompt 7's "variants".
export type Suggestion = {
  variant_id: string;
  title: string;
  changes: string[];
  objections_addressed: string[];
  expected_effect: string;
  risk: string;
  updated_product: {
    product_name: string;
    product_description: string;
    price_inr: number;
    pack_size: string;
    channel: string;
  };
  imagen_prompt: string | null;
};

// How a result was produced, shown on the results page so judges can see it ran live.
export type RunInfo = {
  mode: "live" | "saved_demo";
  run_at: string; // ISO time the simulation ran
  personas: number;
  gemini_calls?: number | null;
  duration_s?: number | null;
  model?: string | null;
};

export type TestResult = {
  test_id: string;
  panel?: string; // customer panel id, see lib/panels.ts
  label: string;
  created_at: string;
  is_demo: boolean;
  is_placeholder: boolean;
  run?: RunInfo;
  variants: VariantResult[];
  suggestions: Suggestion[];
};

export type NewTestInput = {
  name: string;
  description: string;
  price_inr: number;
  pack_size: string;
  channel: string;
  panel: string;
  competitors?: string;
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
  calibrated_rating?: number; // predicted + offset learned on the other hidden products
  n_personas?: number;
  predicted_complaints?: CountedText[];
  actual_complaints?: CountedText[];
  complaint_hits?: number;
  complaint_total?: number;
};

export type Backtest = {
  label: string;
  is_placeholder: boolean;
  category: string;
  n_holdout: number;
  baseline_description: string;
  metrics: {
    mae_model: number;
    mae_baseline: number;
    correlation?: number | null;
    complaint_hits?: number; // real top-3 complaints matched in the predicted top 5
    complaint_total?: number;
    mae_raw?: number; // before calibration
    bias?: number; // average predicted minus actual (negative = harsher than real buyers)
    pairs_correct?: number; // product pairs ordered the same way as real ratings
    pairs_total?: number;
  };
  n_personas?: number;
  n_predictions?: number;
  run_at?: string;
  products: BacktestProduct[];
};

/** POST /lookup: product details found with Gemini + Google Search (Prompt 9). */
export type ProductLookup = {
  found: boolean;
  notes: string;
  product_name?: string;
  product_description?: string;
  price_inr?: number | null;
  pack_size?: string;
  channel?: string;
  competitors_text?: string;
  suggested_panel?: string | null;
  panel_fit?: "good" | "stretch" | "poor" | null;
  searched?: string[];
  sources?: { title: string; url: string }[];
};

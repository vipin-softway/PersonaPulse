"""Create the BigQuery dataset and all PersonaPulse tables. Safe to re-run.

    python scripts/create_tables.py            # create anything missing
    python scripts/create_tables.py --print    # just print the schemas

Free-form Gemini output (signals, persona profiles, insights) is stored as
JSON columns so the prompts can evolve without schema migrations.
"""

from __future__ import annotations

import argparse

from google.cloud import bigquery

from common import BQ_DATASET, BQ_LOCATION, bq_client, require_project

F = bigquery.SchemaField
S, I, FL, B, J, T = "STRING", "INT64", "FLOAT64", "BOOL", "JSON", "TIMESTAMP"
REQ, REP = "REQUIRED", "REPEATED"

TABLES: dict[str, tuple[str, list[bigquery.SchemaField]]] = {
    "reviews_raw": ("One row per review, cleaned from the Kaggle Amazon Sales dataset.", [
        F("review_id", S, REQ), F("panel", S, description="Customer panel id (api/app/panels.py)"),
        F("product_id", S, REQ), F("product_name", S), F("category", S),
        F("price_inr", FL), F("list_price_inr", FL),
        F("product_rating", FL, description="Product's average Amazon rating (the dataset has no per-review rating)"),
        F("rating_count", I),
        F("about_product", S), F("review_title", S), F("review_content", S),
        F("is_holdout", B, description="True for back-test products hidden from persona building"),
        F("loaded_at", T),
    ]),
    "review_signals": ("Prompt 1 output: what each review's author cares about.", [
        F("review_id", S, REQ), F("panel", S), F("product_id", S), F("signals", J, description="Full Prompt 1 signal object"),
        F("price_sensitivity", S), F("sentiment", S), F("usage_context", S),
        F("model", S), F("created_at", T),
    ]),
    "segments": ("Prompt 2 output: customer segments and their share of the market.", [
        F("segment_id", S, REQ), F("panel", S), F("name", S), F("description", S),
        F("share", FL, description="share_percent / 100"), F("price_sensitivity", S),
        F("profile", J, description="Full Prompt 2 segment object"), F("model", S), F("created_at", T),
    ]),
    "personas": ("Prompt 3 output: individual AI customers grounded in real reviews.", [
        F("persona_id", S, REQ), F("panel", S), F("segment_id", S, REQ), F("segment_name", S), F("name", S), F("age", I),
        F("gender", S), F("city", S), F("city_tier", S), F("occupation", S), F("monthly_income_band_inr", S),
        F("price_ceiling_inr", FL), F("skepticism", S), F("preferred_language", S),
        F("profile", J, description="Full Prompt 3 persona object incl. memories (sent to Prompts 4 and 8)"),
        F("is_live", B, description="Included in live tests (capped at MAX_LIVE_PERSONAS)"),
        F("model", S), F("created_at", T),
    ]),
    "tests": ("One row per tested product variant ('original', 'v1', ...).", [
        F("test_id", S, REQ), F("variant", S, REQ), F("panel", S), F("product", J), F("parent_variant", S),
        F("status", S), F("n_personas", I), F("is_demo", B), F("client_ip_hash", S), F("created_at", T),
        F("run", J, description="How it ran: mode, personas, gemini_calls, duration_s, model"),
        F("image_uri", S, description="gs:// URI of the uploaded product image, if any"),
    ]),
    "simulation_results": ("Prompt 4 output: one persona's reaction to one variant.", [
        F("test_id", S, REQ), F("variant", S, REQ), F("persona_id", S, REQ), F("segment_id", S),
        F("purchase_intent", FL, description="1-5"), F("would_buy", S, description="yes | maybe | no"),
        F("willingness_to_pay_inr", FL),
        F("top_likes", S, REP), F("top_objections", S, REP), F("main_reason", S), F("quote", S),
        F("first_impression", S), F("what_would_change_my_mind", S), F("created_at", T),
    ]),
    "insights": ("Prompt 6 (summary), 7 (suggestions) and optional 5 (focus group) output.", [
        F("test_id", S, REQ), F("variant", S), F("kind", S, description="'summary' | 'suggestions' | 'focus_group'"),
        F("payload", J), F("model", S), F("created_at", T),
    ]),
    "backtest_results": ("Prompt 8 output: predicted vs. actual ratings on hidden products.", [
        F("run_id", S, REQ), F("product_id", S, REQ), F("product_name", S), F("price_inr", FL),
        F("predicted_rating", FL), F("actual_rating", FL), F("baseline_rating", FL),
        F("predicted_complaints", J, description="Top predicted complaints with counts"),
        F("actual_complaints", J, description="Top real complaints (real reviews through Prompt 1)"),
        F("complaint_hits", I, description="How many of the top 3 real complaints appear in the top 5 predicted"),
        F("n_personas", I), F("created_at", T),
    ]),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", action="store_true", help="print schemas without touching BigQuery")
    args = ap.parse_args()

    if args.print:
        for name, (desc, schema) in TABLES.items():
            print(f"\n{name}: {desc}")
            for f in schema:
                print(f"  {f.name:28} {f.field_type}{' ' + f.mode if f.mode != 'NULLABLE' else ''}")
        return

    client = bq_client()
    ds = bigquery.Dataset(f"{require_project()}.{BQ_DATASET}")
    ds.location = BQ_LOCATION
    client.create_dataset(ds, exists_ok=True)
    print(f"Dataset {ds.dataset_id} ready ({BQ_LOCATION})")

    for name, (desc, schema) in TABLES.items():
        t = bigquery.Table(f"{ds.project}.{ds.dataset_id}.{name}", schema=schema)
        t.description = desc
        if name in ("simulation_results", "tests", "insights"):
            t.time_partitioning = bigquery.TimePartitioning(field="created_at")
        existing = client.create_table(t, exists_ok=True)
        # Tables created by an older version of this script: append any new (nullable) columns.
        have = {f.name for f in existing.schema}
        missing = [f for f in schema if f.name not in have]
        if missing:
            existing.schema = list(existing.schema) + [
                bigquery.SchemaField(f.name, f.field_type, "NULLABLE" if f.mode == "REQUIRED" else f.mode, description=f.description)
                for f in missing
            ]
            client.update_table(existing, ["schema"])
        print(f"  table {name} ready{f' (added {", ".join(f.name for f in missing)})' if missing else ''}")


if __name__ == "__main__":
    main()

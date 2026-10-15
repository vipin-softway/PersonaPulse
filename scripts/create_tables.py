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
        F("review_id", S, REQ), F("product_id", S, REQ), F("product_name", S), F("category", S),
        F("price_inr", FL), F("list_price_inr", FL), F("rating", FL), F("rating_count", I),
        F("about_product", S), F("review_title", S), F("review_content", S),
        F("is_holdout", B, description="True for back-test products hidden from persona building"),
        F("loaded_at", T),
    ]),
    "review_signals": ("Prompt 1 output: what each review's author cares about.", [
        F("review_id", S, REQ), F("product_id", S), F("signals", J), F("price_sensitivity", S),
        F("model", S), F("created_at", T),
    ]),
    "segments": ("Prompt 2 output: customer segments and their share of the market.", [
        F("segment_id", S, REQ), F("name", S), F("description", S), F("share", FL),
        F("profile", J), F("model", S), F("created_at", T),
    ]),
    "personas": ("Prompt 3 output: individual AI customers grounded in real reviews.", [
        F("persona_id", S, REQ), F("segment_id", S, REQ), F("name", S), F("age", I), F("city", S),
        F("income_band", S), F("profile", J, description="Full persona JSON incl. priorities, dislikes, price ceiling"),
        F("memory_review_ids", S, REP), F("is_live", B, description="Included in live tests (capped at MAX_LIVE_PERSONAS)"),
        F("model", S), F("created_at", T),
    ]),
    "tests": ("One row per tested product variant ('original', 'v1', ...).", [
        F("test_id", S, REQ), F("variant", S, REQ), F("product", J), F("parent_variant", S),
        F("status", S), F("n_personas", I), F("is_demo", B), F("client_ip_hash", S), F("created_at", T),
    ]),
    "simulation_results": ("Prompt 4 output: one persona's reaction to one variant.", [
        F("test_id", S, REQ), F("variant", S, REQ), F("persona_id", S, REQ), F("segment_id", S),
        F("purchase_intent", FL), F("would_buy", B), F("willingness_to_pay_inr", FL),
        F("top_likes", S, REP), F("top_objections", S, REP), F("main_reason", S), F("quote", S),
        F("created_at", T),
    ]),
    "insights": ("Prompt 6 (summary) and Prompt 7 (improvement suggestions) output.", [
        F("test_id", S, REQ), F("variant", S), F("kind", S, description="'summary' or 'suggestions'"),
        F("payload", J), F("model", S), F("created_at", T),
    ]),
    "backtest_results": ("Prompt 8 output: predicted vs. actual ratings on hidden products.", [
        F("run_id", S, REQ), F("product_id", S, REQ), F("product_name", S), F("price_inr", FL),
        F("predicted_rating", FL), F("actual_rating", FL), F("baseline_rating", FL),
        F("predicted_complaints", J), F("actual_complaints", J), F("n_personas", I), F("created_at", T),
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
        client.create_table(t, exists_ok=True)
        print(f"  table {name} ready")


if __name__ == "__main__":
    main()

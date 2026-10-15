"""BigQuery AI engine for Prompt 1: run Gemini inside BigQuery with AI.GENERATE_TEXT.

Rendered prompts (verbatim from docs/prompts.md) are loaded into a request
table; one SQL statement sends every row to the remote Gemini model created
by setup_bqai.sh and writes the replies to a response table. JSON mode and
the system instruction are passed through model_params, mirroring the
Python engine. Rows that fail are returned so the caller can retry them.
"""

from __future__ import annotations

import json

from google.cloud import bigquery

from common import BQ_DATASET, bq_client, require_project

REQUESTS, RESPONSES, MODEL = "p01_requests", "p01_responses", "gemini_flash"


def _model_params(system: str, temperature: float, inline_system: bool) -> str:
    params: dict = {"generation_config": {"response_mime_type": "application/json", "temperature": temperature,
                                          "max_output_tokens": 8192}}
    if not inline_system:
        params["system_instruction"] = {"parts": [{"text": system}]}
    return json.dumps(params, ensure_ascii=False)


def generate(rows: list[dict], system: str, temperature: float) -> dict[str, tuple[str | None, str]]:
    """rows: [{batch_id, prompt}]. Returns {batch_id: (text_or_None, status)}."""
    client, project = bq_client(), require_project()
    ds = f"{project}.{BQ_DATASET}"
    client.load_table_from_json(
        rows, f"{ds}.{REQUESTS}",
        job_config=bigquery.LoadJobConfig(
            schema=[bigquery.SchemaField("batch_id", "STRING"), bigquery.SchemaField("prompt", "STRING")],
            write_disposition="WRITE_TRUNCATE"),
    ).result()

    def run(inline_system: bool) -> None:
        prompt_sql = "CONCAT(@system, '\\n\\n', prompt)" if inline_system else "prompt"
        # model_params must be a string literal, so embed it as a raw string (keeps JSON escapes intact).
        model_params = _model_params(system, temperature, inline_system)
        if "'''" in model_params:
            raise ValueError("model_params contains ''' and can't be embedded as a literal")
        sql = f"""
            CREATE OR REPLACE TABLE `{ds}.{RESPONSES}` AS
            SELECT batch_id, result, status
            FROM AI.GENERATE_TEXT(
              MODEL `{ds}.{MODEL}`,
              (SELECT batch_id, {prompt_sql} AS prompt FROM `{ds}.{REQUESTS}`),
              STRUCT(r'''{model_params}''' AS model_params))"""
        params = [bigquery.ScalarQueryParameter("system", "STRING", system)]
        client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params)).result(timeout=1800)

    try:
        run(inline_system=False)
    except Exception as e:  # noqa: BLE001
        # If this BigQuery version rejects system_instruction in model_params, send it inline instead.
        if "system_instruction" not in str(e):
            raise
        print("  model_params.system_instruction not accepted; sending the system instruction inline")
        run(inline_system=True)

    out = {}
    for r in client.query(f"SELECT batch_id, result, status FROM `{ds}.{RESPONSES}`").result():
        out[r.batch_id] = (r.result if not r.status else None, r.status or "")
    return out

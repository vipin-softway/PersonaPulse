#!/usr/bin/env bash
# One-time setup for BigQuery AI: a Vertex AI connection and a remote Gemini model,
# so Prompt 1 can run inside BigQuery with AI.GENERATE_TEXT (extract_signals.py --engine bigquery).
# Needs billing enabled and the Vertex AI API on. Safe to re-run.
set -euo pipefail

PROJECT="${GCP_PROJECT:?set GCP_PROJECT}"
DATASET="${BQ_DATASET:-personapulse}"
LOCATION="${BQ_LOCATION:-US}"
MODEL_ENDPOINT="${GEMINI_FLASH_MODEL:-gemini-2.5-flash}"
CONN="vertex_conn"

echo "Creating connection ${LOCATION}.${CONN} (ignore 'already exists')"
bq mk --connection --location="$LOCATION" --project_id="$PROJECT" --connection_type=CLOUD_RESOURCE "$CONN" || true

SA=$(bq show --connection --format=json "$PROJECT.$LOCATION.$CONN" | python3 -c 'import json,sys; print(json.load(sys.stdin)["cloudResource"]["serviceAccountId"])')
echo "Granting Vertex AI User to the connection's service account: $SA"
gcloud projects add-iam-policy-binding "$PROJECT" --member="serviceAccount:$SA" --role=roles/aiplatform.user --condition=None --quiet >/dev/null

echo "Waiting 60s for the IAM grant to propagate"
sleep 60

echo "Creating remote model $DATASET.gemini_flash -> $MODEL_ENDPOINT"
bq query --use_legacy_sql=false --project_id="$PROJECT" \
  "CREATE OR REPLACE MODEL \`$PROJECT.$DATASET.gemini_flash\`
   REMOTE WITH CONNECTION \`$PROJECT.$(echo "$LOCATION" | tr '[:upper:]' '[:lower:]').$CONN\`
   OPTIONS (ENDPOINT = '$MODEL_ENDPOINT')"

echo "Done. Try: python extract_signals.py --engine bigquery --panel home --limit 40"

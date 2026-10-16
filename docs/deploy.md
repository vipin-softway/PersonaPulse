# Deploying to Cloud Run

These are the exact steps used for the live deployment. Run from the repo root with the gcloud CLI,
signed in as a project owner (`gcloud auth login`).

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
gcloud config set project $PROJECT_ID
```

## One-time setup

```bash
gcloud services enable aiplatform.googleapis.com bigquery.googleapis.com bigqueryconnection.googleapis.com \
  storage.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com

gcloud artifacts repositories create personapulse --repository-format=docker --location=$REGION

# Runtime identity for the API (no keys: Cloud Run uses it via Application Default Credentials)
gcloud iam service-accounts create personapulse-api --display-name="PersonaPulse API"
export API_SA=personapulse-api@$PROJECT_ID.iam.gserviceaccount.com
for ROLE in roles/aiplatform.user roles/bigquery.dataEditor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$API_SA --role=$ROLE --condition=None
done

# Private bucket for uploaded product images
export BUCKET=$PROJECT_ID-personapulse-images
gcloud storage buckets create gs://$BUCKET --location=$REGION \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets add-iam-policy-binding gs://$BUCKET \
  --member=serviceAccount:$API_SA --role=roles/storage.objectAdmin
```

Then build the data (BigQuery dataset, reviews, signals, segments, personas, back-test): see
"Data pipeline" in the [README](../README.md). BigQuery AI needs `scripts/setup_bqai.sh` once.

## 1. Deploy the API

`--no-cpu-throttling` keeps CPU available after a response is sent, so the background AI summary
(Prompt 6) finishes. With `--min-instances 0` it still costs nothing when idle.

```bash
gcloud run deploy personapulse-api \
  --source api --region $REGION --service-account $API_SA --allow-unauthenticated \
  --min-instances 0 --max-instances 3 --concurrency 20 --timeout 300 --memory 1Gi --cpu 1 \
  --no-cpu-throttling \
  --set-env-vars "^;^GCP_PROJECT=$PROJECT_ID;GCP_LOCATION=global;BQ_DATASET=personapulse;GCS_BUCKET=$BUCKET;GEMINI_FLASH_MODEL=gemini-3.8-flash;GEMINI_PRO_MODEL=gemini-3.1-pro-preview;GEMINI_PRO_FALLBACK_MODEL=gemini-2.5-pro;MAX_LIVE_PERSONAS=30;GEMINI_CONCURRENCY=30;ALLOWED_ORIGINS=http://localhost:3000"

export API_URL=$(gcloud run services describe personapulse-api --region $REGION --format='value(status.url)')
curl $API_URL/health
```

## 2. Build and deploy the web app

`NEXT_PUBLIC_API_URL` is baked in at build time, so build with Cloud Build, then deploy the image.

```bash
export WEB_IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/personapulse/web
gcloud builds submit web --config web/cloudbuild.yaml --substitutions=_API_URL=$API_URL,_IMAGE=$WEB_IMAGE
gcloud run deploy personapulse-web --image $WEB_IMAGE --region $REGION --allow-unauthenticated \
  --min-instances 0 --max-instances 3 --memory 512Mi
export WEB_URL=$(gcloud run services describe personapulse-web --region $REGION --format='value(status.url)')
```

## 3. Allow the web origin on the API (CORS)

```bash
gcloud run services update personapulse-api --region $REGION \
  --update-env-vars "^;^ALLOWED_ORIGINS=$WEB_URL,http://localhost:3000"
echo "Open $WEB_URL"
```

`^;^` switches the gcloud list delimiter so the comma inside the value survives.

## Redeploying

- **API:** rerun step 1 with `ALLOWED_ORIGINS=$WEB_URL,http://localhost:3000` in the env vars (or use
  `--update-env-vars`, which keeps existing values).
- **Web:** rerun both commands in step 2.

## Budget alert (do this once)

Billing → Budgets & alerts in the console, or:

```bash
gcloud billing budgets create --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="PersonaPulse cap" --budget-amount=100USD \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

## Troubleshooting

- **Gemini 404 / model not found:** the newest Gemini models are served from the `global` location
  (`GCP_LOCATION=global`), not `us-central1`. If a preview Pro model is withdrawn or rate-limited, calls
  fall back to `GEMINI_PRO_FALLBACK_MODEL` automatically.
- **Web build fails at `npm install` / `npm ci`:** the image uses Node 24 to match the lockfile; keep
  `npm install` (not `npm ci`) so Linux-only optional packages resolve.
- **AI summary never appears on Cloud Run:** the API must run with `--no-cpu-throttling`.
- **Gemini can't read an uploaded image (`gs://` permission error):** grant the Vertex AI service agent
  (`service-PROJECT_NUMBER@gcp-sa-aiplatform.iam.gserviceaccount.com`) `roles/storage.objectViewer` on the bucket.
- **`AI.GENERATE_TEXT` permission errors:** rerun `scripts/setup_bqai.sh`; IAM grants can take a few minutes to apply.
- **`--allow-unauthenticated` fails with an org policy error:** the org enforces Domain Restricted Sharing; an
  admin must allow `allUsers` for this project.
- **Home page shows "Can't reach the PersonaPulse API":** check `ALLOWED_ORIGINS` matches `$WEB_URL` exactly
  (no trailing slash) and the web image was built with the right `_API_URL`.

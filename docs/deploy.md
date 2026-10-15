# Deploying to Cloud Run

Run from the repo root. Requires the gcloud CLI, logged in as a project owner/editor.

```bash
export PROJECT_ID=your-project-id
export REGION=us-central1
gcloud config set project $PROJECT_ID
```

## One-time setup

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com aiplatform.googleapis.com bigquery.googleapis.com

gcloud artifacts repositories create personapulse \
  --repository-format=docker --location=$REGION

# Runtime identity for the API (no keys; Cloud Run uses it via ADC)
gcloud iam service-accounts create personapulse-api --display-name="PersonaPulse API"
export API_SA=personapulse-api@$PROJECT_ID.iam.gserviceaccount.com
for ROLE in roles/aiplatform.user roles/bigquery.dataEditor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member=serviceAccount:$API_SA --role=$ROLE --condition=None
done

# BigQuery dataset
bq --location=US mk --dataset $PROJECT_ID:personapulse
```

## 1. Deploy the API

```bash
gcloud run deploy personapulse-api \
  --source api \
  --region $REGION \
  --service-account $API_SA \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 3 \
  --concurrency 20 --timeout 300 --memory 1Gi --cpu 1 \
  --set-env-vars GCP_PROJECT=$PROJECT_ID,GCP_LOCATION=$REGION,BQ_DATASET=personapulse,GEMINI_FLASH_MODEL=gemini-2.5-flash,GEMINI_PRO_MODEL=gemini-2.5-pro,MAX_LIVE_PERSONAS=30,ALLOWED_ORIGINS=http://localhost:3000

export API_URL=$(gcloud run services describe personapulse-api --region $REGION --format='value(status.url)')
curl $API_URL/health
```

## 2. Build and deploy the web app

`NEXT_PUBLIC_API_URL` is baked in at build time, so build with Cloud Build, then deploy the image.

```bash
export WEB_IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/personapulse/web

gcloud builds submit web --config web/cloudbuild.yaml \
  --substitutions=_API_URL=$API_URL,_IMAGE=$WEB_IMAGE

gcloud run deploy personapulse-web \
  --image $WEB_IMAGE \
  --region $REGION \
  --allow-unauthenticated \
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

- API: rerun step 1 (keep the latest `ALLOWED_ORIGINS`, or use `--update-env-vars` instead of `--set-env-vars`).
- Web: rerun the two commands in step 2.

## Budget alert (do this once)

Billing → Budgets & alerts in the console, or:

```bash
gcloud billing budgets create --billing-account=YOUR_BILLING_ACCOUNT_ID \
  --display-name="PersonaPulse cap" --budget-amount=50USD \
  --threshold-rule=percent=0.5 --threshold-rule=percent=0.9 --threshold-rule=percent=1.0
```

## Troubleshooting

- **`--allow-unauthenticated` fails with an org policy error**: the org enforces Domain Restricted Sharing. An org admin must allow `allUsers` for this project, or judges can't open the link.
- **`--source` build fails with a permission error**: grant the Cloud Build service account (`PROJECT_NUMBER-compute@developer.gserviceaccount.com` on newer projects) `roles/run.builder`.
- **Home page shows "Can't reach the PersonaPulse API"**: check `ALLOWED_ORIGINS` on the API matches `$WEB_URL` exactly (no trailing slash), and that the web image was built with the right `_API_URL`.
- **Gemini 404 / model not found**: set `GEMINI_FLASH_MODEL` / `GEMINI_PRO_MODEL` to a model available in `$REGION` (check Vertex AI Model Garden).

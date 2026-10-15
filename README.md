# PersonaPulse

**Self-serve AI focus groups for every small business in Asia.** Test a product concept on ~100 AI customer personas grounded in real product reviews, then see purchase intent by segment, objections, quotes, AI insights, improved variants, and a back-test proving accuracy on hidden products.

> All results are **AI-simulated customers**. Personas are built from public product review data.

Google Cloud AI Builder Cup 2026 · Retail & Commerce track.

## Repo layout

```
api/      FastAPI (Python 3.11) – Gemini on Vertex AI + BigQuery
web/      Next.js (App Router, TypeScript, Tailwind, Recharts)
scripts/  one-time data jobs (reviews → signals → segments → personas, back-test)
docs/     prompts.md, architecture.md, deploy.md
```

## Run locally

Prereqs: Python 3.11, Node 22, gcloud CLI.

```bash
gcloud auth application-default login   # ADC; no API keys anywhere
cp .env.example .env                    # fill in GCP_PROJECT etc.
```

API (http://localhost:8080):

```bash
cd api
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
set -a; source ../.env; set +a
uvicorn app.main:app --reload --port 8080
```

Web (http://localhost:3000):

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

## Deploy

See [docs/deploy.md](docs/deploy.md).

## Security

- Authentication uses Application Default Credentials (the Cloud Run service account). No API keys or secrets are stored in this repo.
- `.env`, `.env.local` and credential files are git-ignored; only `.env.example` is committed.

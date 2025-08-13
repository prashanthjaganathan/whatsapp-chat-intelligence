# Deploying to Vercel

This repo is configured to deploy the FastAPI backend to Vercel's Python runtime.

## What was added
- `api/index.py`: entrypoint that exposes the FastAPI `app`
- `vercel.json`: Vercel configuration and routing
- `requirements.txt` (root): points to `backend/requirements.txt`
- `backend/app/main.py`: defer DB initialization to startup
- Python packages marked with `__init__.py`

## Environment variables
Set these in your Vercel Project Settings > Environment Variables:
- `DATABASE_URL` (e.g., from Neon, Supabase, or RDS)
- `REDIS_URL` (e.g., Upstash)
- `ELASTICSEARCH_URL` (e.g., Bonsai/Elastic Cloud)
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `SECRET_KEY`
- `API_V1_STR` (default `/api/v1`)
- `PROJECT_NAME`

## Deploy steps
1. Push this repo to GitHub
2. In Vercel, "Add New… > Project" and import the repo
3. Framework preset: Other
4. Root Directory: repository root
5. Build & Output:
   - Build Command: none
   - Output Directory: not required
   - Install Command: `pip install -r requirements.txt`
6. Click Deploy

The app will be served from `api/index.py` on Vercel, with docs at `/docs`.

## Notes
- Vercel is serverless. Long-lived connections and background workers should use separate services.
- Use managed DBs like Neon/Supabase for Postgres and Upstash for Redis.

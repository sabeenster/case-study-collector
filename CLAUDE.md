# Case Study Collector — Project Rules

## Purpose
Collect metrics snapshots and screenshots from brand partners to build Agentway case studies.

## Standard Agent Repo Structure
See the linkedin-post-automation CLAUDE.md for the canonical pattern. This repo follows it exactly.

## Deployment Rules — NEVER DEVIATE
- **Platform:** Railway (railway.app) with nixpacks builder
- **NO DOCKER. EVER.**
- **NO pyproject.toml** — use requirements.txt only
- **NO src/ layout** — use app/ folder with run.py at root
- **Procfile:** `web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}`
- **Env vars:** Set in Railway dashboard, override config.yaml via os.getenv()

## How to Run

```bash
python run.py serve                    # Start web UI at localhost:8000
python run.py brands                   # List all brands
python run.py generate-case-study --brand "Dippin' Daisy's"
python run.py email-case-study --brand "Dippin' Daisy's"
```

## Data Storage
- SQLite at data/casestudies.db
- Screenshots in uploads/ (gitignored)
- Both directories are auto-created on startup

## Email Notifications
- Use Resend (resend Python package)
- Env vars: RESEND_API_KEY, RESEND_FROM_EMAIL, RESEND_TO_EMAIL
- Skip silently if vars not set

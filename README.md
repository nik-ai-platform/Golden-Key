# Golden-Key

Nik AI Platform with FastAPI backend, analytics endpoints, and a static frontend dashboard.

## Quick Start (One Command)

From the repository root:

```powershell
docker compose up --build
```

Services:

- Frontend + reverse proxy: `http://localhost:8080`
- Backend API (through proxy): `http://localhost:8080/api/v1`
- Postgres host port: `5433`
- Redis host port: `6379`

## Environment Files

- `.env` - Local defaults for development
- `.env.development` - Local development template
- `.env.test` - Test/CI template
- `.env.production` - Production-oriented template values

## Production Configuration

Production should be configured with managed infrastructure and secret injection, not checked-in credentials.

- Use [/.env.production](.env.production) as the source of truth for production variables.
- Inject `DATABASE_URL`, `SECRET_KEY`, `ODDS_API_KEY`, and any deploy tokens from GitHub Secrets or your platform secret store.
- Terminate TLS at the reverse proxy using [deploy/nginx/production.conf](deploy/nginx/production.conf).
- Keep the application server behind the proxy; do not expose FastAPI directly to the public internet.
- Use a managed PostgreSQL service with SSL, backups, and point-in-time recovery.

Health endpoints:

- `GET /health` returns API liveness.
- `GET /ready` checks database connectivity and readiness for traffic.

Operational guidance:

- Structured logging is enabled in the backend logger setup.
- Avoid logging passwords, JWTs, or secrets.
- Track response times, database latency, import duration, scheduler success, and HTTP error rates.
- Run nightly database backups and periodically verify restores.
- Promote changes through local validation, CI, staging, then production.

## CI/CD

GitHub Actions now uses split workflows:

- [backend.yml](.github/workflows/backend.yml) for backend migrations, lint, tests, coverage, and compile checks
- [frontend.yml](.github/workflows/frontend.yml) for lint, formatting, E2E tests, and build verification
- [docker.yml](.github/workflows/docker.yml) for backend/frontend image build validation

Suggested promotion flow:

1. Merge to `main`
2. CI passes
3. Docker images build
4. Deploy to staging
5. Smoke tests pass
6. Deploy to production

### Deployment Secrets

Configure these repository secrets in GitHub:

- `DATABASE_URL`
- `SECRET_KEY`
- `API_KEYS`
- `DEPLOY_TOKEN`
- `RENDER_STAGING_DEPLOY_HOOK_URL`
- `RENDER_PRODUCTION_DEPLOY_HOOK_URL`

The deploy job fails fast if the required hook URL is missing for the current branch.

### Activate Deployment

1. Add repository secrets in GitHub:
	- `RENDER_STAGING_DEPLOY_HOOK_URL`
	- `RENDER_PRODUCTION_DEPLOY_HOOK_URL`
2. Push to `develop` to trigger staging deploy, or push to `main` to trigger production deploy.
3. Optional: run the workflow manually from GitHub Actions using `workflow_dispatch` and select `staging` or `production`.

## Smoke Tests

After deployment, verify the following:

- Application loads
- Login works
- Dashboard loads
- Prediction API responds
- Database queries succeed
- `GET /health` and `GET /ready` return success

### Optional GitHub CLI Setup

If you use GitHub CLI, secrets can be set from the repository root:

```powershell
gh secret set RENDER_STAGING_DEPLOY_HOOK_URL --body "https://api.render.com/deploy/srv-..."
gh secret set RENDER_PRODUCTION_DEPLOY_HOOK_URL --body "https://api.render.com/deploy/srv-..."
```

## Local Smoke Test

Run the same stack validation script used by CI:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

## Backend Details

For backend environment setup and local API run instructions, see [backend/README.md](backend/README.md).

## 5-Minute Local QA Runbook

Use two terminals from the repository root for a fast manual validation pass.

Terminal A (backend):

```powershell
Set-Location .\backend
py -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Terminal B (frontend):

```powershell
Set-Location .\frontend
$env:VITE_API_BASE_URL="http://127.0.0.1:8001/api/v1"
npm run dev
```

Validate in this order:

1. Login
2. Dashboard
3. Predictions
4. Games
5. Team Intelligence
6. Analytics

Quick friction checks before Docker/deploy:

1. Retry behavior: temporarily stop backend and verify Retry recovers.
2. Role behavior: verify viewer and analyst/admin boundaries.
3. Responsive behavior: verify mobile and tablet layouts.

## Local Run Troubleshooting

If `uvicorn` exits with `WinError 10048` on `127.0.0.1:8000`, another process is already using that port.

- Start backend on another port:

```powershell
py -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

- Or stop the conflicting process first, then re-run on `8000`.
# Golden Key Production Rollout

This runbook implements a production path that scales without architectural changes by keeping each concern in its own service boundary.

## Step 1 - Infrastructure Provisioning

Target service chain:

Frontend -> Backend API -> Database -> Redis -> Worker Processes -> Object Storage -> Monitoring

Provisioned assets in this repository:

- Docker production stack: [deploy/docker-compose.production.yml](../deploy/docker-compose.production.yml)
- Kubernetes full-stack manifest: [infra/kubernetes/production-stack.yaml](../infra/kubernetes/production-stack.yaml)
- Kubernetes secret/config templates: [infra/kubernetes/secret.yaml](../infra/kubernetes/secret.yaml), [infra/kubernetes/configmap.yaml](../infra/kubernetes/configmap.yaml)
- Monitoring scrape config: [infra/monitoring/prometheus.yml](../infra/monitoring/prometheus.yml)

Scaling properties:

- Stateless frontend/backend/worker containers can scale horizontally.
- Worker and scheduler are separate processes from API.
- Redis and database are isolated services.
- Object storage is separate from compute.
- Monitoring stack is independent and can be upgraded without application changes.

## Step 2 - Production Deployment

Deployable components:

- Frontend
- Backend
- Database
- Workers
- Pipeline Scheduler

### Compose deployment

```powershell
Set-Location .\deploy
docker compose -f docker-compose.production.yml --env-file ..\.env.production up -d --build
```

### Kubernetes deployment

```powershell
kubectl apply -f infra/kubernetes/configmap.yaml
kubectl apply -f infra/kubernetes/secret.yaml
kubectl apply -f infra/kubernetes/production-stack.yaml
```

### Verification checks

- Health checks:
  - `GET /health`
  - `GET /api/v1/health/ready`
  - `GET /api/v1/health/system`
- API responses: representative reads and writes return expected status codes.
- Authentication: login, token refresh, protected route access.
- Prediction pipeline: scheduler + pipeline endpoints report healthy stage runs.
- Background jobs: worker and scheduler containers remain healthy and emit cycle logs.

## Step 3 - User Onboarding

First-run backend flow is now exposed through onboarding APIs:

- `POST /api/v1/onboarding/register`
- `GET /api/v1/onboarding/status`
- `PUT /api/v1/onboarding/favorite-sports`
- `PUT /api/v1/onboarding/risk-profile`
- `PUT /api/v1/onboarding/bankroll`
- `POST /api/v1/onboarding/complete`

Implementation file:

- [backend/app/api/v1/onboarding.py](../backend/app/api/v1/onboarding.py)

Recommended UX sequence:

1. Register
2. Verify Email
3. Choose Favorite Sports
4. Risk Profile
5. Bankroll Settings
6. Dashboard

Design guidance:

- Collect only one domain decision per step.
- Keep defaults sensible (`moderate` risk profile, conservative bankroll units).
- Show progress and resume state from `/onboarding/status`.

## Step 4 - User Profiles

Profile bootstrap payload is available at:

- `GET /api/v1/onboarding/bootstrap`

Returned sections:

- Profile
- Preferences
- Subscription
- Notification settings
- Favorite teams
- History summary

## Step 5 - Subscription Readiness (Optional)

Current architecture is billing-provider swappable through abstract billing service:

- [backend/app/services/billing_service.py](../backend/app/services/billing_service.py)

Recommended tiers:

- Free
- Pro
- Enterprise

Suggested gates:

- Free: daily picks, limited history, basic dashboard
- Pro: full NPI, AI explanations, portfolio tracking, simulations
- Enterprise: org tools, API access, collaboration, admin

## Step 6 - Analytics

Track these product KPIs:

- Daily active users
- Prediction views
- Games viewed
- API usage
- Portfolio activity
- Retention

Separation rule:

- Product analytics events stay separate from model/betting analytics metrics.

## Step 7 - Error Reporting

Each production error event should include:

- timestamp
- request_id
- user_id (if authenticated)
- service
- stack_trace (internal only)

Coverage targets:

- Frontend runtime errors
- Backend exceptions
- Worker failures
- Pipeline stage failures
- API response failures

## Step 8 - Operational Dashboard

Internal dashboard should show:

- Users
- Predictions generated
- Pipeline status
- System health
- Worker status
- API status
- Database status

Existing admin route surface can seed this dashboard:

- [backend/app/api/v1/commercial.py](../backend/app/api/v1/commercial.py)

## Step 9 - User Support Tools

Support actions should be API-driven, not direct DB edits:

- User lookup
- Account reset
- Notification resend
- Support notes
- Audit logs

## Step 10 - Launch Monitoring

Monitor at launch:

- Response time
- Prediction pipeline runtime
- User registrations
- Database load
- CPU
- Memory
- Error rate

Initial alert thresholds:

- API p95 latency > 750 ms for 10 min
- Error rate > 2% for 5 min
- Worker failure cycle > 3 consecutive runs
- DB CPU > 80% for 10 min
- Pipeline run missed > 1 schedule window

## Step 11 - Documentation

Version these with app code:

- User Guide
- Admin Guide
- Developer Guide
- API Documentation
- Deployment Guide
- Architecture Guide
- Operations Guide

## Step 12 - Release Checklist

- [ ] Production deployed
- [ ] Monitoring active
- [ ] Backups verified
- [ ] SSL configured
- [ ] Domain configured
- [ ] Authentication verified
- [ ] Prediction pipeline healthy
- [ ] AI services responding
- [ ] Frontend optimized
- [ ] Documentation complete

## Step 13 - Version Tag

Release name:

- Golden Key 1.0.0

Tag commands:

```powershell
git checkout -b release/1.0.0
git tag v1.0.0
git push origin release/1.0.0 --tags
```

Freeze policy:

- Freeze feature development on the release branch.
- Allow only bugfixes and release blockers until launch completes.

## Step 14 - Post-Launch Plan (First 30 Days)

Focus areas:

- Bug fixes
- Performance improvements
- User feedback triage
- Usage analytics review
- Small UX improvements

Guardrail:

- Avoid major new features until stability and error budgets are healthy.

## Final Validation Commands

Backend tests:

```powershell
Set-Location .\backend
pytest
```

Frontend build:

```powershell
Set-Location ..\frontend
npm run build
```

Containers:

```powershell
Set-Location ..
docker compose up --build
```

Smoke test:

```powershell
curl http://localhost:8000/health/system
```

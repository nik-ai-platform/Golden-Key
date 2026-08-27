# Kubernetes deployment notes

This directory contains two deployment options:

1. Baseline backend-only manifests:
	- `deployment.yaml`
	- `service.yaml`
	- `hpa.yaml`
	- `ingress.yaml`
	- `configmap.yaml`
	- `secret.yaml`

2. Full production stack manifest:
	- `production-stack.yaml`

The production stack deploys frontend, backend API, PostgreSQL, Redis, worker processes, scheduler process, object storage (MinIO), and monitoring (Prometheus/Grafana).

## Suggested rollout sequence
1. Prepare secret values in `secret.yaml` or external secret manager.
2. Apply shared config (`configmap.yaml`, `secret.yaml`).
3. Apply `production-stack.yaml`.
4. Verify health and readiness probes on frontend/backend.
5. Verify scheduler and worker pods are running and stable.
6. Verify Prometheus and Grafana are reachable.
7. Enable TLS certs for ingress hosts.

## Required backend secrets

Production deployment requires these environment variables to be present via Kubernetes secrets:

- `DATABASE_URL`
- `SECRET_KEY`
- `JWT_SECRET`
- `OPENAI_API_KEY`
- `SPORTSBOOK_API_KEYS`
- `REDIS_URL`
- `SMTP_SETTINGS`

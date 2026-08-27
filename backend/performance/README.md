# Performance Baseline and Optimization Playbook

## Targets

- Prediction generation: < 100 ms per game
- Dashboard load: < 500 ms
- Typical API response: < 250 ms
- Scheduler run: measured per league and stage
- Database query count: minimize unnecessary queries

## 1) Capture Baseline

Run from backend folder:

```powershell
py -m scripts.performance_baseline
```

Output is saved to:

- backend/performance/baseline.json

## 2) Runtime API Metrics

Endpoint:

- GET /api/v1/analytics/performance

Includes:

- Average response time
- 95th percentile response time
- Error rate
- Request count
- Prediction throughput per minute
- Scheduler stage latency and failure counts

## 3) Load Testing

Use k6 with the scenario file:

- backend/performance/k6-load.js

Example:

```powershell
k6 run backend/performance/k6-load.js -e BASE_URL=http://localhost:8000 -e TOKEN=YOUR_TOKEN
```

Scenarios:

- 100 concurrent prediction requests
- 50 concurrent dashboard users
- 10 simultaneous import requests

## 4) Resource Monitoring

For containerized runs:

```powershell
docker stats --no-stream
```

Track:

- CPU
- Memory
- Database connection pressure
- Disk usage
- Scheduler and background job runtime duration

## 5) Validation

```powershell
py -m compileall app
py -m pytest -q
docker compose up --build
```

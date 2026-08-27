# API Documentation

Complete REST API reference for the nik-ai-platform.

## Base URL

```
https://api.nik-ai-platform.com/v1
```

## Authentication

All API requests require authentication using a Bearer token:

```
Authorization: Bearer YOUR_API_TOKEN
```

### Swagger/OpenAPI Login Flow

- Token endpoint: `POST /api/v1/auth/login`
- After login, include access token in `Authorization: Bearer <token>` for protected routes.

### Role-Based Authorization (RBAC)

Authorization denials return a stable, non-revealing response:

```json
{
  "detail": "Insufficient permissions"
}
```

Dependency guard mapping:

| Dependency | Allowed Roles | Typical Use |
| --- | --- | --- |
| `require_viewer` | `viewer`, `analyst`, `admin` | Read-only dashboard and analytics routes |
| `require_analyst` | `analyst`, `admin` | Prediction and import routes |
| `require_admin` | `admin` | Administrative/user-management routes |

Permission matrix for current and planned endpoints:

| Endpoint | Viewer | Analyst | Admin |
| --- | --- | --- | --- |
| `GET /api/v1/dashboard` | ✅ | ✅ | ✅ |
| `GET /api/v1/predictions/{game_id}` | ❌ | ✅ | ✅ |
| `POST /api/v1/imports/{sport}` | ❌ | ✅ | ✅ |
| `GET /api/v1/backtests/*` (planned) | ❌ | ✅ | ✅ |
| `GET /api/v1/users/*` (planned) | ❌ | ❌ | ✅ |

## Predictions Endpoint Behavior

`GET /api/v1/predictions/{game_id}` returns a prediction snapshot for a single game.

- It is not a real-time analytics stream.
- It returns the latest saved prediction when available, otherwise it generates one on demand.
- Score-like fields are model outputs (NPI-style scoring), not live scoreboard values.

Current response shape example:

```json
{
  "game_id": 6,
  "game_date": "2026-07-24T18:00:00Z",
  "home_team": "Dallas Wings",
  "away_team": "Phoenix Mercury",
  "winner": "Dallas Wings",
  "confidence": 62.4,
  "nik_power_index": 58.9,
  "home_npi": 58.9,
  "away_npi": 54.1,
  "model_version": "NPI-v2"
}
```

For aggregated/historical analysis (accuracy trends, confidence buckets, backtesting), use analytics routes under `/api/v1/analytics/*`.

## Endpoints

### Users

- `GET /users` - List all users
- `GET /users/:id` - Get user by ID
- `POST /users` - Create new user
- `PUT /users/:id` - Update user
- `DELETE /users/:id` - Delete user

### Projects

- `GET /projects` - List all projects
- `GET /projects/:id` - Get project by ID
- `POST /projects` - Create new project
- `PUT /projects/:id` - Update project
- `DELETE /projects/:id` - Delete project

### Tasks

- `GET /tasks` - List all tasks
- `GET /tasks/:id` - Get task by ID
- `POST /tasks` - Create new task
- `PUT /tasks/:id` - Update task
- `DELETE /tasks/:id` - Delete task

## Response Format

All responses are returned as JSON:

```json
{
  "success": true,
  "data": {},
  "error": null
}
```

## Error Codes

- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

API requests are rate-limited to 1000 requests per hour per API token.

# API Documentation

## Overview

The nik-ai-platform API provides RESTful endpoints for managing users, projects, and tasks. All endpoints require authentication via JWT tokens.

## Base URL

```
https://api.nik-ai-platform.com/v1
```

## Authentication

All API requests require an `Authorization` header with a valid JWT token:

```
Authorization: Bearer <your_jwt_token>
```

### Swagger/OpenAPI Login Flow

- Token endpoint: `POST /api/v1/auth/login`
- Use returned access token for protected API routes.

### Role-Based Authorization (RBAC)

Authorization denials use a consistent payload:

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

#### Get Current User
```
GET /users/me
```

**Response:**
```json
{
  "id": "user_123",
  "email": "user@example.com",
  "name": "John Doe",
  "createdAt": "2026-07-20T00:00:00Z"
}
```

#### Update User Profile
```
PUT /users/me
```

**Request Body:**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com"
}
```

### Projects

#### List Projects
```
GET /projects
```

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `limit` (optional): Items per page (default: 20)

**Response:**
```json
{
  "data": [
    {
      "id": "project_123",
      "name": "My Project",
      "description": "Project description",
      "status": "active",
      "createdAt": "2026-07-20T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 100
  }
}
```

#### Create Project
```
POST /projects
```

**Request Body:**
```json
{
  "name": "New Project",
  "description": "Project description"
}
```

#### Get Project Details
```
GET /projects/:id
```

#### Update Project
```
PUT /projects/:id
```

**Request Body:**
```json
{
  "name": "Updated Project Name",
  "description": "Updated description"
}
```

#### Delete Project
```
DELETE /projects/:id
```

### Tasks

#### List Tasks
```
GET /projects/:projectId/tasks
```

#### Create Task
```
POST /projects/:projectId/tasks
```

**Request Body:**
```json
{
  "title": "Task Title",
  "description": "Task description",
  "status": "todo",
  "priority": "high",
  "dueDate": "2026-08-20T00:00:00Z"
}
```

#### Update Task
```
PUT /projects/:projectId/tasks/:taskId
```

#### Delete Task
```
DELETE /projects/:projectId/tasks/:taskId
```

## Error Responses

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid request parameters",
  "details": {}
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Invalid or missing authentication token"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "You do not have permission to access this resource"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred"
}
```

## Rate Limiting

- Rate limit: 1000 requests per hour per API key
- Headers returned with each response:
  - `X-RateLimit-Limit`: Maximum requests per hour
  - `X-RateLimit-Remaining`: Requests remaining
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

## Examples

### Get User Projects
```bash
curl -X GET https://api.nik-ai-platform.com/v1/projects \
  -H "Authorization: Bearer your_token_here"
```

### Create New Project
```bash
curl -X POST https://api.nik-ai-platform.com/v1/projects \
  -H "Authorization: Bearer your_token_here" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My New Project",
    "description": "A project description"
  }'
```

## Support

For API support and questions, contact: support@nik-ai-platform.com
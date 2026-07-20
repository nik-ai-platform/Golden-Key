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
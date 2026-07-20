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

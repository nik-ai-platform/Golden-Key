# Source Code

Main source code directory for the nik-ai-platform project.

## Directory Structure

```
src/
├── api/              - REST API endpoints
├── models/           - Data models and schemas
├── services/         - Business logic services
├── middleware/       - Express middleware
├── utils/            - Utility functions
├── config/           - Configuration files
└── index.ts          - Application entry point
```

## Key Modules

### API (`src/api/`)
- User routes
- Project routes
- Task routes
- Authentication routes

### Services (`src/services/`)
- User service
- Project service
- Task service
- Email service

### Models (`src/models/`)
- User model
- Project model
- Task model
- Database schemas

### Middleware (`src/middleware/`)
- Authentication middleware
- Error handling middleware
- Logging middleware
- Validation middleware

### Utils (`src/utils/`)
- Helper functions
- Validators
- Formatters
- Constants

## Getting Started

1. Install dependencies: `npm install`
2. Configure environment variables in `.env`
3. Run development server: `npm run dev`
4. Build for production: `npm run build`

## Development

- Use TypeScript for type safety
- Follow ESLint rules
- Write tests for new features
- Update documentation

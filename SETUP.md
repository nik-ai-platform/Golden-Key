# Setup and Installation Guide

## Prerequisites

- Node.js 18.x or higher
- npm 8.x or higher (or yarn 3.x+)
- Git
- A modern web browser

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/nik-ai-platform/Golden-Key.git
cd Golden-Key
```

### 2. Install Dependencies

Using npm:
```bash
npm install
```

Or using yarn:
```bash
yarn install
```

### 3. Environment Configuration

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```env
# API Configuration
API_URL=http://localhost:3000
API_PORT=3000
API_ENV=development

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=nik_ai_platform
DB_USER=postgres
DB_PASSWORD=your_password

# JWT
JWT_SECRET=your_jwt_secret_key
JWT_EXPIRES_IN=24h

# Logging
LOG_LEVEL=debug
```

### 4. Database Setup (if applicable)

```bash
# Run migrations
npm run migrate

# Seed sample data (optional)
npm run seed
```

## Development

### Start Development Server

```bash
npm run dev
```

The server will start on `http://localhost:3000`

### Running Tests

```bash
# Run all tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

### Code Linting

```bash
# Run linter
npm run lint

# Fix linting issues automatically
npm run lint -- --fix
```

### Code Formatting

```bash
# Format code with Prettier
npm run format

# Check formatting without making changes
npm run format:check
```

## Build and Production

### Build the Project

```bash
npm run build
```

This creates optimized production build in the `dist/` directory.

### Start Production Server

```bash
npm start
```

## Docker Setup (Optional)

### Build Docker Image

```bash
docker build -t nik-ai-platform:latest .
```

### Run Docker Container

```bash
docker run -p 3000:3000 --env-file .env nik-ai-platform:latest
```

### Using Docker Compose

```bash
docker-compose up
```

## Troubleshooting

### Port Already in Use

If port 3000 is already in use:

```bash
# Use a different port
PORT=3001 npm run dev
```

### Module Not Found

Clear node_modules and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

### Database Connection Issues

1. Verify database is running
2. Check `.env` database credentials
3. Ensure database user has proper permissions
4. Try resetting the database:

```bash
npm run db:reset
```

### Port Permission Denied

If you get permission denied on Linux/macOS:

```bash
# Use sudo
sudo npm run dev

# Or use a port > 1024
PORT=8000 npm run dev
```

## IDE Setup

### VS Code

1. Install extensions:
   - ESLint
   - Prettier
   - Node.js Extension Pack

2. Create `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[javascript]" : {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "eslint.validate": [
    "javascript",
    "javascriptreact"
  ]
}
```

## Getting Help

- Check the [API Documentation](./API.md)
- See [Contributing Guidelines](../CONTRIBUTING.md)
- Open an issue on GitHub
- Contact support@nik-ai-platform.com

## Next Steps

1. Review the [API Documentation](./API.md)
2. Check out the [Contributing Guidelines](../CONTRIBUTING.md)
3. Explore the project structure
4. Start developing!

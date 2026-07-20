# Tests

Automated tests for the nik-ai-platform project.

## Test Structure

- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for system components
- `e2e/` - End-to-end tests for user workflows

## Running Tests

### Run all tests
```bash
npm test
```

### Run specific test suite
```bash
npm test -- unit
npm test -- integration
npm test -- e2e
```

### Run with coverage
```bash
npm test -- --coverage
```

## Writing Tests

- Use descriptive test names
- Follow the Arrange-Act-Assert pattern
- Mock external dependencies
- Aim for high code coverage

## Test Tools

- **Jest** - Test runner and assertion library
- **Supertest** - HTTP assertion library
- **Sinon** - Mocking and stubbing library

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Scheduled nightly runs

All tests must pass before merging to main.

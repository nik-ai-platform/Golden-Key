# Contributing to nik-ai-platform

Thank you for your interest in contributing to the nik-ai-platform project! This document provides guidelines and instructions for contributing.

## Code of Conduct

We are committed to providing a welcoming and inspiring community for all. Please be respectful and professional in all interactions.

## Getting Started

### Prerequisites

- Node.js 18.x or higher
- npm or yarn package manager
- Git

### Development Setup

1. Fork the repository
2. Clone your fork locally:
   ```bash
   git clone https://github.com/your-username/Golden-Key.git
   cd Golden-Key
   ```

3. Add upstream remote:
   ```bash
   git remote add upstream https://github.com/nik-ai-platform/Golden-Key.git
   ```

4. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

5. Install dependencies:
   ```bash
   npm install
   ```

6. Run tests to ensure everything works:
   ```bash
   npm test
   ```

## Making Changes

### Code Style

- Follow the existing code style in the project
- Use meaningful variable and function names
- Add comments for complex logic
- Keep functions small and focused

### Commit Messages

Write clear, descriptive commit messages:

```
feat: Add new feature description
fix: Fix bug description
docs: Update documentation
test: Add or update tests
chore: Update dependencies or tooling
```

### Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage

Run tests locally:
```bash
npm test
npm test -- --coverage
```

### Linting

Ensure your code passes linting:
```bash
npm run lint
npm run lint -- --fix
```

## Submitting Changes

### Pull Request Process

1. Update your branch with latest changes from upstream:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

3. Create a Pull Request on GitHub with:
   - Clear title describing the changes
   - Detailed description of what was changed and why
   - Reference to any related issues (e.g., "Fixes #123")
   - Screenshots for UI changes if applicable

4. Respond to code review feedback promptly

### PR Title Format

- `feat: Description of new feature`
- `fix: Description of bug fix`
- `docs: Description of documentation update`
- `refactor: Description of code refactoring`

## Reporting Issues

### Bug Reports

Include:
- Clear, descriptive title
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (Node version, OS, etc.)
- Screenshots or error logs if applicable

### Feature Requests

Include:
- Clear, descriptive title
- Use case and motivation
- Proposed solution (if any)
- Alternative solutions considered

## Project Structure

```
Golden-Key/
├── src/
│   ├── api/          # API endpoints
│   ├── services/     # Business logic
│   ├── models/       # Data models
│   └── utils/        # Utility functions
├── tests/            # Test files
├── docs/             # Documentation
├── .github/          # GitHub configuration
└── package.json      # Project dependencies
```

## Development Commands

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run linter
npm run lint

# Build project
npm run build

# Format code
npm run format
```

## Release Process

- Versions follow [Semantic Versioning](https://semver.org/)
- Updates to CHANGELOG.md are required for each release
- Release notes should summarize changes for users

## Questions?

- Check existing issues and discussions
- Open a new discussion for questions
- Contact the maintainers

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

Thank you for contributing! 🎉
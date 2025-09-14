# Contributing to Advanced Meme Fun Snipper

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites
- Python 3.10+
- MongoDB (for testing)
- Git

### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd Advanced-Meme-Fun-Snipper

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Code Quality

### Linting and Formatting
We use `ruff` for linting and code formatting:

```bash
# Check code style
ruff check .

# Format code
ruff format .

# Check types
mypy snipper/
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=snipper --cov-report=html

# Run specific test file
pytest tests/test_config.py -v

# Run tests with specific markers
pytest -m "not integration"
```

## Code Style Guidelines

### Python Style
- Follow PEP 8 guidelines
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Maximum line length: 88 characters (Black default)

### Naming Conventions
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private attributes: `_leading_underscore`

### Import Organization
```python
# Standard library imports
import os
import sys

# Third-party imports
import pytest
from pydantic import BaseModel

# Local imports
from ..config import settings
from .helpers import mock_data
```

## Architecture Guidelines

### Modular Design
- Keep modules focused on single responsibilities
- Use dependency injection for better testability
- Implement proper interfaces for external dependencies
- Separate business logic from infrastructure concerns

### Error Handling
- Use specific exception types
- Log errors with appropriate context
- Implement retry logic for transient failures
- Provide meaningful error messages

### Async Best Practices
- Use `async`/`await` consistently
- Handle coroutine cancellation gracefully
- Avoid blocking calls in async functions
- Use proper connection pooling for external services

## Testing Guidelines

### Test Structure
```python
class TestClassName:
    """Test class for ClassName functionality."""
    
    def test_specific_behavior(self):
        """Test specific behavior with clear assertions."""
        # Arrange
        setup_data = create_test_data()
        
        # Act
        result = function_under_test(setup_data)
        
        # Assert
        assert result.expected_field == expected_value
```

### Test Types
- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test component interactions
- **Mock Usage**: Mock external dependencies appropriately
- **Fixtures**: Use pytest fixtures for common test data

### Test Coverage
- Aim for >90% code coverage
- Test both success and failure scenarios
- Include edge cases and boundary conditions
- Test error handling and validation

## Documentation

### Code Documentation
- Write clear docstrings using Google style
- Include parameter and return type descriptions
- Provide usage examples for complex functions
- Document any side effects or assumptions

### API Documentation
```python
async def evaluate_token(token_mint: str, token_name: Optional[str] = None) -> Optional[str]:
    """
    Evaluate a token for potential trading.
    
    Args:
        token_mint: The token's mint address
        token_name: Optional token name for display
        
    Returns:
        Trade ID if trade was initiated, None otherwise
        
    Raises:
        ValueError: If token_mint is invalid
        ConnectionError: If external services are unavailable
    """
```

## Feature Development

### New Features
1. **Design Discussion**: Open an issue to discuss the feature
2. **Architecture Review**: Ensure the feature fits the modular design
3. **Implementation**: Follow TDD approach when possible
4. **Testing**: Include comprehensive tests
5. **Documentation**: Update relevant documentation

### Breaking Changes
- Discuss breaking changes in issues before implementation
- Provide migration guides for users
- Use deprecation warnings when possible
- Update version numbers appropriately

## Pull Request Process

### Before Submitting
- [ ] All tests pass locally
- [ ] Code is properly formatted and linted
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive

### PR Requirements
- Clear description of changes
- Reference related issues
- Include test coverage for new functionality
- Update relevant documentation
- Follow semantic versioning for version bumps

### Review Process
1. Automated checks must pass
2. Code review by maintainers
3. Testing in staging environment
4. Approval and merge

## Git Workflow

### Branching
- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/xxx`: Feature development branches
- `hotfix/xxx`: Critical bug fixes

### Commit Messages
```
type(scope): description

Longer description if needed

Fixes #123
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

### Example Commits
```
feat(trading): add circuit breaker for consecutive failures

Implement circuit breaker that halts trading after N consecutive
failures for a configurable cooldown period.

Fixes #45
```

## Release Process

### Version Numbering
We follow Semantic Versioning (SemVer):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

### Release Checklist
- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Run full test suite
- [ ] Update documentation
- [ ] Create release notes
- [ ] Tag release in Git

## Security Considerations

### Sensitive Data
- Never commit API keys or private keys
- Use environment variables for configuration
- Implement proper data redaction in logs
- Follow security guidelines in SECURITY.md

### Dependencies
- Regularly update dependencies
- Use `pip-audit` to check for vulnerabilities
- Pin dependency versions in production
- Review dependency licenses

## Community Guidelines

### Communication
- Be respectful and constructive
- Ask questions in issues or discussions
- Provide helpful feedback in reviews
- Share knowledge and help others

### Issue Reporting
- Use issue templates when available
- Provide clear reproduction steps
- Include relevant system information
- Search for existing issues first

## Getting Help

### Resources
- Documentation: README.md and inline docs
- Security: SECURITY.md
- Architecture: Code comments and design docs
- Examples: Test files and usage examples

### Contact
- GitHub Issues: Bug reports and feature requests
- GitHub Discussions: General questions and ideas
- Security Issues: Follow responsible disclosure in SECURITY.md

Thank you for contributing to make this project better!
# Contributing to Advanced Meme Fun Snipper

Thank you for your interest in contributing to the Advanced Meme Fun Snipper project! This document provides guidelines and information for contributors.

## Development Workflow

### Branching Model

We use a Git Flow-inspired branching model:

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: New features (e.g., `feature/add-dex-screener-integration`)
- `hotfix/*`: Critical fixes for production
- `release/*`: Preparation for new releases

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/Advanced-Meme-Fun-Snipper.git
   cd Advanced-Meme-Fun-Snipper
   ```

3. **Set up the development environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .[dev]
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

5. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

### Development Setup

#### Prerequisites
- Python 3.10 or higher
- Git
- A GitHub account

#### Install Dependencies
```bash
# Install in development mode with dev dependencies
pip install -e .[dev]

# Or install from requirements if available
pip install -r requirements.txt  # If generated
```

#### Environment Configuration
1. Copy `.env.example` to `.env`
2. Fill in your API keys and configuration values
3. Never commit `.env` files with real credentials

### Code Quality Standards

#### Commit Style
We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Adding or modifying tests
- `chore:` Build process or auxiliary tool changes

Examples:
```
feat: add DexScreener API integration for token metadata
fix: handle websocket connection timeout gracefully
docs: update installation instructions for Python 3.12
```

#### Code Formatting and Linting

We use multiple tools to maintain code quality:

- **Ruff**: Fast Python linter and formatter
- **Black**: Code formatting (line length: 100)
- **mypy**: Static type checking
- **pytest**: Testing framework

##### Running Quality Checks Locally

```bash
# Format code with ruff and black
ruff format .
black .

# Lint with ruff
ruff check .

# Type check with mypy
mypy src/

# Run tests
pytest tests/

# Run all pre-commit hooks
pre-commit run --all-files
```

#### Code Style Guidelines

- **Line length**: 100 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Docstrings**: Use Google-style docstrings
- **Type hints**: Required for new code, encouraged for existing code
- **Imports**: Organized by ruff/isort (stdlib, third-party, local)

Example function:
```python
def process_token_data(
    token_mint: str, 
    price_data: Dict[str, Any]
) -> Optional[TokenAnalysis]:
    """Process token data and return analysis.
    
    Args:
        token_mint: The token mint address
        price_data: Price data from external API
        
    Returns:
        TokenAnalysis object if successful, None otherwise
        
    Raises:
        ValueError: If token_mint is invalid
    """
    # Implementation here
    pass
```

### Testing

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=advanced_meme_fun_snipper

# Run specific test file
pytest tests/test_sanity.py

# Run with verbose output
pytest -v
```

#### Writing Tests
- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use descriptive test names
- Mock external dependencies (APIs, databases, etc.)

Example test:
```python
def test_token_analysis_valid_input():
    """Test token analysis with valid input data."""
    # Arrange
    token_data = {"mint": "abc123", "price": 0.001}
    
    # Act
    result = analyze_token(token_data)
    
    # Assert
    assert result is not None
    assert result.score >= 0
    assert result.score <= 10
```

### Pull Request Process

1. **Create a feature branch** from `develop`
2. **Make your changes** following the code quality standards
3. **Add tests** for new functionality
4. **Update documentation** if needed
5. **Run quality checks** locally
6. **Commit your changes** using conventional commit format
7. **Push to your fork** and create a pull request

#### Pull Request Requirements
- [ ] All tests pass
- [ ] Code follows style guidelines (ruff, black, mypy pass)
- [ ] New code has appropriate test coverage
- [ ] Documentation updated if needed
- [ ] Conventional commit messages used
- [ ] PR description explains the changes clearly

#### PR Description Template
```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Tests pass locally
- [ ] Documentation updated
```

### Code Review Guidelines

#### For Authors
- Keep PRs focused and reasonably sized
- Provide clear descriptions and context
- Respond to feedback promptly and professionally
- Update code based on review comments

#### For Reviewers
- Review for correctness, maintainability, and performance
- Check that tests adequately cover the changes
- Ensure documentation is updated
- Be constructive and specific in feedback
- Approve when satisfied with quality

### Issue Reporting

When reporting bugs or requesting features:

1. **Search existing issues** first
2. **Use issue templates** when available
3. **Provide clear, detailed information**:
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Environment details (Python version, OS, etc.)
   - Relevant logs or error messages

### Security

- **Never commit sensitive data** (API keys, private keys, passwords)
- **Use environment variables** for configuration
- **Report security vulnerabilities** privately (see SECURITY.md)
- **Keep dependencies updated** and monitor for security advisories

### Getting Help

- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: Check README.md and docs/ directory
- **Code**: Read the source code and tests for examples

### Recognition

Contributors will be recognized in:
- GitHub contributor statistics
- Release notes for significant contributions
- README.md acknowledgments section

Thank you for contributing to Advanced Meme Fun Snipper!
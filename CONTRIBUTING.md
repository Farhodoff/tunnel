# Contributing to Tunnel

Thank you for your interest in contributing to Tunnel! This document provides guidelines and instructions for contributing.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/yourusername/tunnel.git
   cd tunnel
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

## Development Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clean, documented code
   - Follow PEP 8 style guidelines
   - Add tests for new features

3. **Run tests**
   ```bash
   pytest tests/ -v
   ```

4. **Format code**
   ```bash
   black tunnel/ tests/
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

6. **Push and create a pull request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

## Testing

- Write tests for all new features
- Ensure all tests pass before submitting PR
- Aim for high test coverage
- Test edge cases and error conditions

## Pull Request Process

1. Update the README.md with details of changes if applicable
2. Update CHANGELOG.md with your changes
3. Ensure all CI checks pass
4. Request review from maintainers
5. Address review feedback

## Reporting Issues

When reporting issues, please include:
- Description of the problem
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)

## Code of Conduct

- Be respectful and constructive
- Welcome newcomers
- Focus on what's best for the community
- Show empathy towards others

## Questions?

Feel free to open an issue for questions or join our discussions.

Thank you for contributing! 🎉

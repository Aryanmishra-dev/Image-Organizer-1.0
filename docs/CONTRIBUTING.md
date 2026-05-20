# Contributing to Image Organizer

Thank you for your interest in contributing! This document provides guidelines and instructions to make the contribution process smooth.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Branch Strategy](#branch-strategy)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Code Standards](#code-standards)
- [Testing](#testing)
- [Reporting Issues](#reporting-issues)

---

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to fostering a welcoming, inclusive community.

---

## Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** from `main`
4. **Make your changes** with tests
5. **Push** and open a Pull Request

---

## Development Setup

```bash
# Clone your fork
git clone https://github.com/<your-username>/Image-Organizer-1.0.git
cd Image-Organizer-1.0

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install all dependencies (production + dev)
make dev

# Verify setup
make check
```

---

## Branch Strategy

| Branch     | Purpose                          |
| ---------- | -------------------------------- |
| `main`     | Production-ready, stable code    |
| `develop`  | Integration branch for features  |
| `feat/*`   | New features                     |
| `fix/*`    | Bug fixes                        |
| `docs/*`   | Documentation changes            |
| `refactor/*` | Code refactoring               |

---

## Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type         | Description                                  |
| ------------ | -------------------------------------------- |
| `feat`       | New feature                                  |
| `fix`        | Bug fix                                      |
| `docs`       | Documentation only changes                   |
| `refactor`   | Code change that neither fixes a bug nor adds a feature |
| `test`       | Adding or correcting tests                   |
| `chore`      | Maintenance tasks (CI, deps, config)         |
| `perf`       | Performance improvement                      |
| `style`      | Formatting, missing semicolons, etc.         |

### Examples

```
feat(scanner): add incremental scan support
fix(hasher): handle permission denied on locked files
docs: update installation instructions in README
test(comparator): add perceptual hash clustering tests
chore(ci): add CodeQL security scanning workflow
```

---

## Pull Request Process

1. **Ensure all checks pass** – run `make check` locally
2. **Write meaningful PR descriptions** – explain *what* and *why*
3. **Keep PRs small and focused** – one logical change per PR
4. **Add tests** for new functionality
5. **Update documentation** if behavior changes
6. **Request review** from at least one maintainer

### PR Title Format

Follow the same conventional commit format:
```
feat(core): add batch processing for large directories
```

---

## Code Standards

- **Formatter**: [Black](https://black.readthedocs.io/) (line length: 100)
- **Linter**: [Ruff](https://docs.astral.sh/ruff/) (replaces flake8, isort, pyupgrade)
- **Type checker**: [MyPy](https://mypy.readthedocs.io/)
- **Security**: [Bandit](https://bandit.readthedocs.io/)

Run all checks:

```bash
make check        # lint + format-check + type-check + security + test
make format       # auto-fix formatting
```

---

## Testing

- Write tests in `tests/` using [pytest](https://docs.pytest.org/)
- Aim for **80%+ coverage**
- Use `tmp_path` fixture for file-system tests
- Mark slow tests with `@pytest.mark.slow`

```bash
make test         # Run all tests
make test-cov     # Run with coverage report
make test-fast    # Run in parallel
```

---

## Reporting Issues

When filing an issue, please include:

1. **Python version** (`python --version`)
2. **OS and version** (e.g., macOS 14.2, Apple Silicon)
3. **Steps to reproduce**
4. **Expected vs actual behavior**
5. **Error output / traceback** (if applicable)

Use the appropriate issue template when available.

---

Thank you for contributing! Every improvement, no matter how small, is valued.

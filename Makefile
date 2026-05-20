.PHONY: help install dev lint format type-check security test test-cov clean run-cli run-gui all check

# ── Default ──────────────────────────────────────────────────────────────────
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Setup ────────────────────────────────────────────────────────────────────
install: ## Install production dependencies
	pip install .

dev: ## Install all dependencies (production + dev)
	pip install -e ".[dev]"
	pre-commit install

# ── Code Quality ─────────────────────────────────────────────────────────────
lint: ## Run linter (ruff)
	ruff check src/ tests/

format: ## Auto-format code (black + ruff)
	black src/ tests/
	ruff check --fix src/ tests/

format-check: ## Check formatting without modifying files
	black --check src/ tests/
	ruff check src/ tests/

type-check: ## Run static type checker (mypy)
	mypy src/ --config-file pyproject.toml

# ── Security ─────────────────────────────────────────────────────────────────
security: ## Run security scans (bandit)
	bandit -r src/ -c pyproject.toml

# ── Testing ──────────────────────────────────────────────────────────────────
test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml

test-fast: ## Run tests in parallel
	pytest tests/ -v -n auto

# ── Run ──────────────────────────────────────────────────────────────────────
run-cli: ## Run the CLI (use ARGS="scan ~/Pictures" to pass arguments)
	cd src && python -m duplicate_image_detector.cli.main $(ARGS)

run-gui: ## Launch the GUI application
	cd src && python -c "from duplicate_image_detector.gui.main_window import run_gui; run_gui()"

# ── CI Shortcut ──────────────────────────────────────────────────────────────
check: lint format-check type-check security test ## Run all CI checks locally
all: format lint type-check security test-cov ## Format + full CI pipeline

# ── Cleanup ──────────────────────────────────────────────────────────────────
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ .coverage coverage.xml

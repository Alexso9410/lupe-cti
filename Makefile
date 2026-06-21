.PHONY: install test lint format type-check security all clean build docs-serve help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package in editable mode with dev deps
	pip install -e ".[dev]"

test: ## Run test suite
	pytest

test-cov: ## Run tests with coverage report
	pytest --cov=lupe --cov-report=term-missing

lint: ## Run linter (ruff check)
	ruff check lupe/ tests/

format: ## Format code (ruff format)
	ruff format lupe/ tests/

format-check: ## Check formatting without modifying files
	ruff format --check lupe/ tests/

type-check: ## Run type checker (mypy)
	mypy lupe/

security: ## Run security scans (bandit + pip-audit)
	bandit -r lupe/
	pip-audit

all: lint type-check test security ## Run all checks (lint + type-check + test + security)

clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ .ruff_cache/ .mypy_cache/
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

build: ## Build distribution packages
	python -m build

pre-commit: ## Run pre-commit on all files
	pre-commit run --all-files

docs-serve: ## Serve documentation (placeholder)
	@echo "Documentation is in README.md, CONTRIBUTING.md, and CHANGELOG.md"

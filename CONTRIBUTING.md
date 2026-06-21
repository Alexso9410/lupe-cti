# Contributing to Lupe CTI

Thank you for your interest in contributing to Lupe CTI! This guide will help you get started.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code. Please report unacceptable behavior via [GitHub Issues](https://github.com/lupe-cti/lupe/issues).

## How to Contribute

### Reporting Bugs

- Check [existing issues](https://github.com/lupe-cti/lupe/issues) first
- Use the **Bug Report** issue template
- Include reproduction steps, expected behavior, and environment details

### Suggesting Features

- Use the **Feature Request** issue template
- Explain the use case and why it benefits the community
- Consider if it fits the project's scope (threat intelligence enrichment)

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes (see [Development Setup](#development-setup))
4. Write or update tests
5. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/lupe.git
cd lupe

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run the test suite
pytest

# Run tests with coverage
pytest --cov=lupe --cov-report=term-missing
```

### Prerequisites

- Python 3.10+
- pip or pipx
- Git

## Coding Style

### Python

- **Formatter/Linter**: [Ruff](https://github.com/astral-sh/ruff) — configured in `pyproject.toml`
- **Line length**: 100 characters
- **Import sorting**: Ruff `I` rules (isort-compatible)
- **Type hints**: Required on all public functions and methods

```bash
# Check style
ruff check lupe/ tests/

# Auto-fix
ruff check --fix lupe/ tests/

# Format
ruff format lupe/ tests/
```

### Commits

All commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

# Examples:
feat(enrichment): add Shodan plugin for IP reconnaissance
fix(config): resolve XDG path on Windows
docs(readme): update installation instructions
test(misp): add integration tests for MISPClient
chore(ci): update GitHub Actions workflow
```

Types: `feat`, `fix`, `docs`, `test`, `chore`, `refactor`, `perf`, `ci`, `build`, `style`

### Branching

- `main` — stable release branch
- `feature/*` — new features
- `fix/*` — bug fixes
- `docs/*` — documentation changes

## Testing

### Running Tests

```bash
# All tests
pytest

# Single file
pytest tests/test_ioc_detect.py

# Single test
pytest tests/test_ioc_detect.py::TestIPv4Detection::test_valid_ipv4

# With coverage
pytest --cov=lupe --cov-report=term-missing
```

### Writing Tests

- Use `pytest-asyncio` for async tests (configured with `asyncio_mode = "auto"`)
- Use `respx` for mocking `httpx` calls in enrichment plugin tests
- Place tests in `tests/` mirroring the source structure
- Name test files `test_<module>.py`

### TDD Workflow

All new features must follow Test-Driven Development:

1. **RED**: Write a failing test that defines the expected behavior
2. **GREEN**: Write the minimum code to make the test pass
3. **REFACTOR**: Clean up the code while keeping tests green

### Coverage

- Current baseline: 25%
- New code must include tests
- Target: 80% coverage for new modules

## Adding a New Enrichment Plugin

### Step 1: Create the Plugin

Create `lupe/enrichment/my_plugin.py`:

```python
"""My custom enrichment plugin."""
from __future__ import annotations

import httpx

from lupe.enrichment.base import EnrichmentPlugin, EnrichmentResult
from lupe.models import IOC, IOCType


class MyPlugin(EnrichmentPlugin):
    """Enrich IOCs using MyService API."""

    name = "my_service"
    supported_ioc_types = {IOCType.ipv4, IOCType.domain}
    requires_api_key = False

    async def enrich(self, ioc: IOC, client: httpx.AsyncClient) -> EnrichmentResult | None:
        """Enrich an IOC by querying MyService API."""
        resp = await client.get(
            f"https://api.myservice.com/v1/lookup",
            params={"q": ioc.value},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        if not data.get("results"):
            return None

        return EnrichmentResult(
            source=self.name,
            raw=data,
            summary=f"Found {len(data['results'])} results",
        )
```

### Step 2: Register the Plugin

In `lupe/enrichment/__init__.py`, add to the import section:

```python
from lupe.enrichment.my_plugin import MyPlugin
```

Then add to the `_build_plugins()` function:

- If the plugin is **free** (no API key): add to the `plugins` list directly
- If the plugin is **keyed**: add an `if settings.my_service_key:` block

```python
# Free plugin — add to the unconditional list:
plugins = [
    ...
    MyPlugin(),
]

# Keyed plugin — add a conditional block:
if settings.my_service_key:
    plugins.append(MyPlugin(api_key=settings.my_service_key))
```

### Step 3: Add Configuration (if keyed)

In `lupe/config.py`, add the setting:

```python
my_service_key: str | None = None
```

### Step 4: Write Tests

Create `tests/test_my_plugin.py`:

```python
"""Tests for MyPlugin."""
from __future__ import annotations

import respx
from httpx import Response

from lupe.enrichment.my_plugin import MyPlugin
from lupe.models import IOC, IOCType


class TestMyPlugin:
    def test_plugin_name(self) -> None:
        plugin = MyPlugin()
        assert plugin.name == "my_service"

    def test_supports_ipv4(self) -> None:
        plugin = MyPlugin()
        assert plugin.supports(IOCType.ipv4)

    @respx.mock
    async def test_enrich_ipv4(self) -> None:
        respx.get("https://api.myservice.com/v1/lookup").mock(
            return_value=Response(200, json={"results": [{"score": 85}]})
        )
        plugin = MyPlugin()
        ioc = IOC(value="8.8.8.8", type=IOCType.ipv4)
        async with httpx.AsyncClient() as client:
            result = await plugin.enrich(ioc, client)
        assert result is not None
        assert result.source == "my_service"
```

### Step 5: Run and Verify

```bash
pytest tests/test_my_plugin.py -v
ruff check lupe/enrichment/my_plugin.py
bandit -r lupe/enrichment/my_plugin.py
```

## Adding a New LLM Provider

### Step 1: Create the Provider

Create `lupe/llm/my_provider.py`:

```python
"""My LLM provider implementation."""
from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from lupe.llm.base import LLMProvider, ModelInfo


class MyProvider(LLMProvider):
    """LLM provider for MyAPI."""

    name = "my_provider"
    requires_api_key = True

    def __init__(self, api_key: str, base_url: str = "https://api.myprovider.com/v1"):
        self._api_key = api_key
        self._base_url = base_url

    async def generate(self, prompt: str, *, system: str | None = None) -> str:
        """Generate a response from the LLM."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": "default", "messages": messages},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def stream(self, prompt: str, *, system: str | None = None) -> AsyncIterator[str]:
        """Stream a response from the LLM."""
        # Implementation for streaming
        ...

    async def validate_key(self) -> bool:
        """Validate the API key."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[ModelInfo]:
        """List available models."""
        return [ModelInfo(name="default", description="Default model")]
```

### Step 2: Register the Provider

In `lupe/llm/registry.py`, import and register:

```python
from lupe.llm.my_provider import MyProvider
_PROVIDERS["my_provider"] = MyProvider
```

### Step 3: Add Configuration

In `lupe/config.py`:

```python
my_provider_api_key: str | None = None
```

### Step 4: Wire in the Factory

In `lupe/llm/registry.py`, update `get_provider()` to instantiate the new provider from settings.

## Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** with conventional commits
3. **Run all checks** before submitting:
   ```bash
   pytest
   ruff check lupe/ tests/
   ruff format --check lupe/ tests/
   bandit -r lupe/
   ```
4. **Open a PR** using the PR template
5. **Wait for CI** to pass
6. **Request review** from a maintainer

### PR Checklist

- [ ] Tests pass (`pytest`)
- [ ] Lint passes (`ruff check`)
- [ ] Format passes (`ruff format --check`)
- [ ] Security scan passes (`bandit -r lupe/`)
- [ ] New tests added for new functionality
- [ ] Documentation updated (if needed)
- [ ] No secrets or credentials in code
- [ ] Conventional commit messages

## Questions?

- Open a [Discussion](https://github.com/lupe-cti/lupe/discussions) for general questions
- Open an [Issue](https://github.com/lupe-cti/lupe/issues) for bugs and feature requests

Thank you for contributing to Lupe CTI!

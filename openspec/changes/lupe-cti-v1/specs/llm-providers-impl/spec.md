# Delta for llm-providers-impl

## ADDED Requirements

### Requirement: Ollama Provider

The system MUST implement an Ollama provider in `lupe/llm/ollama.py` that communicates with a local Ollama instance.

#### Scenario: Local Ollama available

- GIVEN `LUPE_LLM_PROVIDER=ollama` and `LUPE_OLLAMA_BASE_URL=http://localhost:11434` (default)
- WHEN `generate()` is called with an enrichment result
- THEN the provider sends a chat completion request to `/v1/chat/completions` and returns the response text

#### Scenario: Ollama unreachable

- GIVEN `LUPE_LLM_PROVIDER=ollama` but the Ollama server is not running
- WHEN `validate_key()` or `generate()` is invoked
- THEN it returns/raises a clear connection error, the system logs a warning, and enrichment continues without AI analysis

### Requirement: OpenAI Provider

The system MUST implement an OpenAI provider in `lupe/llm/openai.py`.

#### Scenario: Valid API key

- GIVEN `LUPE_LLM_PROVIDER=openai` and `LUPE_OPENAI_API_KEY` is a valid sk- key
- WHEN `generate()` is called
- THEN it calls `https://api.openai.com/v1/chat/completions` and returns the assistant message content

#### Scenario: Invalid API key

- GIVEN `LUPE_OPENAI_API_KEY=sk-invalid`
- WHEN `validate_key()` is called
- THEN it returns `False` and the system skips AI analysis

### Requirement: Anthropic Provider

The system MUST implement an Anthropic provider in `lupe/llm/anthropic.py`.

#### Scenario: Valid Claude key

- GIVEN `LUPE_LLM_PROVIDER=anthropic` and `LUPE_ANTHROPIC_API_KEY` is valid
- WHEN `generate()` is called
- THEN it calls `https://api.anthropic.com/v1/messages` and returns the text content

### Requirement: OpenRouter Provider

The system MUST implement an OpenRouter provider in `lupe/llm/openrouter.py`.

#### Scenario: Valid OpenRouter key

- GIVEN `LUPE_LLM_PROVIDER=openrouter` and `LUPE_OPENROUTER_API_KEY` is valid
- WHEN `generate()` is called
- THEN it calls `https://openrouter.ai/api/v1/chat/completions` and returns the response

#### Scenario: List available models

- GIVEN any provider is active
- WHEN `list_models()` is called
- THEN it returns a non-empty list of `ModelInfo` objects with at least `id` and `name` fields

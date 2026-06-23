# Delta for llm-provider-abstraction

## ADDED Requirements

### Requirement: LLM Provider Abstract Base Class

The system MUST define an abstract base class `LLMProvider` in `lupe/llm/base.py` that standardizes all LLM interactions.

#### Scenario: Provider implements the interface

- GIVEN a concrete provider class subclassing `LLMProvider`
- WHEN it implements `async generate(prompt, system=None) -> str`, `async stream(prompt) -> AsyncIterator[str]`, `async validate_key() -> bool`, and `list_models() -> list[ModelInfo]`
- THEN the system accepts it as a valid LLM provider

#### Scenario: Provider with invalid key is rejected

- GIVEN a configured provider whose `validate_key()` returns `False`
- WHEN the system attempts to use it for analysis
- THEN the system skips AI analysis, continues with plugin enrichment, and logs a warning

### Requirement: Provider Selection Configuration

The system MUST select the active provider via the `LUPE_LLM_PROVIDER` environment variable.

#### Scenario: Valid provider is selected

- GIVEN `LUPE_LLM_PROVIDER=openai` and `LUPE_OPENAI_API_KEY` is set
- WHEN an enrichment run completes
- THEN the OpenAI provider is used for AI analysis

#### Scenario: No provider configured

- GIVEN `LUPE_LLM_PROVIDER` is unset or empty
- WHEN an enrichment run completes
- THEN AI analysis is skipped entirely and the CLI continues with raw enrichment output

#### Scenario: Invalid provider name

- GIVEN `LUPE_LLM_PROVIDER=unknown_provider`
- WHEN the system initializes
- THEN it logs a warning listing valid providers and skips AI analysis

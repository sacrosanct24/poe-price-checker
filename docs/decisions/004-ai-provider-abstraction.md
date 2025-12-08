# ADR-004: AI Provider Abstraction Layer

## Status
Accepted

## Context

AI-powered features (upgrade recommendations, item analysis, build advice) require LLM integration. The AI landscape evolves rapidly:
- New providers emerge (Groq, xAI joined after project started)
- Pricing changes affect which provider is cost-effective
- Some users prefer local models (Ollama) for privacy
- API interfaces differ between providers

Hardcoding a single provider would limit flexibility.

## Decision

Create an abstraction layer in `data_sources/ai/` where each provider implements a common interface:

```python
# data_sources/ai/base.py
class BaseAIProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, **kwargs) -> str:
        """Generate a completion for the given prompt."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and accessible."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name."""
        pass
```

Supported providers:
- `gemini.py` - Google Gemini (free tier available)
- `claude.py` - Anthropic Claude
- `openai.py` - OpenAI GPT models
- `groq.py` - Groq Cloud (fast inference)
- `xai.py` - xAI Grok
- `ollama.py` - Local models via Ollama

Provider selection in UI settings, with automatic fallback.

## Consequences

### Positive
- **User choice**: Pick provider based on preference/cost/privacy
- **Easy to add providers**: Implement interface, add to registry
- **Graceful degradation**: Fallback if primary provider unavailable
- **Cost optimization**: Users can use free tiers (Gemini) or local (Ollama)

### Negative
- **Lowest common denominator**: Can't use provider-specific features
- **Prompt engineering**: Same prompt may work differently across providers
- **Testing burden**: Need to test each provider

### Neutral
- API keys stored encrypted in user config
- Provider-specific settings (model name, temperature) configurable
- Response quality varies by provider and model

## References
- `data_sources/ai/`
- `gui_qt/dialogs/settings_dialog.py` (AI settings tab)
- `core/ai_upgrade_advisor.py` (consumer of AI providers)

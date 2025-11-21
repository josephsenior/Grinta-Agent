# Tutorial: Configuring LLM Providers

Learn how to configure and use multiple LLM providers with Forge.

## Overview

Forge supports 30+ LLM providers with 200+ models. You can configure multiple providers and switch between them easily.

## Supported Providers

### Major Providers

- **Anthropic** - Claude models (Sonnet, Opus, Haiku)
- **OpenAI** - GPT models (GPT-4, GPT-3.5)
- **OpenRouter** - Access to 200+ models from multiple providers
- **Google** - Gemini models
- **Groq** - Fast inference models
- **Together AI** - Open source models
- **And 25+ more...**

## Step 1: Get API Keys

### Anthropic

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-ant-`)

### OpenAI

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign up or log in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-`)

### OpenRouter

1. Go to [openrouter.ai](https://openrouter.ai)
2. Sign up or log in
3. Navigate to Keys
4. Create a new API key
5. Copy the key (starts with `sk-or-`)

## Step 2: Configure in .env

Edit your `.env` file:

```bash
# Primary model (required)
LLM_MODEL=claude-sonnet-4-20250514
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Additional providers for fallback
OPENAI_API_KEY=sk-your-key-here
OPENROUTER_API_KEY=sk-or-your-key-here
GOOGLE_API_KEY=AIza-your-key-here
GROQ_API_KEY=gsk_your-key-here
```

## Step 3: Model Selection

### Using Model Names

```bash
# Anthropic models
LLM_MODEL=claude-sonnet-4-20250514
LLM_MODEL=claude-opus-4-20250514
LLM_MODEL=claude-haiku-4-20250514

# OpenAI models
LLM_MODEL=gpt-4o
LLM_MODEL=gpt-4-turbo
LLM_MODEL=gpt-3.5-turbo

# OpenRouter models (prefix with openrouter/)
LLM_MODEL=openrouter/anthropic/claude-3.5-sonnet
LLM_MODEL=openrouter/openai/gpt-4o
LLM_MODEL=openrouter/google/gemini-pro
```

### Model Configuration

You can also configure models in code:

```python
from forge.llm import LLMClient

client = LLMClient(
    model="claude-sonnet-4-20250514",
    provider="anthropic",
    api_key="sk-ant-..."
)
```

## Step 4: Test Your Configuration

### Test Single Provider

```bash
# Test Anthropic
poetry run python -c "
from forge.llm import test_connection
test_connection(provider='anthropic', model='claude-sonnet-4-20250514')
"
```

### Test All Providers

```python
# test_providers.py
from forge.llm import LLMClient

providers = {
    'anthropic': ('claude-sonnet-4-20250514', 'ANTHROPIC_API_KEY'),
    'openai': ('gpt-4o', 'OPENAI_API_KEY'),
    'openrouter': ('openrouter/anthropic/claude-3.5-sonnet', 'OPENROUTER_API_KEY'),
}

for provider, (model, key_env) in providers.items():
    try:
        client = LLMClient(model=model, provider=provider)
        response = client.generate("Hello!")
        print(f"✅ {provider}: {response[:50]}...")
    except Exception as e:
        print(f"❌ {provider}: {e}")
```

## Step 5: Provider Fallback

Forge automatically falls back to alternative providers if the primary fails:

```python
# Configure fallback chain
LLM_MODEL=claude-sonnet-4-20250514  # Primary
FALLBACK_MODELS=openrouter/anthropic/claude-3.5-sonnet,gpt-4o  # Fallbacks
```

## Advanced Configuration

### Custom Provider

```python
from forge.llm.providers import BaseProvider

class MyCustomProvider(BaseProvider):
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def generate(self, prompt: str, **kwargs):
        # Your custom implementation
        pass
```

### Provider-Specific Settings

```bash
# Temperature (creativity)
ANTHROPIC_TEMPERATURE=0.7
OPENAI_TEMPERATURE=0.7

# Max tokens
ANTHROPIC_MAX_TOKENS=4096
OPENAI_MAX_TOKENS=4096

# Timeout
LLM_TIMEOUT=60
```

## Cost Considerations

### Model Costs (Approximate)

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| Claude Sonnet 4 | $3 | $15 |
| GPT-4o | $2.50 | $10 |
| GPT-3.5 Turbo | $0.50 | $1.50 |
| Claude Haiku | $0.25 | $1.25 |

### Cost Tracking

Forge tracks costs automatically:

```python
from forge.monitoring import metrics

# View costs
costs = metrics.get_costs()
print(f"Total cost: ${costs.total}")
print(f"By provider: {costs.by_provider}")
```

## Best Practices

### 1. Use Appropriate Models

- **Simple tasks**: Use cheaper models (Haiku, GPT-3.5)
- **Complex tasks**: Use powerful models (Sonnet, GPT-4)
- **Fast responses**: Use Groq or Together AI

### 2. Set Cost Limits

```bash
# Daily cost limit
COST_QUOTA_DAILY=10.0

# Per-request limit
COST_QUOTA_PER_REQUEST=0.10
```

### 3. Monitor Usage

Check your usage regularly:

```bash
# View analytics
curl http://localhost:3000/api/analytics/costs
```

## Troubleshooting

### "No API key found"

**Solution:** Check your `.env` file has the correct key name and format.

### "Invalid API key"

**Solution:** Verify the key is correct and hasn't expired.

### "Rate limit exceeded"

**Solution:** 
- Wait before retrying
- Use a different provider
- Upgrade your API plan

### "Model not found"

**Solution:** Check the model name is correct for the provider.

## Next Steps

- [Your First Conversation](01-first-conversation.md) - Start using Forge
- [Cost Tracking Tutorial](06-cost-tracking.md) - Monitor your spending
- [Best Practices](../guides/best-practices.md) - Development guidelines

## Summary

You've learned:
- ✅ How to get API keys from major providers
- ✅ How to configure multiple providers
- ✅ How to select and switch models
- ✅ How to set up fallback providers
- ✅ How to monitor costs

Your LLM configuration is complete!


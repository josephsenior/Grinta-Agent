# Supporting 200+ LLM Models: Architecture of a Provider-Agnostic System

## The Challenge

Most AI applications hard-code their LLM provider:

```python
# Typical approach (locked to OpenAI)
import openai

response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[...]
)
```

**Problems:**
- Vendor lock-in
- Can't switch if provider has issues
- Can't leverage new models (Grok, Gemini, etc.)
- Users forced to use one provider

## Our Solution: LiteLLM + Custom Provider Layer

We support **200+ models** from **30+ providers** through a unified interface.

```python
# Forge approach (works with ANY provider)
import litellm

response = litellm.completion(
    model=user_choice,  # ANY model!
    messages=[...]
)
```

**Benefits:**
- User choice (pick any LLM)
- Future-proof (new models work instantly)
- Cost optimization (switch to cheaper models)
- Reliability (fallback providers)

## Architecture

### Layer 1: Provider Detection

```python
# From model string, extract provider
"openrouter/gpt-4o" → "openrouter"
"claude-sonnet-4" → "anthropic"
"gpt-5" → "openai"
"ollama/llama3.3:70b" → "ollama"
```

### Layer 2: API Key Management

```python
# Get correct API key for provider
model = "openrouter/gpt-4o"
provider = "openrouter"  # Auto-detected
api_key = get_api_key_for_provider(provider)
# Returns: OPENROUTER_API_KEY from environment
```

**Features:**
- Auto-detection from model string
- Format validation (sk-or- for OpenRouter, sk-ant- for Anthropic)
- Environment variable fallbacks
- Secure storage (never logs full keys)

### Layer 3: Provider Configuration

Each provider has unique requirements:

```python
# Anthropic config
ProviderConfig(
    name='anthropic',
    required_params={'api_key', 'model'},
    forbidden_params={'custom_llm_provider'},
    api_key_prefix='sk-ant-',
)

# OpenRouter config
ProviderConfig(
    name='openrouter',
    required_params={'api_key', 'model'},
    forbidden_params={'base_url', 'api_version'},
    api_key_prefix='sk-or-',
)
```

**Why this matters:**
- Prevents parameter conflicts (OpenRouter breaks if you send base_url)
- Validates API keys (catch typos early)
- Ensures compatibility

### Layer 4: Feature Detection

Models have different capabilities:

```python
# Check what a model supports
features = get_features("claude-haiku-4-5-20251001")

if features.supports_function_calling:
    # Use native tools
if features.supports_prompt_cache:
    # Enable caching (35% cost savings!)
```

**Detected features:**
- Function calling (tools/actions)
- Prompt caching (Claude, some others)
- Vision (images)
- Reasoning effort (o1, o3, Gemini)

## Implementation Details

### Provider Configurations (30+)

We pre-configured 30 providers:

**Commercial:**
- OpenAI, Anthropic, Google (Gemini)
- OpenRouter (meta-provider for 200+ models)
- xAI (Grok), Mistral, Groq
- Perplexity, Cohere, Together AI

**Enterprise:**
- AWS Bedrock
- Azure OpenAI
- Google Vertex AI

**Self-Hosted:**
- Ollama (local models)
- LiteLLM Proxy (custom routing)

Each has:
- Correct environment variable
- Parameter validation
- API key format rules
- Streaming support flags

### Automatic Fallbacks

```python
try:
    # Try primary model
    response = llm.completion(model="claude-4")
except RateLimitError:
    # Automatically fallback to secondary
    response = llm.completion(model="gpt-4o")
```

## Cost Tracking

We track costs across all providers:

```python
# After each request
cost = calculate_cost(
    model="claude-sonnet-4",
    input_tokens=1000,
    output_tokens=500
)
# Updates metrics automatically
```

**Metrics tracked:**
- Cost per model
- Cost per conversation
- Token usage (input/output)
- Cache hit rate (for savings)

## Real-World Examples

### Example 1: Budget User

```python
# Use free models via OpenRouter
model = "openrouter/meta-llama/llama-3.3-70b-instruct:free"
# Cost: $0
```

### Example 2: Quality User

```python
# Use frontier models
model = "claude-sonnet-4-5-20250929"
# Cost: $3/$15 per 1M tokens
# Quality: 77.2% SWE-bench (best)
```

### Example 3: Speed User

```python
# Use fast, cheap models
model = "claude-haiku-4-5-20251001"
# Cost: $1/$5 per 1M tokens (67% cheaper)
# Speed: 2x faster
# Quality: 73.3% SWE-bench (still excellent!)
```

### Example 4: Privacy User

```python
# Run locally with Ollama
model = "ollama/llama3.3:70b"
# Cost: $0 (free)
# Privacy: 100% local
```

## Adding a New Provider

See our complete guide: `docs/examples/02_custom_provider.py`

**Quick version:**
1. Add ProviderConfig to `provider_config.py`
2. Add feature patterns to `model_features.py` (if needed)
3. Test with your API key
4. Submit PR

**Time required:** 15-30 minutes

## Lessons Learned

### 1. Provider Quirks are Real

- Anthropic: Doesn't allow both temperature AND top_p
- OpenRouter: Breaks if you send base_url
- Gemini: Has unique reasoning_effort parameter
- Each provider has gotchas!

**Solution:** Encode all quirks in ProviderConfig

### 2. API Key Validation Saves Time

Catch "wrong provider key" errors BEFORE making LLM call:

```
Wrong: User provides OpenAI key for Claude model
Detection: Key prefix is "sk-" but should be "sk-ant-"  
Fix: Auto-load ANTHROPIC_API_KEY from environment
Result: No wasted API call, better UX
```

### 3. Feature Detection is Critical

```python
# Bad: Assume all models support function calling
tools = [...]  # Crashes for models without support

# Good: Check first
if supports_function_calling:
    tools = [...]
else:
    # Use mock function calling (fallback)
```

## Impact

**For Users:**
- Freedom to choose any LLM
- Can switch providers instantly
- Cost optimization (use cheap models for simple tasks)
- Privacy options (local models via Ollama)

**For Us:**
- Not dependent on any single provider
- Can leverage new models day-1 (Grok 4 Fast, Haiku 4.5, etc.)
- Better pricing power (negotiate with multiple providers)
- Future-proof architecture

## Try It Yourself

Forge supports 200+ models out of the box:

```bash
# See all available models
curl http://localhost:3000/api/options/models

# Use any model
LLM_MODEL=openrouter/x-ai/grok-4-fast

# Or in UI: Settings → Model → Pick from dropdown
```

## Open Source

The full provider system is open source:
- GitHub: https://github.com/yourusername/Forge
- Provider configs: `Forge/core/config/provider_config.py`
- API key manager: `Forge/core/config/api_key_manager.py`

## Conclusion

Building a provider-agnostic LLM system isn't easy, but it's worth it. 30 provider configurations and 200+ models later, our users have the freedom to choose what works best for them.

Next time: How we built self-improving agents with the ACE Framework (post-beta).


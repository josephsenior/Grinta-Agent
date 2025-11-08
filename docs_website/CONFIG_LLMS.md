# Short guide: configuring LLM profiles and API keys

This project supports multiple LLM profiles under the `[llm]` section in `config.toml`.
You can configure a default profile and any number of named profiles. Each profile may
specify a `model`, provider `base_url`, and an `api_key`.

## Examples

1. Default profile (`[llm]`) — used when `agent.llm_config = 'llm'`:

```
[llm]
model = "Forge/gpt-5-mini-2025-08-07"
api_key = "sk_live_..."   # local dev only; avoid committing secrets
```

2. Named profile (`[llm.openrouter_grok]`) — useful to switch providers:

```
[llm.openrouter_grok]
model = "openrouter/x-ai/grok-code-fast-1"
base_url = "https://openrouter.ai/api/v1"
api_key = "sk_live_..."   # or rely on env var OPENROUTER_API_KEY
```

## Selecting which profile an agent uses

In `config.toml` the `agent` section controls which LLM profile is selected by default:

```
[agent]
llm_config = 'openrouter_grok'  # or 'llm' for the default profile
```

## Environment variables (recommended)

For local development it's safer to set API keys via environment variables instead of
saving them in `config.toml`. Common env vars consumed by the codebase:

- `FORGE_API_KEY` — used by Forge provider and by the config loader as a fallback
- `OPENROUTER_API_KEY` — used by OpenRouter-backed profiles (litellm/OpenRouter)

PowerShell example (temporary session):

```powershell
$env:FORGE_API_KEY = "sk_live_..."
$env:OPENROUTER_API_KEY = "sk_live_..."
python .\scripts\debug_inproc_verbose.py
```

## Notes & best practices

- Avoid committing API keys into the repository. Use `setx` or CI secrets for persistence.
- You can create multiple named `[llm.<profile>]` sections for different workloads (planning, finalization, browsing).
- If you want to ensure the agent uses a specific profile, set `agent.llm_config` to that profile name.

If something still fails, re-run `scripts/debug_inproc_verbose.py` and inspect `logs/metasop_verbose_run.json` to see which model and which env vars were detected.

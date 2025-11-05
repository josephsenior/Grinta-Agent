# Setting API keys (recommended workflow)

This project should not store secrets in `config.toml`. Instead, set provider API keys as environment variables.

Recommended variables

- OPENHANDS_API_KEY — key for the OpenHands LLM proxy provider
- OPENROUTER_API_KEY — key for OpenRouter if you use the `openrouter/...` models

Quick options

1. Use the included PowerShell helper to persist the OpenHands key for your user:

```powershell
# Run from repository root (PowerShell)
.\scripts\set_openhands_api_key.ps1
```

This will:

- Prompt for the key securely (no echo)
- Persist the key for your Windows user using `setx`
- Export the key into the current PowerShell session so you can run the debug runner immediately

2. Manually set for the current session only (temporary):

```powershell
$env:OPENHANDS_API_KEY = "sk-..."
```

3. Persist manually (PowerShell):

```powershell
setx OPENHANDS_API_KEY "sk-..."
# Close and reopen shells/IDE to pick up the persistent value
```

Security notes

- Avoid committing API keys to Git. If you accidentally commit a secret, rotate the key immediately.
- Consider using OS-specific secret storage (Windows Credential Manager, macOS Keychain) and CI secret stores for CI environments.

If you'd like, I can remove any other remaining keys from `config.toml` and add helper scripts for other providers.

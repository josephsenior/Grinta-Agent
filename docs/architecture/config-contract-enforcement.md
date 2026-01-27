## Config Contract & Telemetry Hardenings

### Overview

Recent infrastructure passes focused on making agent configuration failures noisy and actionable while avoiding regressions from silent fallbacks. This document records the decisions behind the new guardrails and telemetry knobs so future changes can extend them consistently.

### Schema Versioning

- `forge/core/config/agent_config.py` now declares `CURRENT_AGENT_CONFIG_SCHEMA_VERSION` (currently `2025-11-14`) and expects the same marker in every `[agent.*]` block.  
- `AgentConfig.from_dict()` emits explicit `ValueError`s for unknown fields because `model_config.extra = "forbid"` is re-enabled.  
- Transitional knobs that historically lived only in `config.toml` (e.g., `max_autonomous_iterations`, `stuck_detection_enabled`) are modeled as real Pydantic fields to avoid breaking existing deployments.

### Loader Telemetry & Startup Summary

- `ConfigLoadSummary` (see `forge/core/config/utils.py`) gathers any section-level issues while `load_from_toml()` runs:
  - Missing sections are marked via `record_missing()`
  - Validation errors / alias mismatches call `record()` with the offending section
  - Even when individual `_process_*` helpers raise and return early, `summary.emit()` fires in a `finally` block so operators always see a single aggregated warning such as:
    ```
    Configuration sections skipped or partially applied while loading config.production.toml:
    [core] missing: section missing; defaults applied
    [sandbox] invalid: timeout must be >= 1
    ```
- `forge/core/config/config_telemetry.py` mirrors these counts (`schema_missing`, `schema_mismatch`, `invalid_agent`, `invalid_base`), and the Prometheus endpoint (`forge/server/routes/monitoring.py`) now exports them for dashboards/alerts.

### Secret Sanitization Tightening

- `EventStream._replace_secrets()` previously masked dict/string pairs only. It now walks dicts, lists, tuples, and byte payloads.  
- Secrets are normalized into a regex/byte cache when `set_secrets()` or `update_secrets()` is called, which both improves coverage and avoids repeated `O(n*m)` string replaces on every event.  
- This guarantees warm pools, delegate forks, or other long-lived runtimes can’t leak secrets when nested arrays or binary blobs hit the event bus.

### LLM Debug Prompt Gating

- `forge/core/logger.py` introduces `DEBUG_LLM_PROMPT`. Setting `DEBUG_LLM=1` still forces verbose LLM logging, but the interactive `input()` gate only appears when both `DEBUG_LLM_PROMPT=1` **and** the process is interactive (TTY or pytest monkeypatch).  
- Headless services, CI, and other non-interactive contexts automatically skip the prompt, preventing hangs while preserving opt-in confirmation for local debugging.

### Operational Checklist

- When adding new `[agent.*]` fields, update `AgentConfig` instead of relying on `extra` to swallow them.  
- If a loader helper swallows an exception, ensure it calls `summary.record(...)` so telemetry stays accurate.  
- Emit telemetry counters for any future config sections (e.g., `[runtime]`) before wiring them into dashboards.



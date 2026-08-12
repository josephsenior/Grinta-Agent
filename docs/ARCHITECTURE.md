# Grinta Architecture

This document describes the current Grinta architecture for maintainers.
For historical context and design rationale (not current spec), see `docs/journey/README.md`.

## High-Level Shape

Grinta is the local-first coding agent that survives failures and finishes long tasks. Its architecture has four visible layers:

1. Interface: console-script launcher, Textual TUI for TTYs, non-interactive runner for piped input.
2. Orchestration: session loop, safeguards, retries, finish validation.
3. Execution: local runtime actions (commands, file ops, tool interaction).
4. Durability: event stream and persisted state for recovery/replay.

## Runtime Boundary

Grinta executes on the local host.

- Default runtime is in-process local execution.
- `hardened_local` applies stricter policy checks.
- `hardened_local` is not sandboxing or host isolation.
- `sandboxed_local` reuses the hardened policy and adds OS-native,
  process-scoped isolation for supported **non-interactive** subprocess
  commands (`bwrap` on Linux, AppContainer on Windows, `sandbox-exec` on
  macOS).
- Interactive PTY sessions remain outside the `sandboxed_local` process
  boundary. The profile is not a VM, container boundary, or complete host
  isolation.

Use Grinta in trusted environments.

## System Overview

```text
User (terminal)
  -> backend.cli.entry
    -> Textual TUI when stdin is a TTY
    -> non-interactive runner when stdin is piped
      -> SessionOrchestrator
        -> Engine (planning + tool intent)
        -> Operation pipeline and safety checks
        -> RuntimeExecutor (commands/files/tools)
        -> Observations
        -> EventStream (durable history)
        -> Task validation before finish
```

## Package Topology

```text
backend/
  cli/            Console entrypoints, Textual TUI, non-interactive runner, slash commands
  context/        Memory and compaction
  core/           Config, constants, logging, shared utilities
  engine/         Agent reasoning, prompt assembly, and tool implementations
  evaluation/     Agent eval pack and related evaluation helpers
  execution/      Local runtime, shell/session plumbing, and executor internals
  inference/      Provider routing and direct LLM clients
  integrations/   External integration adapters (MCP; see docs/INFERENCE_AND_INTEGRATIONS.md)
  knowledge/      Optional retrieval and knowledge features
  ledger/         Event types, serialization, stream infrastructure
  orchestration/  Session orchestrator and focused services
  persistence/    Storage and state persistence
  playbooks/      Playbook definitions and helpers
  security/       Command risk analysis and policies
  telemetry/      Lightweight instrumentation
  tools/          Repo maintenance utilities (not the model-facing tool API)
  utils/          Shared helpers (imports, LSP, HTTP, etc.)
  validation/     Completion and quality validation
```

## Interface Layer

The public console script is `launch.entry:main`, which resolves the installed
or editable project entry file without relying on whatever `backend/` package
may be present in the user's working directory. The resolved path runs
`backend.cli.entry`.

`backend.cli.entry` handles global flags and subcommands:

- `grinta` starts the app in the current project.
- `grinta init` (or first interactive `grinta`) writes user configuration.
- `grinta sessions ...` lists, shows, exports, deletes, and prunes persisted sessions.
- `--project`, `--model`, `--theme`, `--minimal`, `--accessible`, and `--cleanup-storage` customize startup.

`backend.cli.main` then selects the runtime surface:

- TTY stdin -> `backend.cli.tui.main`, the Textual application with transcript cards, HUD, dialogs, and keyboard shortcuts.
- Non-TTY stdin -> `backend.cli.repl.noninteractive`, for scripted/piped one-shot runs.

Interactive UX is the Textual TUI only. The `backend/cli/repl/` package holds slash-command handlers and the non-interactive runner.

### CLI surfaces

| Surface | Path | Role |
| --- | --- | --- |
| **Textual TUI** (product) | `backend/cli/tui/` | Default when stdin is a TTY. Full HUD, slash commands, sessions dialog, mode/autonomy controls. |
| **Slash-command layer** | `backend/cli/repl/slash_command_*` | Shared `/help`, `/mode`, `/health`, etc. Used by TUI and tests. |
| **Non-interactive** | `backend/cli/repl/noninteractive.py` | Piped stdin / one-shot automation. |

New UX work lands in the TUI; keep slash-command handlers thin when parity is required (for example `/mode`, `/autonomy`, `/health`).

## Orchestration Layer

The orchestrator delegates to focused services under `backend/orchestration/services/`.
Current service modules include:

- `action_execution_service.py` - Executes agent actions via the runtime
- `action_service.py` - Action lifecycle management
- `autonomy_service.py` - Controls agent autonomy and delegation
- `circuit_breaker_service.py` - Prevents cascading failures
- `confirmation_service.py` - Handles user confirmation flows
- `event_router_service.py` - Routes events to appropriate handlers
- `exception_handler_service.py` - Centralized exception handling
- `guard_bus.py` - Pub/sub guard rail for system events
- `iteration_guard_service.py` - Prevents infinite loops
- `iteration_service.py` - Manages iteration counting and limits
- `lifecycle_service.py` - Manages agent lifecycle transitions
- `observation_service.py` - Processes observations from actions
- `orchestration_context.py` - Shared service wiring and context object
- `pending_action_service.py` - Tracks in-flight actions
- `recovery_service.py` - Error recovery and retry logic
- `retry_service.py` - Handles retry policies
- `safety_service.py` - Validates actions against safety policies
- `state_transition_service.py` - Manages valid state transitions
- `step_decision_service.py` - Decides whether to continue or finish
- `step_guard_service.py` - Pre-step validation checks
- `step_prerequisite_service.py` - Ensures prerequisites are met
- `stuck_detection_service.py` - Detects stuck agents
- `task_validation_service.py` - Validates task completion

Design intent:

- split control-plane concerns into testable units
- classify errors into recoverable vs terminal paths
- reduce false completion with explicit task tracking and completion-quality validation signals

### Middleware Pipeline

The orchestrator uses a middleware pipeline (assembled in
`backend/orchestration/mixins/lifecycle.py`)
for cross-cutting concerns:

```python
middlewares = [
    SafetyValidatorMiddleware(self),  # Validate action safety
    BlackboardMiddleware(self),  # Track action context
    CircuitBreakerMiddleware(self),  # Prevent cascading failures
    ProgressPolicyMiddleware(),  # Progress indicators
    CostQuotaMiddleware(self),  # Budget tracking
    ContextWindowMiddleware(self),  # Context window management
    RollbackMiddleware(),  # State rollback support
    DestructiveCommandMiddleware(),  # Block dangerous commands
    PreExecDiffMiddleware(),  # Generate diffs before edits
    AutoCheckMiddleware(),  # Post-execution validation
    PostEditDiagnosticsMiddleware(),  # Diagnostics after edits
    SymbolIndexInvalidationMiddleware(),  # Invalidate changed symbol indexes
    FileStateMiddleware(),  # File-state tracking
    LoggingMiddleware(self),  # Request/response logging
    TelemetryMiddleware(self),  # Metrics collection
    ToolResultValidator(),  # Validate tool outputs
]
```

Middleware execution order matters - safety checks run first, telemetry runs last.

### Key Flows

#### Step Execution Flow
1. `SessionOrchestrator.step()` enters the guarded step lifecycle.
2. The engine plans or continues the next action.
3. `PendingActionService` records runnable actions by stream id.
4. The middleware pipeline validates and enriches the action.
5. `ActionExecutionService` dispatches to the local execution server.
6. The resulting observation is appended and routed.
7. Completion, retry, and state-transition services decide the next state.

#### Error Recovery Flow
1. Exception occurs during step
2. `services.recovery.react_to_exception(e)` called
3. Error classified as recoverable or terminal
4. Recoverable: retry with backoff via `services.retry`
5. Terminal: emit an error observation and transition to `ERROR`

#### Lifecycle Transitions
The canonical transition graph is `VALID_TRANSITIONS` in
`backend/orchestration/services/state_transition_service.py`. Public states
include `LOADING`, `RUNNING`, `AWAITING_USER_INPUT`,
`AWAITING_USER_CONFIRMATION`, `RETRYING`, `RATE_LIMITED`, `FINISHED`,
`REJECTED`, `ERROR`, and `STOPPED`.

## Execution Layer

Execution is implemented in `backend/execution/`.

Important components:

- `server/action_execution_server.py`: runtime executor used by the local runtime
- `aes/security_enforcement.py`: policy checks for command/path behavior
- `browser/`: native browser session and CDP helpers
- `dap/`: debugger adapter protocol integration
- `mcp/`: bundled MCP configuration; integration clients live under
  `backend/integrations/mcp/`
- `utils/`: command helpers, diffing, session handling, monitoring

## Durability Layer

Events flow through `backend/ledger/` and persistence modules.

Key properties:

- event-oriented state history
- replay-friendly serialization
- backpressure and stream controls
- persistence support for reliable recovery paths

Workspace rollback is a separate durability path. Grinta consumes the
standalone [ShadowGit](https://github.com/josephsenior/ShadowGit) package through
`backend/execution/rollback/shadow_repo.py`. It writes content-addressed
snapshots to a private bare object store under Grinta's per-workspace data and
never modifies the user's `.git`. Restores preserve bytes, symlinks, and POSIX
executable modes, quarantine post-snapshot extras, and use a recovery journal
to resume or repair an interrupted restore. `RollbackManager` owns Grinta's
checkpoint policy and manifest; ShadowGit owns snapshot storage and restore
mechanics.

## Configuration Model

Default local setup uses:

- installed `~/.grinta/settings.json`, or repository `settings.json` when running from source, for user-facing model/provider keys
- environment variables for automation and secret injection
- `~/.grinta/workspaces/<id>/storage` for runtime/session state

Minimal fields in `settings.template.json`:

- `llm_provider`
- `llm_model`
- `llm_api_key`
- `llm_base_url`

The package metadata reports `1.0.0`.

## Reliability and Safety

Core runtime protections include:

- retry and recovery services
- circuit breaker and stuck detection
- task tracking and completion-quality validation signals before finish
- security policy checks in execution path

These controls are designed to reduce false-success runs and uncontrolled loops while keeping the local workflow fast.

For detailed reliability patterns, see [RELIABILITY.md](RELIABILITY.md).
For performance considerations, see [PERFORMANCE.md](PERFORMANCE.md).

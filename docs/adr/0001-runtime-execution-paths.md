# ADR-0001: Runtime Execution Paths – Hybrid Sync/Async

Date: 2025-11-12

Status: Accepted (Beta)

## Context

The runtime contained two methods named `_execute_action`: one async (agent path) and one sync (direct runtime path). The sync method unintentionally shadowed the async one, bypassing provider token refresh, timeout setup, and long-running detection.

The codebase mixes async (agent loop, event handling) and sync (runtime tool methods like `run`, `read`, `write`, `edit`, and `run_action`) APIs, and tests rely on synchronous execution in several spots.

## Decision

Adopt a hybrid approach during beta:

- Keep `async _execute_action(event)` for agent-driven execution. It performs token refresh, timeouts, and long-running detection, and is awaited by `_handle_action()`.
- Introduce `def _execute_action_sync(action)` for synchronous internal calls. Route `run_action()` and verification helpers through this method.
- Update tests invoking the previous sync `_execute_action` to use `_execute_action_sync`.
- Fix comparator bug in `AgentSession.close()` to trigger only after exceeding the wait window.

## Changes Implemented

- `forge/runtime/base.py`:
  - Added `_execute_action_sync(...)` and routed `run_action()` and verification helpers to it.
  - Preserved `async _execute_action(...)` for the agent pipeline.
- `forge/server/session/agent_session.py`:
  - Changed `<=` to `>=` in close timeout check.
- Tests:
  - Updated the unit test that used the sync path to call `_execute_action_sync(...)`.

## Rationale

- Backward compatibility: Avoids breaking sync callers and existing tests during beta.
- Safety: Restores intended async behavior (timeouts, token refresh) for agent flows.
- Minimal surface area change: Small, targeted refactor instead of a broad async migration.

## Consequences

- Two execution paths exist by design. Developers should prefer:
  - Agent path: `await _execute_action(event)` (async) inside `_handle_action()`.
  - Direct runtime path: `_execute_action_sync(action)` when already in a synchronous context.
- Future migration to full async will still require deprecating sync convenience methods.

## Migration Plan (Future)

1. Introduce async counterparts for sync APIs (`async_run_action`, `async_read/write/edit`).
2. Provide adapters both ways for a transition period.
3. Switch controllers, runtimes, and tests incrementally to async variants.
4. Deprecate sync methods with warnings; remove in a major version once adoption is complete.

## Alternatives Considered

- Immediate full async refactor: Cleaner long-term but high churn and risk during beta.
- Keep duplicate `_execute_action` methods: Error-prone; caused critical behavior regressions.

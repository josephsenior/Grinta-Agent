# Controller Service Directory

This document describes the service-oriented design around `AgentController` after the 2025 modernization pass. Use it as the canonical reference when extending or replacing controller functionality.

## Service Map

| Service | Module | Responsibilities | Depends On |
| --- | --- | --- | --- |
| `LifecycleService` | `forge.controller.services.lifecycle_service` | Initialize controller identity, event stream subscriptions, state tracker, replay context | Config, file store, event stream |
| `IterationService` | `forge.controller.services.iteration_service` | Apply dynamic iteration limits from tool metadata/analyzers | `ToolInvocationContext`, agent config |
| `IterationGuardService` | `forge.controller.services.iteration_guard_service` | Run control flags, enforce iteration/budget limits, initiate graceful shutdowns | `ControllerContext`, state tracker |
| `StepGuardService` | `forge.controller.services.step_guard_service` | Gate each step via circuit breaker checks and stuck detection with recovery hooks | `CircuitBreakerService`, `StuckDetectionService`, controller context |
| `StepPrerequisiteService` | `forge.controller.services.step_prerequisite_service` | Ensure controller only steps when RUNNING and no pending action awaits observations | `ControllerContext`, ActionService |
| `BudgetGuardService` | `forge.controller.services.budget_guard_service` | Keep budget control flags in sync with aggregated LLM cost metrics before each step | `ControllerContext`, StateTracker |
| `ActionExecutionService` | `forge.controller.services.action_execution_service` | Handle LLM/context errors, run pipeline plan/execute stages, delegate action sourcing to `ConfirmationService` | `ControllerContext`, Tool pipeline, ActionService |
| `PendingActionService` | `forge.controller.services.pending_action_service` | Track pending actions, emit timeout events, expose info for guards and telemetry | `ControllerContext`, Event stream |
| `ConfirmationService` | `forge.controller.services.confirmation_service` | Evaluate autonomy/confirmation policy, source actions (replay vs live), transition controller to awaiting confirmation state | `ControllerContext`, `SafetyService`, Replay manager |
| `SafetyService` | `forge.controller.services.safety_service` | Security analyzer integration and risk evaluation for confirmation workflow | Autonomy controller, security analyzer |
| `ActionService` | `forge.controller.services.action_service` | Tool pipeline plan/verify/execute orchestration, telemetry, pending-action lifecycle | `ToolInvocationPipeline`, `ObservationService`, `PendingActionService`, `ConfirmationService` |
| `ObservationService` | `forge.controller.services.observation_service` | Observation logging, pipeline observe stage, action metrics prep | `ActionService`, controller context |
| `DelegateService` | `forge.controller.services.delegate_service` | Delegate agent spawn/teardown, task priming, completion observations, runtime hand-off bookkeeping | `AgentController`, event stream, `DelegateRuntimeProvider` |
| `DelegateRuntimeProvider` | `forge.controller.services.delegate_runtime_provider` | Acquire/release forked runtimes for delegates, bridge delegate event streams back to parent, enforce repo/env token inheritance | `RuntimeOrchestrator`, runtime pool, `DelegateService` |
| `RecoveryService` | `forge.controller.services.recovery_service` | Exception handling, retry coordination, status callbacks, rate-limit state transitions | `RetryService`, circuit breaker |
| `TelemetryService` | `forge.controller.services.telemetry_service` | Tool middleware composition, blocked-action telemetry | Controller config |
| `RetryService` / `CircuitBreakerService` / `StuckDetectionService` | `forge.controller.services.*` | Cross-cutting resilience features that plug into `RecoveryService` and `ActionService` | External queues, detectors |

All services receive a `ControllerContext`, which exposes narrow getters/setters (`state`, `event_stream`, `emit_event`, `set_agent_state`, etc.). Direct mutation of controller attributes outside these services is discouraged.

## Extension Guidelines

1. **Add a service, not a helper**: When a new responsibility doesn’t fit existing services (e.g., future “PlanningService”), define a module under `forge.controller.services`, accept a `ControllerContext`, and register it in `AgentController`.
2. **Avoid hidden coupling**: if a service needs another service, inject it explicitly (as `ActionService` does with `ObservationService`). This keeps dependency chains auditable and makes it easier to stub dependencies in tests (e.g., `DelegateService` receiving `DelegateRuntimeProvider` from `AgentSession` wiring).
3. **Honor context boundaries**: use `ControllerContext` methods (`emit_event`, `pop_action_context`, `set_pending_action`) rather than reaching into controller attributes directly.
4. **Return awaitables for async work**: services should expose async methods (`async def run(...)`) so `AgentController` can schedule or await them consistently.

## Testing Guidance

- **Unit tests per service** live under `tests/unit/controller/` (see `test_service_layers.py`). Use lightweight stubs/mocks for the controller and pipelines. When adding lifecycle changes, prefer covering them via the new `LifecycleService` tests rather than wiring bespoke controller fixtures.
- **Integration slices**: when a change touches multiple services, add scenario tests that instantiate `AgentController` with real services but substitute mocks for external dependencies (LLM, runtime, file store).
- **Stress tests**: keep high-load behaviors (EventStream persistence, retry bursts) under `tests/stress/` to avoid slowing the default suite; mark with `pytest.mark.stress`.

## Adding New Responsibilities

1. Document the service in this file (table entry + short description). For support helpers (e.g., `DelegateRuntimeProvider`), include how they’re injected so future contributors know where state flows.
2. Update `docs/architecture/agent-controller-modernization.md` if the change alters the control flow or service interactions.
3. Add focused tests demonstrating the new behavior.

By following this pattern, `AgentController` remains a thin orchestrator, and future features can leverage or replace services without reintroducing the god-class anti-pattern.


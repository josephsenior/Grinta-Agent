# Grinta Agent Engine

Grinta ships one production agent engine: the **Orchestrator**. Browser, MCP,
debugger, LSP, memory, and editing features are capabilities exposed to that
engine; they are not separate agents.

## Runtime model

```text
user input -> SessionOrchestrator -> Orchestrator -> Planner -> tools
           <- observations / state / validation / completion evidence
```

The engine proposes tool calls and consumes observations. The orchestration
layer owns lifecycle, confirmation, middleware, retries, pending actions, and
completion policy. The execution layer performs approved actions.

## Main implementation

- `backend/engine/orchestrator.py` coordinates a model turn.
- `backend/engine/orchestrator_helpers/` contains step, recovery, prompt, and
  condensation helpers.
- `backend/engine/planner.py` builds and mode-filters the model toolset.
- `backend/engine/executor.py` and `executor_mixins/` process streaming and
  non-streaming model responses.
- `backend/engine/function_calling/` validates and dispatches tool calls.
- `backend/engine/prompts/` builds the system prompt from Python renderers and
  markdown partials.
- `backend/engine/tools/` defines native tools.
- `backend/engine/tool_registry.py` validates the LLM-facing tool registry.

The exact toolset depends on configuration and interaction mode:

- **Chat** exposes read/discovery tools plus user questions.
- **Plan** adds task state, task tracking, and acceptance criteria.
- **Agent** exposes the configured execution surface, including edits,
  terminals, browser, debugger, memory, and MCP tools.

The canonical mode policy is `backend/core/interaction_modes.py`; toolset
construction is in `backend/engine/planner.py`.

## Browser and MCP

Native browser execution lives under `backend/execution/browser/`, with the
model-facing tool in `backend/engine/tools/browser_native.py`. External MCP
servers are integrated under `backend/integrations/mcp/` and reached through
the compact MCP gateway tool.

## Extensibility boundary

The supported extension points are tools, MCP servers, provider/model
configuration, and orchestration services. Grinta does not currently ship an
Echo, Locator, Auditor, or other peer engine, and the repository does not
document a stable third-party agent-class plugin API.

See [ARCHITECTURE.md](ARCHITECTURE.md),
[INFERENCE_AND_INTEGRATIONS.md](INFERENCE_AND_INTEGRATIONS.md), and
[`backend/engine/README.md`](../backend/engine/README.md).

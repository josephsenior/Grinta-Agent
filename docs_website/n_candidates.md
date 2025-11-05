# n_candidates adapter contract

This document describes the optional multi-candidate contract between the orchestrator and the CodeAct engineer adapter.

Purpose

- Allow the orchestrator to request N candidate variants from the agent in a single invocation to reduce token cost and latency.

How it works

- The orchestrator sets a hint in the orchestration context under the key `n_candidates::<step.id>` with the integer number of requested candidates.
- Adapters may honor this hint and instruct the agent to write a JSON summary at `.metasop/engineer_step.json` containing a top-level `candidates` array.
- Each element of `candidates` may be either:
  - A string: interpreted as the candidate content
  - An object: expected keys include `content` (string), optional `diff` (string), and optional `meta` (object)

Adapter behavior

- The adapter will return a `StepResult` whose `artifact.content` contains `artifact_path` and, when present, a `candidates` key with the parsed list from the agent summary file.
- If no summary file or `candidates` array is present, adapters should continue to return their default artifact content. The orchestrator falls back to repeat-invoking the executor when needed.

Notes

- This contract is intentionally opt-in and backward-compatible. Adapters that don't implement the behavior will be used as before.
- Agents should only write `.metasop/engineer_step.json` inside the repository working directory.

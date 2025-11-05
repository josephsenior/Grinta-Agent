# MetaSOP Architecture Gap Analysis

Date: 2025-09-06
Status: Draft v1

## Executive Summary

The MetaSOP subsystem has evolved rapidly to incorporate provenance hashing, environment signature capture, lightweight semantic memory, verification result structuring, remediation scaffolding, and manifest export. While foundational observability and traceability are strong, higher-order autonomy (closed-loop adaptive planning, intelligent remediation execution, and parallel scheduling) remains nascent. This document catalogs current state, enumerates gaps, and proposes target-state actions prioritized by leverage and dependency structure.

## Current Capabilities Snapshot

| Capability                                                            | Status                           | Notes                                                                                      |
| --------------------------------------------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------------ |
| Step Modeling (`StepResult`, `ExpectedOutcome`, `VerificationResult`) | Implemented                      | Verification populated for QA + expected outcome paths.                                    |
| Provenance (artifact & step hash chain)                               | Implemented                      | Deterministic SHA-256 chain, stored in artifacts & events.                                 |
| Environment Reproducibility                                           | Implemented                      | Signature + payload captured & exported in manifest.                                       |
| Lightweight Memory (TF‑IDF)                                           | Implemented (ingest + retrieval) | Retrieval injected pre-step; deterministic scoring.                                        |
| Retrieval-Augmented Generation                                        | Partial                          | Injected context; not yet adaptive (no summarization / token budgeting).                   |
| Failure Taxonomy Classification                                       | Implemented                      | Provides failure_type + meta for warnings/failures.                                        |
| Remediation Strategy Mapping                                          | Implemented (static)             | Advisory only; no automated plan execution.                                                |
| Verification Lifecycle                                                | Partial                          | Expected vs observed for steps with declared criteria; continuous improvement loop absent. |
| Coverage / Quality Metrics                                            | Implemented                      | Coverage deltas + efficiency metrics captured.                                             |
| Token Efficiency Tracking                                             | Implemented                      | Basic per-run metrics; no adaptive throttling.                                             |
| Run Manifest Export                                                   | Implemented                      | Includes hashes, remediation, efficiency, memory stats.                                    |
| Parallel Scheduling                                                   | Not started                      | Linear orchestration only; no lock semantics.                                              |
| Middleware / Hook Pipeline                                            | Not started                      | Cross-cutting concerns inline in orchestrator.                                             |
| Adaptive Budget / Model Strategy                                      | Not started                      | Advisory only on soft budget exceedance.                                                   |
| Automated Remediation Execution                                       | Not started                      | Strategies descriptive only.                                                               |
| Post-Run Analytics / Trend Store                                      | Not started                      | No aggregation of historical manifests.                                                    |

## Key Gap Categories

1. **Execution Flexibility & Concurrency**
   - Lack of lock categorization prevents safe parallel step execution.
   - Orchestrator monolith mixes concerns (retrieval, budget, hashing, remediation injection).
2. **Closed-Loop Remediation & Learning**
   - Remediation plans not converted into actionable follow-up steps or micro-SOPs.
   - No memory of remediation efficacy (success/failure attribution).
3. **Adaptive Resource Management**
   - Token budgets produce passive advisories only; no dynamic context pruning or model fallback logic.
4. **Memory Utilization Depth**
   - Retrieval static: top-k raw excerpts only.
   - No summarization layer, decay/eviction, or semantic clustering for long runs.
5. **Verification Expansion**
   - Coverage of expected outcome application limited to steps that explicitly provide criteria.
   - No aggregate run-level objective reconciliation (e.g., coverage target vs. achieved).
6. **Template Validation & Safety**
   - Step condition mini-language minimally parsed; errors only discovered at runtime.
   - No static validation of schema references or dependency DAG cycles.
7. **Observability & Analytics**
   - Manifests exported per-run but not aggregated for trend (MTTR, common failures, token per role).
8. **Pluggability / Extensibility**
   - No formal middleware pipeline for pre-step (retrieval, enrichment) and post-step (hashing, verification, remediation suggestion).
9. **Security / Policy Enforcement**
   - Engineer system-ops heuristic coarse; lacks centralized policy engine and audit denial logs.
10. **Governance & Compliance**
    - Provenance strong; no signature attestation or tamper-proof channel (e.g., signed manifest with private key).

## Detailed Gap Narratives & Proposed Target State

### 1. Execution Flexibility & Concurrency

Current: Sequential loop within orchestrator; all steps processed inline.
Target: Scheduler abstraction with:

- Step metadata: `lock: read_only|write|test|network`
- Dependency DAG + lock-aware planner to run non-conflicting read-only steps concurrently.
- Future extension: priority queue + backpressure when token budget near hard limit.
  Actions:
- Extend `SopStep` schema with optional `lock` & `priority`.
- Introduce `StepScheduler` interface (plan() -> execution order / batches).
- Migrate loop to consume scheduler output (list of batches).

### 2. Closed-Loop Remediation & Learning

Current: Remediation suggestions appear in events; no execution.
Target: Automatic generation of remediation micro-steps inserted into tail of run (if budget remains).
Actions:

- Represent `RemediationAction` as convertible to `SopStep` prototype.
- Add policy guard (toggle) for auto-remediation.
- Log outcome (success/fail) to remediation effectiveness store (JSONL).
- Add simple bandit heuristic to rank actions by past success.

### 3. Adaptive Resource Management

Current: Soft budget advisory only; no active optimization.
Target: Dynamic adaptation loop:

- If soft budget crossed early (<50% steps executed) reduce retrieval k, enforce summarization, fallback to cheaper model for low-criticality roles.
- If nearing hard budget, early-stop optional downstream steps flagged `optional=true`.
  Actions:
- Add role cost tiers & optional flag to template.
- Implement budget watcher middleware.

### 4. Memory Utilization Depth

Current: Raw TF‑IDF retrieval; no summarization / aging.
Target: Multi-tier memory:

- Short-term (recent steps), long-term (clustered summaries), ephemeral caches.
- Summarizer step merges semantically similar artifacts after N steps.
- Optional embedding backend swap (pluggable interface).
  Actions:
- Introduce `MemoryStrategy` abstraction.
- Add summarization job every K steps (configurable).
- Implement retention policy (max records or TTL).

### 5. Verification Expansion

Current: Metric verification per step where provided.
Target: Hierarchical verification: step → run objectives → historical benchmarks.
Actions:

- Add run-level `RunObjectives` (e.g., min_coverage, max_failures).
- Compute run verification summary; export in manifest.
- Use failure of run objectives to trigger remediation wave.

### 6. Template Validation & Safety

Current: Runtime parse errors & potential schema mismatches.
Target: Pre-flight validator CLI: `metasop validate <template>` producing structured warnings/errors.
Actions:

- Build parser for condition expressions to AST with type checks.
- Validate dependency graph is acyclic & all schemas exist.
- Emit summary + exit code for CI gating.

### 7. Observability & Analytics

Current: Per-run manifest only.
Target: Aggregated metrics store (SQLite or JSONL) enabling queries: failure frequency, coverage progression, token cost trends.
Actions:

- Append minimal summary line per run to `~/.openhands/runs/index.jsonl`.
- Provide `analyze_runs.py` utility to compute aggregates.

### 8. Pluggability / Middleware

Current: Cross-cutting logic in orchestrator.
Target: Middleware pipeline: `pre_step(ctx, step, state) -> modifications`, `post_step(ctx, step, result) -> events`.
Actions:

- Define middleware interface & registry.
- Extract retrieval, hashing, verification, remediation suggestion, budget checks.
- Allow enabling/disabling via config.extended.metasop.middlewares list.

### 9. Security / Policy Enforcement

Current: Heuristic permission inference only for engineer system ops.
Target: Central policy engine evaluating actions against rules (deny/allow + reason).
Actions:

- Define `PolicyRule` objects (pattern → effect).
- Log policy decisions to manifest.
- Provide admin override mechanism.

### 10. Governance & Compliance

Current: Unsigned manifest; integrity only (hash).
Target: Signed attestation chain: private key signs manifest hash, optional transparency log.
Actions:

- Generate signing key pair (local) or integrate KMS.
- Include signature + public key fingerprint in manifest.
- Optional transparency append (Merkle root) for multi-run set.

## Prioritized Roadmap (Quarter-Sized Increments)

| Priority | Epic                                       | Rationale                                          | Dependencies                     |
| -------- | ------------------------------------------ | -------------------------------------------------- | -------------------------------- |
| P1       | Middleware extraction                      | Enables safer iteration on other concerns          | None                             |
| P1       | Template validation CLI                    | Shifts failures left; improves safety              | None                             |
| P2       | Adaptive budget middleware                 | Controls cost escalation early                     | Middleware base                  |
| P2       | Remediation auto-execution MVP             | Closes loop for simple failures                    | Middleware base, remediation map |
| P2       | Scheduler lock metadata                    | Unlocks future concurrency; low coupling           | Template schema update           |
| P3       | Run objectives + hierarchical verification | Strengthens quality gating                         | Verification base present        |
| P3       | Memory summarization & retention           | Prevents context bloat, improves retrieval quality | Current memory index             |
| P3       | Analytics aggregation index                | Enables data-driven optimization                   | Manifest export                  |
| P4       | Policy engine & audit                      | Security posture, enterprise readiness             | Middleware base                  |
| P4       | Manifest signing                           | Compliance & provenance trust                      | Manifest export                  |
| P4       | Concurrency execution batches              | After lock metadata stable                         | Scheduler metadata               |

## Risk Assessment

| Risk                                 | Impact | Mitigation                                                                    |
| ------------------------------------ | ------ | ----------------------------------------------------------------------------- |
| Orchestrator complexity growth       | Medium | Middleware refactor early (P1)                                                |
| Retrieval token inflation            | Medium | Summarization + adaptive k in P2/P3                                           |
| Auto-remediation causing regressions | High   | Start read-only dry-run mode; require pass/fail gating                        |
| Concurrency race conditions          | High   | Incremental simulation mode: logging-only scheduler before real parallel exec |
| Policy misconfiguration              | Medium | Provide dry-run policy evaluation CLI                                         |

## Metrics to Track Going Forward

- remediation_success_rate
- mean_tokens_per_step (by role) trend
- coverage_delta_cumulative
- failure_type_distribution (top 5 over last N runs)
- retrieval_avg_score_top3 vs success correlation
- time_to_first_successful_remediation

## Target State Summary (12–18 Weeks)

A modular, middleware-driven orchestrator executing a lock-aware schedule, with adaptive budgets, memory summarization, auto-generated remediation micro-steps, cryptographically signed manifests, and aggregated analytics guiding iterative optimization—pushing overall architecture maturity toward 9.0+.

## Appendix: Quick Wins (can implement in < 1 day each)

- Add `SopStep.lock` field + no-op acceptance in templates.
- CLI validator stub printing dependency graph.
- Budget watcher that trims retrieval k after soft exceed.
- Summarize last 5 memory records into a rolling “context digest” key.
- Write index.jsonl aggregator on manifest export.

---

End of document.

# DeepSWE paired harness case study — 2026-09-01

## Scope

This is the repository's initial **paired harness case study**. It is the
authoritative record for the eight controlled DeepSWE trials retained under
`evaluation/deepswe/jobs/` on the study machine. It replaces interpreting
individual exploratory runs as results.

This is *not* an official DeepSWE leaderboard submission, a full-suite score,
or a statistically representative model evaluation. The tasks were selected
for implementation diversity, there is one rollout per harness and task, and
the Grinta runtime changed during the study. The external DeepSWE verifier is
the only source of pass/fail; a Grinta `FINISHED` state is not a benchmark
pass.

## Protocol

- **Benchmark and verifier:** DeepSWE v1.1 tasks through DataCurve Pier, with
  the task's isolated behavioral verifier.
- **Compared harnesses:** Grinta's Pier adapter versus Pier's native Codex CLI
  adapter. The Grinta arm runs the normal Grinta orchestrator; it does not use
  Codex CLI as its harness.
- **Model:** `codex/gpt-5.6-luna`, reasoning effort `medium`, Codex CLI
  `0.150.1` for both arms.
- **Authentication:** ChatGPT subscription session carried into the isolated
  task container. No OpenAI API key or usage-billed API fallback was used.
  Any cost displayed in a Pier artifact is an API-equivalent estimate, not a
  subscription charge.
- **Controls:** same task base commit, one trial per arm, concurrency one,
  `--max-retries 0`, and no human changes to task workspaces.
- **Scheduling:** arms were deliberately sequential: Grinta first, then Codex
  only after Grinta had a final verifier result. This avoids simultaneous
  subscription-capacity contention, but it does not make timings a strict
  wall-clock performance comparison.

The first three Grinta task pairs used revision
`762801c210e9f43b4f50af81e0f62493295d0d93`. The remaining five used
`ef435454275cc10e821d705c29ce8f3d86f69a67`, which includes the terminal
background-outcome lifecycle fixes made during the investigation. Therefore
this document describes the study as a whole, not a score for one frozen
Grinta revision.

## Results

`F2P` is task-specific verifier tests; `P2P` is pre-existing project tests.
Reward is all-or-nothing: any failed verifier test yields `0`.

| Task | Language | Grinta F2P / P2P / reward | Codex CLI F2P / P2P / reward |
| --- | --- | --- | --- |
| `abs-module-cache-flags` | JavaScript | 20/20 · 3/3 · **1** | 0/20 · 3/3 · 0 |
| `go-git-worktree-merge-conflicts` | Go | 14/17 · 2/2 · 0 | 2/17 · 2/2 · 0 |
| `wazero-multi-module-snapshots` | Go | 78/78 · 2/2 · **1** | 77/78 · 2/2 · 0 |
| `fastapi-implicit-head-options` | Python | 41/43 · 3134/3134 · 0 | 42/43 · 3131/3134 · 0 |
| `httpx-streaming-json-iteration` | Python | 97/108 · 1404/1404 · 0 | 108/108 · 1404/1404 · **1** |
| `testem-per-launcher-reports` | JavaScript | 64/65 · 469/469 · 0 | 64/65 · 469/469 · 0 |
| `cattrs-partial-structuring-recovery` | Python | 68/69 · 7/7 · 0 | 69/69 · 7/7 · **1** |
| `actionlint-action-pinning-lint` | Go | 55/55 · 145/145 · **1** | 55/55 · 144/145 · 0 |

Descriptively, Grinta received reward on 3/8 tasks, Codex CLI on 2/8, and
three pairs were ties at reward zero. Across heterogeneous task-specific tests,
Grinta passed 437/455 and Codex CLI passed 417/455. Those aggregates are useful
for auditability only; they should not be promoted as a general DeepSWE score.

## Interpretation

The study establishes that Grinta can complete externally verified DeepSWE
tasks using ChatGPT subscription authentication, including two full-reward Go
tasks and a task where the Codex control introduced a regression. It also shows
that native Codex CLI was generally more step- and time-efficient in this small
sample and achieved full reward on two tasks Grinta missed.

These results are evidence for continued harness work, not evidence that either
harness is universally superior. A publishable comparative benchmark needs a
frozen Grinta revision, a pre-registered task selection rule, multiple rollouts
per task, and a separate capacity/latency measurement plan.

## Evidence and reproduction

The eight final paired job directories remain locally under
`evaluation/deepswe/jobs/` and are intentionally Git-ignored because they can
contain large generated artifacts and run-local data. There is one retained
Grinta/Codex pair per task; retries, failed environment setup, and superseded
pairs were removed.

Use [the evaluation protocol](README.md) for prerequisites, authentication
handling, and the exact `pier run` pattern. Never commit `auth.json`, raw
trajectories containing credentials, or generated job directories.

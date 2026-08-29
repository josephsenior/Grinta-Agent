# Grinta × DeepSWE v1.1

This is the preliminary, reproducible Grinta evaluation protocol. It uses the
official DataCurve **Pier** harness and DeepSWE's external behavioral verifier.
Grinta's own `FINISHED` state is diagnostic and can never produce a PASS.

## What is being evaluated

The agent under test is **Grinta**, not Pier's built-in Codex agent:

```text
Pier / DeepSWE task
        ↓
custom Grinta Pier adapter
        ↓
normal headless Grinta Orchestrator
        ↓
Codex app-server model transport (ChatGPT subscription)
        ↓
Grinta tools, state, validation, recovery, patch, and trajectory
        ↓
external DeepSWE verifier
```

`--agent-import-path evaluation.deepswe.pier_agent:Grinta` is what selects the
Grinta harness. Codex supplies the model responses inside Grinta; the command
never uses Pier's `-a codex` agent implementation.

## Frozen model policy

The reported 20-task subset uses:

- `codex/gpt-5.6-sol`
- reasoning effort `xhigh`
- ChatGPT subscription authentication
- no OpenAI API key and no usage-billed API fallback
- one attempt, concurrency 1, zero human intervention
- deterministic selection: `--n-tasks 20 --sample-seed 0`

`codex/gpt-5.6-luna` at `low` is reserved for a single unreported smoke trial.
It must not be mixed into the reported results. The exact machine-readable
definition is in [`protocol.json`](protocol.json), and the resolved task IDs are
frozen in [`subset_seed0_n20.json`](subset_seed0_n20.json).

Token-derived catalog cost is stored only as an **API-equivalent estimate**. It
is not an actual subscription charge and cannot terminate a run. A ChatGPT plan
limit is classified as an infrastructure/capacity failure, never silently
retried with another model.

## Zero-token preflight

The preflight makes no model request:

```powershell
python -m evaluation.deepswe.preflight
```

It requires all of the following before any smoke run:

1. `codex login status` reports an authenticated Codex session. If not, run
   `codex login` and choose ChatGPT sign-in.
2. `datacurve-pier` is installed (`uv tool install datacurve-pier`).
3. Docker is running and accessible.
4. The tracked protocol still enforces `codex/` subscription transport and
   disables usage-billed API execution.

Do not add `OPENAI_API_KEY` to this workflow.

## Authentication boundary

Pier runs agents inside isolated containers. Pass the Codex CLI auth cache via
`CODEX_AUTH_JSON_PATH`; the adapter uploads it to a temporary container path and
removes it after the agent exits. Never copy `auth.json` into this repository,
the jobs directory, a trajectory, or a published artifact. Treat it like a
password.

On Windows the usual host path is:

```powershell
$env:CODEX_AUTH_JSON_PATH = "$env:USERPROFILE\.codex\auth.json"
```

## One smoke trial

First clone and pin DeepSWE, then run an oracle trial to verify Docker and the
verifier without using a model:

```powershell
git clone -c core.autocrlf=false https://github.com/datacurve-ai/deep-swe.git
git -C deep-swe checkout 0b9fabbb63b9104d678fe965e1632f2dd9eaa2ea
git -C deep-swe rev-parse HEAD
pier run -p deep-swe/tasks/abs-module-cache-flags -a oracle `
  -o evaluation/deepswe/jobs --job-name smoke-oracle -q -y
```

The `core.autocrlf=false` clone option is mandatory on Windows. DeepSWE's
verifier entrypoints are Linux shell scripts; CRLF checkout conversion makes
them fail before a reward file can be produced.

After the oracle passes, commit and push the Grinta benchmark adapter. Substitute
that exact 40-character commit below. Then run one **unreported** Luna trial:

```powershell
pier run -p deep-swe/tasks/abs-module-cache-flags `
  --agent-import-path evaluation.deepswe.pier_agent:Grinta `
  --model codex/gpt-5.6-luna `
  --agent-kwarg grinta_commit=<exact-40-character-Grinta-commit> `
  --agent-kwarg reasoning_effort=low `
  --agent-kwarg codex_version=0.150.1 `
  --agent-env CODEX_AUTH_JSON_PATH="$env:CODEX_AUTH_JSON_PATH" `
  --agent-timeout-multiplier 2 `
  -o evaluation/deepswe/jobs --job-name smoke-grinta -q -y
```

The adapter installs the exact Grinta revision and Codex CLI version inside the
task image, invokes normal headless Grinta, and writes `manifest.json`,
`model.patch`, and `trajectory.json` under Pier's agent artifacts.

## Reported deterministic subset

Only after the oracle and one Luna smoke trial succeed:

```powershell
$subset = Get-Content evaluation/deepswe/subset_seed0_n20.json | ConvertFrom-Json
$taskArgs = foreach ($taskId in $subset.task_ids) { '--include-task-name'; $taskId }

pier run -p deep-swe/tasks `
  --agent-import-path evaluation.deepswe.pier_agent:Grinta `
  --model codex/gpt-5.6-sol `
  --agent-kwarg grinta_commit=<exact-40-character-Grinta-commit> `
  --agent-kwarg reasoning_effort=xhigh `
  --agent-kwarg codex_version=0.150.1 `
  --agent-env CODEX_AUTH_JSON_PATH="$env:CODEX_AUTH_JSON_PATH" `
  @taskArgs --n-tasks 20 --sample-seed 0 -n 1 -k 1 --max-retries 0 `
  --agent-timeout-multiplier 2 `
  -o evaluation/deepswe/jobs --job-name grinta-deepswe-v1-1-n20-seed0 -q -y
```

Before publication, record the exact DeepSWE and Pier revisions, the resulting
20 task IDs, Grinta commit, config/protocol hashes, verifier output, patches, and
trajectories. Label the result “DeepSWE v1.1 — deterministic preliminary subset
(n=20, seed=0),” not a full DeepSWE score.

## Direct runner dry-run

The lower-level runner validates provenance without model usage:

```powershell
python -m evaluation.deepswe.run_grinta `
  --workspace C:\path\to\prepared-task `
  --instruction "dry-run only" `
  --task-id example `
  --grinta-commit <exact-40-character-Grinta-commit> `
  --output-dir evaluation/deepswe/artifacts/example `
  --dry-run
```

External verifier output remains a separate immutable artifact. Do not copy its
verdict into Grinta's manifest.

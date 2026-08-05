# Grinta 1.0 — First Stable Release

Grinta 1.0 is the first stable release of the local-first coding agent that survives failures and finishes long tasks. Version 1.0.0 is published on PyPI and as a GitHub release.

## Highlights

- Local execution, session state, checkpoints, and audit trails
- Provider-agnostic inference across hosted and local models
- LSP and debugger integrations
- Recovery-oriented orchestration for failures, timeouts, malformed tool calls, and context pressure
- Chat, Plan, and Agent workflows in a terminal UI
- Risk classification, confirmation gates, secret masking, and execution profiles

## Evidence

The launch evidence includes the sanitized 4h 33m autonomous-run report with 16,393 events and 373 tool outcomes, plus the Raft recovery recording distributed as a GitHub Release asset.

## Install

```bash
pipx install grinta
grinta
```

Python 3.12 and 3.13 are supported. Consult the support matrix and security checklist before increasing autonomy or running against untrusted repositories.

## Release integrity

Install the published package from PyPI and verify that `grinta --version` reports `1.0.0`. Maintainers should use the current [release checklist](RELEASE_CHECKLIST.md) for later releases.

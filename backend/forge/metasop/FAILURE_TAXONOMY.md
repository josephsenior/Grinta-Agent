# Failure Taxonomy

This document lists the failure categories used by MetaSOP and the corrective hints mapped to each.

Failure categories

- `schema_validation`: Schema validation errors when the produced JSON doesn't match the expected schema.
- `json_parse`: JSON parsing or repair failures.
- `qa_test_fail`: Unit/integration test failures (pytest traces, assertions).
- `qa_lint_fail`: Linting/style failures (eslint, flake8, etc.).
- `build_error`: Build/import errors (ModuleNotFoundError, ImportError).
- `runtime_error`: Runtime exceptions (Traceback lines, TypeError, NameError).
- `dependency_error`: Dependency resolution or version conflicts.
- `retries_exhausted`: All retries attempted without producing a valid artifact.
- `budget_exceeded`: Hard token budget exceeded.
- `semantic_gap`: Fallback for outputs that are structurally incorrect but show no clear error signature.

Corrective hint mapping

- `json_parse`: "Ensure you output STRICT JSON. Remove commentary and markdown fences."
- `schema_validation`: "Re-check required keys and types; fill arrays/objects even if empty."
- `qa_test_fail`: "Analyze failing assertion trace; propose minimal code diff to satisfy expected behavior."
- `qa_lint_fail`: "Run lint locally (eslint/flake8) and fix style errors before re-running."
- `build_error`: "Resolve import/module errors (missing file, wrong path, dependency not installed)."
- `dependency_error`: "Adjust dependency spec or install version compatible with existing lockfile."
- `runtime_error`: "Inspect stack trace variable values; guard against None/undefined and type mismatches."
- `semantic_gap`: "Clarify ambiguous requirement—ensure acceptance criteria fully addressed."
- `retries_exhausted`: "Stop repeating same structure—rewrite response from scratch guided by schema."
- `budget_exceeded`: "Reduce verbosity; consolidate sections; avoid repeating unchanged code."

Usage

- The orchestrator will attach `failure_type` and `meta` fields to `step_events` when failures are detected.
- The CLI reporter aggregates `failure_type` counts and surfaces top categories.

Guidance

- Add unit tests that simulate stderr/stdout/validation_err snippets to ensure `classify_failure` maps correctly.
- Consider labeling events with a uniform `severity` integer: executed=0, advisory=1, warning=2, failed=3.

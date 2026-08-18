# Execution Evidence

Execution Evidence is a compact, privacy-preserving record of what occurred during a
Grinta session. It is observational: the EventStream remains the source of truth for
full action and observation data, while `EXECUTION_EVIDENCE` records in `session.jsonl`
hold correlation IDs, structural metadata, and canonical SHA-256 fingerprints.

Schema v1 event kinds are `model_turn`, `tool_execution`, `control_intervention`,
`context_compaction`, `checkpoint`, `user_input`, `finish_declared`, and
`completion_validation`. Unknown kinds and optional fields are ignored by the
projector to keep the format forward compatible.

Evidence never stores duplicate prompt text, command text, tool arguments, source
contents, stdout, or stderr. Full execution detail remains retrievable through the
ledger. `session.evidence.json` is an atomically written, rebuildable deterministic
projection of `session.jsonl`; it is not a new persistence system.

`finish_declared` records that the agent declared completion and the recorded task
state. The optional completion validator is still advisory. Execution Evidence
records what happened and what Grinta observed. It does not independently certify
that the user's task was completed correctly.

A future verifier can consume the report plus its ledger correlations without
changing executor completion semantics.

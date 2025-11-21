# MetaSOP (experimental)

MetaGPT-inspired orchestration layer for Forge. Provides:

- Role Profiles (PM, Architect, Engineer, QA)
- SOP templates (e.g., feature_delivery)
- Prompt scaffolding with structured JSON outputs
- Schema validation with corrective re-prompts
- Adapter to run steps via Forge agents
- Minimal QA runner (pytest) and shaped reports

Feature-flag integration recommended.

## Layout

```
Forge/metasop/
  models.py         # Pydantic data models
  registry.py       # YAML/JSON loaders for profiles/SOPs/schemas
  validators.py     # JSON/schema validation + corrective prompts
  orchestrator.py   # Linear orchestrator MVP
  adapters/
    Forge.py    # Adapter stub for Forge agent execution
  profiles/*.yaml   # Role profiles
  sops/*.yaml       # SOP definitions
  templates/schemas/*.json  # Output schemas
```

## Quick start

```python
from forge.metasop.orchestrator import MetaSOPOrchestrator

orch = MetaSOPOrchestrator("feature_delivery")
ok, artifacts = orch.run(user_request="Add CSV export endpoint", repo_root="/workspace/repo")
print(ok, list(artifacts.keys()))
```

## Notes

- This is an MVP. The adapter must be wired to the real Forge agent runner.
- Schemas use JSON Schema draft-07 for compatibility with our validator.
- Add a config flag (metasop.enabled) to guard in production.

## UI Designer (Conditional Role)

An optional `UI Designer` profile and `designer.schema.json` have been added. It is only invoked in the enhanced SOP `feature_delivery_with_ui` when the Product Manager sets `ui_multi_section=true` in its JSON output (and may optionally provide `ui_sections` to indicate scale).

### Gating Fields (Product Manager Output)

```
ui_multi_section: boolean  # triggers UI Designer step when true
ui_sections: number        # approximate count of distinct UI panels/sections
```

### Designer Output Schema

```
layout_plan: string                # hierarchical outline of sections & component mapping
accessibility: [{issue, severity(low|med|high), recommendation}]
design_tokens: object              # color/spacing/typography tokens reused or needed
risks: [string]                    # design / cohesion risks
next_engineering_focus: [string]   # concrete next tasks for Engineer
```

### SOP Variant

Use `feature_delivery_with_ui` to allow conditional design. It inserts a `ui_design` step after `pm_spec` with condition:

```
condition: "pm_spec.ui_multi_section == true"
```

If the flag is false or absent, flow proceeds directly to architecture.

### Rationale

Avoids overhead on trivial UI changes while enforcing a structured layout + accessibility pass on multi-section interfaces, improving consistency and reducing refactors.

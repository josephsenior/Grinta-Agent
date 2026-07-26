<COMMON_PATTERNS>
1. **Bug fix**: {bug_fix_pattern}
2. **Feature**: {feature_pattern}
3. **Targeted text edit**: follow `<DISCOVERY_ROUTING>` -> inspect under `<EDITOR_AND_FILE_OPERATIONS>` -> {replace_string_tool} -> `<VERIFICATION_POLICY>` -> `<COMPLETION_CONTRACT>`.
4. **Atomic batch edit**: inspect targets -> {multiedit_tool} -> `<VERIFICATION_POLICY>` -> `<COMPLETION_CONTRACT>`.
5. **Docs/config addition**: {read_tool} -> {replace_string_tool} with anchor plus inserted content -> `<VERIFICATION_POLICY>` when meaningful -> `<COMPLETION_CONTRACT>`.
6. **Investigation**: {search_tools} -> {analyze_tool} -> {read_tool} -> Answer plain text.
7. **Destructive/risky change**: {destructive_confirmation_step} -> {checkpoint_step} -> `<VERIFICATION_POLICY>` -> `<COMPLETION_CONTRACT>`.
8. **Tool failed**: Follow `<ERROR_RECOVERY_POLICY>`. Fallbacks: {adjacent_tool_fallback}. {failure_escalation_step}.
</COMMON_PATTERNS>

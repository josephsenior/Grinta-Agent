import json
import pathlib
import sys
from typing import Any, Mapping

from forge.llm.fn_call_converter import convert_fncall_messages_to_non_fncall_messages

test_file = (
    pathlib.Path(__file__).parents[1]
    / "tests"
    / "unit"
    / "llm"
    / "test_llm_fncall_converter.py"
)
ns: dict[str, Any] = {}
code = test_file.read_text(encoding="utf-8")
exec(compile(code, str(test_file), "exec"), ns)  # nosec B102 - Safe: debug script
FNCALL_MESSAGES = ns["FNCALL_MESSAGES"]
FNCALL_TOOLS = ns["FNCALL_TOOLS"]
NON_FNCALL_MESSAGES = ns["NON_FNCALL_MESSAGES"]
converted = convert_fncall_messages_to_non_fncall_messages(
    FNCALL_MESSAGES, FNCALL_TOOLS
)
print(f"expected len={len(NON_FNCALL_MESSAGES)}, actual len={len(converted)}")
minlen = min(len(NON_FNCALL_MESSAGES), len(converted))
for i in range(minlen):
    if NON_FNCALL_MESSAGES[i] != converted[i]:
        print(f"first difference at index {i}")
        print("--- expected ---")
        print(json.dumps(NON_FNCALL_MESSAGES[i], indent=2, ensure_ascii=False))
        print("--- actual ---")
        print(json.dumps(converted[i], indent=2, ensure_ascii=False))

        def _extract_text(m: Mapping[str, Any]) -> str:
            content = m.get("content")
            if isinstance(content, list):
                parts = [
                    c.get("text", "")
                    for c in content
                    if isinstance(c, Mapping) and c.get("type") == "text"
                ]
                return "\n".join(parts)
            if isinstance(content, str):
                return content
            return ""

        exp_text = _extract_text(NON_FNCALL_MESSAGES[i])
        act_text = _extract_text(converted[i])
        import difflib

        print("\n--- text diff ---")
        for l in difflib.unified_diff(
            exp_text.splitlines(), act_text.splitlines(), lineterm=""
        ):
            print(l)
        sys.exit(0)
if len(NON_FNCALL_MESSAGES) != len(converted):
    print("messages differ in length but all common indices equal")
else:
    print("no message-level differences found")

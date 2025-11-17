import difflib
import json
import pathlib
from typing import Any

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
exp = json.dumps(NON_FNCALL_MESSAGES, indent=2, ensure_ascii=False)
act = json.dumps(converted, indent=2, ensure_ascii=False)
print("\n".join(difflib.unified_diff(exp.splitlines(), act.splitlines(), lineterm="")))

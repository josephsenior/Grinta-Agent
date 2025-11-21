import importlib
import json
from typing import Any

to_check: dict[str, list[str]] = {
    "forge.core.config": [
        "load_FORGE_config",
        "AppConfig",
        "ForgeConfig",
        "LLMConfig",
        "ForgeMCPConfigImpl",
    ],
    "forge.core.logger": ["forge_logger", "get_trace_context"],
    "forge.core.pydantic_compat": ["model_dump_json"],
    "forge.events.observation": [],
    "forge.events.action": [],
}

results: dict[str, dict[str, Any]] = {}
for mod, attrs in to_check.items():
    info: dict[str, Any] = {"imported": False, "file": None, "attrs": {}, "dir": []}
    try:
        m = importlib.import_module(mod)
        info["imported"] = True
        info["file"] = getattr(m, "__file__", None)
        info["dir"] = sorted([n for n in dir(m) if not n.startswith("_")])
        for a in attrs:
            info["attrs"][a] = hasattr(m, a)
    except Exception as e:
        info["error"] = repr(e)
    results[mod] = info

print(json.dumps(results, indent=2))

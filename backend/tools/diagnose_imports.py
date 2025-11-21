import importlib
import sys
import inspect

modules = [
    "forge",
    "forge.core",
    "forge.core.config",
    "forge.core.logger",
    "mcp",
    "mcp.types",
    "fastmcp",
]

print("Python executable:", sys.executable)
print("sys.path[0]:", sys.path[0])
print("---")
for name in modules:
    try:
        mod = importlib.import_module(name)
        path = getattr(mod, "__file__", None) or (
            getattr(mod, "__path__", None) and list(mod.__path__)[0]
        )
        print(f"{name} -> {path}")
        if hasattr(mod, "load_FORGE_config"):
            print("  contains load_FORGE_config")
        if hasattr(mod, "get_trace_context"):
            print("  contains get_trace_context")
    except Exception as e:
        print(f"{name} IMPORT ERROR: {e}")

# Show top-level forge package location if available
try:
    import forge

    print("\nforge package spec:", forge.__spec__)
except Exception:
    pass

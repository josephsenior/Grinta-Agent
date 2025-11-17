import importlib

try:
    mod = importlib.import_module("mcp.types")
    print("FOUND", getattr(mod, "__file__", None))
except Exception as e:
    print("ERR", repr(e))

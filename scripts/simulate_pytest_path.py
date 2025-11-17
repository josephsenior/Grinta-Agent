import sys, os, importlib

repo_root = os.getcwd()
# simulate pytest adding tests paths early
sim_paths = [os.path.join(repo_root, "tests", "unit"), os.path.join(repo_root, "tests")]
for p in reversed(sim_paths):
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)
print("sys.path[0:6]=", sys.path[:6])
try:
    m = importlib.import_module("mcp")
    print("mcp module file:", getattr(m, "__file__", None))
    print("mcp __path__:", getattr(m, "__path__", None))
    try:
        t = importlib.import_module("mcp.types")
        print("mcp.types file:", getattr(t, "__file__", None))
    except Exception as e:
        print("mcp.types import error:", repr(e))
except Exception as e:
    print("import mcp error:", repr(e))

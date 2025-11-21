import sys
import importlib

checks = [
    ("forge.core.config", "ForgeConfig"),
    ("forge.core.logger", "get_trace_context"),
    ("forge.events.action", "MessageAction"),
    ("forge.events.observation", "FileReadObservation"),
    ("forge.runtime.utils.bash_constants", None),
]

print("Python:", sys.version)
print("sys.path:")
for p in sys.path:
    print("  ", p)

for module_name, attr in checks:
    print("\nChecking module:", module_name, "attr:", attr)
    try:
        mod = importlib.import_module(module_name)
        print(" module __file__:", getattr(mod, '__file__', 'package or namespace'))
        if attr:
            print(" has attr:", hasattr(mod, attr))
            if hasattr(mod, attr):
                print(" attr type:", type(getattr(mod, attr)))
    except Exception as e:
        print(" import error:", type(e).__name__, e)

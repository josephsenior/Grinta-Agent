import importlib, traceback
try:
    m = importlib.import_module('forge.events.observation')
    attrs = [a for a in dir(m) if not a.startswith('_')]
    print('OK, attributes:', sorted(attrs))
except Exception:
    print('IMPORT ERROR:')
    traceback.print_exc()

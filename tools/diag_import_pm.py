import importlib, traceback
try:
    m = importlib.import_module('forge.runtime.utils.process_manager')
    print('OK, module file:', getattr(m,'__file__',None))
    print('attrs:', [a for a in dir(m) if not a.startswith('_')][:50])
except Exception:
    traceback.print_exc()

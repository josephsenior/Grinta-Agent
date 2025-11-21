import importlib
import sys
try:
    import forge
    print('forge package:', getattr(forge, '__file__', getattr(forge, '__path__', None)))
except Exception as e:
    print('error importing forge:', e)
try:
    fc = importlib.import_module('forge.core.config')
    print('forge.core.config file:', getattr(fc, '__file__', None))
except Exception as e:
    print('error importing forge.core.config:', e)
print('--- sys.path (first 15 entries) ---')
for i, p in enumerate(sys.path[:15], 1):
    print(f'{i}: {p}')

import sys, importlib, inspect
print('\n=== Direct import probe in same interpreter ===')
print('sys.path preview:')
for p in sys.path[:50]:
    print('-', p)
try:
    from forge.core.config import ForgeConfig
    print('ForgeConfig imported from', inspect.getsourcefile(ForgeConfig))
except Exception as e:
    print('Import failed:', e)
print('=== End probe ===\n')

import sys, importlib, traceback, inspect
print('sys.path:')
for p in sys.path:
    print('-', p)

module_name = 'tests.unit.runtime.impl.test_docker_runtime'
try:
    m = importlib.import_module(module_name)
    print('Imported module', module_name, 'from', inspect.getsourcefile(m))
except Exception:
    traceback.print_exc()

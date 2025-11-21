import importlib
import traceback
import conftest

try:
    m = importlib.import_module('forge.core.config')
    print('module:', m)
    print('file:', getattr(m, '__file__', None))
    print('has ForgeConfig:', hasattr(m, 'ForgeConfig'))
    if hasattr(m, 'ForgeConfig'):
        print('ForgeConfig repr:', repr(m.ForgeConfig))
except Exception as e:
    traceback.print_exc()

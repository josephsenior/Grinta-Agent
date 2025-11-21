import traceback
try:
    from forge.core.config import ForgeConfig
    import inspect
    print('ForgeConfig import OK, file:', inspect.getsourcefile(ForgeConfig))
except Exception:
    traceback.print_exc()

try:
    import forge.events.observation as obs
    import inspect
    print('forge.events.observation file:', inspect.getsourcefile(obs))
    print('has FileReadObservation?', hasattr(obs, 'FileReadObservation'))
    print('has CmdOutputObservation?', hasattr(obs, 'CmdOutputObservation'))
    print('members:', [n for n in dir(obs) if 'Observation' in n][:200])
except Exception:
    traceback.print_exc()

try:
    from forge.runtime.utils.process_manager import ProcessManager
    import inspect
    print('ProcessManager OK, file:', inspect.getsourcefile(ProcessManager))
except Exception:
    traceback.print_exc()

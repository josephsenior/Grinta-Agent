import asyncio

from forge.runtime.utils.process_manager import ProcessManager


class _DummyObs:
    def __init__(self, content: str = "", exit_code: int = 0):
        self.content = content
        self.exit_code = exit_code


class _FakeRuntime:
    def __init__(self):
        self.commands = []

    def run(self, action):  # action is CmdRunAction in production; here we accept any
        # Capture the command string for assertions
        cmd = getattr(action, "command", str(action))
        self.commands.append(cmd)
        return _DummyObs()


async def _do_cleanup_and_capture(pm: ProcessManager, runtime: _FakeRuntime):
    await pm.cleanup_all(runtime=runtime)


def test_process_manager_cleanup_uses_full_command_and_clears_state(event_loop):
    pm = ProcessManager()
    runtime = _FakeRuntime()

    # Register two representative long-running commands
    pm.register_process("uvicorn main:app --reload", command_id="c1")
    pm.register_process("npm run dev", command_id="c2")
    assert pm.count() == 2

    # Run async cleanup using provided event loop from conftest
    event_loop.run_until_complete(_do_cleanup_and_capture(pm, runtime))

    # Assert pkill invoked with full command strings (TERM then KILL) for each
    commands_str = "\n".join(runtime.commands)
    assert "pkill -TERM -f 'uvicorn main:app --reload'" in commands_str
    assert "pkill -9 -f 'uvicorn main:app --reload'" in commands_str
    assert "pkill -TERM -f 'npm run dev'" in commands_str
    assert "pkill -9 -f 'npm run dev'" in commands_str

    # Manager should clear internal state after cleanup
    assert pm.count() == 0

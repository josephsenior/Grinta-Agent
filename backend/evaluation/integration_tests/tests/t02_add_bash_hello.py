from evaluation.integration_tests.tests.base import BaseIntegrationTest, TestResult
from evaluation.utils.shared import assert_and_raise
from forge.events.action import CmdRunAction
from forge.events.event import Event
from forge.runtime.base import Runtime


class Test(BaseIntegrationTest):
    INSTRUCTION = "Write a shell script '/workspace/hello.sh' that prints 'hello'."

    @classmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        action = CmdRunAction(command="mkdir -p /workspace")
        obs = runtime.run_action(action)
        assert_and_raise(obs.exit_code == 0, f"Failed to run command: {obs.content}")

    @classmethod
    def verify_result(cls, runtime: Runtime, histories: list[Event]) -> TestResult:
        action = CmdRunAction(command="cat /workspace/hello.sh")
        obs = runtime.run_action(action)
        if obs.exit_code != 0:
            return TestResult(
                success=False,
                reason=f"Failed to cat /workspace/hello.sh: {obs.content}.",
            )
        action = CmdRunAction(command="bash /workspace/hello.sh")
        obs = runtime.run_action(action)
        if obs.exit_code != 0:
            return TestResult(
                success=False,
                reason=f"Failed to execute /workspace/hello.sh: {obs.content}.",
            )
        if obs.content.strip() != "hello":
            return TestResult(
                success=False, reason=f'Script did not print "hello": {obs.content}.'
            )
        return TestResult(success=True)

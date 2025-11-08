import os
import tempfile
from evaluation.integration_tests.tests.base import BaseIntegrationTest, TestResult
from forge.events.action import CmdRunAction
from forge.events.event import Event
from forge.runtime.base import Runtime


class Test(BaseIntegrationTest):
    INSTRUCTION = "Fix typos in bad.txt."

    @classmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, "bad.txt")
            with open(temp_file_path, "w", encoding='utf-8') as f:
                f.write("This is a stupid typoo.\nReally?\nNo mor typos!\nEnjoy!")
            runtime.copy_to(temp_file_path, "/workspace")

    @classmethod
    def verify_result(cls, runtime: Runtime, histories: list[Event]) -> TestResult:
        action = CmdRunAction(command="cat /workspace/bad.txt")
        obs = runtime.run_action(action)
        if obs.exit_code != 0:
            return TestResult(success=False, reason=f"Failed to run command: {obs.content}")
        if obs.content.strip().replace("\r\n", "\n") == "This is a stupid typo.\nReally?\nNo more typos!\nEnjoy!":
            return TestResult(success=True)
        return TestResult(success=False, reason=f"File not fixed: {obs.content}")

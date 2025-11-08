import os
import tempfile
from evaluation.integration_tests.tests.base import BaseIntegrationTest, TestResult
from evaluation.utils.shared import assert_and_raise
from forge.events.action import AgentFinishAction, CmdRunAction, MessageAction
from forge.events.event import Event
from forge.events.observation import AgentDelegateObservation
from forge.runtime.base import Runtime

HTML_FILE = '\n<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>The Ultimate Answer</title>\n    <style>\n        body {\n            display: flex;\n            justify-content: center;\n            align-items: center;\n            height: 100vh;\n            margin: 0;\n            background: linear-gradient(to right, #1e3c72, #2a5298);\n            color: #fff;\n            font-family: \'Arial\', sans-serif;\n            text-align: center;\n        }\n        .container {\n            text-align: center;\n            padding: 20px;\n            background: rgba(255, 255, 255, 0.1);\n            border-radius: 10px;\n            box-shadow: 0 0 10px rgba(0, 0, 0, 0.2);\n        }\n        h1 {\n            font-size: 36px;\n            margin-bottom: 20px;\n        }\n        p {\n            font-size: 18px;\n            margin-bottom: 30px;\n        }\n        #showButton {\n            padding: 10px 20px;\n            font-size: 16px;\n            color: #1e3c72;\n            background: #fff;\n            border: none;\n            border-radius: 5px;\n            cursor: pointer;\n            transition: background 0.3s ease;\n        }\n        #showButton:hover {\n            background: #f0f0f0;\n        }\n        #result {\n            margin-top: 20px;\n            font-size: 24px;\n        }\n    </style>\n</head>\n<body>\n    <div class="container">\n        <h1>The Ultimate Answer</h1>\n        <p>Click the button to reveal the answer to life, the universe, and everything.</p>\n        <button id="showButton">Click me</button>\n        <div id="result"></div>\n    </div>\n    <script>\n        document.getElementById(\'showButton\').addEventListener(\'click\', function() {\n            document.getElementById(\'result\').innerText = \'The answer is Forge is all you need!\';\n        });\n    </script>\n</body>\n</html>\n'


class Test(BaseIntegrationTest):
    INSTRUCTION = "Browse localhost:8000, and tell me the ultimate answer to life."

    @classmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        action = CmdRunAction(command="mkdir -p /workspace")
        obs = runtime.run_action(action)
        assert_and_raise(obs.exit_code == 0, f"Failed to run command: {obs.content}")
        action = CmdRunAction(command="mkdir -p /tmp/server")
        obs = runtime.run_action(action)
        assert_and_raise(obs.exit_code == 0, f"Failed to run command: {obs.content}")
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = os.path.join(temp_dir, "index.html")
            with open(temp_file_path, "w", encoding='utf-8') as f:
                f.write(HTML_FILE)
            runtime.copy_to(temp_file_path, "/tmp/server")  # nosec B108 - Safe: test environment
        action = CmdRunAction(command="cd /tmp/server && nohup python3 -m http.server 8000 &")
        obs = runtime.run_action(action)

    @classmethod
    def verify_result(cls, runtime: Runtime, histories: list[Event]) -> TestResult:
        from forge.core.logger import forge_logger as logger

        message_actions = [
            event
            for event in histories
            if isinstance(event, (MessageAction, AgentFinishAction, AgentDelegateObservation))
        ]
        logger.debug("Total message-like events: %s", len(message_actions))
        for event in message_actions:
            try:
                if isinstance(event, AgentDelegateObservation) or (
                    not isinstance(event, AgentFinishAction) and isinstance(event, MessageAction)
                ):
                    content = event.content
                elif isinstance(event, AgentFinishAction):
                    content = event.outputs.get("content", "")
                else:
                    logger.warning("Unexpected event type: %s", type(event))
                    continue
                if "Forge is all you need!" in content:
                    return TestResult(success=True)
            except Exception as e:
                logger.error("Error processing event: %s", e)
        logger.debug("Total messages: %s. Messages: %s", len(message_actions), message_actions)
        return TestResult(
            success=False,
            reason=f"The answer is not found in any message. Total messages: {
                len(message_actions)}.",
        )

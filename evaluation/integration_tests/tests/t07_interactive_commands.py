import hashlib
from evaluation.integration_tests.tests.base import BaseIntegrationTest, TestResult
from forge.events.action import AgentFinishAction, FileWriteAction, MessageAction
from forge.events.event import Event
from forge.events.observation import AgentDelegateObservation
from forge.runtime.base import Runtime


class Test(BaseIntegrationTest):
    INSTRUCTION = 'Execute the python script /workspace/python_script.py with input "John" and "25" and tell me the secret number.'
    SECRET_NUMBER = int(hashlib.sha256(str(25).encode()).hexdigest()[:8], 16) % 1000

    @classmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        from forge.core.logger import forge_logger as logger

        action = FileWriteAction(
            path="/workspace/python_script.py",
            content='name = input("Enter your name: "); age = input("Enter your age: "); import hashlib; secret = int(hashlib.sha256(str(age).encode()).hexdigest()[:8], 16) % 1000; print(f"Hello {name}, you are {age} years old. Tell you a secret number: {secret}")',
        )
        logger.info(action, extra={"msg_type": "ACTION"})
        observation = runtime.run_action(action)
        logger.info(observation, extra={"msg_type": "OBSERVATION"})

    @classmethod
    def verify_result(cls, runtime: Runtime, histories: list[Event]) -> TestResult:
        from forge.core.logger import forge_logger as logger

        message_actions = [
            event
            for event in histories
            if isinstance(
                event, (MessageAction, AgentFinishAction, AgentDelegateObservation)
            )
        ]
        logger.info("Total message-like events: %s", len(message_actions))
        for event in message_actions:
            try:
                if isinstance(event, AgentDelegateObservation) or (
                    not isinstance(event, AgentFinishAction)
                    and isinstance(event, MessageAction)
                ):
                    content = event.content
                elif isinstance(event, AgentFinishAction):
                    content = event.outputs.get("content", "")
                    if event.thought:
                        content += f"\n\n{event.thought}"
                else:
                    logger.warning("Unexpected event type: %s", type(event))
                    continue
                if str(cls.SECRET_NUMBER) in content:
                    return TestResult(success=True)
            except Exception as e:
                logger.error("Error processing event: %s", e)
        logger.debug(
            "Total messages: %s. Messages: %s", len(message_actions), message_actions
        )
        return TestResult(
            success=False,
            reason=f"The answer is not found in any message. Total messages: {
                len(message_actions)
            }.",
        )

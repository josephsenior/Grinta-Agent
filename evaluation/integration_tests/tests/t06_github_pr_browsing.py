from evaluation.integration_tests.tests.base import BaseIntegrationTest, TestResult
from forge.events.action import AgentFinishAction, MessageAction
from forge.events.event import Event
from forge.events.observation import AgentDelegateObservation
from forge.runtime.base import Runtime


class Test(BaseIntegrationTest):
    INSTRUCTION = "Look at https://github.com/All-Hands-AI/Forge/pull/8, and tell me what is happening there and what did @asadm suggest."

    @classmethod
    def initialize_runtime(cls, runtime: Runtime) -> None:
        pass

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
                if (
                    "non-commercial" in content
                    or "MIT" in content
                    or "Apache 2.0" in content
                ):
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

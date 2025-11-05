import asyncio
import logging
from openhands.core.config import OpenHandsConfig
from openhands.llm.llm_registry import LLMRegistry
from openhands.server.services.conversation_stats import ConversationStats
from openhands.server.session.session import Session
from openhands.storage.local import LocalFileStore


class DummySIO:
    manager = {}

    async def emit(self, *args, **kwargs):
        logging.getLogger(__name__).info("SIO EMIT: %s %s", args, kwargs)


async def run_test():
    config = OpenHandsConfig()
    llm_registry = LLMRegistry(config)
    fs = LocalFileStore("logs")
    stats = ConversationStats(fs, "test-sid", "user1")
    sio = DummySIO()
    session = Session("test-sid", config, llm_registry, stats, fs, sio, user_id="user1")
    data = {"action": "message", "args": {"content": "sop: test orchestration"}}
    await session.dispatch(data)
    await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(run_test())

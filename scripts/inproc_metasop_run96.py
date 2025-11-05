"""Run MetaSOP synchronously for a given conversation id.

This script calls run_metasop_for_conversation directly with asyncio.run so
the orchestration runs in-process and its logs are emitted synchronously.
"""

import asyncio
import logging
import sys
from datetime import datetime
from openhands.metasop.router import run_metasop_for_conversation


def configure_logging():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not any((isinstance(h, logging.StreamHandler) for h in root.handlers)):
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.DEBUG)
        fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        sh.setFormatter(fmt)
        root.addHandler(sh)


def run_sync_metasop(conv_id: str, message: str):
    configure_logging()
    logging.getLogger("openhands").debug(f"Starting synchronous MetaSOP run for conversation {conv_id}")
    start = datetime.utcnow().isoformat()
    try:
        asyncio.run(
            run_metasop_for_conversation(conversation_id=conv_id, user_id=None, raw_message=message, repo_root=None)
        )
    except Exception as e:
        logging.getLogger("openhands").exception(f"MetaSOP run failed: {e}")
        raise
    finally:
        end = datetime.utcnow().isoformat()
        logging.getLogger("openhands").debug(f"Finished MetaSOP run (start={start}, end={end})")


if __name__ == "__main__":
    conv_id = "96.41329850281282"
    run_sync_metasop(conv_id, "sop: inproc synchronous run (logged)")

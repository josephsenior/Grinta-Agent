import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
try:
    import logging

    logger = logging.getLogger(__name__)
    logger.info("orchestrator imported")
except Exception:
    import traceback

    traceback.print_exc()
    raise

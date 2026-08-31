from collections import deque

from backend.ledger.action import Action


def try_batch_file_reads(pending_actions: deque[Action]) -> Action | None:
    """Compatibility shim for the removed file-read batching optimization.

    Keeping the queue intact lets the orchestrator produce one typed result
    for every native tool-call ID.
    """
    return None

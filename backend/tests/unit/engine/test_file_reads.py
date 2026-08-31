from __future__ import annotations

from collections import deque
from typing import cast

from backend.engine.file_reads import try_batch_file_reads
from backend.ledger.action import Action
from backend.ledger.action.files import FileReadAction


def test_try_batch_file_reads_leaves_parallel_reads_in_the_queue():
    pending_actions = deque(
        [
            FileReadAction(path='src/repomentor/index.py'),
            FileReadAction(path='src/repomentor/__main__.py'),
        ]
    )

    assert try_batch_file_reads(cast(deque[Action], pending_actions)) is None
    assert [action.path for action in pending_actions] == [
        'src/repomentor/index.py',
        'src/repomentor/__main__.py',
    ]

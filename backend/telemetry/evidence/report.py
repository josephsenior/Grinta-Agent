"""Atomic derived execution-evidence report generation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from backend.core.logging.session_event_logger import SESSION_LOG_FILENAME

from .projector import project

EVIDENCE_REPORT_FILENAME = 'session.evidence.json'


def write_evidence_report(
    session_dir: str | Path, task_state: dict[str, Any] | None = None
) -> dict[str, Any]:
    directory = Path(session_dir)
    summary = project(directory / SESSION_LOG_FILENAME, task_state)
    target = directory / EVIDENCE_REPORT_FILENAME
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=directory,
        prefix='.session.evidence.',
        delete=False,
    ) as handle:
        json.dump(summary, handle, indent=2, sort_keys=True, ensure_ascii=False)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    os.replace(temporary, target)
    return summary

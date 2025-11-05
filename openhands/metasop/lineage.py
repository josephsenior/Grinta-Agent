from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


def append_lineage(ctx, step_id: str, record: dict[str, Any], settings=None) -> None:
    """Append a structured failure/remediation lineage record to the run context.

    - Stores in-memory under ctx.extra['failure_lineage::{step_id}'] as a list.
    - If settings.remediation_lineage_dir is set, appends a JSONL line to
      <dir>/<run_id>_failure_lineage.jsonl (created if missing).

    This helper is best-effort and never raises.
    """
    try:
        key = f"failure_lineage::{step_id}"
        extra = getattr(ctx, "extra", None)
        if extra is None:
            try:
                ctx.extra = {}
                extra = ctx.extra
            except Exception:
                return
        lst = extra.get(key)
        if lst is None:
            extra[key] = []
            lst = extra[key]
        rec = dict(record or {})
        rec.setdefault("timestamp", time.time())
        rec.setdefault("run_id", getattr(ctx, "run_id", None))
        lst.append(rec)
        try:
            dirpath = getattr(settings, "remediation_lineage_dir", None) if settings is not None else None
            if dirpath:
                p = Path(dirpath)
                p.mkdir(parents=True, exist_ok=True)
                fn = p / f"{getattr(ctx, 'run_id', 'run')}_failure_lineage.jsonl"
                with fn.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass
    except Exception:
        return

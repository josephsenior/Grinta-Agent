"""Canonical, privacy-preserving fingerprints for execution evidence."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def fingerprint_text(value: str) -> str:
    return 'sha256:' + hashlib.sha256(value.encode('utf-8')).hexdigest()


def fingerprint_json(value: Any) -> str:
    canonical = json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str
    )
    return fingerprint_text(canonical)


def fingerprint_contract(contract: Any) -> str:
    """Fingerprint the immutable acceptance definition, excluding state/evidence."""
    if not isinstance(contract, dict):
        return fingerprint_json({})
    result: dict[str, Any] = {'objective': contract.get('objective', '')}
    for group in ('requirements', 'constraints', 'success_conditions'):
        result[group] = [
            {key: row.get(key, '') for key in ('id', 'text', 'source')}
            for row in contract.get(group, [])
            if isinstance(row, dict)
        ]
    return fingerprint_json(result)


def fingerprint_plan(plan: Any) -> str:
    return fingerprint_json(plan if isinstance(plan, dict) else {})

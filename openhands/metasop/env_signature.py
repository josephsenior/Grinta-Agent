from __future__ import annotations

"Environment signature utilities.\n\nProduces a deterministic SHA256 hash and payload capturing the execution\ncontext for a MetaSOP run. This supports provenance, reproducibility, and\ncache key derivation.\n"
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
LOCK_FILES = [Path("poetry.lock"), Path("requirements.txt")]


def _hash_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit_short() -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except Exception:
        return None


def collect_environment_payload(config_models: list[str] | None = None) -> dict[str, Any]:
    lock_hashes = {}
    for rel in LOCK_FILES:
        if h := _hash_file(ROOT / rel):
            lock_hashes[str(rel)] = h
    payload: dict[str, Any] = {
        "python_version": platform.python_version(),
        "platform": platform.system().lower(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "git_commit": _git_commit_short(),
        "dependency_locks": lock_hashes,
        "env_vars_exposed": sorted([k for k in os.environ if k.startswith("OPENHANDS_")]),
        "llm_models": config_models or [],
    }
    return payload


def compute_environment_signature(config_models: list[str] | None = None) -> tuple[str, dict[str, Any]]:
    """Return (signature_hash, payload).

    Payload is serialized with sorted keys to ensure deterministic hashing.
    """
    payload = collect_environment_payload(config_models=config_models)
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hashlib.sha256(encoded).hexdigest()
    return (signature, payload)

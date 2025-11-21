"""Environment signature helpers for MetaSOP provenance and cache keys."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.runtime.base import Runtime

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


def collect_environment_payload(
    *,
    config: ForgeConfig | None = None,
    runtime: Runtime | None = None,
    config_models: list[str] | None = None,
) -> dict[str, Any]:
    """Collect key runtime/environment details for inclusion in context hash payload."""
    runtime_env = _extract_runtime_env(config)
    runtime_identity = _extract_runtime_identity(runtime)
    lock_hashes = _collect_lock_hashes()
    return {
        "python_version": platform.python_version(),
        "platform": platform.system().lower(),
        "platform_release": platform.release(),
        "architecture": platform.machine(),
        "git_commit": _git_commit_short(),
        "dependency_locks": lock_hashes,
        "env_vars_exposed": sorted([k for k in os.environ if k.startswith("FORGE_")]),
        "llm_models": list(config_models) if config_models else [],
        "runtime_env": runtime_env,
        "runtime_identity": {
            k: v for k, v in runtime_identity.items() if v is not None
        },
    }


def _extract_runtime_env(config: ForgeConfig | None) -> dict[str, str]:
    if config is None:
        return {}
    runtime_config = getattr(config, "runtime", None)
    env_config = getattr(runtime_config, "env", {})
    if isinstance(env_config, dict):
        return {str(k): str(v) for k, v in env_config.items()}
    return {}


def _extract_runtime_identity(runtime: Runtime | None) -> dict[str, Any]:
    if runtime is None:
        return {}
    return {
        "runtime_id": getattr(runtime, "runtime_id", None),
        "runtime_name": getattr(runtime, "name", None),
    }


def _collect_lock_hashes() -> dict[str, str]:
    lock_hashes: dict[str, str] = {}
    for rel in LOCK_FILES:
        if h := _hash_file(ROOT / rel):
            lock_hashes[str(rel)] = h
    return lock_hashes


def compute_environment_signature(
    config_models: list[str] | None = None,
    *,
    config: ForgeConfig | None = None,
    runtime: Runtime | None = None,
) -> tuple[str, dict[str, Any]]:
    """Return (signature_hash, payload).

    Payload is serialized with sorted keys to ensure deterministic hashing.
    """
    payload = collect_environment_payload(
        config=config,
        runtime=runtime,
        config_models=config_models,
    )
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hashlib.sha256(encoded).hexdigest()
    return (signature, payload)

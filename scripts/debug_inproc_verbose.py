import json
import logging
from pathlib import Path
from typing import Any, Mapping

from forge.core.config.utils import load_FORGE_config
from forge.metasop.orchestrator import MetaSOPOrchestrator


def _dump_model(obj: Any) -> Any:
    """Return a serializable representation of MetaSOP models."""
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        return model_dump()
    if isinstance(obj, Mapping):
        return dict(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return obj


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    config = load_FORGE_config(
        set_logging_levels=False, config_file=str(repo_root / "config.toml")
    )
    logger = logging.getLogger(__name__)
    logger.info(
        "Using config.extended.metasop = %s", getattr(config.extended, "metasop", None)
    )
    orc = MetaSOPOrchestrator("feature_delivery_with_ui", config=config)
    logger.info("settings.enabled= %s", orc.settings.enabled)
    ok, arts = orc.run("sop: hi", repo_root=str(repo_root), max_retries=1)
    logger.info("\n=== RESULT ===")
    logger.info("run ok= %s", ok)
    rep = orc.get_verification_report()

    events = rep.get("events", [])
    traces = [_dump_model(t) for t in orc.traces]
    ctx_extra = getattr(getattr(orc, "_ctx", None), "extra", {})

    out = {
        "ok": ok,
        "events": events,
        "traces": traces,
        "artifacts": {k: getattr(v, "content", None) for k, v in arts.items()},
        "ctx_extra": ctx_extra,
    }

    Path("logs").mkdir(parents=True, exist_ok=True)
    out_path = Path("logs/metasop_verbose_run.json")
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote %s", out_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

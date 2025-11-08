import json
import logging
from pathlib import Path
from forge.core.config.utils import load_FORGE_config
from forge.metasop.orchestrator import MetaSOPOrchestrator

repo_root = Path(__file__).resolve().parents[1]
config = load_FORGE_config(set_logging_levels=False, config_file=str(repo_root / "config.toml"))
logger = logging.getLogger(__name__)
logger.info("Using config.extended.metasop = %s", getattr(config.extended, "metasop", None))
orc = MetaSOPOrchestrator("feature_delivery_with_ui", config=config)
logger.info("settings.enabled= %s", orc.settings.enabled)
ok, arts = orc.run("sop: hi", repo_root=str(repo_root), max_retries=1)
logger.info("\n=== RESULT ===")
logger.info("run ok= %s", ok)
rep = orc.get_verification_report()
logger.info("\nEvents:")
try:
    from forge.core.io import print_json_stdout
except Exception:
    logger.info("%s", json.dumps(rep.get("events", []), indent=2))
else:
    print_json_stdout(rep.get("events", []), pretty=True)
logger.info("\nTraces:")
try:
    from forge.core.io import print_json_stdout as _pj
except Exception:
    logger.info("%s", json.dumps([t.model_dump() for t in orc.traces], indent=2))
else:
    _pj([t.model_dump() for t in orc.traces], pretty=True)
logger.info("\nArtifacts keys: %s", list(arts.keys()))
logger.info("\nCTX EXTRA:")
try:
    from forge.core.io import print_json_stdout as _pj
except Exception:
    logger.info("%s", json.dumps(getattr(orc, "_ctx").extra, indent=2))
else:
    _pj(getattr(orc, "_ctx").extra, pretty=True)
out = {
    "ok": ok,
    "events": rep.get("events", []),
    "traces": [t.model_dump() for t in orc.traces],
    "artifacts": {k: getattr(v, "content", None) for k, v in arts.items()},
    "ctx_extra": getattr(orc, "_ctx").extra,
}
Path("logs").mkdir(parents=True, exist_ok=True)
with open("logs/metasop_verbose_run.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
logger.info("\nWrote logs/metasop_verbose_run.json")

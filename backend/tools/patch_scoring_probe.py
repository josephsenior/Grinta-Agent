import json
import logging
import sys
import traceback
from pathlib import Path

logger = logging.getLogger(__name__)
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root))
try:
    from forge.metasop import patch_scoring

    class S:
        patch_score_weight_complexity = 0.25
        patch_score_weight_lint = 0.25
        patch_score_weight_diffsize = 0.25
        patch_score_weight_length = 0.25

    c1 = patch_scoring.PatchCandidate(
        content="def foo():\n    return 1\n",
        diff="+def foo():\n+    return 1\n",
        meta={},
    )
    c2 = patch_scoring.PatchCandidate(
        content="def foo():\n    return 2\n",
        diff="+def foo():\n+    return 2\n",
        meta={},
    )
    res = patch_scoring.score_candidates([c1, c2], S())
    out = [
        {"composite": r.composite, "features": r.features, "raw": r.raw} for r in res
    ]
    try:
        from forge.core.io import print_json_stdout
    except Exception:
        try:
            logger.info(json.dumps(out, indent=2, ensure_ascii=False, default=str))
        except Exception:
            logger.info(repr(out))
    else:
        try:
            print_json_stdout(out, pretty=True)
        except Exception:
            logger.info(json.dumps(out, indent=2, ensure_ascii=False, default=str))
except Exception:
    traceback.print_exc()
    sys.exit(2)

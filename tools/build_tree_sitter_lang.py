"""Build a combined tree-sitter language shared library for the installed.

third_party grammar(s) so py-tree-sitter can load them via Language(...).

This script uses py-tree-sitter's Language.build_library API which requires
that the grammar directories exist (e.g., third_party/tree-sitter-python).
"""

import logging
import sys
from pathlib import Path

try:
    from tree_sitter import Language
except Exception:
    logger = logging.getLogger(__name__)
    logger.error("py-tree-sitter not available; please pip install tree_sitter")
    sys.exit(2)
base = Path(__file__).resolve().parents[1] / "third_party"
out = base / "my-langs"
if sys.platform.startswith("win"):
    out_file = f"{str(out)}.dll"
elif sys.platform == "darwin":
    out_file = f"{str(out)}.dylib"
else:
    out_file = f"{str(out)}.so"
grammars = []
for name in ("tree-sitter-python",):
    p = base / name
    if p.exists():
        grammars.append(str(p))
    else:
        logger = logging.getLogger(__name__)
        logger.warning("warning: grammar dir not found: %s", p)
if not grammars:
    logger = logging.getLogger(__name__)
    logger.error(
        "No grammars found under third_party; clone tree-sitter-<lang> into third_party first"
    )
    sys.exit(1)
logger = logging.getLogger(__name__)
logger.info("Building language lib -> %s", out_file)
Language.build_library(out_file, grammars)  # type: ignore[attr-defined]
logger.info("Built: %s", out_file)

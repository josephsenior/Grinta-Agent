from __future__ import annotations

import importlib
import sys
import types
from typing import Any

from pydantic import BaseModel

if "tokenizers" not in sys.modules:
    sys.modules["tokenizers"] = types.ModuleType("tokenizers")


def test_download_module_importable():
    module = importlib.import_module("forge.core.download")
    assert module.__doc__ is not None

from __future__ import annotations

import base64
import importlib.util
import os
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[4]
    / "forge"
    / "runtime"
    / "utils"
    / "file_viewer.py"
)
spec = importlib.util.spec_from_file_location(
    "forge.runtime.utils.file_viewer", MODULE_PATH
)
assert spec and spec.loader
file_viewer = importlib.util.module_from_spec(spec)
sys.modules["forge.runtime.utils.file_viewer"] = file_viewer
spec.loader.exec_module(file_viewer)


def test_generate_file_viewer_html_image(tmp_path):
    image_path = tmp_path / "image.png"
    image_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10
    image_path.write_bytes(image_data)

    html = file_viewer.generate_file_viewer_html(str(image_path))
    assert "File Viewer" in html
    encoded = base64.b64encode(image_data).decode("utf-8")
    assert encoded in html


def test_generate_file_viewer_html_pdf(tmp_path):
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n%fake pdf")
    html = file_viewer.generate_file_viewer_html(str(pdf_path))
    assert "pdfjsLib" in html


def test_generate_file_viewer_html_missing_file(tmp_path):
    missing_path = tmp_path / "missing.png"
    with pytest.raises(ValueError) as exc:
        file_viewer.generate_file_viewer_html(str(missing_path))
    assert "File not found locally" in str(exc.value)


def test_generate_file_viewer_html_unsupported_extension(tmp_path):
    text_path = tmp_path / "note.txt"
    text_path.write_text("hello")
    with pytest.raises(ValueError) as exc:
        file_viewer.generate_file_viewer_html(str(text_path))
    assert "Unsupported file extension" in str(exc.value)

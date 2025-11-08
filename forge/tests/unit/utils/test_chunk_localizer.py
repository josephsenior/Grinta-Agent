from __future__ import annotations

import pytest

from forge.utils import chunk_localizer


def test_chunk_visualize() -> None:
    chunk = chunk_localizer.Chunk(text="line1\nline2", line_range=(1, 2))
    rendered = chunk.visualize()
    assert rendered.startswith("1|line1")
    assert rendered.endswith("2|line2\n")


def test_create_chunks_fallback_and_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chunk_localizer, "get_parser", lambda language: None)
    chunks = chunk_localizer.create_chunks("a\nb\nc", size=2, language="python")
    assert chunks[0].line_range == (1, 2)

    def raise_attr(language):
        raise AttributeError("missing")

    monkeypatch.setattr(chunk_localizer, "get_parser", raise_attr)
    chunks = chunk_localizer.create_chunks("x\ny", size=1, language="python")
    assert len(chunks) == 2

    class DummyParser:
        pass

    monkeypatch.setattr(chunk_localizer, "get_parser", lambda language: DummyParser())
    with pytest.raises(NotImplementedError):
        chunk_localizer.create_chunks("a\nb", language="python")


def test_normalized_lcs_and_get_top_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    score = chunk_localizer.normalized_lcs("hello", "hello world")
    assert 0 < score <= 1
    assert chunk_localizer.normalized_lcs("", "anything") == 0.0

    monkeypatch.setattr(chunk_localizer, "create_chunks", lambda text, size: [chunk_localizer.Chunk(text=text, line_range=(1, 1))])
    matches = chunk_localizer.get_top_k_chunk_matches("hello", "hello", k=1)
    assert matches[0].normalized_lcs == chunk_localizer.normalized_lcs("hello", "hello")


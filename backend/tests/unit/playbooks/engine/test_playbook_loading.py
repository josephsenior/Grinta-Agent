"""Tests for backend.playbooks.engine.playbook — Playbook loading logic."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.core.errors import PlaybookValidationError
from backend.playbooks.engine.playbook import (
    BasePlaybook,
    KnowledgePlaybook,
    RepoPlaybook,
    TaskPlaybook,
    _collect_markdown_files,
    _collect_special_files,
    _finalize_loaded_playbook,
    _infer_playbook_type,
)
from backend.playbooks.engine.types import InputMetadata, PlaybookMetadata, PlaybookType


class TestFinalizeLoadedPlaybook:
    def test_valid_metadata(self):
        m = _finalize_loaded_playbook({'name': 'test'}, Path('test.md'))
        assert isinstance(m, PlaybookMetadata)
        assert m.name == 'test'

    def test_version_coerced_to_string(self):
        m = _finalize_loaded_playbook({'version': 1.0}, Path('t.md'))
        assert m.version == '1.0'

    def test_invalid_type_raises(self):
        with pytest.raises(PlaybookValidationError, match='Invalid'):
            _finalize_loaded_playbook({'type': 'bad_type'}, Path('t.md'))

    def test_duplicate_triggers_raise(self):
        with pytest.raises(PlaybookValidationError, match='duplicate trigger'):
            _finalize_loaded_playbook(
                {'triggers': ['/debug', '/DEBUG']},
                Path('t.md'),
            )

    def test_empty_trigger_raises(self):
        with pytest.raises(PlaybookValidationError, match='empty values'):
            _finalize_loaded_playbook({'triggers': ['/debug', '   ']}, Path('t.md'))

    def test_duplicate_input_names_raise(self):
        with pytest.raises(PlaybookValidationError, match='duplicate input name'):
            _finalize_loaded_playbook(
                {
                    'inputs': [
                        {'name': 'PR_URL', 'description': 'd1'},
                        {'name': 'pr_url', 'description': 'd2'},
                    ]
                },
                Path('t.md'),
            )


class TestInferPlaybookType:
    def test_task_when_inputs(self):
        meta = PlaybookMetadata(
            name='build',
            inputs=[InputMetadata(name='x', description='d')],
        )
        result = _infer_playbook_type(meta)
        assert result == PlaybookType.TASK
        assert f'/{meta.name}' in meta.triggers

    def test_knowledge_when_triggers(self):
        meta = PlaybookMetadata(triggers=['review'])
        result = _infer_playbook_type(meta)
        assert result == PlaybookType.KNOWLEDGE

    def test_repo_when_neither(self):
        meta = PlaybookMetadata()
        result = _infer_playbook_type(meta)
        assert result == PlaybookType.REPO_KNOWLEDGE

    def test_task_trigger_not_duplicated(self):
        meta = PlaybookMetadata(
            name='build',
            triggers=['/build'],
            inputs=[InputMetadata(name='x', description='d')],
        )
        _infer_playbook_type(meta)
        assert meta.triggers.count('/build') == 1

    def test_task_trigger_appended_when_different(self):
        meta = PlaybookMetadata(
            name='build',
            triggers=['other'],
            inputs=[InputMetadata(name='x', description='d')],
        )
        _infer_playbook_type(meta)
        assert 'other' in meta.triggers


class TestBasePlaybookMethods:
    def test_from_file_resolve_error(self, tmp_path: Path):
        f = tmp_path / "test.md"
        f.write_text("# Test Playbook\nHello", encoding="utf-8")
        with patch.object(Path, "resolve", side_effect=RuntimeError("Resolution failure")):
            pb = BasePlaybook.load(f, playbook_dir=tmp_path)
            assert pb is not None

    def test_collect_markdown_files(self, tmp_path: Path):
        d = tmp_path / "playbooks"
        d.mkdir()
        valid = d / "valid.md"
        valid.write_text("# Valid\nContent", encoding="utf-8")
        files = _collect_markdown_files(d)
        assert len(files) >= 1

    def test_read_locked_file_windows_fallback(self, tmp_path: Path):
        if not os.name == 'nt':
            pytest.skip("Windows only test")
        f = tmp_path / "locked.md"
        f.write_text("# Locked file content", encoding="utf-8")
        
        with patch("builtins.open", side_effect=PermissionError("File locked")):
            content = BasePlaybook._load_file_content(f, None)
            assert "# Locked file content" in content


class TestSpecializedPlaybookClasses:
    def test_knowledge_playbook_match_trigger(self):
        meta = PlaybookMetadata(name="review", triggers=["/review"])
        pb = KnowledgePlaybook(
            name="review",
            content="Review guide",
            metadata=meta,
            source="review.md",
            type=PlaybookType.KNOWLEDGE,
        )
        assert pb.match_trigger("/review my code") == "/review"
        assert pb.match_trigger("unrelated") is None



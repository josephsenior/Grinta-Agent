"""Compatibility adapter for the standalone :mod:`shadowgit` package."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from shadowgit import ShadowRepo as _ShadowRepo
from shadowgit import ShadowRepoError, build_ignore_matcher

from backend.core.workspace_resolution import workspace_grinta_root


class ShadowRepo(_ShadowRepo):
    """Preserve Grinta's historical storage and ignore conventions."""

    def __init__(
        self,
        workspace_root: str | Path,
        shadow_dir: str | Path | None = None,
        *,
        ignore: Callable[[str, bool], bool] | None = None,
    ) -> None:
        workspace = Path(workspace_root).resolve()
        store = (
            Path(shadow_dir).resolve()
            if shadow_dir is not None
            else workspace_grinta_root(workspace) / 'rollback' / 'shadow_repo'
        )
        base_ignore = build_ignore_matcher(workspace)

        def grinta_ignore(relative_path: str, is_dir: bool) -> bool:
            candidate = relative_path.rstrip('/') + ('/' if is_dir else '')
            if candidate == '.grinta/' or candidate.startswith('.grinta/'):
                return True
            if ignore is not None and ignore(relative_path, is_dir):
                return True
            return base_ignore(relative_path, is_dir)

        super().__init__(
            workspace,
            store,
            ignore=grinta_ignore,
            reserved_roots={'.grinta'},
        )


__all__ = ['ShadowRepo', 'ShadowRepoError']

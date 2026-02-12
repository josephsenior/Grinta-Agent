"""Expose file reader agent skills for runtime plugins."""

from backend.runtime.plugins.agent_skills.file_reader import file_readers
from backend.runtime.plugins.agent_skills.utils.dependency import import_functions

import_functions(
    module=file_readers, function_names=file_readers.__all__, target_globals=globals()
)
__all__ = file_readers.__all__

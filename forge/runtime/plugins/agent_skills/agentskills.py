"""Aggregate agent skill functions and documentation helpers."""

from inspect import signature

from forge.runtime.plugins.agent_skills import file_ops, file_reader
from forge.runtime.plugins.agent_skills.file_editor import file_editor
from forge.runtime.plugins.agent_skills.utils.dependency import import_functions

import_functions(
    module=file_ops, function_names=file_ops.__all__, target_globals=globals()
)
import_functions(
    module=file_reader, function_names=file_reader.__all__, target_globals=globals()
)
__all__ = file_ops.__all__ + file_reader.__all__
try:
    from forge.runtime.plugins.agent_skills import repo_ops

    import_functions(
        module=repo_ops, function_names=repo_ops.__all__, target_globals=globals()
    )
    __all__ += repo_ops.__all__
except ImportError:
    pass
DOCUMENTATION = ""
for func_name in __all__:
    func = globals()[func_name]
    cur_doc = func.__doc__ or "No documentation available"
    cur_doc = "\n".join(filter(None, (x.strip() for x in cur_doc.split("\n"))))
    cur_doc = "\n".join(" " * 4 + x for x in cur_doc.split("\n"))
    fn_signature = f"{func.__name__}{signature(func)!s}"
    DOCUMENTATION += f"{fn_signature}:\n{cur_doc}\n\n"
__all__ += ["file_editor"]

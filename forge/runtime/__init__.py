"""Runtime backends and supporting infrastructure for Forge agents."""

import importlib

from forge.runtime.base import Runtime
from forge.runtime.impl.cli.cli_runtime import CLIRuntime
from forge.runtime.impl.docker.docker_runtime import DockerRuntime
from forge.runtime.impl.kubernetes.kubernetes_runtime import KubernetesRuntime
from forge.runtime.impl.local.local_runtime import LocalRuntime
from forge.runtime.impl.remote.remote_runtime import RemoteRuntime
from forge.utils.import_utils import get_impl

_DEFAULT_RUNTIME_CLASSES: dict[str, type[Runtime]] = {
    "eventstream": DockerRuntime,
    "docker": DockerRuntime,
    "remote": RemoteRuntime,
    "local": LocalRuntime,
    "kubernetes": KubernetesRuntime,
    "cli": CLIRuntime,
}
_THIRD_PARTY_RUNTIME_CLASSES: dict[str, type[Runtime]] = {}
try:
    import third_party.runtime.impl

    third_party_base = "third_party.runtime.impl"
    potential_runtimes = []
    try:
        import pkgutil

        # Only consider valid Python identifiers as potential runtime names.
        # Filesystem directories like 'tree-sitter-python' are not valid module
        # names and will cause import errors like "X is not a package" when
        # used with importlib.import_module. Filter them out.
        for _importer, modname, ispkg in pkgutil.iter_modules(third_party.runtime.impl.__path__):
            if not ispkg:
                continue
            # Accept only valid Python identifiers (letters, digits, underscores,
            # not starting with a digit).
            if modname.isidentifier():
                potential_runtimes.append(modname)
    except Exception:
        potential_runtimes = []
    for runtime_name in potential_runtimes:
        try:
            module_path = f"{third_party_base}.{runtime_name}.{runtime_name}_runtime"
            module = importlib.import_module(module_path)
            possible_class_names = [f"{runtime_name.upper()}Runtime", f"{runtime_name.capitalize()}Runtime"]
            runtime_class = None
            for class_name in possible_class_names:
                try:
                    runtime_class = getattr(module, class_name)
                    break
                except AttributeError:
                    continue
            if runtime_class:
                _THIRD_PARTY_RUNTIME_CLASSES[runtime_name] = runtime_class
        except ImportError:
            pass
        except Exception as e:
            from forge.core.logger import forge_logger as logger

            logger.warning("Failed to import third-party runtime %s: %s", module_path, e)
except ImportError:
    pass
_ALL_RUNTIME_CLASSES = _DEFAULT_RUNTIME_CLASSES | _THIRD_PARTY_RUNTIME_CLASSES


def get_runtime_cls(name: str) -> type[Runtime]:
    """If name is one of the predefined runtime names (e.g. 'docker'), return its class.

    Otherwise attempt to resolve name as subclass of Runtime and return it.
    Raise on invalid selections.
    """
    if name in _ALL_RUNTIME_CLASSES:
        return _ALL_RUNTIME_CLASSES[name]
    try:
        return get_impl(Runtime, name)
    except Exception as e:
        known_keys = _ALL_RUNTIME_CLASSES.keys()
        msg = f"Runtime {name} not supported, known are: {known_keys}"
        raise ValueError(msg) from e


__all__ = [
    "CLIRuntime",
    "DockerRuntime",
    "KubernetesRuntime",
    "LocalRuntime",
    "RemoteRuntime",
    "Runtime",
    "get_runtime_cls",
]
__all__.extend((runtime_class.__name__ for runtime_name, runtime_class in _THIRD_PARTY_RUNTIME_CLASSES.items()))

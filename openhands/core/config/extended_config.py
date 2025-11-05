from typing import Any

from pydantic import RootModel

from openhands.core.pydantic_compat import model_dump_with_options


class ExtendedConfig(RootModel[dict[str, Any]]):
    """Configuration for extended functionalities.

    This is implemented as a root model so that the entire input is stored
    as the root value. This allows arbitrary keys to be stored and later
    accessed via attribute or dictionary-style access.
    """

    def __str__(self) -> str:
        root_dict: dict[str, Any] = model_dump_with_options(self)
        attr_str = [f"{k}={v!r}" for k, v in root_dict.items()]
        return f"ExtendedConfig({', '.join(attr_str)})"

    def __repr__(self) -> str:
        return self.__str__()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExtendedConfig":
        return cls(data)

    def __getitem__(self, key: str) -> Any:
        root_dict: dict[str, Any] = model_dump_with_options(self)
        return root_dict[key]

    def __getattr__(self, key: str) -> Any:
        try:
            root_dict: dict[str, Any] = model_dump_with_options(self)
            return root_dict[key]
        except KeyError as e:
            msg = f"'ExtendedConfig' object has no attribute '{key}'"
            raise AttributeError(msg) from e

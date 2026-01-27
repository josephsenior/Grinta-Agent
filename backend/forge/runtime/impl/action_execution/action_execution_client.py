from __future__ import annotations

from typing import TYPE_CHECKING, Any

from forge.runtime.base import Runtime

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig
    from forge.events import EventStream
    from forge.llm.llm_registry import LLMRegistry


class ActionExecutionClient(Runtime):
    """Lightweight compatibility shim for action-execution based runtimes.

    This minimal implementation exists so that `LocalRuntime` and any other
    runtime implementations can inherit from a common base without pulling in
    removed or heavy dependencies.
    """

    def __init__(
        self,
        config: "ForgeConfig",
        event_stream: "EventStream" | None,
        llm_registry: "LLMRegistry",
        sid: str = "default",
        plugins: list[Any] | None = None,
        env_vars: dict[str, str] | None = None,
        status_callback: Any | None = None,
        attach_to_existing: bool = False,
        headless_mode: bool = False,
        user_id: str | None = None,
        git_provider_tokens: Any | None = None,
        workspace_base: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(
            config=config,
            event_stream=event_stream,
            llm_registry=llm_registry,
            sid=sid,
            plugins=plugins,
            env_vars=env_vars,
            status_callback=status_callback,
            attach_to_existing=attach_to_existing,
            headless_mode=headless_mode,
            user_id=user_id,
            git_provider_tokens=git_provider_tokens,
            workspace_base=workspace_base,
        )

    async def connect(self) -> None:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError()

    def get_mcp_config(self, extra_stdio_servers: list[Any] | None = None) -> Any:
        raise NotImplementedError()

    def run(self, action: Any) -> Any:
        raise NotImplementedError()

    def read(self, action: Any) -> Any:
        raise NotImplementedError()

    def write(self, action: Any) -> Any:
        raise NotImplementedError()

    def edit(self, action: Any) -> Any:
        raise NotImplementedError()

    def copy_to(self, host_src: str, sandbox_dest: str, recursive: bool = False) -> None:
        raise NotImplementedError()

    def copy_from(self, path: str) -> Any:
        raise NotImplementedError()

    def list_files(self, path: str, recursive: bool = False) -> list[str]:
        raise NotImplementedError()

    def browse(self, action: Any) -> Any:
        raise NotImplementedError()

    def browse_interactive(self, action: Any) -> Any:
        raise NotImplementedError()

    async def call_tool_mcp(self, action: Any) -> Any:
        raise NotImplementedError()

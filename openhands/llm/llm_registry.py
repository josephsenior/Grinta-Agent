"""LLM integration and communication layer.

Classes:
    RegistryEvent
    LLMRegistry

Functions:
    request_extraneous_completion
    get_llm_from_agent_config
    get_llm
    get_active_llm
    subscribe
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Callable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

from openhands.core.logger import openhands_logger as logger
from openhands.llm.llm import LLM

if TYPE_CHECKING:
    from openhands.core.config.agent_config import AgentConfig
    from openhands.core.config.llm_config import LLMConfig
    from openhands.core.config.openhands_config import OpenHandsConfig


class RegistryEvent(BaseModel):
    llm: LLM
    service_id: str
    model_config = ConfigDict(arbitrary_types_allowed=True)


class LLMRegistry:

    def __init__(
        self,
        config: OpenHandsConfig,
        agent_cls: str | None = None,
        retry_listener: Callable[[int, int], None] | None = None,
    ) -> None:
        self.registry_id = str(uuid4())
        self.config = copy.deepcopy(config)
        self.retry_listner = retry_listener
        self.agent_to_llm_config = self.config.get_agent_to_llm_config_map()
        self.service_to_llm: dict[str, LLM] = {}
        self.subscriber: Callable[[Any], None] | None = None
        selected_agent_cls = agent_cls or self.config.default_agent
        agent_name = selected_agent_cls if selected_agent_cls is not None else "agent"
        llm_config = self.config.get_llm_config_from_agent(agent_name)
        self.active_agent_llm: LLM = self.get_llm("agent", llm_config)

    def _create_new_llm(self, service_id: str, config: LLMConfig, with_listener: bool = True) -> LLM:
        if with_listener:
            llm = LLM(service_id=service_id, config=config, retry_listener=self.retry_listner)
        else:
            llm = LLM(service_id=service_id, config=config)
        self.service_to_llm[service_id] = llm
        self.notify(RegistryEvent(llm=llm, service_id=service_id))
        return llm

    def request_extraneous_completion(
        self,
        service_id: str,
        llm_config: LLMConfig,
        messages: list[dict[str, str]],
    ) -> str:
        logger.info("extraneous completion: %s", service_id)
        if service_id not in self.service_to_llm:
            self._create_new_llm(config=llm_config, service_id=service_id, with_listener=False)
        llm = self.service_to_llm[service_id]
        response = llm.completion(messages=messages)
        return response.choices[0].message.content.strip()

    def get_llm_from_agent_config(self, service_id: str, agent_config: AgentConfig):
        llm_config = self.config.get_llm_config_from_agent_config(agent_config)
        if service_id in self.service_to_llm:
            return self.service_to_llm[service_id]
        return self._create_new_llm(config=llm_config, service_id=service_id)

    def get_llm(self, service_id: str, config: LLMConfig | None = None):
        logger.info("[LLM registry %s]: Registering service for %s", self.registry_id, service_id)
        if service_id in self.service_to_llm and self.service_to_llm[service_id].config != config:
            msg = f"Requesting same service ID {service_id} with different config, use a new service ID"
            raise ValueError(msg)
        if service_id in self.service_to_llm:
            return self.service_to_llm[service_id]
        if not config:
            msg = "Requesting new LLM without specifying LLM config"
            raise ValueError(msg)
        return self._create_new_llm(config=config, service_id=service_id)

    def get_active_llm(self) -> LLM:
        return self.active_agent_llm

    def _set_active_llm(self, service_id) -> None:
        if service_id not in self.service_to_llm:
            msg = f"Unrecognized service ID: {service_id}"
            raise ValueError(msg)
        self.active_agent_llm = self.service_to_llm[service_id]

    def subscribe(self, callback: Callable[[RegistryEvent], None]) -> None:
        self.subscriber = callback
        self.notify(RegistryEvent(llm=self.active_agent_llm, service_id=self.active_agent_llm.service_id))

    def notify(self, event: RegistryEvent) -> None:
        if self.subscriber:
            try:
                self.subscriber(event)
            except Exception as e:
                logger.warning("Failed to emit event: %s", e)

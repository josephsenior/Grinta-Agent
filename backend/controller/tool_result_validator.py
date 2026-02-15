"""Tool result validation framework.

Provides a pipeline middleware that validates tool/action results against
configurable schemas and constraints before they are passed back to the
agent.  Invalid results are flagged as warnings or transformed into
structured error observations so the LLM can self-correct.

Usage::

    from backend.controller.tool_result_validator import ToolResultValidator

    validator = ToolResultValidator()
    validator.register("CmdRunAction", max_output_len=50_000)
    # ... add to tool pipeline middlewares
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from backend.controller.tool_pipeline import (
    ToolInvocationContext,
    ToolInvocationMiddleware,
)
from backend.core.logger import FORGE_logger as logger

if TYPE_CHECKING:
    from backend.events.observation import Observation


@dataclass
class ValidationRule:
    """A single validation constraint for a tool result."""

    name: str
    check: Callable[[ToolInvocationContext, Observation], str | None]
    """Return an error message string if validation fails, ``None`` if OK."""
    severity: str = "warning"  # "warning" | "error" | "block"


@dataclass
class ValidationResult:
    """Aggregated result of running all applicable rules."""

    passed: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    blocked: bool = False
    block_reason: str | None = None

    def add(self, message: str, severity: str) -> None:
        if severity == "block":
            self.blocked = True
            self.block_reason = message
            self.passed = False
        elif severity == "error":
            self.errors.append(message)
            self.passed = False
        else:
            self.warnings.append(message)


class ToolResultValidator(ToolInvocationMiddleware):
    """Middleware that validates tool observations against registered rules.

    Rules can be registered globally or per-action-type.  The ``observe``
    stage runs after the tool has executed and the observation is available.
    """

    def __init__(self) -> None:
        self._global_rules: list[ValidationRule] = []
        self._action_rules: dict[str, list[ValidationRule]] = {}
        # Register built-in rules
        self._register_builtins()

    # ------------------------------------------------------------------ #
    # Rule registration
    # ------------------------------------------------------------------ #

    def add_rule(
        self,
        name: str,
        check: Callable[[ToolInvocationContext, Observation], str | None],
        *,
        severity: str = "warning",
        action_type: str | None = None,
    ) -> None:
        """Register a validation rule.

        Args:
            name: Human-readable rule name.
            check: Callable ``(ctx, observation) -> error_msg | None``.
            severity: ``"warning"``, ``"error"``, or ``"block"``.
            action_type: If given, rule only applies to this action class name.
        """
        rule = ValidationRule(name=name, check=check, severity=severity)
        if action_type:
            self._action_rules.setdefault(action_type, []).append(rule)
        else:
            self._global_rules.append(rule)

    # ------------------------------------------------------------------ #
    # Middleware hook
    # ------------------------------------------------------------------ #

    async def observe(
        self,
        ctx: ToolInvocationContext,
        observation: Observation | None,
    ) -> None:
        if observation is None:
            return

        action_type = type(ctx.action).__name__
        applicable_rules = list(self._global_rules)
        applicable_rules.extend(self._action_rules.get(action_type, []))

        if not applicable_rules:
            return

        result = ValidationResult()
        for rule in applicable_rules:
            try:
                msg = rule.check(ctx, observation)
                if msg:
                    result.add(msg, rule.severity)
            except Exception:
                logger.debug("Validation rule %s raised", rule.name, exc_info=True)

        # Store result in context metadata for downstream consumers
        ctx.metadata["validation_result"] = result

        if result.warnings:
            logger.info(
                "Tool result validation warnings for %s: %s",
                action_type,
                "; ".join(result.warnings),
            )
        if result.errors:
            logger.warning(
                "Tool result validation errors for %s: %s",
                action_type,
                "; ".join(result.errors),
            )
        if result.blocked:
            ctx.block(reason=f"result_validation:{result.block_reason}")

    # ------------------------------------------------------------------ #
    # Built-in rules
    # ------------------------------------------------------------------ #

    def _register_builtins(self) -> None:
        """Register default validation rules."""

        # 1. Truncated output detection
        def check_truncated(ctx: ToolInvocationContext, obs: Observation) -> str | None:
            content = getattr(obs, "content", "")
            if isinstance(content, str) and len(content) > 100_000:
                return f"Output truncated ({len(content)} chars) — may be incomplete"
            return None

        self.add_rule("output_size", check_truncated, severity="warning")

        # 2. Error observation passthrough (informational)
        def check_error_obs(ctx: ToolInvocationContext, obs: Observation) -> str | None:
            from backend.events.observation import ErrorObservation

            if isinstance(obs, ErrorObservation):
                return f"Tool returned error: {getattr(obs, 'content', '')[:200]}"
            return None

        self.add_rule("error_observation", check_error_obs, severity="warning")

        # 3. Empty result detection
        def check_empty(ctx: ToolInvocationContext, obs: Observation) -> str | None:
            content = getattr(obs, "content", None)
            if content is not None and isinstance(content, str) and not content.strip():
                return "Tool returned empty result"
            return None

        self.add_rule("empty_result", check_empty, severity="warning")

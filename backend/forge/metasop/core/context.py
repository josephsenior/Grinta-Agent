from __future__ import annotations

import contextlib
import logging
import os
import re
import sys
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from forge.core.logger import bind_context, FORGE_logger, set_trace_context

if TYPE_CHECKING:  # pragma: no cover
    from forge.metasop.models import Artifact, OrchestrationContext, RetryPolicy, SopStep, StepResult
    from forge.metasop.orchestrator import MetaSOPOrchestrator


class OrchestrationContextManager:
    """Manages orchestration context, logging, and step lifecycle tracking."""

    def __init__(self, orchestrator: "MetaSOPOrchestrator") -> None:
        self._orch: Any = orchestrator

    # ------------------------------------------------------------------
    # Context initialization
    # ------------------------------------------------------------------
    def initialize_orchestration_context(
        self, user_request: str, repo_root: Optional[str]
    ) -> "OrchestrationContext":
        """Initialize orchestration context and setup logging."""
        from forge.metasop.models import OrchestrationContext

        ctx = OrchestrationContext(
            run_id=str(uuid.uuid4()), user_request=user_request, repo_root=repo_root
        )
        self._orch._ctx = ctx

        if self._orch.llm_registry:
            ctx.llm_registry = self._orch.llm_registry

        if self._orch.llm_registry and self._orch.ace_framework is None:
            self._orch._initialize_ace_framework()

        if self._orch.llm_registry and self._orch.prompt_optimizer is None:
            self._orch._initialize_prompt_optimization()

        self.setup_logging_and_trace_context(ctx)
        self.setup_micro_iteration_settings()

        return ctx

    def setup_logging_and_trace_context(self, ctx: "OrchestrationContext") -> None:
        """Setup logging and trace context for the orchestration."""
        try:
            trace_id = str(uuid.uuid4())
            ctx.extra["trace_id"] = trace_id
            self._setup_logger(trace_id)
            self._setup_global_trace_context(trace_id)
        except Exception:
            self._orch._logger = logging.getLogger("forge")

    def _setup_logger(self, trace_id: str) -> None:
        """Setup logger with trace context."""
        try:
            self._orch._logger = bind_context(FORGE_logger, trace_id=trace_id)
        except Exception:
            self._orch._logger = logging.getLogger("forge")

    def _setup_global_trace_context(self, trace_id: str) -> None:
        """Setup global trace context."""
        try:
            set_trace_context({"trace_id": trace_id})
        except Exception:
            pass

    def setup_micro_iteration_settings(self) -> None:
        """Setup micro-iteration settings."""
        try:
            candidate_count = getattr(
                self._orch.settings, "micro_iteration_candidate_count", None
            )
            if isinstance(candidate_count, int) and candidate_count < 1:
                self._orch.settings.micro_iteration_candidate_count = 1
        except Exception:
            pass

    def setup_retry_policy(self, max_retries: int) -> "RetryPolicy":
        """Setup retry policy from settings."""
        from forge.metasop.models import RetryPolicy

        try:
            if retry_kwargs := self._orch.settings.build_retry_policy_kwargs():
                retry_policy = RetryPolicy(**retry_kwargs)
            else:
                retry_policy = RetryPolicy(max_attempts=max_retries + 1)
        except Exception:
            retry_policy = RetryPolicy(max_attempts=max_retries + 1)

        self._log_retry_policy(retry_policy, max_retries)
        return retry_policy

    def _log_retry_policy(self, retry_policy: "RetryPolicy", max_retries: int) -> None:
        """Log retry policy for debugging."""
        try:
            effective_max_retries = max(0, (retry_policy.max_attempts or 1) - 1)
            try:
                self._orch._logger.info(
                    f"metasop: retry_policy={retry_policy} effective_max_retries={effective_max_retries}"
                )
            except Exception:
                logging.info(
                    f"metasop: retry_policy={retry_policy} effective_max_retries={effective_max_retries}"
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Step lifecycle tracking
    # ------------------------------------------------------------------
    def log_step_entry(self, step: "SopStep") -> None:
        """Log step entry with error handling."""
        try:
            self._orch._logger.info(
                f"metasop: entering step id={getattr(step, 'id', None)} role={getattr(step, 'role', None)}",
            )
        except (AttributeError, RuntimeError):
            with contextlib.suppress(AttributeError, RuntimeError):
                logging.info(
                    f"metasop: entering step id={getattr(step, 'id', None)} role={getattr(step, 'role', None)}",
                )

    def add_active_step(self, step: "SopStep") -> None:
        """Add step to active tracking."""
        self._orch.active_steps[step.id] = step
        self._orch._logger.debug(f"Added step {step.id} to active tracking")

    def remove_active_step(self, step_id: str) -> None:
        """Remove step from active tracking."""
        if step_id in self._orch.active_steps:
            del self._orch.active_steps[step_id]
            self._orch._logger.debug(f"Removed step {step_id} from active tracking")

    # ------------------------------------------------------------------
    # Dependency and condition checking
    # ------------------------------------------------------------------
    def check_dependencies_and_conditions(
        self, step: "SopStep", done: Dict[str, "Artifact"]
    ) -> bool:
        """Check step dependencies and conditions."""
        self._orch._logger.info("Checking dependencies and conditions for step %s", step.id)

        if not self._deps_satisfied(done, step):
            self._orch._logger.info("Step %s skipped: unsatisfied_dependencies", step.id)
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "unsatisfied_dependencies",
                },
            )
            return False

        cond_ok, cond_warn, parse_err = self._evaluate_condition(done, step)
        self._orch._logger.info(
            "Condition evaluation for step %s: ok=%s, warn=%s, parse_err=%s",
            step.id,
            cond_ok,
            cond_warn,
            parse_err,
        )

        if not cond_ok:
            self._orch._emit_event(
                {
                    "step_id": step.id,
                    "role": step.role,
                    "status": "skipped",
                    "reason": "condition_false",
                    "condition": step.condition,
                    "condition_error": cond_warn,
                },
            )
            return False

        return True

    def _deps_satisfied(
        self, done: Dict[str, "Artifact"], step: "SopStep"
    ) -> bool:
        """Check if all dependencies for a step have been completed."""
        result = all(dep in done for dep in step.depends_on)
        self._orch._logger.info(
            "Dependency check for step %s: depends_on=%s, done=%s, result=%s",
            step.id,
            step.depends_on,
            list(done.keys()),
            result,
        )
        return result

    def _evaluate_condition(
        self, done: Dict[str, "Artifact"], step: "SopStep"
    ) -> Tuple[bool, Optional[str], bool]:
        """Evaluate a simple logical expression with AND-chained clauses."""
        expr = step.condition
        if not expr:
            return True, None, False

        clauses = re.split(r"\band\b", expr, flags=re.IGNORECASE)
        return self._evaluate_clauses(done, clauses)

    def _evaluate_clauses(
        self, done: Dict[str, "Artifact"], clauses: List[str]
    ) -> Tuple[bool, Optional[str], bool]:
        """Evaluate all clauses and return overall result."""
        any_parse_error = False
        parse_messages = []
        overall = True

        clause_re = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s*(==|!=|>|<)\s*(.+?)\s*$")
        op_token_re = re.compile(r"^\s*([A-Za-z0-9_\.]+)\s*([=!<>]{1,3})\s*(.+?)\s*$")

        for raw_clause in clauses:
            clause = raw_clause.strip()
            if not clause:
                continue

            clause_result, clause_error, clause_parse_error = (
                self._evaluate_single_clause(done, clause, clause_re, op_token_re)
            )

            if clause_parse_error:
                any_parse_error = True
                parse_messages.append(clause_error)
                overall = False
            elif not clause_result:
                overall = False

        warning = (
            "; ".join(msg for msg in parse_messages if msg) if any_parse_error else None
        )
        return overall, warning, any_parse_error

    def _evaluate_single_clause(
        self,
        done: Dict[str, "Artifact"],
        clause: str,
        clause_re: Any,
        op_token_re: Any,
    ) -> Tuple[bool, Optional[str], bool]:
        """Evaluate a single condition clause."""
        # First detect operator token
        m_op = op_token_re.match(clause)
        if not m_op:
            return False, f"Unrecognized clause syntax: '{clause}'", True

        path, op, value_raw = m_op.groups()
        if op not in {"==", "!=", ">", "<"}:
            return False, f"Unsupported operator '{op}' in clause: '{clause}'", True

        # Use stricter clause_re to parse fields
        m = clause_re.match(clause)
        if not m:
            return False, f"Unrecognized clause syntax: '{clause}'", True

        path, op, value_raw = m.groups()
        value = self._parse_value(value_raw)

        # Get artifact and navigate to field
        current = self._get_field_value(done, path.split("."))
        if current is None:
            return False, "", False

        # Perform comparison
        return self._perform_comparison(current, op, value, clause)

    def _parse_value(self, raw: str) -> Any:
        """Parse a value from string representation."""
        t = raw.strip()
        tl = t.lower()

        if tl in {"true", "false"}:
            return tl == "true"

        # Try numeric parsing
        try:
            if re.match(r"^[+-]?\d+\.\d+$", t):
                return float(t)
            if re.match(r"^[+-]?\d+$", t):
                return int(t)
        except (ValueError, OverflowError):
            pass

        # Handle quoted strings
        if (t.startswith('"') and t.endswith('"')) or (
            t.startswith("'") and t.endswith("'")
        ):
            return t[1:-1]

        return t  # bare word string

    def _get_field_value(
        self, done: Dict[str, "Artifact"], path: List[str]
    ) -> Any:
        """Get field value from artifact by path."""
        parts = path
        art = done.get(parts[0])
        if not art:
            return None

        current: Any = art.content
        for p in parts[1:]:
            if isinstance(current, dict):
                current = current.get(p)
            else:
                return None
        return current

    def _perform_comparison(
        self, current: Any, op: str, value: Any, clause: str
    ) -> Tuple[bool, str, bool]:
        """Perform the actual comparison operation."""
        try:
            if op in {"==", "!="}:
                result = current == value
                if op == "!=":
                    result = not result
                return result, "", False
            if op in {">", "<"}:
                if isinstance(current, (int, float)) and isinstance(
                    value, (int, float)
                ):
                    result = current > value if op == ">" else current < value
                    return result, "", False
                return False, "", False
            return False, "", False
        except (TypeError, ValueError, AttributeError) as exc:
            return False, f"Comparison error in clause '{clause}': {exc}", True

    # ------------------------------------------------------------------
    # ACE reflection
    # ------------------------------------------------------------------
    def reflect_and_update_ace(
        self,
        step: "SopStep",
        result: "StepResult",
        artifact: "Artifact",
        verification: Optional[Dict[str, Any]],
    ) -> None:
        """Reflect on step execution and update ACE playbook."""
        if not self._orch.ace_framework or not getattr(
            self._orch.settings, "ace_enable_online_adaptation", True
        ):
            return

        try:
            from forge.metasop.ace.models import ACETrajectory, ACEExecutionResult

            trajectory = ACETrajectory(
                content=self._stringify_content(result.artifact.content)
                if result.artifact
                else "",
                task_type="metasop",
                used_bullet_ids=[],
                playbook_content="",
                generation_metadata={
                    "step_id": step.id,
                    "role": getattr(step, "role", "unknown"),
                    "task": getattr(step, "task", "unknown"),
                    "expected_outcome": getattr(step, "expected_outcome", None),
                },
            )

            execution_result = ACEExecutionResult(
                success=result.ok,
                output=self._stringify_content(result.artifact.content)
                if result.artifact
                else "",
                error=result.error if not result.ok else None,
                execution_time=0.0,
                tokens_used=0,
                cost=0.0,
                metadata={
                    "step_id": step.id,
                    "verification": verification,
                    "retries": getattr(result, "retries", 0),
                },
            )

            self._orch.ace_framework.process_task(
                query=getattr(step, "task", "unknown"),
                task_type="metasop",
                role=getattr(step, "role", "unknown"),
                expected_outcome=getattr(step, "expected_outcome", None),
            )

            if getattr(self._orch.settings, "ace_auto_save_playbook", True) and getattr(
                self._orch.settings, "ace_playbook_persistence_path", None
            ):
                self._orch.optional_engines.save_ace_playbook()

        except Exception as exc:
            logging.warning("ACE reflection failed: %s", exc)

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    @staticmethod
    def _stringify_content(content: Any) -> str:
        """Convert content to a string representation."""
        import json

        if isinstance(content, str):
            return content
        try:
            return json.dumps(content, ensure_ascii=False)
        except Exception:
            return str(content)

    @staticmethod
    def running_under_pytest() -> bool:
        """Check if running under pytest."""
        if os.environ.get("PYTEST_CURRENT_TEST"):
            return True
        return any("pytest" in str(a) for a in sys.argv)


__all__ = ["OrchestrationContextManager"]


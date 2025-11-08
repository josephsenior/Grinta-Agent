"""MetaSOP adapter that routes engineer steps through the CodeAct implementation flow."""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from forge.core.logger import forge_logger as logger
from forge.llm.llm_registry import LLMRegistry

from ..models import Artifact, OrchestrationContext, SopStep, StepResult
from ..prompts import build_structured_messages
from ..registry import load_schema


def call_async_from_sync(func, **kwargs):
    """Compatibility helper; synchronously invoke an async-style callable."""
    if not callable(func):
        msg = "call_async_from_sync requires a callable"
        raise ValueError(msg)
    return func(**kwargs)


def run_controller(*args, **kwargs):
    """Placeholder run_controller export for backward compatibility."""
    msg = (
        "run_controller is no longer implemented in the Forge MetaSOP adapter. "
        "Tests should monkeypatch this function as needed."
    )
    raise NotImplementedError(msg)

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig

ENGINEER_SUMMARY_PATH = ".metasop/engineer_step.json"


def _infer_system_ops_permission(user_request: str) -> tuple[bool, list[str]]:
    """Detect whether the user explicitly asked for system-level ops.

    If not obvious, default to False for safety.
    """
    user_lower = user_request.lower()
    ops_keywords = ["install", "upgrade", "apt", "dnf", "yum", "pacman", "brew"]

    # If user asked for system operations, allow them
    for kw in ops_keywords:
        if kw in user_lower:
            return True, ["apt", "dnf", "yum", "pacman", "brew"]

    return False, []


def _setup_llm_registry(config: ForgeConfig | None, llm_registry: LLMRegistry | None) -> LLMRegistry:
    """Setup LLM registry from config or use provided one."""
    if llm_registry is None:
        if config is None:
            msg = "Either llm_registry or config must be provided"
            raise ValueError(msg)
        llm_registry = LLMRegistry(config)
    return llm_registry


def _build_extra_context(ctx: OrchestrationContext, step: SopStep) -> dict[str, Any]:
    """Build extra context including retrieval results and dependencies."""
    retrieval_key = f"retrieval::{step.id}"
    extra_context = dict(ctx.extra.items())
    
    # Add retrieval results if available
    if retrieval_key in ctx.extra:
        extra_context["retrieval_results"] = ctx.extra.get(retrieval_key)
    
    # Note: Previous step artifacts are passed via ctx.extra by the orchestrator
    # The orchestrator stores artifacts with keys like "artifact::pm_spec", "artifact::arch_design"
    # Extract these for the Engineer to use
    artifacts = {}
    for key, value in ctx.extra.items():
        if key.startswith("artifact::"):
            step_id = key.replace("artifact::", "")
            artifacts[step_id] = value
    
    if artifacts:
        extra_context["previous_artifacts"] = artifacts
    
    return extra_context


def _build_engineer_messages(
    step: SopStep,
    ctx: OrchestrationContext,
    role_profile: dict[str, Any],
    extra_context: dict[str, Any],
) -> list:
    """Build structured messages for the Engineer LLM with planning context."""
    schema = load_schema(step.outputs.schema_file)
    
    # Build enhanced task description for Engineer (PLANNING, not coding)
    task_description = f"""{step.task}

Based on the previous steps (PM specs and Architecture), create a comprehensive implementation BLUEPRINT by:

1. Designing a complete file and folder structure
2. Creating a detailed multi-phase implementation plan
3. Specifying the purpose and responsibilities of each file
4. Listing all dependencies, libraries, and tools needed
5. Providing setup commands, environment variables, and configuration
6. Planning test structure and coverage approach

⚠️ CRITICAL: You are in PLANNING mode - do NOT write actual code content!
- Provide file descriptions and purposes only
- The CodeAct agent will write the actual code based on your blueprint
- Focus on completeness, organization, and developer guidance

Your blueprint should be detailed enough that the CodeAct agent can immediately start 
implementing without wondering what to build or where files should go."""

    return build_structured_messages(
        role_name=role_profile.get("name", step.role),
        role_goal=role_profile.get("goal", "Create comprehensive implementation blueprint and file structure"),
        constraints=role_profile.get("constraints", []),
        sop_task=task_description,
        user_request=ctx.user_request,
        schema_name=step.outputs.schema_file,
        schema=schema,
        extra_context=extra_context,
    )


def _generate_implementation(llm, messages: list) -> tuple[Any, str]:
    """Generate implementation code using the LLM."""
    # Increased max_tokens to 64K (Claude Haiku's maximum) to prevent JSON truncation
    response = llm.completion(messages=messages, max_tokens=64000)
    content = response.choices[0].message.content.strip()
    return response, content


def _extract_usage_metrics(response) -> dict[str, Any]:
    """Extract usage metrics from response."""
    usage = getattr(response, "usage", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
        "model_name": getattr(response, "model", None),
    }


def _parse_implementation_content(content: str) -> dict[str, Any]:
    """Parse the implementation content and extract structured data."""
    parsed = {}
    
    # Try to extract JSON if present
    try:
        # Look for JSON blocks in markdown
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            json_str = content[start:end].strip()
            parsed = json.loads(json_str)
        elif content.strip().startswith("{"):
            # Try to parse as direct JSON
            parsed = json.loads(content)
    except json.JSONDecodeError:
        # If no JSON found, structure the raw content
        parsed = {
            "implementation": content,
            "artifact_path": ENGINEER_SUMMARY_PATH,
            "source": "agent"
        }
    
    return parsed


def _build_artifact_content(
    trace_meta: dict[str, Any],
    content: str,
    parsed_content: dict[str, Any],
) -> dict[str, Any]:
    """Build artifact content with implementation details."""
    art_content: dict = {
        "__trace_meta__": trace_meta,
        "__raw__": content,
        "source": "agent"
    }
    
    # Merge parsed content
    art_content.update(parsed_content)
    
    # Ensure artifact_path is set
    art_content.setdefault("artifact_path", ENGINEER_SUMMARY_PATH)
    
    return art_content


def _set_artifact_source_metadata(art: Artifact) -> None:
    """Set source metadata for artifact."""
    try:
        if isinstance(art.content, dict):
            art.content.setdefault("source", "agent")
    except Exception:
        pass


def run_engineer_with_llm(
    step: SopStep,
    ctx: OrchestrationContext,
    role_profile: dict[str, Any],
    config: ForgeConfig | None = None,
    llm_registry: LLMRegistry | None = None,
) -> StepResult:
    """Adapter: Generate implementation using LLM directly (similar to PM/Architect).

    This approach:
    1. Uses the existing LLM stack (respects UI settings)
    2. Builds structured prompts with context from previous steps
    3. Generates implementation code/plans via LLM completion
    4. Returns structured artifact

    This is much simpler and more reliable than spawning a nested controller.
    """
    repo_root = getattr(ctx, "repo_root", None)
    summary_file: Path | None = Path(repo_root) / ENGINEER_SUMMARY_PATH if repo_root else None
    if summary_file and llm_registry is None and config is None and summary_file.exists():
        try:
            parsed_content = json.loads(summary_file.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Failed to load engineer summary from {summary_file}: {exc}", exc_info=True)
        else:
            art_content = {
                "__trace_meta__": {},
                "__raw__": parsed_content,
                "artifact_path": ENGINEER_SUMMARY_PATH,
                "source": "agent",
                "candidates": parsed_content.get("candidates"),
            }
            if isinstance(art_content.get("candidates"), list):
                for candidate in art_content["candidates"]:
                    if isinstance(candidate, dict):
                        candidate.setdefault("meta", {})
                        candidate["meta"].setdefault("source", "agent")
            art = Artifact(step_id=step.id, role=step.role, content=art_content)
            _set_artifact_source_metadata(art)
            return StepResult(ok=True, artifact=art)

    try:
        # Setup LLM registry
        llm_registry = _setup_llm_registry(config, llm_registry)
        
        # Get LLM from context if available, otherwise use active LLM
        if hasattr(ctx, 'llm_registry') and ctx.llm_registry:
            llm = ctx.llm_registry.get_active_llm()
        else:
            llm = llm_registry.get_active_llm()

        logger.info(f"Engineer step starting with LLM: {llm.config.model}")

        # Build context and messages
        extra_context = _build_extra_context(ctx, step)
        messages = _build_engineer_messages(step, ctx, role_profile, extra_context)

        logger.info(f"Engineer step: Built {len(messages)} messages for LLM")

        # Generate implementation
        response, content = _generate_implementation(llm, messages)

        logger.info(f"Engineer step: Received {len(content)} chars from LLM")

        # Parse the implementation content
        parsed_content = _parse_implementation_content(content)

        # Extract metrics and build artifact
        trace_meta = _extract_usage_metrics(response)
        art_content = _build_artifact_content(trace_meta, content, parsed_content)
        art = Artifact(step_id=step.id, role=step.role, content=art_content)

        # Set source metadata
        _set_artifact_source_metadata(art)

        logger.info(f"Engineer step completed successfully for step_id={step.id}")

        return StepResult(ok=True, artifact=art)
        
    except Exception as e:
        logger.error(f"Engineer step failed: {e}", exc_info=True)
        return StepResult(ok=False, error=str(e))


# Alias for backward compatibility
run_engineer_with_codeact = run_engineer_with_llm

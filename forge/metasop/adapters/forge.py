"""Forge MetaSOP adapter.

This module implements the Forge-branded adapter for running structured MetaSOP
steps through the platform's LLM stack. It supersedes the previous OpenHands
adapter implementation while keeping a compatible surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from forge.llm.llm_registry import LLMRegistry

from ..models import Artifact, OrchestrationContext, SopStep, StepResult
from ..prompts import build_structured_messages
from ..registry import load_schema

if TYPE_CHECKING:
    from forge.core.config import ForgeConfig


def _setup_llm_registry(config: ForgeConfig | None, llm_registry: LLMRegistry | None) -> LLMRegistry:
    """Setup LLM registry from config or use provided one."""
    if llm_registry is None:
        if config is None:
            msg = "Either llm_registry or config must be provided"
            raise ValueError(msg)
        llm_registry = LLMRegistry(config)
    return llm_registry


def _build_extra_context(ctx: OrchestrationContext, step: SopStep) -> dict[str, Any]:
    """Build extra context including retrieval results."""
    retrieval_key = f"retrieval::{step.id}"
    extra_context = dict(ctx.extra.items())
    if retrieval_key in ctx.extra:
        extra_context["retrieval_results"] = ctx.extra.get(retrieval_key)
    return extra_context


def _build_messages(
    step: SopStep,
    ctx: OrchestrationContext,
    role_profile: dict[str, Any],
    extra_context: dict[str, Any],
) -> list:
    """Build structured messages for the LLM."""
    schema = load_schema(step.outputs.schema_file)
    return build_structured_messages(
        role_name=role_profile.get("name", step.role),
        role_goal=role_profile.get("goal", ""),
        constraints=role_profile.get("constraints", []),
        sop_task=step.task,
        user_request=ctx.user_request,
        schema_name=step.outputs.schema_file,
        schema=schema,
        extra_context=extra_context,
    )


def _get_candidate_hint(ctx: OrchestrationContext, step: SopStep) -> int | None:
    """Get number of candidates hint from context."""
    hint_key = f"n_candidates::{step.id}"
    if ctx is None or not hasattr(ctx, "extra"):
        return None
    extra = getattr(ctx, "extra")
    if not isinstance(extra, dict):
        return None
    raw_hint = extra.get(hint_key)
    if isinstance(raw_hint, bool):
        return int(raw_hint)
    if isinstance(raw_hint, (int, float)):
        return int(raw_hint)
    if isinstance(raw_hint, str):
        try:
            return int(raw_hint)
        except ValueError:
            return None
    return None


def _generate_multiple_candidates(llm, messages: list, n_hint: int) -> tuple[Any, list[dict]]:
    """Generate multiple candidates for the step."""
    candidates_list = []
    last_resp = None

    for _ in range(n_hint):
        try:
            # Increased max_tokens to 64K (Claude Haiku's maximum) to prevent JSON truncation
            resp = llm.completion(messages=messages, max_tokens=64000)
        except TypeError:
            resp = llm.completion(messages=messages)
        except Exception:
            break
        last_resp = resp
        try:
            c = resp.choices[0].message.content.strip()
        except Exception:
            break
        candidates_list.append({"content": c, "meta": {"source": "agent"}})

    return last_resp, candidates_list


def _generate_single_response(llm, messages: list) -> tuple[Any, str]:
    """Generate single response for the step."""
    # Increased max_tokens to 64K (Claude Haiku's maximum) to prevent JSON truncation
    try:
        response = llm.completion(messages=messages, max_tokens=64000)
    except TypeError:
        response = llm.completion(messages=messages)
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


def _build_artifact_content(
    trace_meta: dict[str, Any],
    candidates_list: list[dict] | None,
    content: str | None,
) -> dict[str, Any]:
    """Build artifact content with candidates or raw content."""
    art_content: dict = {"__trace_meta__": trace_meta}

    if candidates_list is not None:
        art_content["candidates"] = candidates_list
        art_content["__raw__"] = candidates_list[0]["content"] if candidates_list else ""
    else:
        art_content["__raw__"] = content

    return art_content


def _set_artifact_source_metadata(art: Artifact) -> None:
    """Set source metadata for artifact and its candidates."""
    try:
        if isinstance(art.content, dict):
            art.content.setdefault("source", "agent")
            if isinstance(art.content.get("candidates"), list):
                for c in art.content["candidates"]:
                    if isinstance(c, dict):
                        meta = c.setdefault("meta", {})
                        meta.setdefault("source", "agent")
    except Exception:
        pass


def run_step_with_Forge(
    step: SopStep,
    ctx: OrchestrationContext,
    role_profile: dict[str, Any],
    config: ForgeConfig | None = None,
    llm_registry: LLMRegistry | None = None,
) -> StepResult:
    """Adapter: build a structured prompt and call LLM via LLMRegistry for JSON-only output."""
    try:
        # Setup LLM registry
        llm_registry = _setup_llm_registry(config, llm_registry)
        # Use the same LLM as regular chat (respects UI settings)
        llm = llm_registry.get_active_llm()

        # Build context and messages
        extra_context = _build_extra_context(ctx, step)
        messages = _build_messages(step, ctx, role_profile, extra_context)

        # Get candidate hint and generate response(s)
        n_hint = _get_candidate_hint(ctx, step)

        if n_hint and isinstance(n_hint, int) and (n_hint > 1):
            response, candidates_list = _generate_multiple_candidates(llm, messages, n_hint)
            content = None
        else:
            response, content = _generate_single_response(llm, messages)
            candidates_list = None

        # Extract metrics and build artifact
        trace_meta = _extract_usage_metrics(response)
        art_content = _build_artifact_content(trace_meta, candidates_list, content)
        art = Artifact(step_id=step.id, role=step.role, content=art_content)

        # Set source metadata
        _set_artifact_source_metadata(art)

        return StepResult(ok=True, artifact=art)
    except Exception as e:
        return StepResult(ok=False, error=str(e))


__all__ = ["LLMRegistry", "load_schema", "run_step_with_Forge"]
 
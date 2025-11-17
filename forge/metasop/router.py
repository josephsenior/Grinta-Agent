"""MetaSOP Router utilities.

Provides the production router helpers that wire socket emission,
validation, and orchestration routing via the canonical orchestrator helpers.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional

from forge.core.logger import forge_logger as logger
from forge.server.shared import config, conversation_manager, sio
from forge.metasop.orchestrator import run_metasop_orchestration as run_metasop_core


def create_emit_callback() -> Callable:
    """Create an emit callback (deprecated – prefer conversation-specific helpers)."""

    return create_emit_callback_with_conversation("unknown")


def create_emit_callback_with_conversation(conversation_id: str) -> Callable:
    """Create an emit callback for a specific conversation."""

    async def emit_callback(event_data: Dict[str, Any]) -> None:
        try:
            event_data["conversation_id"] = conversation_id
            status_data = {
                "status_update": True,
                "type": "metasop_event",
                "message": format_event_message(event_data),
                "id": f"metasop_{int(asyncio.get_event_loop().time() * 1000)}",
                **event_data,
            }
            await sio.emit("oh_event", status_data, room=conversation_id)
            logger.debug(
                "Emitted MetaSOP event %s to room %s",
                event_data.get("event_type", "unknown"),
                conversation_id,
            )
        except Exception as exc:  # pragma: no cover - defensive logging only
            logger.error("Failed to emit MetaSOP event: %s", exc)

    return emit_callback


def format_event_message(event_data: Dict[str, Any]) -> str:
    """Format event data as a message for the frontend."""

    event_type = event_data.get("event_type", "unknown")
    if event_type == "metasop_orchestration_start":
        return "MetaSOP orchestration started"
    if event_type == "metasop_orchestration_complete":
        return "MetaSOP orchestration completed successfully"
    if event_type == "metasop_orchestration_failed":
        error = event_data.get("error", "Unknown error")
        return f"MetaSOP orchestration failed: {error}"
    if event_type == "metasop_step_start":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        return f"step:{step_id} role:{role} status:running retries:0"
    if event_type == "metasop_step_complete":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        retries = event_data.get("retries", 0)
        return f"step:{step_id} role:{role} status:executed retries:{retries}"
    if event_type == "metasop_step_failed":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        retries = event_data.get("retries", 0)
        return f"step:{step_id} role:{role} status:failed retries:{retries}"
    if event_type == "metasop_artifact_produced":
        step_id = event_data.get("step_id", "unknown")
        artifact = event_data.get("artifact", {})
        try:
            artifact_json = json.dumps(artifact, indent=2)
            return (
                f"Artifact produced for step: {step_id}\n```json\n{artifact_json}\n```"
            )
        except Exception:  # pragma: no cover - best-effort pretty print
            return f"Artifact produced for step: {step_id}"
    return f"MetaSOP event: {event_type}"


async def run_clean_metasop_orchestration(
    conversation_id: str,
    user_id: Optional[str],
    raw_message: str,
    repo_root: Optional[str] = None,
    template_name: str = "feature_delivery",
) -> None:
    """Run MetaSOP orchestration via the router helpers."""

    logger.info(
        "Starting MetaSOP orchestration: conversation_id=%s, user_id=%s, template=%s",
        conversation_id,
        user_id,
        template_name,
    )
    try:
        emit_cb = create_emit_callback_with_conversation(conversation_id)
        result = await run_metasop_core(
            raw_message,
            template_name=template_name,
            repo_root=repo_root,
            max_retries=2,
            emit_callback=emit_cb,
        )
        if result.get("success"):
            logger.info(
                "MetaSOP orchestration completed successfully: artifacts=%d, template=%s",
                result.get("steps_executed", 0),
                result.get("template"),
            )
        else:
            logger.error(
                "MetaSOP orchestration failed: %s",
                result.get("error", "Unknown error"),
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("MetaSOP orchestration failed: %s", exc)
        try:
            error_data = {
                "status_update": True,
                "type": "error",
                "message": f"MetaSOP error: {exc}",
                "id": f"metasop_{int(asyncio.get_event_loop().time() * 1000)}",
            }
            await sio.emit("oh_event", error_data, room=conversation_id)
        except Exception:  # pragma: no cover
            pass


async def validate_metasop_message(raw_message: str) -> Optional[str]:
    """Validate and clean a MetaSOP message."""

    if not raw_message or not raw_message.strip():
        return None

    cleaned = raw_message.strip()
    if cleaned.lower().startswith("sop:"):
        cleaned = cleaned[4:].strip()
    return cleaned or None


def is_metasop_enabled() -> bool:
    """Check if MetaSOP is enabled."""

    try:
        metasop_cfg = getattr(config.extended, "metasop", {})
        return metasop_cfg.get("enabled", True)
    except Exception:  # pragma: no cover - config guardrail
        return True


def get_metasop_template() -> str:
    """Get the configured MetaSOP template."""

    try:
        metasop_cfg = getattr(config.extended, "metasop", {})
        return metasop_cfg.get("default_sop", "feature_delivery_full")
    except Exception:  # pragma: no cover - config guardrail
        return "feature_delivery_full"


async def run_metasop_for_conversation(
    conversation_id: str,
    user_id: Optional[str],
    raw_message: str,
    repo_root: Optional[str] = None,
    llm_registry=None,
) -> None:
    """Legacy function kept for backward compatibility with existing callers."""

    del llm_registry
    cleaned_message = await validate_metasop_message(raw_message)
    if not cleaned_message:
        logger.warning("Invalid MetaSOP message, skipping orchestration")
        return

    template_name = get_metasop_template()
    await run_clean_metasop_orchestration(
        conversation_id=conversation_id,
        user_id=user_id,
        raw_message=cleaned_message,
        repo_root=repo_root,
        template_name=template_name,
    )


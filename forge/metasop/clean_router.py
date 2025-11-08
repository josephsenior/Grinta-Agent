"""Clean MetaSOP Router.

A production-ready router that uses the clean orchestrator and event emitter
for robust MetaSOP orchestration with proper error handling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable

from forge.core.logger import forge_logger as logger
from forge.server.shared import config, conversation_manager, sio
from forge.metasop.clean_orchestrator import create_clean_orchestrator
from forge.metasop.event_emitter import MetaSOPEventEmitter

# Global orchestrator instance
_clean_orchestrator: Optional[Any] = None

def get_clean_orchestrator() -> Any:
    """Get the global clean orchestrator instance.
    
    Returns:
        CleanMetaSOPOrchestrator: The clean orchestrator instance

    """
    global _clean_orchestrator
    if _clean_orchestrator is None:
        _clean_orchestrator = create_clean_orchestrator(
            emit_callback=create_emit_callback(),
            template_name="feature_delivery_full"
        )
    return _clean_orchestrator

def create_emit_callback() -> Callable:
    """Create an emit callback for the orchestrator (deprecated - use create_emit_callback_with_conversation).
    
    Returns:
        Callable: Function to emit events to the frontend

    """
    return create_emit_callback_with_conversation("unknown")

def create_emit_callback_with_conversation(conversation_id: str) -> Callable:
    """Create an emit callback for a specific conversation.
    
    Args:
        conversation_id: The conversation ID to emit events to
    
    Returns:
        Callable: Function to emit events to the frontend

    """
    async def emit_callback(event_data: Dict[str, Any]) -> None:
        """Emit event data to the frontend.
        
        Args:
            event_data: Event data to emit

        """
        try:
            # Add conversation_id to event data
            event_data["conversation_id"] = conversation_id
            
            # Format event as a status update message
            status_data = {
                "status_update": True,
                "type": "metasop_event",  # Always use "metasop_event" for type
                "message": format_event_message(event_data),
                "id": f"metasop_{int(asyncio.get_event_loop().time() * 1000)}",
                **event_data
            }
            
            # Emit via socketio to the specific conversation room
            await sio.emit("oh_event", status_data, room=conversation_id)
            
            logger.debug(f"Emitted clean MetaSOP event: {event_data.get('event_type', 'unknown')} to room {conversation_id}")
            
        except Exception as e:
            logger.error(f"Failed to emit clean MetaSOP event: {e}")
    
    return emit_callback

def format_event_message(event_data: Dict[str, Any]) -> str:
    """Format event data as a message for the frontend.
    
    Args:
        event_data: Event data to format
        
    Returns:
        str: Formatted message

    """
    event_type = event_data.get("event_type", "unknown")
    
    if event_type == "metasop_orchestration_start":
        return "MetaSOP orchestration started"
    elif event_type == "metasop_orchestration_complete":
        return "MetaSOP orchestration completed successfully"
    elif event_type == "metasop_orchestration_failed":
        error = event_data.get("error", "Unknown error")
        return f"MetaSOP orchestration failed: {error}"
    elif event_type == "metasop_step_start":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        return f"step:{step_id} role:{role} status:running retries:0"
    elif event_type == "metasop_step_complete":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        retries = event_data.get("retries", 0)
        return f"step:{step_id} role:{role} status:executed retries:{retries}"
    elif event_type == "metasop_step_failed":
        step_id = event_data.get("step_id", "unknown")
        role = event_data.get("role", "Unknown")
        retries = event_data.get("retries", 0)
        return f"step:{step_id} role:{role} status:failed retries:{retries}"
    elif event_type == "metasop_artifact_produced":
        step_id = event_data.get("step_id", "unknown")
        artifact = event_data.get("artifact", {})
        
        # Format artifact as JSON
        try:
            artifact_json = json.dumps(artifact, indent=2)
            return f"Artifact produced for step: {step_id}\n```json\n{artifact_json}\n```"
        except Exception:
            return f"Artifact produced for step: {step_id}"
    else:
        return f"MetaSOP event: {event_type}"

async def run_clean_metasop_orchestration(
    conversation_id: str,
    user_id: Optional[str],
    raw_message: str,
    repo_root: Optional[str] = None,
    template_name: str = "feature_delivery"
) -> None:
    """Run clean MetaSOP orchestration.
    
    Args:
        conversation_id: The conversation ID
        user_id: The user ID (optional)
        raw_message: The user's message
        repo_root: Repository root path (optional)
        template_name: Template to use (optional)

    """
    logger.info(
        "Starting clean MetaSOP orchestration: conversation_id=%s, user_id=%s, template=%s",
        conversation_id,
        user_id,
        template_name
    )
    
    try:
        # Create orchestrator with conversation-specific emit callback
        emit_cb = create_emit_callback_with_conversation(conversation_id)
        orchestrator = create_clean_orchestrator(
            emit_callback=emit_cb,
            template_name=template_name
        )
        
        # Run orchestration
        result = await orchestrator.run_orchestration(
            user_request=raw_message,
            repo_root=repo_root,
            max_retries=2
        )
        
        # Log results
        if result["success"]:
            logger.info(
                "Clean MetaSOP orchestration completed successfully: "
                "artifacts=%d, template=%s",
                result["steps_executed"],
                result["template"]
            )
        else:
            logger.error(
                "Clean MetaSOP orchestration failed: %s",
                result.get("error", "Unknown error")
            )
            
    except Exception as e:
        logger.exception("Clean MetaSOP orchestration failed: %s", e)
        
        # Emit error event via socketio
        try:
            error_data = {
                "status_update": True,
                "type": "error",
                "message": f"MetaSOP error: {str(e)}",
                "id": f"metasop_{int(asyncio.get_event_loop().time() * 1000)}"
            }
            await sio.emit("oh_event", error_data, room=conversation_id)
        except Exception:
            pass

async def validate_metasop_message(raw_message: str) -> Optional[str]:
    """Validate and clean a MetaSOP message.
    
    Args:
        raw_message: The raw message to validate
        
    Returns:
        Optional[str]: Cleaned message if valid, None if invalid

    """
    if not raw_message or not raw_message.strip():
        return None
        
    # Remove SOP: prefix if present
    cleaned = raw_message.strip()
    if cleaned.lower().startswith("sop:"):
        cleaned = cleaned[4:].strip()
        
    if not cleaned:
        return None
        
    return cleaned

def is_metasop_enabled() -> bool:
    """Check if MetaSOP is enabled.
    
    Returns:
        bool: True if MetaSOP is enabled

    """
    try:
        metasop_cfg = getattr(config.extended, "metasop", {})
        return metasop_cfg.get("enabled", True)
    except Exception:
        return True

def get_metasop_template() -> str:
    """Get the configured MetaSOP template.
    
    Returns:
        str: Template name

    """
    try:
        metasop_cfg = getattr(config.extended, "metasop", {})
        return metasop_cfg.get("default_sop", "feature_delivery_full")
    except Exception:
        return "feature_delivery_full"

# Legacy compatibility functions
async def run_metasop_for_conversation(
    conversation_id: str,
    user_id: Optional[str],
    raw_message: str,
    repo_root: Optional[str] = None,
    llm_registry=None
) -> None:
    """Legacy function for backward compatibility.
    
    Args:
        conversation_id: The conversation ID
        user_id: The user ID (optional)
        raw_message: The user's message
        repo_root: Repository root path (optional)
        llm_registry: LLM registry (unused, kept for compatibility)

    """
    # Validate message
    cleaned_message = await validate_metasop_message(raw_message)
    if not cleaned_message:
        logger.warning("Invalid MetaSOP message, skipping orchestration")
        return
        
    # Get template from config
    template_name = get_metasop_template()
    
    # Run clean orchestration
    await run_clean_metasop_orchestration(
        conversation_id=conversation_id,
        user_id=user_id,
        raw_message=cleaned_message,
        repo_root=repo_root,
        template_name=template_name
    )

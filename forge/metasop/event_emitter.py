"""MetaSOP Event Emitter.

Provides a clean, consistent mechanism for emitting MetaSOP events to the frontend.
This addresses the event emission inconsistency issues identified in the analysis.

Enhanced with schema validation to ensure artifact integrity and type safety.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Types of MetaSOP events."""
    STEP_START = "metasop_step_start"
    STEP_COMPLETE = "metasop_step_complete"
    STEP_FAILED = "metasop_step_failed"
    ARTIFACT_PRODUCED = "metasop_artifact_produced"
    ORCHESTRATION_START = "metasop_orchestration_start"
    ORCHESTRATION_COMPLETE = "metasop_orchestration_complete"
    ORCHESTRATION_FAILED = "metasop_orchestration_failed"

@dataclass
class MetaSOPEvent:
    """Structured MetaSOP event."""
    event_type: EventType
    step_id: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    artifact: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None
    retries: int = 0
    metadata: Optional[Dict[str, Any]] = None

class MetaSOPEventEmitter:
    """Handles emission of MetaSOP events to the frontend with schema validation."""
    
    def __init__(self, emit_callback, enable_validation: bool = True, 
                 strict_validation: bool = False):
        """Initialize event emitter.
        
        Args:
            emit_callback: Function to call when emitting events (e.g., WebSocket emit)
            enable_validation: Whether to validate artifacts against schemas (default: True)
            strict_validation: If True, log validation errors prominently (default: False)

        """
        self.emit_callback = emit_callback
        self.enable_validation = enable_validation
        self.strict_validation = strict_validation
        
        # Lazy import validator to avoid circular dependencies
        self._validator = None
        
    def emit_step_start(self, step_id: str, role: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit step start event.
        
        Args:
            step_id: ID of the step starting
            role: Role executing the step
            metadata: Additional metadata

        """
        event = MetaSOPEvent(
            event_type=EventType.STEP_START,
            step_id=step_id,
            role=role,
            status="running",
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def _prepare_completion_metadata(
        self,
        artifact: Optional[Dict[str, Any]],
        role: str,
        step_id: str,
        metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Prepare metadata for completion event.
        
        Args:
            artifact: Artifact to validate
            role: Role that completed the step
            step_id: Step ID
            metadata: Existing metadata
            
        Returns:
            Updated metadata dict

        """
        if metadata is None:
            metadata = {}
        
        if self.enable_validation and artifact:
            validation_result = self._validate_artifact(artifact, role, step_id)
            metadata['validation'] = validation_result
        
        return metadata

    def emit_step_complete(self, step_id: str, role: str, artifact: Optional[Dict[str, Any]] = None, 
                          retries: int = 0, metadata: Optional[Dict[str, Any]] = None):
        """Emit step completion event with artifact validation.
        
        Args:
            step_id: ID of the completed step
            role: Role that completed the step
            artifact: Artifact produced by the step
            retries: Number of retries used
            metadata: Additional metadata

        """
        metadata = self._prepare_completion_metadata(artifact, role, step_id, metadata)
        
        event = MetaSOPEvent(
            event_type=EventType.STEP_COMPLETE,
            step_id=step_id,
            role=role,
            status="success",
            artifact=artifact,
            retries=retries,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_step_failed(self, step_id: str, role: str, error: str, retries: int = 0, 
                        metadata: Optional[Dict[str, Any]] = None):
        """Emit step failure event.
        
        Args:
            step_id: ID of the failed step
            role: Role that failed
            error: Error message
            retries: Number of retries used
            metadata: Additional metadata

        """
        event = MetaSOPEvent(
            event_type=EventType.STEP_FAILED,
            step_id=step_id,
            role=role,
            status="failed",
            error=error,
            retries=retries,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_artifact_produced(self, step_id: str, role: str, artifact: Dict[str, Any], 
                              metadata: Optional[Dict[str, Any]] = None):
        """Emit artifact production event with validation.
        
        Args:
            step_id: ID of the step that produced the artifact
            role: Role that produced the artifact
            artifact: The artifact data
            metadata: Additional metadata

        """
        if metadata is None:
            metadata = {}
        
        # Validate artifact if enabled
        if self.enable_validation:
            validation_result = self._validate_artifact(artifact, role, step_id)
            metadata['validation'] = validation_result
        
        event = MetaSOPEvent(
            event_type=EventType.ARTIFACT_PRODUCED,
            step_id=step_id,
            role=role,
            artifact=artifact,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_orchestration_start(self, metadata: Optional[Dict[str, Any]] = None):
        """Emit orchestration start event.
        
        Args:
            metadata: Additional metadata

        """
        event = MetaSOPEvent(
            event_type=EventType.ORCHESTRATION_START,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_orchestration_complete(self, metadata: Optional[Dict[str, Any]] = None):
        """Emit orchestration completion event.
        
        Args:
            metadata: Additional metadata

        """
        event = MetaSOPEvent(
            event_type=EventType.ORCHESTRATION_COMPLETE,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_orchestration_failed(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Emit orchestration failure event.
        
        Args:
            error: Error message
            metadata: Additional metadata

        """
        event = MetaSOPEvent(
            event_type=EventType.ORCHESTRATION_FAILED,
            error=error,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def _emit_event(self, event: MetaSOPEvent):
        """Emit an event to the frontend.
        
        Args:
            event: The event to emit

        """
        try:
            # Convert event to frontend-compatible format
            event_data = self._serialize_event(event)
            
            # Emit via callback (e.g., WebSocket)
            self.emit_callback(event_data)
            
            logger.debug(f"Emitted MetaSOP event: {event.event_type.value}")
            
        except Exception as e:
            logger.error(f"Failed to emit MetaSOP event: {e}")
            
    def _serialize_event(self, event: MetaSOPEvent) -> Dict[str, Any]:
        """Serialize event for frontend consumption.
        
        Args:
            event: The event to serialize
            
        Returns:
            Dict[str, Any]: Serialized event data

        """
        # Create the base event structure
        timestamp = event.timestamp or self._get_timestamp()
        event_data: Dict[str, Any] = {
            "type": "metasop_event",
            "event_type": event.event_type.value,
            "timestamp": timestamp,
        }
        
        # Add step-specific data
        if event.step_id:
            event_data["step_id"] = event.step_id
        if event.role:
            event_data["role"] = event.role
        if event.status:
            event_data["status"] = event.status
        if event.retries > 0:
            event_data["retries"] = event.retries
            
        # Add artifact data
        if event.artifact:
            event_data["artifact"] = event.artifact
            
        # Add error data
        if event.error:
            event_data["error"] = event.error
            
        # Add metadata
        if event.metadata:
            event_data["metadata"] = event.metadata
            
        return event_data
        
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format.
        
        Returns:
            str: ISO timestamp

        """
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
    
    def _get_validator(self):
        """Lazy load the schema validator to avoid circular imports."""
        if self._validator is None:
            try:
                from .schema_validator import get_validator
                self._validator = get_validator()
            except ImportError as e:
                logger.warning(f"Schema validator not available: {e}")
                self._validator = None
        return self._validator
    
    def _validate_artifact(self, artifact: Dict[str, Any], role: str, step_id: str) -> Dict[str, Any]:
        """Validate an artifact against its schema.
        
        Args:
            artifact: The artifact to validate
            role: The role that produced the artifact
            step_id: The step ID for logging
            
        Returns:
            Dict containing validation results

        """
        validator = self._get_validator()
        
        if validator is None:
            return {
                'enabled': False,
                'is_valid': True,
                'errors': [],
                'warnings': ['Schema validation not available']
            }
        
        try:
            # Validate the artifact
            is_valid, errors, warnings, suggestions = validator.validate_with_suggestions(
                artifact, role
            )
            
            # Log validation results
            if is_valid:
                logger.info(f"✅ Artifact validation passed for {role} (step {step_id})")
                if warnings:
                    for warning in warnings:
                        logger.info(f"  ⚠️  {warning}")
            else:
                log_func = logger.error if self.strict_validation else logger.warning
                log_func(f"❌ Artifact validation failed for {role} (step {step_id}): {len(errors)} errors")
                for error in errors:
                    log_func(f"  • {error}")
                
                if suggestions:
                    logger.info(f"💡 Validation suggestions:")
                    for suggestion in suggestions:
                        logger.info(f"  • {suggestion}")
            
            return {
                'enabled': True,
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'suggestions': suggestions,
                'error_count': len(errors),
                'warning_count': len(warnings)
            }
            
        except Exception as e:
            logger.error(f"Validation error for {role} (step {step_id}): {e}")
            return {
                'enabled': True,
                'is_valid': False,
                'errors': [f"Validation exception: {str(e)}"],
                'warnings': [],
                'suggestions': []
            }

# Legacy compatibility functions for existing code
def emit_step_event(conversation_id: str, step_id: str, role: str, status: str, 
                   retries: int = 0, emit_callback=None):
    """Legacy function for emitting step events.
    
    Args:
        conversation_id: Conversation ID (unused, kept for compatibility)
        step_id: Step ID
        role: Role
        status: Status
        retries: Number of retries
        emit_callback: Callback function for emitting

    """
    if emit_callback is None:
        logger.warning("No emit callback provided for step event")
        return
        
    emitter = MetaSOPEventEmitter(emit_callback)
    
    if status in ["executed", "success", "completed"]:
        emitter.emit_step_complete(step_id, role, retries=retries)
    elif status in ["running", "executing"]:
        emitter.emit_step_start(step_id, role)
    elif status in ["failed", "error"]:
        emitter.emit_step_failed(step_id, role, f"Step {step_id} failed", retries=retries)
    else:
        logger.warning(f"Unknown step status: {status}")

def emit_artifact_event(conversation_id: str, step_id: str, artifact: Dict[str, Any], 
                       emit_callback=None):
    """Legacy function for emitting artifact events.
    
    Args:
        conversation_id: Conversation ID (unused, kept for compatibility)
        step_id: Step ID
        artifact: Artifact data
        emit_callback: Callback function for emitting

    """
    if emit_callback is None:
        logger.warning("No emit callback provided for artifact event")
        return
        
    emitter = MetaSOPEventEmitter(emit_callback)
    emitter.emit_artifact_produced(step_id, "Unknown", artifact)

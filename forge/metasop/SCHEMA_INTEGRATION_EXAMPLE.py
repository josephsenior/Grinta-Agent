"""Example: Integrating Schema Validation into MetaSOP Event Emission.

This file demonstrates how to integrate the schema validator into the 
MetaSOP event emitter to validate artifacts before emission.
"""

import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from .schema_validator import validate_artifact, validate_artifact_with_suggestions

logger = logging.getLogger(__name__)


class EventType(Enum):
    """MetaSOP event types."""
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_FAILED = "step_failed"
    ARTIFACT_PRODUCED = "artifact_produced"
    ARTIFACT_VALIDATION_FAILED = "artifact_validation_failed"
    ORCHESTRATION_START = "orchestration_start"
    ORCHESTRATION_COMPLETE = "orchestration_complete"
    ORCHESTRATION_FAILED = "orchestration_failed"


@dataclass
class MetaSOPEvent:
    """MetaSOP event data structure."""
    event_type: EventType
    step_id: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    artifact: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retries: int = 0
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    # New fields for validation
    validation_errors: Optional[list] = None
    validation_warnings: Optional[list] = None
    validation_suggestions: Optional[list] = None


class EnhancedMetaSOPEventEmitter:
    """Enhanced event emitter with schema validation.
    
    This version validates artifacts before emission and includes validation
    results in the event metadata.
    """
    
    def __init__(self, emit_callback, enable_validation: bool = True, 
                 strict_validation: bool = False):
        """Initialize enhanced event emitter.
        
        Args:
            emit_callback: Function to call when emitting events
            enable_validation: Whether to validate artifacts
            strict_validation: If True, fail step on validation errors

        """
        self.emit_callback = emit_callback
        self.enable_validation = enable_validation
        self.strict_validation = strict_validation
        
    def _validate_artifact_if_enabled(
        self,
        artifact: Optional[Dict[str, Any]],
        role: str,
        step_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Validate artifact if validation is enabled.
        
        Args:
            artifact: Artifact to validate
            role: Role that produced artifact
            step_id: Step ID
            metadata: Metadata dict to update
            
        Returns:
            True if validation passed or disabled

        """
        if not (self.enable_validation and artifact):
            return True
        
        is_valid, errors, warnings, suggestions = validate_artifact_with_suggestions(
            artifact, role
        )
        
        metadata['validation'] = {
            'is_valid': is_valid,
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }
        
        if not is_valid:
            self._log_validation_errors(role, step_id, errors)
        
        return is_valid

    def _log_validation_errors(self, role: str, step_id: str, errors: list) -> None:
        """Log validation errors.
        
        Args:
            role: Role that produced artifact
            step_id: Step ID
            errors: List of validation errors

        """
        logger.warning(
            f"Artifact validation failed for {role} (step {step_id}): "
            f"{len(errors)} errors"
        )
        
        for error in errors:
            logger.warning(f"  Validation error: {error}")

    def emit_step_complete(
        self,
        step_id: str,
        role: str,
        artifact: Optional[Dict[str, Any]] = None,
        retries: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Emit step completion event with artifact validation.
        
        Args:
            step_id: ID of the completed step
            role: Role that completed the step
            artifact: Artifact produced by the step
            retries: Number of retries used
            metadata: Additional metadata

        """
        if metadata is None:
            metadata = {}
        
        validation_passed = self._validate_artifact_if_enabled(artifact, role, step_id, metadata)

        # If strict mode, emit validation failure event when validation fails
        if not validation_passed and self.strict_validation:
            validation_info = metadata.get('validation', {}) if metadata else {}
            errors = validation_info.get('errors') or []
            warnings = validation_info.get('warnings') or []
            suggestions = validation_info.get('suggestions') or []

            self._emit_validation_failed(
                step_id, role, artifact, errors, warnings, suggestions
            )
            return  # Don't emit success event when strict validation fails

        if validation_passed:
            logger.info(f"Artifact validation passed for {role} (step {step_id})")

            validation_info = metadata.get('validation', {}) if metadata else {}
            warnings = validation_info.get('warnings') or []
            suggestions = validation_info.get('suggestions') or []

            # Log warnings if any
            for warning in warnings:
                logger.info(f"  Validation warning: {warning}")

            # Log suggestions if any
            if suggestions:
                logger.info(f"  Validation suggestions: {len(suggestions)}")
        
        # Emit the step complete event
        event = MetaSOPEvent(
            event_type=EventType.STEP_COMPLETE,
            step_id=step_id,
            role=role,
            status="success" if validation_passed else "success_with_warnings",
            artifact=artifact,
            retries=retries,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
        
    def emit_artifact_produced(
        self,
        step_id: str,
        role: str,
        artifact: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Emit artifact production event with validation.
        
        Args:
            step_id: ID of the step that produced the artifact
            role: Role that produced the artifact
            artifact: The artifact data
            metadata: Additional metadata

        """
        if metadata is None:
            metadata = {}
        
        # Validate artifact
        if self.enable_validation:
            is_valid, errors, warnings, suggestions = validate_artifact_with_suggestions(
                artifact, role
            )
            
            metadata['validation'] = {
                'is_valid': is_valid,
                'errors': errors,
                'warnings': warnings,
                'suggestions': suggestions
            }
            
            if not is_valid:
                logger.warning(
                    f"Artifact validation failed for {role}: {len(errors)} errors"
                )
        
        event = MetaSOPEvent(
            event_type=EventType.ARTIFACT_PRODUCED,
            step_id=step_id,
            role=role,
            artifact=artifact,
            timestamp=self._get_timestamp(),
            metadata=metadata
        )
        self._emit_event(event)
    
    def _emit_validation_failed(
        self,
        step_id: str,
        role: str,
        artifact: Optional[Dict[str, Any]],
        errors: list,
        warnings: list,
        suggestions: list
    ):
        """Emit artifact validation failure event."""
        event = MetaSOPEvent(
            event_type=EventType.ARTIFACT_VALIDATION_FAILED,
            step_id=step_id,
            role=role,
            status="validation_failed",
            artifact=artifact,
            validation_errors=errors,
            validation_warnings=warnings,
            validation_suggestions=suggestions,
            timestamp=self._get_timestamp(),
            metadata={
                'error_count': len(errors),
                'warning_count': len(warnings),
                'suggestion_count': len(suggestions)
            }
        )
        self._emit_event(event)
    
    def _emit_event(self, event: MetaSOPEvent):
        """Emit an event through the callback."""
        try:
            event_dict = {
                'event_type': event.event_type.value,
                'step_id': event.step_id,
                'role': event.role,
                'status': event.status,
                'artifact': event.artifact,
                'error': event.error,
                'retries': event.retries,
                'timestamp': event.timestamp,
                'metadata': event.metadata,
                'validation_errors': event.validation_errors,
                'validation_warnings': event.validation_warnings,
                'validation_suggestions': event.validation_suggestions
            }
            self.emit_callback(event_dict)
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"


# Example usage
def example_usage():
    """Example of how to use the enhanced event emitter."""
    
    # Define a callback function
    def my_emit_callback(event_data):
        print(f"Event emitted: {event_data['event_type']}")
        if event_data.get('metadata', {}).get('validation'):
            validation = event_data['metadata']['validation']
            if validation['is_valid']:
                print("  ✅ Artifact validation passed")
            else:
                print(f"  ❌ Artifact validation failed: {len(validation['errors'])} errors")
                for error in validation['errors']:
                    print(f"     - {error}")
    
    # Create emitter with validation enabled
    emitter = EnhancedMetaSOPEventEmitter(
        emit_callback=my_emit_callback,
        enable_validation=True,
        strict_validation=False  # Set to True to fail steps on validation errors
    )
    
    # Example artifact (Product Manager)
    pm_artifact = {
        "user_stories": [
            {
                "id": "US-001",
                "title": "User Login",
                "story": "As a user I want to login so that I can access my account",
                "priority": "high",
                "estimated_complexity": "medium"
            }
        ],
        "acceptance_criteria": [
            "User can enter email and password",
            "Invalid credentials show error message",
            "Successful login redirects to dashboard"
        ],
        "ui_multi_section": False
    }
    
    # Emit step complete with artifact
    emitter.emit_step_complete(
        step_id="step_001",
        role="Product Manager",
        artifact=pm_artifact,
        retries=0
    )
    
    # Example of invalid artifact (missing required field)
    invalid_artifact = {
        "user_stories": []  # Empty array violates minItems: 1
    }
    
    emitter.emit_step_complete(
        step_id="step_002",
        role="Product Manager",
        artifact=invalid_artifact,
        retries=0
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()


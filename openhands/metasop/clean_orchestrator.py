"""
Clean MetaSOP Orchestrator

A production-ready, clean implementation of the MetaSOP orchestrator that addresses
all the issues identified in the comprehensive analysis.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path

from openhands.metasop.models import SopTemplate, SopStep, Artifact, StepResult
from openhands.metasop.template_loader import get_default_template, load_template
from openhands.metasop.event_emitter import MetaSOPEventEmitter
from openhands.metasop.orchestrator import MetaSOPOrchestrator

logger = logging.getLogger(__name__)

class CleanMetaSOPOrchestrator:
    """Clean, production-ready MetaSOP orchestrator."""
    
    def __init__(self, emit_callback: Optional[Callable] = None, template_name: str = "feature_delivery"):
        """Initialize the clean orchestrator.
        
        Args:
            emit_callback: Function to call when emitting events
            template_name: Name of the template to use
        """
        self.emit_callback = emit_callback
        self.template_name = template_name
        self.template: Optional[SopTemplate] = None
        self.event_emitter: Optional[MetaSOPEventEmitter] = None
        self.legacy_orchestrator: Optional[MetaSOPOrchestrator] = None
        
        # Initialize components
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize orchestrator components."""
        try:
            # Load template
            self.template = load_template(self.template_name)
            logger.info(f"Loaded template '{self.template_name}' with {len(self.template.steps)} steps")
            
            # Initialize event emitter
            if self.emit_callback:
                self.event_emitter = MetaSOPEventEmitter(self.emit_callback)
                logger.info("Event emitter initialized")
            
            # Initialize legacy orchestrator for actual execution
            self.legacy_orchestrator = MetaSOPOrchestrator(self.template_name, None)
            self.legacy_orchestrator.template = self.template
            
            # Set up event callbacks
            if self.event_emitter:
                self.legacy_orchestrator.set_step_event_callback(self._handle_step_event)
                
            logger.info("Clean MetaSOP orchestrator initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize clean orchestrator: {e}")
            raise
            
    def _handle_step_event(self, event: Dict[str, Any]):
        """Handle step events from the legacy orchestrator.
        
        Args:
            event: Event data from legacy orchestrator
        """
        if not self.event_emitter:
            return
            
        try:
            step_id = event.get("step_id", "unknown")
            role = event.get("role", "Unknown")
            status = event.get("status", "unknown")
            retries = event.get("retries", 0)
            artifact = event.get("artifact")
            error = event.get("error")
            
            # Map legacy status to clean events
            if status in ["executed", "success", "completed"]:
                self.event_emitter.emit_step_complete(step_id, role, artifact, retries)
            elif status in ["running", "executing"]:
                self.event_emitter.emit_step_start(step_id, role)
            elif status in ["failed", "error"]:
                self.event_emitter.emit_step_failed(step_id, role, error or "Unknown error", retries)
            else:
                logger.warning(f"Unknown step status: {status}")
                
        except Exception as e:
            logger.error(f"Failed to handle step event: {e}")
            
    async def run_orchestration(self, user_request: str, repo_root: Optional[str] = None, 
                               max_retries: int = 2) -> Dict[str, Any]:
        """Run MetaSOP orchestration.
        
        Args:
            user_request: User's request
            repo_root: Repository root path
            max_retries: Maximum number of retries
            
        Returns:
            Dict[str, Any]: Orchestration results
        """
        if not self.legacy_orchestrator:
            raise RuntimeError("Orchestrator not properly initialized")
            
        try:
            # Emit orchestration start event
            if self.event_emitter:
                self.event_emitter.emit_orchestration_start({
                    "user_request": user_request[:100] + "..." if len(user_request) > 100 else user_request,
                    "template": self.template_name,
                    "max_retries": max_retries
                })
            
            logger.info(f"Starting MetaSOP orchestration with template '{self.template_name}'")
            
            # Run the orchestration with TRUE async execution for maximum performance
            success, artifacts = await self.legacy_orchestrator.run_async(
                user_request,
                repo_root,
                max_retries
            )
            
            # Emit orchestration completion event
            if self.event_emitter:
                if success:
                    self.event_emitter.emit_orchestration_complete({
                        "artifacts_count": len(artifacts),
                        "template": self.template_name
                    })
                else:
                    self.event_emitter.emit_orchestration_failed("Orchestration failed")
            
            logger.info(f"MetaSOP orchestration completed: success={success}, artifacts={len(artifacts)}")
            
            return {
                "success": success,
                "artifacts": artifacts,
                "template": self.template_name,
                "steps_executed": len(artifacts)
            }
            
        except Exception as e:
            logger.error(f"MetaSOP orchestration failed: {e}")
            
            # Emit orchestration failure event
            if self.event_emitter:
                self.event_emitter.emit_orchestration_failed(str(e))
                
            return {
                "success": False,
                "error": str(e),
                "artifacts": {},
                "template": self.template_name,
                "steps_executed": 0
            }
            
    def get_template_info(self) -> Dict[str, Any]:
        """Get information about the current template.
        
        Returns:
            Dict[str, Any]: Template information
        """
        if not self.template:
            return {"error": "No template loaded"}
            
        return {
            "name": self.template.name,
            "steps": [
                {
                    "id": step.id,
                    "role": step.role,
                    "task": step.task,
                    "depends_on": step.depends_on,
                    "condition": step.condition,
                    "priority": step.priority
                }
                for step in self.template.steps
            ],
            "total_steps": len(self.template.steps)
        }
        
    def set_emit_callback(self, callback: Callable):
        """Set the event emission callback.
        
        Args:
            callback: Function to call when emitting events
        """
        self.emit_callback = callback
        if callback:
            self.event_emitter = MetaSOPEventEmitter(callback)
            if self.legacy_orchestrator:
                self.legacy_orchestrator.set_step_event_callback(self._handle_step_event)
        else:
            self.event_emitter = None
            if self.legacy_orchestrator:
                self.legacy_orchestrator.set_step_event_callback(None)
                
    def change_template(self, template_name: str):
        """Change the template being used.
        
        Args:
            template_name: Name of the new template
        """
        try:
            self.template = load_template(template_name)
            self.template_name = template_name
            
            if self.legacy_orchestrator:
                self.legacy_orchestrator.template = self.template
                
            logger.info(f"Changed template to '{template_name}'")
            
        except Exception as e:
            logger.error(f"Failed to change template to '{template_name}': {e}")
            raise

# Factory function for easy creation
def create_clean_orchestrator(emit_callback: Optional[Callable] = None, 
                             template_name: str = "feature_delivery") -> CleanMetaSOPOrchestrator:
    """Create a clean MetaSOP orchestrator.
    
    Args:
        emit_callback: Function to call when emitting events
        template_name: Name of the template to use
        
    Returns:
        CleanMetaSOPOrchestrator: New orchestrator instance
    """
    return CleanMetaSOPOrchestrator(emit_callback, template_name)

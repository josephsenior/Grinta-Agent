"""
Context-Aware Collaborative Streaming Engine for MetaSOP Multi-Agent Orchestration.

This module provides intelligent real-time streaming collaboration between agents
while preventing partial context issues through sophisticated validation mechanisms.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Set, Optional, Tuple, Any, AsyncGenerator, Union, TYPE_CHECKING
from collections import defaultdict

from openhands.core.logger import openhands_logger as logger
from openhands.metasop.models import SopStep, Artifact, OrchestrationContext

if TYPE_CHECKING:
    from openhands.metasop.parallel_execution import ParallelExecutionEngine
    from openhands.metasop.causal_reasoning import CausalReasoningEngine
    from openhands.metasop.predictive_execution import PredictiveExecutionPlanner


class StreamChunkType(Enum):
    """Types of stream chunks with different validation requirements."""
    PARTIAL_ARTIFACT = "partial_artifact"
    COMPLETE_ARTIFACT = "complete_artifact"
    CONTEXT_UPDATE = "context_update"
    DEPENDENCY_REMOVED = "dependency_removed"
    RESOURCE_AVAILABLE = "resource_available"


class ContextReadiness(Enum):
    """Context readiness levels for safe agent consumption."""
    INSUFFICIENT = "insufficient"  # < 50% context complete, dangerous to consume
    PARTIAL = "partial"           # 50-79% context, limited consumption only
    SUFFICIENT = "sufficient"     # 80-94% context, safe with validation
    COMPLETE = "complete"         # 95%+ context, fully safe


@dataclass
class StreamChunk:
    """A chunk of streaming data with metadata."""
    step_id: str
    chunk_type: StreamChunkType
    content: Any
    timestamp: float
    confidence: float = 0.0
    metadata: Dict[str, Any] = None


@dataclass
class ValidatedStreamChunk:
    """A stream chunk validated for context completeness and safety."""
    chunk: Optional[StreamChunk]
    context_verified: bool
    confidence: float
    readiness_level: ContextReadiness
    validation_details: Dict[str, Any]
    reason: Optional[str] = None
    safe_to_consume: bool = False


@dataclass
class ContextValidationResult:
    """Result of context validation for streaming chunks."""
    completeness_score: float
    consistency_score: float
    dependency_satisfaction: float
    role_appropriateness: float
    overall_confidence: float
    blocking_issues: List[str]
    warnings: List[str]
    safe_for_role: bool


class ContextAwareStreamingEngine:
    """
    Intelligent streaming engine that prevents partial context issues through
    sophisticated validation and context awareness mechanisms.
    """
    
    def __init__(
        self,
        parallel_engine: Optional["ParallelExecutionEngine"] = None,
        causal_engine: Optional["CausalReasoningEngine"] = None,
        predictive_planner: Optional["PredictiveExecutionPlanner"] = None,
        context_completeness_threshold: float = 0.8,
        semantic_consistency_threshold: float = 0.7
    ):
        """Initialize the context-aware streaming engine."""
        self.parallel_engine = parallel_engine
        self.causal_engine = causal_engine
        self.predictive_planner = predictive_planner
        
        # Validation thresholds
        self.context_completeness_threshold = context_completeness_threshold
        self.semantic_consistency_threshold = semantic_consistency_threshold
        
        # Streaming state management
        self.active_streams: Dict[str, asyncio.Queue] = {}
        self.consumer_registrations: Dict[str, Set[str]] = defaultdict(set)
        self.completed_artifacts: Dict[str, Artifact] = {}
        self.partial_contexts: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # Performance tracking
        self.streaming_stats = {
            "total_streams": 0,
            "context_validation_blocks": 0,
            "successful_collaborations": 0,
            "avg_context_completeness": 0.0,
            "avg_streaming_latency_ms": 0.0
        }
        
        logger.info("Context-Aware Collaborative Streaming Engine initialized")

    async def stream_step_execution_with_validation(
        self, 
        step: SopStep, 
        execution_func,
        *args,
        **kwargs
    ) -> AsyncGenerator[ValidatedStreamChunk, None]:
        """
        Stream step execution with intelligent context validation to prevent
        partial context issues and ensure safe agent collaboration.
        """
        start_time = time.perf_counter()
        stream_id = f"{step.id}_{int(start_time * 1000)}"
        
        try:
            logger.info(f"🔗 Starting context-aware streaming for step {step.id}")
            
            # Create stream queue for this execution
            stream_queue = asyncio.Queue()
            self.active_streams[stream_id] = stream_queue
            
            # Register consumers (other agents that need this step's output)
            await self._register_stream_consumers(step, stream_id)
            
            # Start streaming execution in background
            streaming_task = asyncio.create_task(
                self._stream_execution_background(
                    stream_id, step, execution_func, *args, **kwargs
                )
            )
            
            # Process and validate stream chunks as they arrive
            async for chunk in self._process_stream_queue(stream_id, step):
                yield chunk
                
            await streaming_task
            
        except Exception as e:
            logger.error(f"Streaming execution failed for step {step.id}: {e}")
            yield ValidatedStreamChunk(
                chunk=None,
                context_verified=False,
                confidence=0.0,
                readiness_level=ContextReadiness.INSUFFICIENT,
                validation_details={"error": str(e)},
                reason=f"Streaming failed: {e}",
                safe_to_consume=False
            )
        finally:
            # Cleanup
            await self._cleanup_stream(stream_id)

    async def _stream_execution_background(
        self, 
        stream_id: str, 
        step: SopStep, 
        execution_func, 
        *args, 
        **kwargs
    ) -> None:
        """Background task that streams execution results as they're produced."""
        try:
            # This would integrate with your existing step execution
            # For now, we'll simulate streaming chunks
            if hasattr(execution_func, '__aiter__'):
                async for partial_result in execution_func(*args, **kwargs):
                    chunk = StreamChunk(
                        step_id=step.id,
                        chunk_type=StreamChunkType.PARTIAL_ARTIFACT,
                        content=partial_result,
                        timestamp=time.perf_counter()
                    )
                    await self.active_streams[stream_id].put(chunk)
            else:
                # For non-streaming functions, we'll simulate chunks
                # In real implementation, this would hook into LLM streaming
                result = await execution_func(*args, **kwargs)
                chunk = StreamChunk(
                    step_id=step.id,
                    chunk_type=StreamChunkType.COMPLETE_ARTIFACT,
                    content=result,
                    timestamp=time.perf_counter()
                )
                await self.active_streams[stream_id].put(chunk)
                
        except Exception as e:
            logger.error(f"Background streaming failed: {e}")
        finally:
            # Signal end of stream
            await self.active_streams[stream_id].put(None)

    async def _process_stream_queue(
        self, 
        stream_id: str, 
        step: SopStep
    ) -> AsyncGenerator[ValidatedStreamChunk, None]:
        """Process stream queue and validate chunks before yielding."""
        stream_queue = self.active_streams[stream_id]
        
        while True:
            try:
                # Get next chunk with timeout
                chunk = await asyncio.wait_for(stream_queue.get(), timeout=30.0)
                
                if chunk is None:  # End of stream signal
                    break
                
                # Validate chunk for context safety
                validated_chunk = await self._validate_stream_chunk(chunk, step)
                yield validated_chunk
                
                # Only process if context is verified and safe
                if validated_chunk.safe_to_consume and validated_chunk.chunk:
                    await self._update_consumers_with_validated_chunk(
                        stream_id, validated_chunk
                    )
                    
            except asyncio.TimeoutError:
                logger.warning(f"Stream timeout for {step.id}")
                break
            except Exception as e:
                logger.error(f"Error processing stream chunk: {e}")
                break

    async def _validate_stream_chunk(
        self, 
        chunk: StreamChunk, 
        step: SopStep
    ) -> ValidatedStreamChunk:
        """
        Validate stream chunk to prevent partial context issues.
        
        This is the core safety mechanism that ensures agents only receive
        contextually complete and semantically consistent information.
        """
        try:
            # 1. CONTEXT COMPLETENESS VALIDATION
            completeness_score = await self._validate_context_completeness(
                step, chunk
            )
            
            # 2. SEMANTIC CONSISTENCY VALIDATION
            consistency_score = await self._validate_semantic_consistency(
                step, chunk
            )
            
            # 3. DEPENDENCY SATISFACTION CHECK
            dependency_score = await self._validate_dependency_satisfaction(
                step, chunk
            )
            
            # 4. ROLE APPROPRIATENESS VALIDATION
            role_score = await self._validate_role_appropriateness(
                step, chunk
            )
            
            # Calculate overall confidence
            overall_confidence = (
                completeness_score * 0.3 +
                consistency_score * 0.3 +
                dependency_score * 0.2 +
                role_score * 0.2
            )
            
            # Determine readiness level
            readiness_level = self._determine_readiness_level(overall_confidence)
            
            # Assess safety for consumption
            safe_to_consume = (
                overall_confidence >= self.context_completeness_threshold and
                completeness_score >= 0.7 and
                consistency_score >= self.semantic_consistency_threshold
            )
            
            validation_details = {
                "completeness_score": completeness_score,
                "consistency_score": consistency_score,
                "dependency_score": dependency_score,
                "role_score": role_score,
                "overall_confidence": overall_confidence
            }
            
            # Generate blocking issues and warnings
            blocking_issues, warnings = await self._generate_validation_feedback(
                completeness_score, consistency_score, dependency_score, role_score
            )
            
            reason = None
            if not safe_to_consume:
                reason = "Context incomplete or inconsistent - not safe for agent consumption"
                self.streaming_stats["context_validation_blocks"] += 1
            
            return ValidatedStreamChunk(
                chunk=chunk if safe_to_consume else None,
                context_verified=safe_to_consume,
                confidence=overall_confidence,
                readiness_level=readiness_level,
                validation_details=validation_details,
                reason=reason,
                safe_to_consume=safe_to_consume
            )
            
        except Exception as e:
            logger.error(f"Chunk validation failed: {e}")
            return ValidatedStreamChunk(
                chunk=None,
                context_verified=False,
                confidence=0.0,
                readiness_level=ContextReadiness.INSUFFICIENT,
                validation_details={"error": str(e)},
                reason=f"Validation error: {e}",
                safe_to_consume=False
            )

    async def _validate_context_completeness(
        self, 
        step: SopStep, 
        chunk: StreamChunk
    ) -> float:
        """
        Validate that the stream chunk provides sufficient context completeness
        for safe agent consumption.
        """
        try:
            # Check if all required dependencies are satisfied
            if step.depends_on:
                satisfied_deps = 0
                for dep_id in step.depends_on:
                    if dep_id in self.completed_artifacts:
                        satisfied_deps += 1
                
                dependency_completeness = satisfied_deps / len(step.depends_on)
            else:
                dependency_completeness = 1.0
            
            # Check artifact content completeness
            content_completeness = await self._assess_content_completeness(chunk)
            
            # Weighted score
            completeness_score = (
                dependency_completeness * 0.6 + 
                content_completeness * 0.4
            )
            
            return min(1.0, completeness_score)
            
        except Exception as e:
            logger.warning(f"Context completeness validation failed: {e}")
            return 0.0

    async def _validate_semantic_consistency(
        self, 
        step: SopStep, 
        chunk: StreamChunk
    ) -> float:
        """
        Validate semantic consistency to prevent agents from making
        decisions based on contradictory or inconsistent information.
        """
        try:
            if not isinstance(chunk.content, dict):
                return 0.8  # Assume consistent for non-dict content
            
            # Check for semantic contradictions in the content
            consistency_score = 1.0
            
            # Simple consistency checks (can be enhanced with LLM-based validation)
            content = chunk.content
            
            # Check for logical contradictions
            if "error" in content and "success" in content:
                if content.get("error") and content.get("success"):
                    consistency_score *= 0.3  # Major contradiction
            
            # Check for incomplete required fields based on step role
            required_fields = self._get_required_fields_for_role(step.role)
            missing_fields = 0
            for field in required_fields:
                if field not in content or not content[field]:
                    missing_fields += 1
            
            if required_fields:
                field_completeness = 1.0 - (missing_fields / len(required_fields))
                consistency_score *= field_completeness
            
            return min(1.0, consistency_score)
            
        except Exception as e:
            logger.warning(f"Semantic consistency validation failed: {e}")
            return 0.5  # Conservative score

    async def _validate_dependency_satisfaction(
        self, 
        step: SopStep, 
        chunk: StreamChunk
    ) -> float:
        """Validate that all dependencies are properly satisfied."""
        if not step.depends_on:
            return 1.0
        
        satisfied_count = 0
        for dep_id in step.depends_on:
            if dep_id in self.completed_artifacts:
                # Check if dependency is actually usable
                dep_artifact = self.completed_artifacts[dep_id]
                if self._is_dependency_usable(dep_artifact, step):
                    satisfied_count += 1
        
        return satisfied_count / len(step.depends_on)

    async def _validate_role_appropriateness(
        self, 
        step: SopStep, 
        chunk: StreamChunk
    ) -> float:
        """Validate that the chunk content is appropriate for the consuming agent's role."""
        try:
            # Define role-specific content requirements
            role_requirements = self._get_role_content_requirements(step.role)
            
            if not isinstance(chunk.content, dict):
                return 0.7  # Default for non-dict content
            
            content = chunk.content
            appropriateness_score = 1.0
            
            # Check required fields for this role
            for field, importance in role_requirements.items():
                if field not in content or not content[field]:
                    appropriateness_score -= importance
            
            return max(0.0, appropriateness_score)
            
        except Exception as e:
            logger.warning(f"Role appropriateness validation failed: {e}")
            return 0.5

    def _determine_readiness_level(self, overall_confidence: float) -> ContextReadiness:
        """Determine context readiness level based on confidence score."""
        if overall_confidence < 0.5:
            return ContextReadiness.INSUFFICIENT
        elif overall_confidence < 0.8:
            return ContextReadiness.PARTIAL
        elif overall_confidence < 0.95:
            return ContextReadiness.SUFFICIENT
        else:
            return ContextReadiness.COMPLETE

    async def _get_required_fields_for_role(self, role: str) -> List[str]:
        """Get required fields for a specific role."""
        role_requirements = {
            "engineer": ["code", "implementation", "functionality"],
            "qa": ["tests", "validation", "coverage"],
            "product_manager": ["requirements", "specification", "acceptance_criteria"],
            "architect": ["design", "architecture", "patterns"],
            "ui_designer": ["interface", "design", "mockups"]
        }
        return role_requirements.get(role.lower(), [])

    async def _get_role_content_requirements(self, role: str) -> Dict[str, float]:
        """Get content requirements and their importance weights for a role."""
        requirements = {
            "engineer": {"code": 0.4, "implementation": 0.3, "functionality": 0.3},
            "qa": {"tests": 0.4, "validation": 0.3, "coverage": 0.3},
            "product_manager": {"requirements": 0.4, "specification": 0.3, "acceptance_criteria": 0.3},
            "architect": {"design": 0.4, "architecture": 0.4, "patterns": 0.2},
            "ui_designer": {"interface": 0.4, "design": 0.4, "mockups": 0.2}
        }
        return requirements.get(role.lower(), {})

    async def _assess_content_completeness(self, chunk: StreamChunk) -> float:
        """Assess how complete the content appears to be."""
        try:
            if not isinstance(chunk.content, dict):
                return 0.8  # Default for non-dict
            
            content = chunk.content
            
            # Check for indicators of completeness
            completeness_indicators = [
                "complete" in str(content).lower(),
                "finished" in str(content).lower(),
                "done" in str(content).lower(),
                chunk.chunk_type == StreamChunkType.COMPLETE_ARTIFACT
            ]
            
            # Check for indicators of incompleteness
            incompleteness_indicators = [
                "partial" in str(content).lower(),
                "incomplete" in str(content).lower(),
                "draft" in str(content).lower(),
                chunk.chunk_type == StreamChunkType.PARTIAL_ARTIFACT
            ]
            
            completeness_score = 0.5  # Base score
            
            if any(completeness_indicators):
                completeness_score += 0.3
            if any(incompleteness_indicators):
                completeness_score -= 0.2
            
            # Check content size/structure as additional indicator
            if isinstance(content, dict) and len(content) > 3:
                completeness_score += 0.1
            
            return min(1.0, max(0.0, completeness_score))
            
        except Exception:
            return 0.5

    def _is_dependency_usable(self, dep_artifact: Artifact, step: SopStep) -> bool:
        """Check if a dependency artifact is actually usable for the current step."""
        try:
            # Basic check - artifact exists and has content
            if not dep_artifact or not dep_artifact.content:
                return False
            
            # Could add more sophisticated checks based on step requirements
            return True
            
        except Exception:
            return False

    async def _register_stream_consumers(self, step: SopStep, stream_id: str) -> None:
        """Register other agents that need this step's output."""
        # This would integrate with the dependency system to register consumers
        # For now, we'll simulate based on step dependencies
        if step.depends_on:
            for dep_id in step.depends_on:
                # Register as potential consumer
                self.consumer_registrations[stream_id].add(dep_id)

    async def _update_consumers_with_validated_chunk(
        self, 
        stream_id: str, 
        validated_chunk: ValidatedStreamChunk
    ) -> None:
        """Update registered consumers with validated chunk information."""
        if not validated_chunk.safe_to_consume or not validated_chunk.chunk:
            return
        
        # Update partial contexts for consumers
        for consumer_id in self.consumer_registrations[stream_id]:
            self.partial_contexts[consumer_id][stream_id] = validated_chunk.chunk.content

    async def _generate_validation_feedback(
        self, 
        completeness_score: float,
        consistency_score: float,
        dependency_score: float,
        role_score: float
    ) -> Tuple[List[str], List[str]]:
        """Generate blocking issues and warnings from validation scores."""
        blocking_issues = []
        warnings = []
        
        if completeness_score < 0.7:
            blocking_issues.append("Context completeness insufficient for safe consumption")
        elif completeness_score < 0.9:
            warnings.append("Context partially complete - proceed with caution")
        
        if consistency_score < 0.6:
            blocking_issues.append("Semantic inconsistencies detected in content")
        elif consistency_score < 0.8:
            warnings.append("Minor semantic inconsistencies present")
        
        if dependency_score < 0.8:
            blocking_issues.append("Critical dependencies not satisfied")
        elif dependency_score < 1.0:
            warnings.append("Some dependencies may be incomplete")
        
        if role_score < 0.7:
            blocking_issues.append("Content not appropriate for target role")
        elif role_score < 0.9:
            warnings.append("Content may be partially inappropriate for role")
        
        return blocking_issues, warnings

    async def _cleanup_stream(self, stream_id: str) -> None:
        """Clean up stream resources."""
        try:
            if stream_id in self.active_streams:
                del self.active_streams[stream_id]
            if stream_id in self.consumer_registrations:
                del self.consumer_registrations[stream_id]
        except Exception as e:
            logger.warning(f"Stream cleanup failed: {e}")

    def get_streaming_stats(self) -> Dict[str, Any]:
        """Get streaming performance statistics."""
        return self.streaming_stats.copy()

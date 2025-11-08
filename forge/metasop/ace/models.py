"""Pydantic models for ACE components."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field

from .context_playbook import BulletSection


class ACEInsight(BaseModel):
    """Insight extracted by the Reflector from execution analysis."""
    reasoning: str = Field(description="Chain of thought and analysis")
    error_identification: str = Field(description="What specifically went wrong")
    root_cause_analysis: str = Field(description="Why the error occurred")
    correct_approach: str = Field(description="What should have been done instead")
    key_insight: str = Field(description="Strategy or principle to remember")
    bullet_tags: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Tags for bullets used (id, tag)"
    )
    success: bool = Field(description="Whether the execution was successful")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the insight")
    created_at: datetime = Field(default_factory=datetime.now)


class ACEDeltaUpdate(BaseModel):
    """Delta update to be applied to the context playbook."""
    type: str = Field(description="Type of operation: ADD, UPDATE, REMOVE")
    section: Optional[BulletSection] = Field(default=None, description="Section for the update")
    content: Optional[str] = Field(default=None, description="Content for the bullet")
    bullet_id: Optional[str] = Field(default=None, description="ID of bullet to update")
    tags: List[str] = Field(default_factory=list, description="Tags for the bullet")
    helpful: Optional[bool] = Field(default=None, description="Whether the bullet was helpful")
    harmful: Optional[bool] = Field(default=None, description="Whether the bullet was harmful")
    priority: int = Field(default=0, description="Priority for the update")


class ACEExecutionResult(BaseModel):
    """Result of executing a trajectory."""
    success: bool = Field(description="Whether execution was successful")
    output: str = Field(description="Output from execution")
    error: Optional[str] = Field(description="Error message if failed")
    execution_time: float = Field(description="Time taken for execution")
    tokens_used: int = Field(description="Number of tokens used")
    cost: float = Field(description="Cost of execution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ACETrajectory(BaseModel):
    """Generated trajectory from the Generator."""
    content: str = Field(description="The generated trajectory content")
    task_type: str = Field(description="Type of task (appworld, code_generation, general)")
    used_bullet_ids: List[str] = Field(description="Bullet IDs used in generation")
    playbook_content: str = Field(description="Playbook content used")
    generation_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the generation process"
    )
    created_at: datetime = Field(default_factory=datetime.now)


class ACEPerformanceMetrics(BaseModel):
    """Performance metrics for the ACE framework."""
    total_tasks: int = Field(default=0, description="Total tasks processed")
    successful_tasks: int = Field(default=0, description="Successful tasks")
    failed_tasks: int = Field(default=0, description="Failed tasks")
    context_updates: int = Field(default=0, description="Context updates made")
    playbook_size: int = Field(default=0, description="Current playbook size")
    avg_helpfulness: float = Field(default=0.0, description="Average helpfulness score")
    adaptation_latency: float = Field(default=0.0, description="Average adaptation latency")
    token_usage: int = Field(default=0, description="Total tokens used")
    cost: float = Field(default=0.0, description="Total cost")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.failed_tasks / self.total_tasks


class ACEReflectionResult(BaseModel):
    """Result of reflection analysis."""
    insights: List[ACEInsight] = Field(description="Insights extracted")
    success: bool = Field(description="Whether reflection was successful")
    confidence: float = Field(ge=0.0, le=1.0, description="Overall confidence")
    processing_time: float = Field(description="Time taken for reflection")
    tokens_used: int = Field(description="Tokens used for reflection")


class ACECurationResult(BaseModel):
    """Result of curation process."""
    delta_updates: List[ACEDeltaUpdate] = Field(description="Delta updates generated")
    success: bool = Field(description="Whether curation was successful")
    redundancy_removed: int = Field(default=0, description="Number of redundant items removed")
    processing_time: float = Field(description="Time taken for curation")
    tokens_used: int = Field(description="Tokens used for curation")


class ACEGenerationResult(BaseModel):
    """Result of trajectory generation."""
    trajectory: ACETrajectory = Field(description="Generated trajectory")
    success: bool = Field(description="Whether generation was successful")
    processing_time: float = Field(description="Time taken for generation")
    tokens_used: int = Field(description="Tokens used for generation")
    retries: int = Field(default=0, description="Number of retries needed")


class ACEFrameworkResult(BaseModel):
    """Complete result from ACE framework processing."""
    generation_result: ACEGenerationResult = Field(description="Generation result")
    execution_result: ACEExecutionResult = Field(description="Execution result")
    reflection_result: ACEReflectionResult = Field(description="Reflection result")
    curation_result: ACECurationResult = Field(description="Curation result")
    success: bool = Field(description="Overall success")
    processing_time: float = Field(description="Total processing time")
    performance_metrics: ACEPerformanceMetrics = Field(description="Updated metrics")


class ACEConfig(BaseModel):
    """Configuration for ACE framework."""
    enable_ace: bool = Field(default=False, description="Enable ACE framework")
    max_bullets: int = Field(default=1000, description="Maximum playbook size")
    multi_epoch: bool = Field(default=True, description="Enable multi-epoch training")
    num_epochs: int = Field(default=5, description="Number of training epochs")
    reflector_max_iterations: int = Field(default=5, description="Max reflection iterations")
    enable_online_adaptation: bool = Field(default=True, description="Enable test-time learning")
    playbook_persistence_path: Optional[str] = Field(
        default=None, description="Path for playbook persistence"
    )
    min_helpfulness_threshold: float = Field(default=0.0, description="Minimum helpfulness for retrieval")
    max_playbook_content_length: int = Field(default=50, description="Max bullets in playbook content")
    enable_grow_and_refine: bool = Field(default=True, description="Enable grow-and-refine mechanism")
    cleanup_interval_days: int = Field(default=30, description="Days between cleanup cycles")
    redundancy_threshold: float = Field(default=0.8, description="Similarity threshold for redundancy")

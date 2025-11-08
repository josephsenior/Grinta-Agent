"""Core data models for Dynamic Prompt Optimization.

Defines the fundamental data structures used throughout the prompt optimization system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4


class PromptCategory(Enum):
    """Categories of prompts that can be optimized."""
    METASOP_ROLE = "metasop_role"
    CODEACT_SYSTEM = "codeact_system"
    TOOL_PROMPT = "tool_prompt"
    CUSTOM = "custom"


@dataclass
class PromptVariant:
    """Individual prompt version with metadata and performance tracking."""
    
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = ""
    version: int = 1
    parent_id: Optional[str] = None
    category: PromptCategory = PromptCategory.CUSTOM
    prompt_id: str = ""  # Base prompt identifier (e.g., "engineer_role", "codeact_system")
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Performance tracking
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    total_execution_time: float = 0.0
    total_token_cost: float = 0.0
    
    # A/B testing
    is_active: bool = False
    is_testing: bool = False
    traffic_percentage: float = 0.0
    
    def __post_init__(self):
        """Initialize computed fields after dataclass creation."""
        if not self.prompt_id:
            self.prompt_id = f"{self.category.value}_{self.id[:8]}"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_executions == 0:
            return 0.0
        return self.failed_executions / self.total_executions
    
    @property
    def avg_execution_time(self) -> float:
        """Calculate average execution time."""
        if self.total_executions == 0:
            return 0.0
        return self.total_execution_time / self.total_executions
    
    @property
    def avg_token_cost(self) -> float:
        """Calculate average token cost per execution."""
        if self.total_executions == 0:
            return 0.0
        return self.total_token_cost / self.total_executions
    
    def update_metrics(self, success: bool, execution_time: float, token_cost: float = 0.0):
        """Update performance metrics after execution."""
        self.total_executions += 1
        self.last_used = datetime.now()
        
        if success:
            self.successful_executions += 1
        else:
            self.failed_executions += 1
            
        self.total_execution_time += execution_time
        self.total_token_cost += token_cost
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'id': self.id,
            'content': self.content,
            'version': self.version,
            'parent_id': self.parent_id,
            'category': self.category.value,
            'prompt_id': self.prompt_id,
            'created_at': self.created_at.isoformat(),
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'metadata': self.metadata,
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'failed_executions': self.failed_executions,
            'total_execution_time': self.total_execution_time,
            'total_token_cost': self.total_token_cost,
            'is_active': self.is_active,
            'is_testing': self.is_testing,
            'traffic_percentage': self.traffic_percentage
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptVariant:
        """Create instance from dictionary."""
        # Handle datetime fields
        created_at = datetime.fromisoformat(data['created_at']) if data.get('created_at') else datetime.now()
        last_used = datetime.fromisoformat(data['last_used']) if data.get('last_used') else None
        
        return cls(
            id=data['id'],
            content=data['content'],
            version=data['version'],
            parent_id=data.get('parent_id'),
            category=PromptCategory(data['category']),
            prompt_id=data['prompt_id'],
            created_at=created_at,
            last_used=last_used,
            metadata=data.get('metadata', {}),
            total_executions=data.get('total_executions', 0),
            successful_executions=data.get('successful_executions', 0),
            failed_executions=data.get('failed_executions', 0),
            total_execution_time=data.get('total_execution_time', 0.0),
            total_token_cost=data.get('total_token_cost', 0.0),
            is_active=data.get('is_active', False),
            is_testing=data.get('is_testing', False),
            traffic_percentage=data.get('traffic_percentage', 0.0)
        )


@dataclass
class PromptMetrics:
    """Aggregated performance metrics for a prompt variant."""
    
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    error_rate: float = 0.0
    avg_token_cost: float = 0.0
    sample_count: int = 0
    composite_score: float = 0.0
    
    # Weights for composite score calculation
    success_weight: float = 0.4
    time_weight: float = 0.2
    error_weight: float = 0.2
    cost_weight: float = 0.2
    
    def __post_init__(self):
        """Calculate composite score after initialization."""
        self.composite_score = self._calculate_composite_score()
    
    def _calculate_composite_score(self) -> float:
        """Calculate weighted composite score from individual metrics."""
        if self.sample_count == 0:
            return 0.0
        
        # Normalize execution time (lower is better, max 60 seconds)
        normalized_time = max(0, 1 - (self.avg_execution_time / 60.0))
        
        # Normalize token cost (lower is better, max 1000 tokens)
        normalized_cost = max(0, 1 - (self.avg_token_cost / 1000.0))
        
        # Calculate weighted score
        score = (
            self.success_rate * self.success_weight +
            normalized_time * self.time_weight +
            (1 - self.error_rate) * self.error_weight +  # Lower error rate is better
            normalized_cost * self.cost_weight
        )
        
        return min(1.0, max(0.0, score))  # Clamp between 0 and 1
    
    def update_from_variant(self, variant: PromptVariant):
        """Update metrics from a PromptVariant."""
        self.success_rate = variant.success_rate
        self.avg_execution_time = variant.avg_execution_time
        self.error_rate = variant.error_rate
        self.avg_token_cost = variant.avg_token_cost
        self.sample_count = variant.total_executions
        self.composite_score = self._calculate_composite_score()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'success_rate': self.success_rate,
            'avg_execution_time': self.avg_execution_time,
            'error_rate': self.error_rate,
            'avg_token_cost': self.avg_token_cost,
            'sample_count': self.sample_count,
            'composite_score': self.composite_score,
            'success_weight': self.success_weight,
            'time_weight': self.time_weight,
            'error_weight': self.error_weight,
            'cost_weight': self.cost_weight
        }


@dataclass
class PromptPerformance:
    """Performance data for a single prompt execution."""
    
    variant_id: str
    prompt_id: str
    category: PromptCategory
    success: bool
    execution_time: float
    token_cost: float = 0.0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'variant_id': self.variant_id,
            'prompt_id': self.prompt_id,
            'category': self.category.value,
            'success': self.success,
            'execution_time': self.execution_time,
            'token_cost': self.token_cost,
            'error_message': self.error_message,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PromptPerformance:
        """Create instance from dictionary."""
        timestamp = datetime.fromisoformat(data['timestamp']) if data.get('timestamp') else datetime.now()
        
        return cls(
            variant_id=data['variant_id'],
            prompt_id=data['prompt_id'],
            category=PromptCategory(data['category']),
            success=data['success'],
            execution_time=data['execution_time'],
            token_cost=data.get('token_cost', 0.0),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {}),
            timestamp=timestamp
        )


@dataclass
class OptimizationConfig:
    """Configuration for prompt optimization behavior."""
    
    # A/B Testing
    ab_split_ratio: float = 0.8  # 80% to best, 20% to experiments
    min_samples_for_switch: int = 5
    confidence_threshold: float = 0.95
    
    # Composite Score Weights
    success_weight: float = 0.4
    time_weight: float = 0.2
    error_weight: float = 0.2
    cost_weight: float = 0.2
    
    # Evolution
    enable_evolution: bool = True
    evolution_threshold: float = 0.7  # Evolve if score < 0.7
    max_variants_per_prompt: int = 10
    
    # Storage
    storage_path: str = "~/.Forge/prompt_optimization/"
    sync_interval: int = 100  # Sync every 100 updates
    auto_save: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'ab_split_ratio': self.ab_split_ratio,
            'min_samples_for_switch': self.min_samples_for_switch,
            'confidence_threshold': self.confidence_threshold,
            'success_weight': self.success_weight,
            'time_weight': self.time_weight,
            'error_weight': self.error_weight,
            'cost_weight': self.cost_weight,
            'enable_evolution': self.enable_evolution,
            'evolution_threshold': self.evolution_threshold,
            'max_variants_per_prompt': self.max_variants_per_prompt,
            'storage_path': self.storage_path,
            'sync_interval': self.sync_interval,
            'auto_save': self.auto_save
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> OptimizationConfig:
        """Create instance from dictionary."""
        return cls(**data)

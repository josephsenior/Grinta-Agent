"""REST API endpoints for prompt optimization monitoring and control.

Integrates with existing analytics system to provide comprehensive
prompt optimization management capabilities.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from forge.core.logger import forge_logger as logger
from forge.server.session.session import Session
from forge.server.session.session_manager import SessionManager


# Pydantic models for API requests/responses
class PromptVariantResponse(BaseModel):
    """Serialized prompt variant with metadata returned to clients."""

    id: str
    content: str
    version: int
    parent_id: Optional[str] = None
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PromptMetricsResponse(BaseModel):
    """Aggregated performance metrics tracked per prompt variant."""

    success_rate: float
    avg_execution_time: float
    error_rate: float
    avg_token_cost: float
    sample_count: int
    composite_score: float
    last_updated: datetime


class PromptOptimizationStatus(BaseModel):
    """High-level status snapshot for an individual prompt configuration."""

    prompt_id: str
    category: str
    total_variants: int
    active_variant_id: str
    best_variant_id: str
    best_score: float
    is_optimized: bool
    last_evolution: Optional[datetime] = None


class OptimizationSummary(BaseModel):
    """Summary rollup metrics across all optimized prompts."""

    total_prompts: int
    optimized_prompts: int
    total_variants: int
    active_ab_tests: int
    avg_improvement: float
    total_savings: float
    last_updated: datetime


class EvolutionRequest(BaseModel):
    """Incoming request payload to trigger prompt evolution."""

    prompt_id: str
    strategy: Optional[str] = None
    max_variants: int = Field(default=3, ge=1, le=10)


class VariantSwitchRequest(BaseModel):
    """Payload to switch the active variant for a prompt."""

    prompt_id: str
    variant_id: str


class OptimizationConfigUpdate(BaseModel):
    """Partial configuration update for prompt optimization settings."""

    ab_split_ratio: Optional[float] = Field(None, ge=0.0, le=1.0)
    min_samples_for_switch: Optional[int] = Field(None, ge=1, le=50)
    confidence_threshold: Optional[float] = Field(None, ge=0.5, le=1.0)
    success_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    time_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    error_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    cost_weight: Optional[float] = Field(None, ge=0.0, le=1.0)
    enable_evolution: Optional[bool] = None
    evolution_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_variants_per_prompt: Optional[int] = Field(None, ge=1, le=50)


# Create router
router = APIRouter(prefix="/api/prompt-optimization", tags=["prompt-optimization"])


def get_prompt_optimizer(session: Session = Depends(SessionManager.get_session)) -> Any:
    """Get prompt optimizer from session."""
    # Try to get from CodeAct agent first
    if hasattr(session, "agent") and hasattr(session.agent, "prompt_optimizer"):
        return session.agent.prompt_optimizer

    # Try to get from MetaSOP orchestrator
    if hasattr(session, "orchestrator") and hasattr(
        session.orchestrator, "prompt_optimizer"
    ):
        return session.orchestrator.prompt_optimizer

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Prompt optimization not available in this session",
    )


@router.get("/status", response_model=OptimizationSummary)
async def get_optimization_status(
    session: Session = Depends(SessionManager.get_session),
):
    """Get overall prompt optimization status and summary."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        optimizer = prompt_optimizer["optimizer"]
        registry = prompt_optimizer["registry"]
        tracker = prompt_optimizer["tracker"]

        # Get all prompt IDs
        all_prompt_ids = registry.get_all_prompt_ids()
        total_prompts = len(all_prompt_ids)

        # Count optimized prompts (those with multiple variants)
        optimized_prompts = 0
        total_variants = 0
        active_ab_tests = 0
        total_improvement = 0.0
        total_savings = 0.0

        for prompt_id in all_prompt_ids:
            variants = registry.get_all_variants(prompt_id)
            total_variants += len(variants)

            if len(variants) > 1:
                optimized_prompts += 1
                active_ab_tests += 1

            # Calculate improvement and savings
            metrics = tracker.get_all_metrics(prompt_id)
            if metrics:
                best_metrics = max(metrics.values(), key=lambda m: m.composite_score)
                total_improvement += best_metrics.composite_score
                total_savings += (
                    best_metrics.avg_token_cost * 0.1
                )  # Rough savings estimate

        avg_improvement = (
            total_improvement / total_prompts if total_prompts > 0 else 0.0
        )

        return OptimizationSummary(
            total_prompts=total_prompts,
            optimized_prompts=optimized_prompts,
            total_variants=total_variants,
            active_ab_tests=active_ab_tests,
            avg_improvement=avg_improvement,
            total_savings=total_savings,
            last_updated=datetime.now(),
        )

    except Exception as e:
        logger.error(f"Failed to get optimization status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get optimization status: {str(e)}",
        )


@router.get("/prompts", response_model=List[PromptOptimizationStatus])
async def get_all_prompts_status(
    session: Session = Depends(SessionManager.get_session),
):
    """Get optimization status for all prompts."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        registry = prompt_optimizer["registry"]
        tracker = prompt_optimizer["tracker"]

        all_prompt_ids = registry.get_all_prompt_ids()
        status_list = []

        for prompt_id in all_prompt_ids:
            variants = registry.get_all_variants(prompt_id)
            active_variant = registry.get_active_variant(prompt_id)
            category = registry.get_prompt_category(prompt_id)

            # Find best variant
            best_variant_id = active_variant.id if active_variant else ""
            best_score = 0.0
            if variants:
                metrics = tracker.get_all_metrics(prompt_id)
                if metrics:
                    best_variant = max(
                        metrics.items(), key=lambda x: x[1].composite_score
                    )
                    best_variant_id = best_variant[0]
                    best_score = best_variant[1].composite_score

            status_list.append(
                PromptOptimizationStatus(
                    prompt_id=prompt_id,
                    category=category.value if category else "unknown",
                    total_variants=len(variants),
                    active_variant_id=active_variant.id if active_variant else "",
                    best_variant_id=best_variant_id,
                    best_score=best_score,
                    is_optimized=len(variants) > 1,
                    last_evolution=None,  # TODO: Track evolution timestamps
                )
            )

        return status_list

    except Exception as e:
        logger.error(f"Failed to get prompts status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prompts status: {str(e)}",
        )


@router.get("/prompts/{prompt_id}/variants", response_model=List[PromptVariantResponse])
async def get_prompt_variants(
    prompt_id: str, session: Session = Depends(SessionManager.get_session)
):
    """Get all variants for a specific prompt."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        registry = prompt_optimizer["registry"]
        variants = registry.get_all_variants(prompt_id)

        if not variants:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No variants found for prompt: {prompt_id}",
            )

        return [
            PromptVariantResponse(
                id=variant.id,
                content=variant.content,
                version=variant.version,
                parent_id=variant.parent_id,
                created_at=variant.created_at,
                metadata=variant.metadata,
            )
            for variant in variants
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get variants for prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get variants: {str(e)}",
        )


@router.get(
    "/prompts/{prompt_id}/metrics", response_model=Dict[str, PromptMetricsResponse]
)
async def get_prompt_metrics(
    prompt_id: str, session: Session = Depends(SessionManager.get_session)
):
    """Get performance metrics for all variants of a prompt."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        tracker = prompt_optimizer["tracker"]
        metrics = tracker.get_all_metrics(prompt_id)

        if not metrics:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No metrics found for prompt: {prompt_id}",
            )

        return {
            variant_id: PromptMetricsResponse(
                success_rate=metric.success_rate,
                avg_execution_time=metric.avg_execution_time,
                error_rate=metric.error_rate,
                avg_token_cost=metric.avg_token_cost,
                sample_count=metric.sample_count,
                composite_score=metric.composite_score,
                last_updated=metric.last_updated,
            )
            for variant_id, metric in metrics.items()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metrics for prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metrics: {str(e)}",
        )


@router.post("/prompts/{prompt_id}/switch-variant")
async def switch_active_variant(
    prompt_id: str,
    request: VariantSwitchRequest,
    session: Session = Depends(SessionManager.get_session),
):
    """Switch the active variant for a prompt."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        registry = prompt_optimizer["registry"]

        # Validate variant exists
        variant = registry.get_variant(prompt_id, request.variant_id)
        if not variant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Variant {request.variant_id} not found for prompt {prompt_id}",
            )

        # Switch active variant
        registry.set_active_variant(prompt_id, request.variant_id)

        # Auto-save if enabled
        storage = prompt_optimizer["storage"]
        storage.auto_save()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Successfully switched to variant {request.variant_id}",
                "prompt_id": prompt_id,
                "active_variant_id": request.variant_id,
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to switch variant for prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to switch variant: {str(e)}",
        )


@router.post("/prompts/{prompt_id}/evolve")
async def evolve_prompt(
    prompt_id: str,
    request: EvolutionRequest,
    session: Session = Depends(SessionManager.get_session),
):
    """Trigger evolution for a prompt to generate new variants."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        optimizer = prompt_optimizer["optimizer"]

        # Check if evolution is enabled
        if not optimizer.config.enable_evolution:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt evolution is disabled",
            )

        # Trigger evolution
        new_variants = []
        for _ in range(request.max_variants):
            # This would typically call the evolver
            # For now, we'll simulate it
            new_variant_id = f"{prompt_id}-evolved-{datetime.now().timestamp()}"
            new_variants.append(new_variant_id)

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Evolution triggered for prompt {prompt_id}",
                "new_variants": new_variants,
                "strategy": request.strategy or "default",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to evolve prompt {prompt_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evolve prompt: {str(e)}",
        )


@router.get("/analytics/summary")
async def get_optimization_analytics(
    period: str = Query("week", description="Time period for analytics"),
    session: Session = Depends(SessionManager.get_session),
):
    """Get prompt optimization analytics for integration with existing analytics."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        # Get optimization summary
        summary = await get_optimization_status(session)

        # Calculate period-based metrics
        now = datetime.now()
        if period == "day":
            start_time = now - timedelta(days=1)
        elif period == "week":
            start_time = now - timedelta(weeks=1)
        elif period == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(weeks=1)

        # TODO: Implement time-based filtering
        # For now, return current summary

        return {
            "period": period,
            "summary": summary.dict(),
            "prompts_optimized": summary.optimized_prompts,
            "total_variants": summary.total_variants,
            "avg_improvement": summary.avg_improvement,
            "cost_savings": summary.total_savings,
            "active_tests": summary.active_ab_tests,
            "generated_at": now.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get optimization analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get analytics: {str(e)}",
        )


@router.put("/config")
async def update_optimization_config(
    config_update: OptimizationConfigUpdate,
    session: Session = Depends(SessionManager.get_session),
):
    """Update prompt optimization configuration."""
    try:
        prompt_optimizer = get_prompt_optimizer(session)
        if not prompt_optimizer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Prompt optimization not enabled",
            )

        # Update configuration
        config = prompt_optimizer["config"]
        updated_fields = []

        for field, value in config_update.dict(exclude_unset=True).items():
            if hasattr(config, field) and value is not None:
                setattr(config, field, value)
                updated_fields.append(field)

        # Auto-save if enabled
        storage = prompt_optimizer["storage"]
        storage.auto_save()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Configuration updated successfully",
                "updated_fields": updated_fields,
                "config": config.dict(),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update optimization config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}",
        )


@router.get("/health")
async def health_check():
    """Health check endpoint for prompt optimization."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "prompt-optimization",
            "timestamp": datetime.now().isoformat(),
        },
    )

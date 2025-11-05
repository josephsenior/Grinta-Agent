"""
Main ACE Framework - Orchestrates the three-agent system
"""

import time
from typing import Dict, Any, Optional, List
from openhands.core.logger import openhands_logger as logger
from openhands.llm.llm import LLM

from .context_playbook import ContextPlaybook
from .generator import ACEGenerator
from .reflector import ACEReflector
from .curator import ACECurator
from .models import (
    ACEFrameworkResult, ACEGenerationResult, ACEExecutionResult,
    ACEReflectionResult, ACECurationResult, ACEPerformanceMetrics,
    ACETrajectory, ACEConfig
)


class ACEFramework:
    """
    Main ACE Framework that orchestrates Generator, Reflector, and Curator
    Implements the complete self-improvement loop
    """
    
    def __init__(self, llm: LLM, context_playbook: Optional[ContextPlaybook] = None, 
                 config: Optional[ACEConfig] = None):
        self.llm = llm
        self.context_playbook = context_playbook or ContextPlaybook()
        self.config = config or ACEConfig()
        
        # Initialize the three agents
        self.generator = ACEGenerator(self.llm, self.context_playbook)
        self.reflector = ACEReflector(self.llm, self.context_playbook)
        self.curator = ACECurator(self.llm, self.context_playbook)
        
        # Performance metrics
        self.performance_metrics = ACEPerformanceMetrics()
        self.adaptation_history: List[ACEFrameworkResult] = []
        
        logger.info("ACE Framework initialized successfully")
    
    def process_task(self, query: str, task_type: str = 'general', 
                    role: str = None, ground_truth: Any = None,
                    expected_outcome: str = None) -> ACEFrameworkResult:
        """
        Process a task through the complete ACE pipeline
        
        Args:
            query: The task or problem to solve
            task_type: Type of task (appworld, code_generation, metasop, general)
            role: Role for MetaSOP tasks (product_manager, architect, engineer, etc.)
            ground_truth: Ground truth answer for evaluation
            expected_outcome: Expected outcome for MetaSOP tasks
            
        Returns:
            ACEFrameworkResult containing the complete processing result
        """
        start_time = time.time()
        self.performance_metrics.total_tasks += 1
        
        try:
            # 1. Generate initial trajectory
            generation_result = self.generator.generate(
                query=query,
                task_type=task_type,
                role=role
            )
            
            if not generation_result.success:
                return self._create_failed_result(
                    generation_result, None, None, None, 
                    time.time() - start_time, "Generation failed"
                )
            
            # 2. Execute the trajectory (simulated for now)
            execution_result = self._simulate_execution(
                generation_result.trajectory, query, task_type
            )
            
            # 3. Reflect on the performance
            reflection_result = self.reflector.analyze(
                trajectory=generation_result.trajectory,
                execution_result=execution_result,
                ground_truth=ground_truth,
                used_bullet_ids=generation_result.trajectory.used_bullet_ids,
                task_type=task_type,
                role=role,
                max_iterations=self.config.reflector_max_iterations
            )
            
            # 4. Update context playbook based on insights
            curation_result = None
            if reflection_result.success and reflection_result.insights:
                curation_result = self.curator.curate(
                    insights=reflection_result.insights,
                    current_playbook=self.context_playbook,
                    task_context=query,
                    task_type=task_type,
                    role=role,
                    expected_outcome=expected_outcome
                )
                
                if curation_result.success and curation_result.delta_updates:
                    self._apply_delta_updates(curation_result.delta_updates)
                    self.performance_metrics.context_updates += len(curation_result.delta_updates)
            
            # 5. Determine overall success
            overall_success = (
                generation_result.success and 
                execution_result.success and 
                reflection_result.success
            )
            
            if overall_success:
                self.performance_metrics.successful_tasks += 1
            else:
                self.performance_metrics.failed_tasks += 1
            
            # 6. Update performance metrics
            processing_time = time.time() - start_time
            self.performance_metrics.adaptation_latency = processing_time
            self.performance_metrics.playbook_size = len(self.context_playbook.bullets)
            
            # Calculate average helpfulness
            if self.context_playbook.bullets:
                self.performance_metrics.avg_helpfulness = sum(
                    bullet.helpfulness_score for bullet in self.context_playbook.bullets.values()
                ) / len(self.context_playbook.bullets)
            
            # Update token usage and cost
            total_tokens = (
                generation_result.tokens_used + 
                reflection_result.tokens_used + 
                (curation_result.tokens_used if curation_result else 0)
            )
            self.performance_metrics.token_usage += total_tokens
            
            # Estimate cost (rough approximation)
            estimated_cost = total_tokens * 0.0001  # $0.0001 per token
            self.performance_metrics.cost += estimated_cost
            
            # Create result
            result = ACEFrameworkResult(
                generation_result=generation_result,
                execution_result=execution_result,
                reflection_result=reflection_result,
                curation_result=curation_result,
                success=overall_success,
                processing_time=processing_time,
                performance_metrics=self.performance_metrics
            )
            
            # Store in history
            self.adaptation_history.append(result)
            
            logger.info(f"ACE processing completed in {processing_time:.2f}s - Success: {overall_success}")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.performance_metrics.failed_tasks += 1
            logger.error(f"ACE processing failed: {e}")
            
            return self._create_failed_result(
                None, None, None, None, processing_time, str(e)
            )
    
    def process_task_with_feedback(self, query: str, previous_result: ACEFrameworkResult,
                                 task_type: str = 'general', role: str = None) -> ACEFrameworkResult:
        """
        Process a task with feedback from previous attempts
        
        Args:
            query: The task or problem to solve
            previous_result: Result from previous attempt
            task_type: Type of task
            role: Role for MetaSOP tasks
            
        Returns:
            ACEFrameworkResult containing the improved result
        """
        if not previous_result.generation_result:
            return self.process_task(query, task_type, role)
        
        # Use feedback to generate improved trajectory
        improved_generation = self.generator.generate_with_feedback(
            query=query,
            previous_result=previous_result.generation_result,
            task_type=task_type,
            role=role
        )
        
        # Continue with normal processing
        return self.process_task(query, task_type, role)
    
    def multi_epoch_training(self, queries: List[str], task_type: str = 'general',
                           roles: List[str] = None, ground_truths: List[Any] = None) -> List[ACEFrameworkResult]:
        """
        Perform multi-epoch training on a set of queries
        
        Args:
            queries: List of queries to process
            task_type: Type of tasks
            roles: List of roles for MetaSOP tasks
            ground_truths: List of ground truth answers
            
        Returns:
            List of ACEFrameworkResult for each epoch
        """
        if not self.config.multi_epoch:
            logger.warning("Multi-epoch training is disabled")
            return []
        
        if roles is None:
            roles = [None] * len(queries)
        if ground_truths is None:
            ground_truths = [None] * len(queries)
        
        all_results = []
        
        for epoch in range(self.config.num_epochs):
            logger.info(f"Starting epoch {epoch + 1}/{self.config.num_epochs}")
            epoch_results = []
            
            for i, (query, role, ground_truth) in enumerate(zip(queries, roles, ground_truths)):
                result = self.process_task(
                    query=query,
                    task_type=task_type,
                    role=role,
                    ground_truth=ground_truth
                )
                epoch_results.append(result)
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(f"Epoch {epoch + 1}: Processed {i + 1}/{len(queries)} queries")
            
            all_results.extend(epoch_results)
            
            # Apply grow-and-refine after each epoch
            if self.context_playbook.enable_grow_and_refine:
                refinement_stats = self.context_playbook.grow_and_refine()
                logger.info(f"Epoch {epoch + 1} refinement: {refinement_stats}")
        
        logger.info(f"Multi-epoch training completed: {len(all_results)} total results")
        return all_results
    
    def _simulate_execution(self, trajectory: ACETrajectory, query: str, 
                          task_type: str) -> ACEExecutionResult:
        """
        Simulate execution of the trajectory
        In real implementation, this would execute the generated code/solution
        """
        # This is a placeholder - in real implementation, this would:
        # 1. Parse the trajectory for code
        # 2. Execute the code
        # 3. Capture results and errors
        # 4. Return execution metadata
        
        # Simulate execution time
        execution_time = 0.5 + (len(trajectory.content) / 1000) * 0.1
        
        # Simulate success/failure based on content quality
        success = len(trajectory.content) > 50 and "error" not in trajectory.content.lower()
        
        return ACEExecutionResult(
            success=success,
            output=f"Simulated execution of {task_type} task: {query[:50]}...",
            error=None if success else "Simulated execution error",
            execution_time=execution_time,
            tokens_used=len(trajectory.content.split()),
            cost=execution_time * 0.01,
            metadata={
                'task_type': task_type,
                'trajectory_length': len(trajectory.content),
                'simulated': True
            }
        )
    
    def _apply_delta_updates(self, delta_updates: List):
        """Apply delta updates to the context playbook"""
        for update in delta_updates:
            try:
                if update.type == 'ADD':
                    self.context_playbook.add_bullet(
                        content=update.content,
                        section=update.section,
                        tags=update.tags
                    )
                elif update.type == 'UPDATE':
                    self.context_playbook.update_bullet(
                        bullet_id=update.bullet_id,
                        content=update.content,
                        helpful=update.helpful,
                        harmful=update.harmful
                    )
                elif update.type == 'REMOVE':
                    self.context_playbook.remove_bullet(update.bullet_id)
            except Exception as e:
                logger.warning(f"Failed to apply delta update: {e}")
    
    def _create_failed_result(self, generation_result, execution_result, 
                            reflection_result, curation_result, 
                            processing_time: float, error: str) -> ACEFrameworkResult:
        """Create a failed result with error information"""
        return ACEFrameworkResult(
            generation_result=generation_result,
            execution_result=execution_result,
            reflection_result=reflection_result,
            curation_result=curation_result,
            success=False,
            processing_time=processing_time,
            performance_metrics=self.performance_metrics
        )
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        return {
            'framework_metrics': self.performance_metrics.dict(),
            'generator_metrics': self.generator.get_metrics(),
            'reflector_metrics': self.reflector.get_metrics(),
            'curator_metrics': self.curator.get_metrics(),
            'playbook_statistics': self.context_playbook.get_statistics(),
            'adaptation_history_length': len(self.adaptation_history),
            'config': self.config.dict() if self.config else {}
        }
    
    def save_playbook(self, filepath: str) -> bool:
        """Save the current playbook to disk"""
        try:
            import json
            with open(filepath, 'w') as f:
                json.dump(self.context_playbook.export_playbook(), f, indent=2)
            logger.info(f"Playbook saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save playbook: {e}")
            return False
    
    def load_playbook(self, filepath: str) -> bool:
        """Load a playbook from disk"""
        try:
            import json
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.context_playbook.import_playbook(data)
            logger.info(f"Playbook loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to load playbook: {e}")
            return False
    
    def reset_metrics(self):
        """Reset all performance metrics"""
        self.performance_metrics = ACEPerformanceMetrics()
        self.adaptation_history.clear()
        logger.info("ACE Framework metrics reset")

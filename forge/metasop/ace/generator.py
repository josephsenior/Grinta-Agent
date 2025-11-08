"""ACE Generator - Produces reasoning trajectories using context playbook."""

import json
import time
from typing import Any, Dict, List, Optional, Tuple
from forge.core.logger import forge_logger as logger
from forge.llm.llm import LLM

from .context_playbook import ContextPlaybook, BulletSection
from .models import ACETrajectory, ACEGenerationResult


class ACEGenerator:
    """Generate reasoning trajectories using the context playbook.

    Leverages accumulated knowledge for better solutions.
    """
    
    def __init__(self, llm: LLM, context_playbook: ContextPlaybook):
        """Store dependencies and preload generation prompts and counters."""
        self.llm = llm
        self.context_playbook = context_playbook
        self.generation_prompts = self._load_generation_prompts()
        self.generation_metrics = {
            'total_generations': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'total_tokens': 0,
            'total_time': 0.0
        }
    
    def _load_generation_prompts(self) -> Dict[str, str]:
        """Load generation prompts for different task types."""
        return {
            'appworld': """
You are a super intelligent AI Assistant whose job is to achieve tasks completely autonomously.
You will be given a curated playbook of strategies, patterns, and examples to help you solve the current task.

ACE Playbook:
{playbook_content}

Task: {task}

Instructions:
1. Read the Playbook first, then execute the task by explicitly leveraging each relevant section
2. Use only the parts that are relevant and applicable to your specific situation
3. Show your reasoning step-by-step
4. Apply strategies from the playbook when applicable
5. If the playbook contains relevant code snippets or formulas, use them appropriately
6. Double-check your calculations and logic before providing the final answer

Generate your solution:
""",
            'code_generation': """
You are an expert code generator with access to a comprehensive playbook of strategies and insights.

ACE Playbook:
{playbook_content}

Task: {task}

Instructions:
1. Analyze the task using relevant playbook strategies
2. Generate clean, efficient code following playbook guidelines
3. Apply domain-specific insights from the playbook
4. Show your reasoning process
5. Use code patterns and debugging tips from the playbook
6. Ensure your code follows best practices mentioned in the playbook

Generate your code solution:
""",
            'metasop': """
You are an expert {role} working on a software development task. You have access to a comprehensive playbook of strategies and insights.

ACE Playbook:
{playbook_content}

Task: {task}

Instructions:
1. Use relevant strategies from the playbook for your role
2. Apply domain-specific insights and patterns
3. Follow verification checklists from the playbook
4. Avoid common mistakes listed in the playbook
5. Show your reasoning step-by-step
6. Leverage tools and utilities mentioned in the playbook

Generate your solution:
""",
            'general': """
You are an expert problem solver with access to a comprehensive knowledge base.

ACE Playbook:
{playbook_content}

Task: {task}

Instructions:
1. Use relevant strategies from the playbook
2. Apply domain-specific insights
3. Show your reasoning step-by-step
4. Leverage proven approaches from the playbook
5. Follow verification steps if applicable
6. Avoid common pitfalls mentioned in the playbook

Generate your solution:
"""
        }
    
    def generate(self, query: str, task_type: str = 'general', 
                role: Optional[str] = None, max_retries: int = 3) -> ACEGenerationResult:
        """Generate a reasoning trajectory for the given query.
        
        Args:
            query: The task or problem to solve
            task_type: Type of task (appworld, code_generation, metasop, general)
            role: Role for MetaSOP tasks (product_manager, architect, engineer, etc.)
            max_retries: Maximum number of retry attempts
            
        Returns:
            ACEGenerationResult containing the generated trajectory and metadata

        """
        start_time = time.time()
        self.generation_metrics['total_generations'] += 1
        
        try:
            # Get relevant context from playbook
            relevant_bullets = self.context_playbook.get_relevant_bullets(
                query, limit=20
            )
            
            # Format playbook content
            playbook_content = self._format_playbook_content(relevant_bullets)
            
            # Get generation prompt
            prompt_template = self.generation_prompts.get(task_type, self.generation_prompts['general'])
            
            # Format prompt with role if provided
            if role and task_type == 'metasop':
                prompt = prompt_template.format(
                    playbook_content=playbook_content,
                    task=query,
                    role=role
                )
            else:
                prompt = prompt_template.format(
                    playbook_content=playbook_content,
                    task=query
                )
            
            # Generate response with retry logic
            trajectory_content, token_usage = self._generate_with_retries(prompt, max_retries)
            
            # Track which bullets were used
            used_bullet_ids = [bullet.id for bullet in relevant_bullets]
            
            # Create trajectory object
            trajectory = ACETrajectory(
                content=trajectory_content,
                task_type=task_type,
                used_bullet_ids=used_bullet_ids,
                playbook_content=playbook_content,
                generation_metadata={
                    'num_bullets_used': len(used_bullet_ids),
                    'prompt_length': len(prompt),
                    'response_length': len(trajectory_content),
                    'role': role
                }
            )
            
            # Update metrics
            processing_time = time.time() - start_time
            self.generation_metrics['successful_generations'] += 1
            self.generation_metrics['total_time'] += processing_time
            
            # Token usage
            self.generation_metrics['total_tokens'] += token_usage
            
            logger.debug(f"Generated trajectory for {task_type} task in {processing_time:.2f}s")
            
            return ACEGenerationResult(
                trajectory=trajectory,
                success=True,
                processing_time=processing_time,
                tokens_used=token_usage,
                retries=0
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.generation_metrics['failed_generations'] += 1
            logger.error(f"Generation failed: {e}")
            
            return ACEGenerationResult(
                trajectory=ACETrajectory(
                    content="",
                    task_type=task_type,
                    used_bullet_ids=[],
                    playbook_content="",
                    generation_metadata={'error': str(e)}
                ),
                success=False,
                processing_time=processing_time,
                tokens_used=0,
                retries=max_retries
            )
    
    def generate_with_feedback(self, query: str, previous_result: ACEGenerationResult, 
                             task_type: str = 'general', role: Optional[str] = None) -> ACEGenerationResult:
        """Generate improved trajectory using feedback from previous attempts.
        
        Args:
            query: The task or problem to solve
            previous_result: Result from previous attempt
            task_type: Type of task
            role: Role for MetaSOP tasks
            
        Returns:
            ACEGenerationResult containing the improved trajectory

        """
        # Get bullets that were marked as helpful/harmful
        helpful_bullets = []
        harmful_bullets = []
        
        for bullet_id in previous_result.trajectory.used_bullet_ids:
            bullet = self.context_playbook.bullets.get(bullet_id)
            if bullet:
                if bullet.helpful_count > bullet.harmful_count:
                    helpful_bullets.append(bullet)
                elif bullet.harmful_count > bullet.helpful_count:
                    harmful_bullets.append(bullet)
        
        # Create feedback-aware prompt
        feedback_prompt = self._create_feedback_prompt(
            query, helpful_bullets, harmful_bullets, task_type, role
        )
        
        # Generate improved response
        start_time = time.time()
        try:
            trajectory_content, token_usage = self._generate_with_retries(feedback_prompt, max_retries=3)
            
            # Create improved trajectory
            trajectory = ACETrajectory(
                content=trajectory_content,
                task_type=task_type,
                used_bullet_ids=[b.id for b in helpful_bullets],
                playbook_content=self._format_playbook_content(helpful_bullets),
                generation_metadata={
                    'feedback_incorporated': True,
                    'helpful_bullets': len(helpful_bullets),
                    'harmful_bullets_avoided': len(harmful_bullets),
                    'role': role
                }
            )
            
            processing_time = time.time() - start_time
            return ACEGenerationResult(
                trajectory=trajectory,
                success=True,
                processing_time=processing_time,
                tokens_used=token_usage,
                retries=0
            )
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            return ACEGenerationResult(
                trajectory=ACETrajectory(
                    content="",
                    task_type=task_type,
                    used_bullet_ids=[],
                    playbook_content="",
                    generation_metadata={'error': str(e)}
                ),
                success=False,
                processing_time=time.time() - start_time,
                tokens_used=0,
                retries=3
            )
    
    def _format_playbook_content(self, bullets: List) -> str:
        """Format bullet points for LLM consumption."""
        if not bullets:
            return "No relevant strategies found in playbook."
        
        content = "RELEVANT STRATEGIES FROM PLAYBOOK:\n"
        content += "=" * 50 + "\n\n"
        
        for bullet in bullets:
            content += f"[{bullet.id}] helpful={bullet.helpful_count} harmful={bullet.harmful_count} :: {bullet.content}\n"
        
        return content
    
    def _generate_with_retries(self, prompt: str, max_retries: int) -> Tuple[str, int]:
        """Generate response with retry logic."""
        for attempt in range(max_retries):
            try:
                response = self.llm.completion(
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_completion_tokens=4000,
                )
                text = self._extract_response_text(response)
                tokens_used = self._extract_total_tokens(response, prompt, text)
                return text, tokens_used
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                logger.warning(f"Generation attempt {attempt + 1} failed: {e}")
                time.sleep(0.5 * (attempt + 1))  # Exponential backoff
                continue
        
        raise Exception("All generation attempts failed")

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        """Extract assistant text content from completion response."""
        choices = getattr(response, "choices", None)
        if not choices:
            return ""
        message = getattr(choices[0], "message", None)
        if message is None:
            return ""
        content = getattr(message, "content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, dict):
                    text_part = item.get("text")
                    if isinstance(text_part, str):
                        parts.append(text_part)
                elif isinstance(item, str):
                    parts.append(item)
            return "".join(parts)
        return str(content)

    @staticmethod
    def _extract_total_tokens(response: Any, prompt: str, text: str) -> int:
        """Extract total token usage from response with fallback estimation."""
        usage = getattr(response, "usage", None)
        if usage is not None:
            total = getattr(usage, "total_tokens", None)
            if total is None and isinstance(usage, dict):
                total = usage.get("total_tokens")
            if isinstance(total, int):
                return total
        # Fallback rough estimate
        return len(prompt.split()) + len(text.split())
    
    def _create_feedback_prompt(self, query: str, helpful_bullets: List, 
                               harmful_bullets: List, task_type: str, role: Optional[str] = None) -> str:
        """Create prompt that incorporates feedback from previous attempts."""
        base_prompt = self.generation_prompts.get(task_type, self.generation_prompts['general'])
        
        # Add helpful strategies
        helpful_content = ""
        if helpful_bullets:
            helpful_content = "\n\nHELPFUL STRATEGIES (use these):\n"
            for bullet in helpful_bullets:
                helpful_content += f"[{bullet.id}] {bullet.content}\n"
        
        # Add harmful strategies to avoid
        harmful_content = ""
        if harmful_bullets:
            harmful_content = "\n\nSTRATEGIES TO AVOID (these didn't work well):\n"
            for bullet in harmful_bullets:
                harmful_content += f"[{bullet.id}] {bullet.content}\n"
        
        playbook_content = helpful_content + harmful_content
        
        if role and task_type == 'metasop':
            prompt = base_prompt.format(
                playbook_content=playbook_content,
                task=query,
                role=role
            )
        else:
            prompt = base_prompt.format(
                playbook_content=playbook_content,
                task=query
            )
        
        return prompt
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get generation metrics."""
        total = self.generation_metrics['total_generations']
        if total == 0:
            return self.generation_metrics
        
        return {
            **self.generation_metrics,
            'success_rate': self.generation_metrics['successful_generations'] / total,
            'failure_rate': self.generation_metrics['failed_generations'] / total,
            'avg_processing_time': self.generation_metrics['total_time'] / total,
            'avg_tokens_per_generation': self.generation_metrics['total_tokens'] / total
        }

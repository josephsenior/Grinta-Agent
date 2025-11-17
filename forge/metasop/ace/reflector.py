"""ACE Reflector - Analyzes performance and extracts insights."""

import json
import time
from typing import Any, Dict, List, Optional, Union
from forge.core.logger import forge_logger as logger
from forge.llm.llm import LLM

from .context_playbook import ContextPlaybook
from .models import ACEInsight, ACEReflectionResult, ACETrajectory, ACEExecutionResult


class ACEReflector:
    """Analyze performance and extract insights from execution results.

    Supports iterative refinement for deep reasoning.
    """

    def __init__(self, llm: LLM, context_playbook: ContextPlaybook):
        """Initialize reflection prompts, metrics, and shared dependencies."""
        self.llm = llm
        self.context_playbook = context_playbook
        self.reflection_prompts = self._load_reflection_prompts()
        self.reflection_metrics = {
            "total_reflections": 0,
            "successful_reflections": 0,
            "failed_reflections": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "iterative_refinements": 0,
        }

    def _load_reflection_prompts(self) -> Dict[str, str]:
        """Load reflection prompts for different task types."""
        return {
            "appworld": """
You are an expert AppWorld coding agent and educator. Your job is to diagnose the current trajectory: identify what went wrong (or could be better), grounded in execution feedback, API usage, unit test report, and ground truth when applicable.

Instructions:
- Carefully analyze the model's reasoning trace to identify where it went wrong
- Take the environment feedback into account, comparing the predicted answer with the ground truth to understand the gap
- Identify specific conceptual errors, calculation mistakes, or misapplied strategies
- Provide actionable insights that could help the model avoid this mistake in the future
- Identify root causes: wrong source of truth, bad filters (timeframe/direction/identity), formatting issues, or missing authentication and how to correct them
- Provide concrete, step-by-step corrections the model should take in this task
- Be specific about what the model should have done differently
- You will receive bulletpoints that are part of playbook that's used by the generator to answer the question
- You need to analyze these bulletpoints, and give the tag for each bulletpoint, tag can be ['helpful', 'harmful', 'neutral'] (for the generator to generate the correct answer)
- Explicitly curate from the environment feedback the output format/schema of APIs used when unclear or mismatched with expectations

Inputs:
Ground truth code (reference, known-correct):
GROUND_TRUTH_CODE_START
{ground_truth_code}
GROUND_TRUTH_CODE_END

Test report (unit tests result for the task after the generated code was run):
TEST_REPORT_START
{test_report}
TEST_REPORT_END

ACE playbook (playbook that's used by model for code generation):
PLAYBOOK_START
{playbook_content}
PLAYBOOK_END

Generated Trajectory:
TRAJECTORY_START
{trajectory}
TRAJECTORY_END

Execution Result:
EXECUTION_START
{execution_result}
EXECUTION_END

Outputs: Your output should be a json object, which contains the following fields:
- reasoning: your chain of thought / reasoning / thinking process, detailed analysis and calculations
- error_identification: what specifically went wrong in the reasoning?
- root_cause_analysis: why did this error occur? What concept was misunderstood?
- correct_approach: what should the model have done instead?
- key_insight: what strategy, formula, or principle should be remembered to avoid this error?
- bullet_tags: a list of json objects with bullet_id and tag for each bulletpoint used by the generator

Answer in this exact JSON format:
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process, detailed analysis and calculations]",
    "error_identification": "[What specifically went wrong in the reasoning?]",
    "root_cause_analysis": "[Why did this error occur? What concept was misunderstood?]",
    "correct_approach": "[What should the model have done instead?]",
    "key_insight": "[What strategy, formula, or principle should be remembered to avoid this error?]",
    "bullet_tags": [
        {{"id": "ctx-00001", "tag": "helpful"}},
        {{"id": "ctx-00002", "tag": "harmful"}}
    ]
}}
""",
            "metasop": """
You are an expert software development analyst and educator. Your job is to diagnose the current step execution: identify what went wrong (or could be better), grounded in execution feedback, step traces, and expected outcomes.

Instructions:
- Carefully analyze the step execution to identify where it went wrong
- Take the execution feedback into account, comparing the actual result with the expected outcome
- Identify specific conceptual errors, implementation mistakes, or misapplied strategies
- Provide actionable insights that could help the agent avoid this mistake in the future
- Focus on role-specific issues (e.g., architect design problems, engineer implementation issues, QA testing gaps)
- Provide concrete, step-by-step corrections the agent should take
- Be specific about what the agent should have done differently
- Analyze which playbook bullets were helpful, harmful, or neutral for this specific task
- Extract key insights that should be added to the playbook

Inputs:
Step Information:
- Role: {role}
- Task: {task}
- Expected Outcome: {expected_outcome}

Generated Trajectory:
TRAJECTORY_START
{trajectory}
TRAJECTORY_END

Execution Result:
EXECUTION_START
{execution_result}
EXECUTION_END

ACE playbook (playbook that's used by model for step execution):
PLAYBOOK_START
{playbook_content}
PLAYBOOK_END

Outputs: Your output should be a json object, which contains the following fields:
- reasoning: your chain of thought / reasoning / thinking process, detailed analysis
- error_identification: what specifically went wrong in the step execution?
- root_cause_analysis: why did this error occur? What concept was misunderstood?
- correct_approach: what should the agent have done instead?
- key_insight: what strategy, formula, or principle should be remembered to avoid this error?
- bullet_tags: a list of json objects with bullet_id and tag for each bulletpoint used

Answer in this exact JSON format:
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process, detailed analysis]",
    "error_identification": "[What specifically went wrong in the step execution?]",
    "root_cause_analysis": "[Why did this error occur? What concept was misunderstood?]",
    "correct_approach": "[What should the agent have done instead?]",
    "key_insight": "[What strategy, formula, or principle should be remembered to avoid this error?]",
    "bullet_tags": [
        {{"id": "ctx-00001", "tag": "helpful"}},
        {{"id": "ctx-00002", "tag": "harmful"}}
    ]
}}
""",
            "general": """
You are an expert analyst and educator. Your job is to diagnose the current execution: identify what went wrong (or could be better), grounded in execution feedback and results.

Instructions:
- Carefully analyze the execution to identify where it went wrong
- Take the execution feedback into account, comparing the actual result with expectations
- Identify specific conceptual errors, implementation mistakes, or misapplied strategies
- Provide actionable insights that could help avoid this mistake in the future
- Focus on the root cause, not just surface-level errors
- Be specific about what should have been done differently
- Analyze which playbook bullets were helpful, harmful, or neutral for this specific task

Inputs:
Generated Trajectory:
TRAJECTORY_START
{trajectory}
TRAJECTORY_END

Execution Result:
EXECUTION_START
{execution_result}
EXECUTION_END

ACE playbook (playbook that's used by model):
PLAYBOOK_START
{playbook_content}
PLAYBOOK_END

Outputs: Your output should be a json object, which contains the following fields:
- reasoning: your chain of thought / reasoning / thinking process, detailed analysis
- error_identification: what specifically went wrong in the execution?
- root_cause_analysis: why did this error occur? What concept was misunderstood?
- correct_approach: what should have been done instead?
- key_insight: what strategy, formula, or principle should be remembered to avoid this error?
- bullet_tags: a list of json objects with bullet_id and tag for each bulletpoint used

Answer in this exact JSON format:
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process, detailed analysis]",
    "error_identification": "[What specifically went wrong in the execution?]",
    "root_cause_analysis": "[Why did this error occur? What concept was misunderstood?]",
    "correct_approach": "[What should have been done instead?]",
    "key_insight": "[What strategy, formula, or principle should be remembered to avoid this error?]",
    "bullet_tags": [
        {{"id": "ctx-00001", "tag": "helpful"}},
        {{"id": "ctx-00002", "tag": "harmful"}}
    ]
}}
""",
        }

    def analyze(
        self,
        trajectory: ACETrajectory,
        execution_result: ACEExecutionResult,
        ground_truth: Optional[Any] = None,
        used_bullet_ids: Optional[List[str]] = None,
        task_type: str = "general",
        role: Optional[str] = None,
        max_iterations: int = 5,
    ) -> ACEReflectionResult:
        """Analyze execution and extract insights.

        Args:
            trajectory: Generated trajectory
            execution_result: Result of execution
            ground_truth: Ground truth answer (optional)
            used_bullet_ids: List of bullet IDs used in generation
            task_type: Type of task (appworld, metasop, general)
            role: Role for MetaSOP tasks
            max_iterations: Maximum number of reflection iterations

        Returns:
            ACEReflectionResult containing insights and analysis

        """
        start_time = time.time()
        self.reflection_metrics["total_reflections"] += 1

        try:
            # Get playbook content for used bullets
            playbook_content = self._get_playbook_content_for_bullets(
                used_bullet_ids or []
            )

            # Perform iterative reflection
            insights = []
            for iteration in range(max_iterations):
                insight = self._perform_reflection_iteration(
                    trajectory,
                    execution_result,
                    ground_truth,
                    playbook_content,
                    task_type,
                    role,
                    iteration,
                )

                if insight:
                    insights.append(insight)

                    # Check if we should continue iterating
                    if not self._should_continue_iteration(
                        insight, iteration, max_iterations
                    ):
                        break

                    # Update playbook content for next iteration
                    playbook_content = self._update_playbook_content_for_iteration(
                        playbook_content, insight
                    )

                    self.reflection_metrics["iterative_refinements"] += 1

            # Determine overall success and confidence
            success = len(insights) > 0
            confidence = self._calculate_overall_confidence(insights)

            # Update bullet tags based on insights
            self._update_bullet_tags(insights)

            processing_time = time.time() - start_time
            self.reflection_metrics["successful_reflections"] += 1
            self.reflection_metrics["total_time"] += processing_time

            # Estimate token usage
            estimated_tokens = self._estimate_token_usage(
                trajectory, execution_result, playbook_content
            )
            self.reflection_metrics["total_tokens"] += estimated_tokens

            logger.debug(
                f"Reflection completed with {len(insights)} insights in {processing_time:.2f}s"
            )

            return ACEReflectionResult(
                insights=insights,
                success=success,
                confidence=confidence,
                processing_time=processing_time,
                tokens_used=estimated_tokens,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.reflection_metrics["failed_reflections"] += 1
            logger.error(f"Reflection failed: {e}")

            return ACEReflectionResult(
                insights=[],
                success=False,
                confidence=0.0,
                processing_time=processing_time,
                tokens_used=0,
            )

    def _perform_reflection_iteration(
        self,
        trajectory: ACETrajectory,
        execution_result: ACEExecutionResult,
        ground_truth: Optional[Any],
        playbook_content: str,
        task_type: str,
        role: Optional[str],
        iteration: int,
    ) -> Optional[ACEInsight]:
        """Perform a single reflection iteration."""
        try:
            # Get reflection prompt
            prompt_template = self.reflection_prompts.get(
                task_type, self.reflection_prompts["general"]
            )

            # Format prompt based on task type
            if task_type == "appworld":
                prompt = prompt_template.format(
                    ground_truth_code=ground_truth or "Not provided",
                    test_report=execution_result.metadata.get(
                        "test_report", "Not available"
                    ),
                    playbook_content=playbook_content,
                    trajectory=trajectory.content,
                    execution_result=execution_result.output,
                )
            elif task_type == "metasop":
                prompt = prompt_template.format(
                    role=role or "unknown",
                    task=trajectory.generation_metadata.get("task", "Unknown task"),
                    expected_outcome=execution_result.metadata.get(
                        "expected_outcome", "Not specified"
                    ),
                    playbook_content=playbook_content,
                    trajectory=trajectory.content,
                    execution_result=execution_result.output,
                )
            else:
                prompt = prompt_template.format(
                    playbook_content=playbook_content,
                    trajectory=trajectory.content,
                    execution_result=execution_result.output,
                )

            # Generate reflection
            response = self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_completion_tokens=2000,
            )
            response_text = self._extract_response_text(response)

            # Parse JSON response
            try:
                reflection_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    reflection_data = json.loads(response_text[json_start:json_end])
                else:
                    logger.warning("Could not parse reflection JSON response")
                    return None

            # Create insight object
            insight = ACEInsight(
                reasoning=reflection_data.get("reasoning", ""),
                error_identification=reflection_data.get("error_identification", ""),
                root_cause_analysis=reflection_data.get("root_cause_analysis", ""),
                correct_approach=reflection_data.get("correct_approach", ""),
                key_insight=reflection_data.get("key_insight", ""),
                bullet_tags=reflection_data.get("bullet_tags", []),
                success=execution_result.success,
                confidence=self._calculate_insight_confidence(reflection_data),
            )

            return insight

        except Exception as e:
            logger.warning(f"Reflection iteration {iteration} failed: {e}")
            return None

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

    def _get_playbook_content_for_bullets(self, bullet_ids: List[str]) -> str:
        """Get playbook content for specific bullet IDs."""
        if not bullet_ids:
            return "No playbook content available."

        bullets = []
        for bullet_id in bullet_ids:
            bullet = self.context_playbook.bullets.get(bullet_id)
            if bullet:
                bullets.append(bullet)

        if not bullets:
            return "No playbook content available."

        content = "ACE PLAYBOOK (Used Bullets):\n"
        content += "=" * 50 + "\n\n"

        for bullet in bullets:
            content += f"[{bullet.id}] helpful={bullet.helpful_count} harmful={bullet.harmful_count} :: {bullet.content}\n"

        return content

    def _update_playbook_content_for_iteration(
        self, playbook_content: str, insight: ACEInsight
    ) -> str:
        """Update playbook content for next iteration based on insight."""
        # Add the key insight to the playbook content for next iteration
        if insight.key_insight:
            playbook_content += (
                f"\n\nNEW INSIGHT FROM ITERATION:\n{insight.key_insight}\n"
            )

        return playbook_content

    def _should_continue_iteration(
        self, insight: ACEInsight, iteration: int, max_iterations: int
    ) -> bool:
        """Determine if reflection should continue iterating."""
        # Stop if we've reached max iterations
        if iteration >= max_iterations - 1:
            return False

        # Stop if confidence is high and we have a clear insight
        if insight.confidence > 0.8 and insight.key_insight:
            return False

        # Stop if this is the first iteration and we have a good insight
        if iteration == 0 and insight.confidence > 0.6:
            return False

        return True

    def _calculate_insight_confidence(self, reflection_data: Dict[str, Any]) -> float:
        """Calculate confidence score for an insight."""
        confidence = 0.0

        # Base confidence on completeness of analysis
        if reflection_data.get("reasoning"):
            confidence += 0.2
        if reflection_data.get("error_identification"):
            confidence += 0.2
        if reflection_data.get("root_cause_analysis"):
            confidence += 0.2
        if reflection_data.get("correct_approach"):
            confidence += 0.2
        if reflection_data.get("key_insight"):
            confidence += 0.2

        return min(confidence, 1.0)

    def _calculate_overall_confidence(self, insights: List[ACEInsight]) -> float:
        """Calculate overall confidence from multiple insights."""
        if not insights:
            return 0.0

        return sum(insight.confidence for insight in insights) / len(insights)

    def _update_bullet_tags(self, insights: List[ACEInsight]):
        """Update bullet tags based on insights."""
        for insight in insights:
            for bullet_tag in insight.bullet_tags:
                bullet_id = bullet_tag.get("id")
                tag = bullet_tag.get("tag")

                if bullet_id and tag in ["helpful", "harmful"]:
                    self.context_playbook.update_bullet(
                        bullet_id=bullet_id,
                        helpful=(tag == "helpful"),
                        harmful=(tag == "harmful"),
                    )

    def _estimate_token_usage(
        self,
        trajectory: ACETrajectory,
        execution_result: ACEExecutionResult,
        playbook_content: str,
    ) -> int:
        """Estimate token usage for reflection."""
        # Rough approximation based on content length
        total_content = trajectory.content + execution_result.output + playbook_content
        return len(total_content.split())

    def get_metrics(self) -> Dict[str, Any]:
        """Get reflection metrics."""
        total = self.reflection_metrics["total_reflections"]
        if total == 0:
            return self.reflection_metrics

        return {
            **self.reflection_metrics,
            "success_rate": self.reflection_metrics["successful_reflections"] / total,
            "failure_rate": self.reflection_metrics["failed_reflections"] / total,
            "avg_processing_time": self.reflection_metrics["total_time"] / total,
            "avg_tokens_per_reflection": self.reflection_metrics["total_tokens"]
            / total,
            "avg_iterations_per_reflection": self.reflection_metrics[
                "iterative_refinements"
            ]
            / total,
        }

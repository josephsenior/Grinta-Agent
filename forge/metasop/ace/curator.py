"""ACE Curator - Synthesizes insights into context updates."""

import json
import time
from typing import Any, Dict, List, Optional
from forge.core.logger import forge_logger as logger
from forge.llm.llm import LLM

from .context_playbook import ContextPlaybook, BulletSection
from .models import ACEInsight, ACEDeltaUpdate, ACECurationResult


class ACECurator:
    """Synthesizes insights from Reflector into structured context updates.

    Maintains grow-and-refine balance and prevents redundancy.
    """

    def __init__(self, llm: LLM, context_playbook: ContextPlaybook):
        """Store dependencies and prime prompt templates and metrics."""
        self.llm = llm
        self.context_playbook = context_playbook
        self.curation_prompts = self._load_curation_prompts()
        self.curation_metrics = {
            "total_curations": 0,
            "successful_curations": 0,
            "failed_curations": 0,
            "total_tokens": 0,
            "total_time": 0.0,
            "delta_updates_generated": 0,
            "redundancy_removed": 0,
        }

    def _load_curation_prompts(self) -> Dict[str, str]:
        """Load curation prompts for different task types."""
        return {
            "appworld": """
You are a master curator of knowledge. Your job is to identify what new insights should be added to an existing playbook based on a reflection from a previous attempt.

Context:
- The playbook you created will be used to help answering similar questions
- The reflection is generated using ground truth answers that will NOT be available when the playbook is being used
- So you need to come up with content that can aid the playbook user to create predictions that likely align with ground truth

Instructions:
- Review the existing playbook and the reflection from the previous attempt
- Identify ONLY the NEW insights, strategies, or mistakes that are MISSING from the current playbook
- Avoid redundancy - if similar advice already exists, only add new content that is a perfect complement to the existing playbook
- Do NOT regenerate the entire playbook - only provide the additions needed
- Focus on quality over quantity - a focused, well-organized playbook is better than an exhaustive one
- Format your response as a PURE JSON object with specific sections
- For any operation if no new content to add, return an empty list for the operations field
- Be concise and specific - each addition should be actionable
- For coding tasks, explicitly curate from the reflections the output format/schema of APIs used when unclear or mismatched with expectations

Task Context (the actual task instruction):
{question_context}

Current Playbook:
{current_playbook}

Current Generated Attempt (latest attempt, with reasoning and planning):
{final_generated_code}

Current Reflections (principles and strategies that helped to achieve current task):
{guidebook}

Your Task: Output ONLY a valid JSON object with these exact fields:
- reasoning: your chain of thought / reasoning / thinking process, detailed analysis and calculations
- operations: a list of operations to be performed on the playbook
  - type: the type of operation to be performed
  - section: the section to add the bullet to
  - content: the new content of the bullet

Available Operations:
1. ADD: Create new bullet points with fresh IDs
  - section: the section to add the new bullet to
  - content: the new content of the bullet. Note: no need to include the bullet_id in the content like '[ctx-00263] helpful=1 harmful=0 ::', the bullet_id will be added by the system.

RESPONSE FORMAT - Output ONLY this JSON structure (no markdown, no code blocks):
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process, detailed analysis and calculations here]",
    "operations": [
        {{
            "type": "ADD",
            "section": "strategies_and_hard_rules",
            "content": "[New strategy or rule...]"
        }}
    ]
}}
""",
            "metasop": """
You are a master curator of knowledge for software development workflows. Your job is to identify what new insights should be added to an existing playbook based on a reflection from a previous step execution.

Context:
- The playbook will be used to help similar software development tasks
- The reflection is generated using execution feedback that may not be available in future tasks
- Focus on actionable insights that can guide future development work

Instructions:
- Review the existing playbook and the reflection from the previous attempt
- Identify ONLY the NEW insights, strategies, or patterns that are MISSING from the current playbook
- Avoid redundancy - if similar advice already exists, only add new content that complements existing knowledge
- Focus on role-specific insights (architect, engineer, QA, etc.)
- Do NOT regenerate the entire playbook - only provide the additions needed
- Be concise and specific - each addition should be actionable
- Format your response as a PURE JSON object

Task Context:
- Role: {role}
- Task: {task}
- Expected Outcome: {expected_outcome}

Current Playbook:
{current_playbook}

Generated Attempt:
{generated_attempt}

Reflection Insights:
{reflection_insights}

Your Task: Output ONLY a valid JSON object with these exact fields:
- reasoning: your chain of thought / reasoning / thinking process
- operations: a list of operations to be performed on the playbook

RESPONSE FORMAT - Output ONLY this JSON structure:
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process here]",
    "operations": [
        {{
            "type": "ADD",
            "section": "strategies_and_hard_rules",
            "content": "[New strategy or rule...]"
        }}
    ]
}}
""",
            "general": """
You are a master curator of knowledge. Your job is to identify what new insights should be added to an existing playbook based on a reflection from a previous attempt.

Instructions:
- Review the existing playbook and the reflection from the previous attempt
- Identify ONLY the NEW insights, strategies, or patterns that are MISSING from the current playbook
- Avoid redundancy - if similar advice already exists, only add new content that complements existing knowledge
- Do NOT regenerate the entire playbook - only provide the additions needed
- Be concise and specific - each addition should be actionable
- Format your response as a PURE JSON object

Current Playbook:
{current_playbook}

Generated Attempt:
{generated_attempt}

Reflection Insights:
{reflection_insights}

Your Task: Output ONLY a valid JSON object with these exact fields:
- reasoning: your chain of thought / reasoning / thinking process
- operations: a list of operations to be performed on the playbook

RESPONSE FORMAT - Output ONLY this JSON structure:
{{
    "reasoning": "[Your chain of thought / reasoning / thinking process here]",
    "operations": [
        {{
            "type": "ADD",
            "section": "strategies_and_hard_rules",
            "content": "[New strategy or rule...]"
        }}
    ]
}}
""",
        }

    def _format_prompt_for_task_type(
        self,
        task_type: str,
        task_context: str,
        playbook_content: str,
        insights_text: str,
        insights: List[ACEInsight],
        role: str | None,
        expected_outcome: str | None,
    ) -> str:
        """Format curation prompt based on task type.

        Args:
            task_type: Type of task
            task_context: Task context
            playbook_content: Current playbook content
            insights_text: Formatted insights
            insights: List of insights
            role: Role for MetaSOP
            expected_outcome: Expected outcome for MetaSOP

        Returns:
            Formatted prompt

        """
        prompt_template = self.curation_prompts.get(
            task_type, self.curation_prompts["general"]
        )

        if task_type == "appworld":
            return prompt_template.format(
                question_context=task_context,
                current_playbook=playbook_content,
                final_generated_code=insights[0].reasoning
                if insights
                else "No generated code",
                guidebook=insights_text,
            )
        elif task_type == "metasop":
            return prompt_template.format(
                role=role or "unknown",
                task=task_context,
                expected_outcome=expected_outcome or "Not specified",
                current_playbook=playbook_content,
                generated_attempt=insights[0].reasoning
                if insights
                else "No generated attempt",
                reflection_insights=insights_text,
            )
        else:
            return prompt_template.format(
                current_playbook=playbook_content,
                generated_attempt=insights[0].reasoning
                if insights
                else "No generated attempt",
                reflection_insights=insights_text,
            )

    def curate(
        self,
        insights: List[ACEInsight],
        current_playbook: ContextPlaybook,
        task_context: str,
        task_type: str = "general",
        role: Optional[str] = None,
        expected_outcome: Optional[str] = None,
    ) -> ACECurationResult:
        """Curate insights into delta updates for the context playbook.

        Args:
            insights: List of insights from Reflector
            current_playbook: Current state of the playbook
            task_context: Context of the task being performed
            task_type: Type of task
            role: Role for MetaSOP tasks
            expected_outcome: Expected outcome for MetaSOP tasks

        Returns:
            ACECurationResult containing delta updates and metadata

        """
        start_time = time.time()
        self.curation_metrics["total_curations"] += 1

        try:
            if not insights:
                return ACECurationResult(
                    delta_updates=[],
                    success=True,
                    redundancy_removed=0,
                    processing_time=time.time() - start_time,
                    tokens_used=0,
                )

            playbook_content = current_playbook.get_playbook_content(max_bullets=30)
            insights_text = self._format_insights_for_curation(insights)

            # Format prompt based on task type
            prompt = self._format_prompt_for_task_type(
                task_type,
                task_context,
                playbook_content,
                insights_text,
                insights,
                role,
                expected_outcome,
            )

            # Generate curation
            response = self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_completion_tokens=1500,
            )
            response_text = self._extract_response_text(response)

            # Parse JSON response
            try:
                curation_data = json.loads(response_text)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    curation_data = json.loads(response_text[json_start:json_end])
                else:
                    logger.warning("Could not parse curation JSON response")
                    return ACECurationResult(
                        delta_updates=[],
                        success=False,
                        redundancy_removed=0,
                        processing_time=time.time() - start_time,
                        tokens_used=0,
                    )

            # Convert to delta updates
            delta_updates = self._convert_to_delta_updates(
                curation_data.get("operations", [])
            )

            # Apply redundancy checking
            redundancy_removed = self._check_and_remove_redundancy(
                delta_updates, current_playbook
            )

            processing_time = time.time() - start_time
            self.curation_metrics["successful_curations"] += 1
            self.curation_metrics["total_time"] += processing_time
            self.curation_metrics["delta_updates_generated"] += len(delta_updates)
            self.curation_metrics["redundancy_removed"] += redundancy_removed

            # Token usage
            tokens_used = self._extract_total_tokens(response, prompt, response_text)
            self.curation_metrics["total_tokens"] += tokens_used

            logger.debug(
                f"Curation completed with {len(delta_updates)} updates in {processing_time:.2f}s"
            )

            return ACECurationResult(
                delta_updates=delta_updates,
                success=True,
                redundancy_removed=redundancy_removed,
                processing_time=processing_time,
                tokens_used=tokens_used,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            self.curation_metrics["failed_curations"] += 1
            logger.error(f"Curation failed: {e}")

            return ACECurationResult(
                delta_updates=[],
                success=False,
                redundancy_removed=0,
                processing_time=processing_time,
                tokens_used=0,
            )

    def _format_insights_for_curation(self, insights: List[ACEInsight]) -> str:
        """Format insights for curation prompt."""
        if not insights:
            return "No insights available."

        formatted = "REFLECTION INSIGHTS:\n"
        formatted += "=" * 50 + "\n\n"

        for i, insight in enumerate(insights, 1):
            formatted += f"Insight {i}:\n"
            formatted += f"Reasoning: {insight.reasoning}\n"
            formatted += f"Error Identification: {insight.error_identification}\n"
            formatted += f"Root Cause: {insight.root_cause_analysis}\n"
            formatted += f"Correct Approach: {insight.correct_approach}\n"
            formatted += f"Key Insight: {insight.key_insight}\n"
            formatted += f"Success: {insight.success}\n"
            formatted += f"Confidence: {insight.confidence:.2f}\n\n"

        return formatted

    def _convert_to_delta_updates(
        self, operations: List[Dict[str, Any]]
    ) -> List[ACEDeltaUpdate]:
        """Convert operations to delta updates."""
        delta_updates = []

        for operation in operations:
            try:
                update_type = operation.get("type", "ADD")
                section_name = operation.get("section", "strategies_and_hard_rules")
                content = operation.get("content", "")

                # Convert section name to enum
                try:
                    section = BulletSection(section_name)
                except ValueError:
                    logger.warning(f"Unknown section: {section_name}, using default")
                    section = BulletSection.STRATEGIES_AND_HARD_RULES

                if update_type == "ADD" and content.strip():
                    delta_update = ACEDeltaUpdate(
                        type="ADD", section=section, content=content.strip(), tags=[]
                    )
                    delta_updates.append(delta_update)

            except Exception as e:
                logger.warning(f"Failed to convert operation to delta update: {e}")
                continue

        return delta_updates

    def _check_and_remove_redundancy(
        self, delta_updates: List[ACEDeltaUpdate], current_playbook: ContextPlaybook
    ) -> int:
        """Check for redundancy and remove duplicate updates."""
        if not delta_updates:
            return 0

        redundancy_removed = 0
        filtered_updates = []

        for update in delta_updates:
            if update.type == "ADD" and update.content:
                # Check if this content is redundant with existing playbook
                is_redundant = False

                for bullet_id, bullet in current_playbook.bullets.items():
                    if bullet.section == update.section:
                        # Simple similarity check
                        similarity = self._compute_similarity(
                            update.content, bullet.content
                        )
                        if similarity > 0.8:  # High similarity threshold
                            is_redundant = True
                            redundancy_removed += 1
                            logger.debug(
                                f"Removed redundant update: {update.content[:50]}..."
                            )
                            break

                if not is_redundant:
                    filtered_updates.append(update)

        # Update the delta_updates list
        delta_updates.clear()
        delta_updates.extend(filtered_updates)

        return redundancy_removed

    def _compute_similarity(self, content1: str, content2: str) -> float:
        """Compute simple similarity between two content strings."""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def curate_batch(
        self,
        insights_batch: List[List[ACEInsight]],
        current_playbook: ContextPlaybook,
        task_contexts: List[str],
        task_types: Optional[List[str]] = None,
    ) -> List[ACECurationResult]:
        """Curate multiple batches of insights efficiently."""
        if task_types is None:
            task_types = ["general"] * len(insights_batch)

        results = []
        for i, (insights, context, task_type) in enumerate(
            zip(insights_batch, task_contexts, task_types)
        ):
            result = self.curate(insights, current_playbook, context, task_type)
            results.append(result)

        return results

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
        return len(prompt.split()) + len(text.split())

    def get_metrics(self) -> Dict[str, Any]:
        """Get curation metrics."""
        total = self.curation_metrics["total_curations"]
        if total == 0:
            return self.curation_metrics

        return {
            **self.curation_metrics,
            "success_rate": self.curation_metrics["successful_curations"] / total,
            "failure_rate": self.curation_metrics["failed_curations"] / total,
            "avg_processing_time": self.curation_metrics["total_time"] / total,
            "avg_tokens_per_curation": self.curation_metrics["total_tokens"] / total,
            "avg_updates_per_curation": self.curation_metrics["delta_updates_generated"]
            / total,
            "avg_redundancy_removed": self.curation_metrics["redundancy_removed"]
            / total,
        }

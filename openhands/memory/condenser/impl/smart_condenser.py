"""Smart condenser with LLM-assisted importance scoring.

This condenser uses an LLM to score the importance of events and preserve
critical information during condensation, preventing loss of key insights.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openhands.core.config.condenser_config import SmartCondenserConfig
    from openhands.llm.llm import LLM
    from openhands.llm.llm_registry import LLMRegistry

from openhands.core.logger import openhands_logger as logger
from openhands.events.action import Action, MessageAction
from openhands.events.action.agent import CondensationAction
from openhands.events.event import Event, EventSource
from openhands.events.observation import ErrorObservation, Observation
from openhands.memory.condenser.condenser import Condensation, RollingCondenser
from openhands.memory.view import View


class SmartCondenser(RollingCondenser):
    """LLM-assisted condenser that preserves critical information.

    Uses an LLM to:
    1. Score event importance
    2. Identify critical breakthroughs
    3. Preserve error context
    4. Maintain coherent narrative

    Keeps:
    - Essential events (first message, system message)
    - High-importance events (scored by LLM)
    - Recent events (recency bonus)
    - Critical errors and their context

    Summarizes:
    - Medium-importance event clusters

    Forgets:
    - Low-importance redundant events
    """

    def __init__(
        self,
        llm: LLM,
        max_size: int = 200,
        keep_first: int = 5,
        importance_threshold: float = 0.6,
        recency_bonus_window: int = 20,
    ) -> None:
        """Initialize smart condenser.

        Args:
            llm: LLM instance for importance scoring
            max_size: Maximum events before condensation
            keep_first: Number of initial events to always keep
            importance_threshold: Minimum importance score to keep (0.0-1.0)
            recency_bonus_window: Number of recent events to give bonus
        """
        self.llm = llm
        self.max_size = max_size
        self.keep_first = keep_first
        self.importance_threshold = importance_threshold
        self.recency_bonus_window = recency_bonus_window
        super().__init__()

        logger.info(
            f"SmartCondenser initialized: max_size={max_size}, "
            f"threshold={importance_threshold}, "
            f"llm={llm.config.model if llm else 'none'}",
        )

    def should_condense(self, view: View) -> bool:
        """Check if condensation should occur.

        Args:
            view: Current event view

        Returns:
            True if should condense
        """
        return len(view) > self.max_size

    def get_condensation(self, view: View) -> Condensation:
        """Apply LLM-assisted condensation.

        Args:
            view: Current event view

        Returns:
            Condensation action specifying what to forget/summarize
        """
        events = list(view)

        if len(events) <= self.keep_first:
            # Not enough events to condense
            return Condensation(action=CondensationAction(forgotten_event_ids=[]))

        # Identify essential events (always keep)
        essential_event_ids = self._identify_essential_events(events)

        # Score importance of remaining events
        importance_scores = self._score_event_importance(events, essential_event_ids)

        # Determine which events to keep
        events_to_keep = self._select_events_to_keep(
            events,
            essential_event_ids,
            importance_scores,
        )

        # Calculate forgotten events
        all_event_ids = {e.id for e in events}
        forgotten_event_ids = sorted(all_event_ids - events_to_keep)

        logger.info(
            f"SmartCondenser: Keeping {len(events_to_keep)} events, forgetting {len(forgotten_event_ids)} events",
        )

        return Condensation(action=CondensationAction(forgotten_event_ids=forgotten_event_ids))

    def _identify_essential_events(self, events: list[Event]) -> set[int]:
        """Identify essential events that must always be kept.

        Args:
            events: All events

        Returns:
            Set of essential event IDs
        """
        essential = set()

        # Keep first N events
        for event in events[: self.keep_first]:
            essential.add(event.id)

        # Keep first user message
        first_user_msg = next(
            (e for e in events if isinstance(e, MessageAction) and e.source == EventSource.USER),
            None,
        )
        if first_user_msg:
            essential.add(first_user_msg.id)

        # Keep critical errors (recent ones)
        recent_events = events[-50:]
        for event in recent_events:
            if isinstance(event, ErrorObservation):
                error_content = event.content.lower()
                # Keep critical errors
                if any(keyword in error_content for keyword in ["critical", "crash", "fatal", "stuck"]):
                    essential.add(event.id)

        return essential

    def _score_event_importance(
        self,
        events: list[Event],
        essential_ids: set[int],
    ) -> dict[int, float]:
        """Score importance of events using LLM.

        Args:
            events: All events
            essential_ids: IDs of essential events (don't score these)

        Returns:
            Dictionary mapping event ID to importance score (0.0-1.0)
        """
        scores = {}

        # Filter out essential events (they're already kept)
        events_to_score = [e for e in events if e.id not in essential_ids]

        if not events_to_score:
            return scores

        # Use heuristic scoring if LLM not available
        if not self.llm:
            return self._heuristic_scoring(events_to_score)

        # Group events into batches for efficient LLM scoring
        batch_size = 20
        for i in range(0, len(events_to_score), batch_size):
            batch = events_to_score[i: i + batch_size]
            batch_scores = self._score_event_batch_with_llm(batch)
            scores.update(batch_scores)

        return scores

    def _heuristic_scoring(self, events: list[Event]) -> dict[int, float]:
        """Score events using heuristics (fallback when no LLM).

        Args:
            events: Events to score

        Returns:
            Event ID to importance score mapping
        """
        scores = {}

        for event in events:
            score = 0.5  # Default medium importance

            # User messages are important
            if isinstance(event, MessageAction) and event.source == EventSource.USER:
                score = 0.9

            # Errors are important
            elif isinstance(event, ErrorObservation):
                score = 0.8

            # Actions that modify state are important
            elif isinstance(event, Action):
                if hasattr(event, "runnable") and event.runnable:
                    score = 0.7

            # Observations with long content might be important
            elif isinstance(event, Observation):
                if len(event.content) > 500:
                    score = 0.6

            scores[event.id] = score

        return scores

    def _score_event_batch_with_llm(self, events: list[Event]) -> dict[int, float]:
        """Score a batch of events using LLM.

        Args:
            events: Batch of events to score

        Returns:
            Event ID to importance score mapping
        """
        try:
            # Create scoring prompt
            prompt = self._create_scoring_prompt(events)

            # Get LLM response
            response = self.llm.completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
            )

            # Parse scores from response
            return self._parse_llm_scores(response, events)

        except Exception as e:
            logger.warning(f"LLM scoring failed, using heuristics: {e}")
            return self._heuristic_scoring(events)

    def _create_scoring_prompt(self, events: list[Event]) -> str:
        """Create prompt for LLM importance scoring.

        Args:
            events: Events to score

        Returns:
            Scoring prompt
        """
        event_summaries = []

        for i, event in enumerate(events):
            event_type = type(event).__name__
            event_content = self._get_event_summary(event)
            event_summaries.append(f"{i}. [{event_type}] {event_content}")

        return f"""Score the importance of these conversation events for an autonomous agent task.

Events:
{chr(10).join(event_summaries)}

For each event, assign an importance score from 0.0 to 1.0:
- 1.0: Critical information (breakthroughs, solutions, critical errors)
- 0.7-0.9: Important (meaningful progress, key insights)
- 0.4-0.6: Moderate (useful context, routine operations)
- 0.0-0.3: Low importance (redundant info, trivial actions)

Respond ONLY with a JSON array of scores in order:
[0.8, 0.3, 0.9, ...]
"""

    def _get_event_summary(self, event: Event) -> str:
        """Get brief summary of event for scoring.

        Args:
            event: Event to summarize

        Returns:
            Summary string (truncated to 100 chars)
        """
        if hasattr(event, "content"):
            return str(event.content)[:100]
        if hasattr(event, "command"):
            return f"Command: {event.command[:50]}"
        if hasattr(event, "code"):
            return f"Code: {event.code[:50]}"
        return str(event)[:100]

    def _parse_llm_scores(self, response, events: list[Event]) -> dict[int, float]:
        """Parse LLM response into event scores.

        Args:
            response: LLM response
            events: Events that were scored

        Returns:
            Event ID to score mapping
        """
        try:
            content = response.choices[0].message.content

            # Extract JSON array from response
            # Handle both raw array and wrapped in markdown
            if "```" in content:
                json_str = content.split("```")[1].strip()
                if json_str.startswith("json"):
                    json_str = json_str[4:].strip()
            else:
                json_str = content.strip()

            scores_list = json.loads(json_str)

            # Map to event IDs
            scores = {}
            for i, score in enumerate(scores_list):
                if i < len(events):
                    scores[events[i].id] = max(0.0, min(1.0, float(score)))

            return scores

        except Exception as e:
            logger.warning(f"Failed to parse LLM scores: {e}")
            return self._heuristic_scoring(events)

    def _select_events_to_keep(
        self,
        events: list[Event],
        essential_ids: set[int],
        importance_scores: dict[int, float],
    ) -> set[int]:
        """Select which events to keep based on importance and recency.

        Args:
            events: All events
            essential_ids: Essential event IDs (always keep)
            importance_scores: Event importance scores

        Returns:
            Set of event IDs to keep
        """
        keep_ids = essential_ids.copy()

        # Apply recency bonus to recent events
        recent_events = events[-self.recency_bonus_window:]

        for event in events:
            if event.id in essential_ids:
                continue

            # Get base importance score
            base_score = importance_scores.get(event.id, 0.5)

            # Apply recency bonus
            if event in recent_events:
                recency_bonus = 0.3
                final_score = min(1.0, base_score + recency_bonus)
            else:
                final_score = base_score

            # Keep if above threshold
            if final_score >= self.importance_threshold:
                keep_ids.add(event.id)

        # Ensure action-observation pairs are preserved
        keep_ids = self._preserve_action_observation_pairs(events, keep_ids)

        # Ensure we keep at least recent events even if scores are low
        recent_ids = {e.id for e in events[-self.recency_bonus_window:]}
        keep_ids.update(recent_ids)

        return keep_ids

    def _preserve_action_observation_pairs(
        self,
        events: list[Event],
        keep_ids: set[int],
    ) -> set[int]:
        """Ensure action-observation pairs aren't broken.

        Args:
            events: All events
            keep_ids: Current set of IDs to keep

        Returns:
            Updated set with paired events
        """
        paired_ids = keep_ids.copy()

        for i, event in enumerate(events):
            if event.id not in keep_ids:
                continue

            if isinstance(event, Action) and hasattr(event, "id"):
                self._pair_observation_for_action(events, i, event, paired_ids)
            elif isinstance(event, Observation) and hasattr(event, "_cause"):
                self._pair_action_for_observation(events, i, event, paired_ids)

        return paired_ids

    def _pair_observation_for_action(
        self, events: list[Event], action_idx: int, action: Action, paired_ids: set[int],
    ) -> None:
        """Find and pair observation for an action.

        Args:
            events: All events
            action_idx: Index of action
            action: Action event
            paired_ids: Set to add paired IDs to
        """
        for j in range(action_idx + 1, min(action_idx + 5, len(events))):
            next_event = events[j]
            if isinstance(next_event, Observation):
                if hasattr(next_event, "_cause") and next_event._cause == action.id:
                    paired_ids.add(next_event.id)
                break

    def _pair_action_for_observation(
        self, events: list[Event], obs_idx: int, observation: Observation, paired_ids: set[int],
    ) -> None:
        """Find and pair action for an observation.

        Args:
            events: All events
            obs_idx: Index of observation
            observation: Observation event
            paired_ids: Set to add paired IDs to
        """
        for j in range(max(0, obs_idx - 5), obs_idx):
            prev_event = events[j]
            if isinstance(prev_event, Action) and prev_event.id == observation._cause:
                paired_ids.add(prev_event.id)
                break

    @classmethod
    def from_config(
        cls,
        config: SmartCondenserConfig,
        llm_registry: LLMRegistry,
    ) -> SmartCondenser:
        """Create SmartCondenser from configuration.

        Args:
            config: Condenser configuration
            llm_registry: LLM registry for getting LLM instance

        Returns:
            Configured SmartCondenser instance
        """
        llm = llm_registry.get_llm_config(config.llm_config) if config.llm_config else None

        return cls(
            llm=llm,
            max_size=config.max_size,
            keep_first=config.keep_first,
            importance_threshold=getattr(config, "importance_threshold", 0.6),
            recency_bonus_window=getattr(config, "recency_bonus_window", 20),
        )

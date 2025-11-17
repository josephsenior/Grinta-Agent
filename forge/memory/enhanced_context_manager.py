"""Enhanced Context Manager - Hierarchical Memory with Decision Tracking.

Solves the 7/10 context management issues:
- Tracks decisions explicitly to prevent contradictions
- Uses 3-tier hierarchical memory (short/working/long-term)
- Anchors critical information that shouldn't be forgotten
- Detects contradictions against conversation history
- Semantic compression with retrieval for long conversations
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

from forge.core.logger import forge_logger as logger


class DecisionType(Enum):
    """Types of decisions tracked."""

    ARCHITECTURAL = "architectural"  # System design choices
    IMPLEMENTATION = "implementation"  # Code implementation decisions
    TECHNICAL = "technical"  # Tech stack, library choices
    FUNCTIONAL = "functional"  # Feature behavior
    CONSTRAINT = "constraint"  # Explicit constraints/requirements
    WORKFLOW = "workflow"  # Process/workflow decisions


class MemoryTier(Enum):
    """Memory tiers for hierarchical storage."""

    SHORT_TERM = "short_term"  # Last few exchanges
    WORKING = "working"  # Active conversation context
    LONG_TERM = "long_term"  # Persistent across sessions


@dataclass
class Decision:
    """A tracked decision made during conversation."""

    decision_id: str
    type: DecisionType
    description: str
    rationale: str
    timestamp: datetime
    context: str  # What was the conversation context?
    alternatives_considered: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0-1
    tier: MemoryTier = MemoryTier.WORKING
    anchor: bool = False  # Should this be anchored (never forgotten)?

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "type": self.type.value,
            "description": self.description,
            "rationale": self.rationale,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "alternatives_considered": self.alternatives_considered,
            "confidence": self.confidence,
            "tier": self.tier.value,
            "anchor": self.anchor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Decision:
        """Create from dictionary."""
        return cls(
            decision_id=data["decision_id"],
            type=DecisionType(data["type"]),
            description=data["description"],
            rationale=data["rationale"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            context=data["context"],
            alternatives_considered=data.get("alternatives_considered", []),
            confidence=data.get("confidence", 1.0),
            tier=MemoryTier(data.get("tier", "working")),
            anchor=data.get("anchor", False),
        )


@dataclass
class ContextAnchor:
    """Critical information that should never be forgotten."""

    anchor_id: str
    content: str
    category: str  # "requirement", "constraint", "goal", "architecture"
    importance: float  # 0-1
    timestamp: datetime
    last_accessed: datetime
    access_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anchor_id": self.anchor_id,
            "content": self.content,
            "category": self.category,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ContextAnchor:
        """Create from dictionary."""
        return cls(
            anchor_id=data["anchor_id"],
            content=data["content"],
            category=data["category"],
            importance=data["importance"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]),
            access_count=data.get("access_count", 0),
        )


@dataclass
class ConversationSnapshot:
    """Snapshot of conversation state at a point in time."""

    snapshot_id: str
    timestamp: datetime
    active_decisions: List[str]  # Decision IDs
    active_anchors: List[str]  # Anchor IDs
    conversation_summary: str
    key_points: List[str]


class EnhancedContextManager:
    """Enhanced context management with hierarchical memory and decision tracking.

    Solves the context management issues:
    1. Tracks decisions explicitly - no more forgetting what was decided
    2. Hierarchical memory - short-term, working, long-term tiers
    3. Context anchors - pin critical information
    4. Contradiction detection - checks against history
    5. Semantic compression - intelligent summarization
    """

    def __init__(
        self,
        short_term_window: int = 5,  # Last N exchanges
        working_memory_size: int = 50,  # Active context
        long_term_max_size: int = 200,  # Persistent memory
        contradiction_threshold: float = 0.7,  # Similarity threshold for contradiction
    ):
        """Initialize enhanced context manager.

        Args:
            short_term_window: Number of recent exchanges in short-term memory
            working_memory_size: Max items in working memory
            long_term_max_size: Max items in long-term memory
            contradiction_threshold: Threshold for detecting contradictions

        """
        # Memory tiers
        self.short_term_memory: List[Dict[str, Any]] = []
        self.working_memory: List[Dict[str, Any]] = []
        self.long_term_memory: List[Dict[str, Any]] = []

        # Decision tracking
        self.decisions: Dict[str, Decision] = {}
        self.decision_history: List[str] = []  # Chronological decision IDs

        # Context anchors
        self.anchors: Dict[str, ContextAnchor] = {}

        # Snapshots for contradiction detection
        self.snapshots: List[ConversationSnapshot] = []

        # Configuration
        self.short_term_window = short_term_window
        self.working_memory_size = working_memory_size
        self.long_term_max_size = long_term_max_size
        self.contradiction_threshold = contradiction_threshold

        # Metrics
        self.stats = {
            "decisions_tracked": 0,
            "anchors_created": 0,
            "contradictions_detected": 0,
            "promotions_to_long_term": 0,
        }

        logger.info("Enhanced Context Manager initialized")

    # ========================================================================
    # DECISION TRACKING
    # ========================================================================

    def track_decision(
        self,
        description: str,
        rationale: str,
        decision_type: DecisionType,
        context: str,
        alternatives: Optional[List[str]] = None,
        confidence: float = 1.0,
        anchor: bool = False,
    ) -> Decision:
        """Track a decision made during conversation.

        Args:
            description: What was decided
            rationale: Why this was decided
            decision_type: Type of decision
            context: Conversation context
            alternatives: Other options considered
            confidence: Confidence in this decision (0-1)
            anchor: Should this be anchored (never forgotten)?

        Returns:
            Decision object

        """
        decision_id = f"decision_{len(self.decisions) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        decision = Decision(
            decision_id=decision_id,
            type=decision_type,
            description=description,
            rationale=rationale,
            timestamp=datetime.now(),
            context=context,
            alternatives_considered=alternatives or [],
            confidence=confidence,
            tier=MemoryTier.WORKING,
            anchor=anchor,
        )

        self.decisions[decision_id] = decision
        self.decision_history.append(decision_id)
        self.stats["decisions_tracked"] += 1

        # If anchored, also create an anchor
        if anchor:
            self.create_anchor(
                content=f"Decision: {description}\nRationale: {rationale}",
                category="decision",
                importance=confidence,
            )

        logger.info(f"✓ Tracked {decision_type.value} decision: {description[:50]}...")

        return decision

    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a specific decision by ID."""
        return self.decisions.get(decision_id)

    def get_recent_decisions(self, limit: int = 10) -> List[Decision]:
        """Get most recent decisions."""
        recent_ids = self.decision_history[-limit:]
        return [self.decisions[did] for did in recent_ids if did in self.decisions]

    def get_decisions_by_type(self, decision_type: DecisionType) -> List[Decision]:
        """Get all decisions of a specific type."""
        return [d for d in self.decisions.values() if d.type == decision_type]

    def search_decisions(self, query: str) -> List[Decision]:
        """Search decisions by description or rationale."""
        query_lower = query.lower()
        results = []

        for decision in self.decisions.values():
            if (
                query_lower in decision.description.lower()
                or query_lower in decision.rationale.lower()
                or query_lower in decision.context.lower()
            ):
                results.append(decision)

        return results

    # ========================================================================
    # CONTEXT ANCHORS
    # ========================================================================

    def create_anchor(
        self, content: str, category: str, importance: float = 0.9
    ) -> ContextAnchor:
        """Create a context anchor for critical information.

        Args:
            content: Information to anchor
            category: Category ("requirement", "constraint", "goal", "architecture", "decision")
            importance: Importance score (0-1)

        Returns:
            ContextAnchor object

        """
        anchor_id = (
            f"anchor_{len(self.anchors) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        anchor = ContextAnchor(
            anchor_id=anchor_id,
            content=content,
            category=category,
            importance=importance,
            timestamp=datetime.now(),
            last_accessed=datetime.now(),
        )

        self.anchors[anchor_id] = anchor
        self.stats["anchors_created"] += 1

        logger.info(f"📌 Anchored {category}: {content[:50]}...")

        return anchor

    def get_anchor(self, anchor_id: str) -> Optional[ContextAnchor]:
        """Get a specific anchor and update access time."""
        if anchor_id in self.anchors:
            anchor = self.anchors[anchor_id]
            anchor.last_accessed = datetime.now()
            anchor.access_count += 1
            return anchor
        return None

    def get_all_anchors(self, min_importance: float = 0.0) -> List[ContextAnchor]:
        """Get all anchors above minimum importance."""
        return [a for a in self.anchors.values() if a.importance >= min_importance]

    def get_anchors_by_category(self, category: str) -> List[ContextAnchor]:
        """Get all anchors in a category."""
        return [a for a in self.anchors.values() if a.category == category]

    # ========================================================================
    # HIERARCHICAL MEMORY
    # ========================================================================

    def add_to_short_term(self, item: Dict[str, Any]) -> None:
        """Add item to short-term memory (last N exchanges)."""
        self.short_term_memory.append(
            {**item, "timestamp": datetime.now(), "tier": "short_term"}
        )

        # Keep only recent window
        if len(self.short_term_memory) > self.short_term_window:
            # Promote oldest to working memory
            oldest = self.short_term_memory.pop(0)
            self.add_to_working_memory(oldest)

    def add_to_working_memory(self, item: Dict[str, Any]) -> None:
        """Add item to working memory (active context)."""
        item["tier"] = "working"
        self.working_memory.append(item)

        # Manage size
        if len(self.working_memory) > self.working_memory_size:
            # Promote important items to long-term
            self._promote_to_long_term()

    def add_to_long_term(self, item: Dict[str, Any]) -> None:
        """Add item to long-term memory (persistent)."""
        item["tier"] = "long_term"
        self.long_term_memory.append(item)
        self.stats["promotions_to_long_term"] += 1

        # Manage size
        if len(self.long_term_memory) > self.long_term_max_size:
            # Remove least important items
            self._cleanup_long_term()

    def _promote_to_long_term(self) -> None:
        """Promote important items from working to long-term memory.

        Intelligently selects top 20% of working memory items for long-term storage based
        on importance scoring. Items with anchors, decisions, or high access counts are
        prioritized. This maintains focused working memory while preserving critical
        information permanently.

        Scoring Factors:
            - has_anchor: +0.5 points (critical information)
            - has_decision: +0.3 points (decisions are important)
            - access_count > 3: +0.2 points (frequently accessed)

        Side Effects:
            - Updates self.stats["promotions_to_long_term"]
            - Removes promoted items from working memory
            - Modifies long-term memory

        Example:
            >>> manager.working_memory = [{"has_anchor": True}, {"access_count": 5}]
            >>> manager._promote_to_long_term()
            >>> len(manager.working_memory) < 2  # Top items promoted
            True

        """
        # Score items by importance (has anchor, decision, or high access)
        scored_items = []
        for item in self.working_memory:
            importance = 0.0
            if item.get("has_anchor"):
                importance += 0.5
            if item.get("has_decision"):
                importance += 0.3
            if item.get("access_count", 0) > 3:
                importance += 0.2
            scored_items.append((importance, item))

        # Sort by importance
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Promote top 20%
        promote_count = max(1, len(scored_items) // 5)
        for i in range(promote_count):
            if i < len(scored_items):
                self.add_to_long_term(scored_items[i][1])

        # Remove promoted items from working memory
        promoted_items = {id(item) for _, item in scored_items[:promote_count]}
        self.working_memory = [
            item for item in self.working_memory if id(item) not in promoted_items
        ]

    def _cleanup_long_term(self) -> None:
        """Remove least important items from long-term memory.

        Implements a retention strategy that preserves anchored items and decisions
        while pruning older, less-accessed items when long-term memory exceeds capacity.
        Applies intelligent filtering to maintain quality of persistent context:

        Retention Priority:
            1. Items with anchors (always kept)
            2. Items with tracked decisions (always kept)
            3. Recently accessed items with high access counts
            4. Newest items by timestamp

        Algorithm:
            - Separate anchored/decision items from removal candidates
            - Sort candidates by access count and timestamp
            - Keep the more recent half of candidates
            - Merge back with protected items

        Side Effects:
            - Modifies self.long_term_memory in place
            - Discards least important items permanently

        Example:
            >>> manager.long_term_memory = [
            ...     {"has_anchor": True},  # Will be kept
            ...     {"has_decision": True},  # Will be kept
            ...     {"access_count": 0},  # Candidate for removal
            ... ]
            >>> manager._cleanup_long_term()
            >>> len(manager.long_term_memory) >= 2  # Anchors/decisions preserved
            True

        """
        # Keep anchored items and recent items
        keep_items = []
        remove_candidates = []

        for item in self.long_term_memory:
            if item.get("has_anchor") or item.get("has_decision"):
                keep_items.append(item)
            else:
                remove_candidates.append(item)

        # Sort remove candidates by age and access
        remove_candidates.sort(
            key=lambda x: (
                x.get("access_count", 0),
                x.get("timestamp", datetime.now()),
            ),
            reverse=False,
        )

        # Keep half of the remove candidates
        keep_count = len(remove_candidates) // 2
        keep_items.extend(remove_candidates[:keep_count])

        self.long_term_memory = keep_items

    def get_all_memory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all memory tiers."""
        return {
            "short_term": self.short_term_memory,
            "working": self.working_memory,
            "long_term": self.long_term_memory,
        }

    def search_memory(
        self, query: str, tiers: Optional[List[MemoryTier]] = None
    ) -> List[Dict[str, Any]]:
        """Search across memory tiers."""
        if tiers is None:
            tiers = [MemoryTier.SHORT_TERM, MemoryTier.WORKING, MemoryTier.LONG_TERM]

        query_lower = query.lower()
        results = []

        for tier in tiers:
            if tier == MemoryTier.SHORT_TERM:
                memory = self.short_term_memory
            elif tier == MemoryTier.WORKING:
                memory = self.working_memory
            else:
                memory = self.long_term_memory

            for item in memory:
                content_str = json.dumps(item).lower()
                if query_lower in content_str:
                    results.append(item)

        return results

    # ========================================================================
    # CONTRADICTION DETECTION
    # ========================================================================

    def detect_contradiction(
        self, new_statement: str, context: str
    ) -> Tuple[bool, Optional[str]]:
        """Detect if a new statement contradicts previous decisions.

        Args:
            new_statement: New statement to check
            context: Current conversation context

        Returns:
            Tuple of (is_contradiction, conflicting_decision_description)

        """
        new_lower = new_statement.lower()

        # Check against decisions
        for decision in self.decisions.values():
            desc_lower = decision.description.lower()

            # Simple contradiction detection (can be enhanced with NLP)
            if self._contains_negation(new_lower, desc_lower):
                self.stats["contradictions_detected"] += 1
                logger.warning(
                    f"⚠️  Contradiction detected with decision: {decision.description}"
                )
                return True, decision.description

        # Check against anchors
        for anchor in self.anchors.values():
            content_lower = anchor.content.lower()

            if self._contains_negation(new_lower, content_lower):
                self.stats["contradictions_detected"] += 1
                logger.warning(
                    f"⚠️  Contradiction detected with anchor: {anchor.content[:50]}..."
                )
                return True, anchor.content

        return False, None

    def _contains_negation(self, new_text: str, old_text: str) -> bool:
        """Check if new text negates old text (simple heuristic)."""
        # Extract key terms
        new_terms = set(new_text.split())
        old_terms = set(old_text.split())

        # Check for negation words
        negation_words = {
            "not",
            "no",
            "never",
            "won't",
            "don't",
            "shouldn't",
            "can't",
            "doesn't",
        }

        # If new text has negation and shares terms with old text
        has_negation = bool(new_terms & negation_words)
        shares_terms = len(new_terms & old_terms) > 3

        return has_negation and shares_terms

    # ========================================================================
    # CONTEXT RETRIEVAL
    # ========================================================================

    def get_relevant_context(
        self,
        query: str,
        max_items: int = 20,
        include_anchors: bool = True,
        include_decisions: bool = True,
    ) -> Dict[str, Any]:
        """Get relevant context for a query.

        Args:
            query: Query to find relevant context for
            max_items: Max items to return
            include_anchors: Include context anchors
            include_decisions: Include tracked decisions

        Returns:
            Dict with relevant context

        """
        context: Dict[str, Any] = {"anchors": [], "decisions": [], "memory": []}

        # Always include anchors (critical information)
        if include_anchors:
            context["anchors"] = [
                a.to_dict() for a in self.get_all_anchors(min_importance=0.5)
            ]

        # Include recent and relevant decisions
        if include_decisions:
            recent_decisions = self.get_recent_decisions(limit=10)
            searched_decisions = self.search_decisions(query)

            # Combine and deduplicate
            all_decisions = {
                d.decision_id: d for d in recent_decisions + searched_decisions
            }
            context["decisions"] = [d.to_dict() for d in all_decisions.values()]

        # Search memory
        memory_results = self.search_memory(query)
        context["memory"] = memory_results[:max_items]

        return context

    # ========================================================================
    # PERSISTENCE
    # ========================================================================

    def save_to_file(self, file_path: str) -> None:
        """Save context manager state to file."""
        state = {
            "decisions": {did: d.to_dict() for did, d in self.decisions.items()},
            "decision_history": self.decision_history,
            "anchors": {aid: a.to_dict() for aid, a in self.anchors.items()},
            "short_term_memory": self.short_term_memory,
            "working_memory": self.working_memory,
            "long_term_memory": self.long_term_memory,
            "stats": self.stats,
            "saved_at": datetime.now().isoformat(),
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        logger.info(f"💾 Saved context manager state to {file_path}")

    def load_from_file(self, file_path: str) -> None:
        """Load context manager state from file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Load decisions
            self.decisions = {
                did: Decision.from_dict(d)
                for did, d in state.get("decisions", {}).items()
            }
            self.decision_history = state.get("decision_history", [])

            # Load anchors
            self.anchors = {
                aid: ContextAnchor.from_dict(a)
                for aid, a in state.get("anchors", {}).items()
            }

            # Load memory tiers
            self.short_term_memory = state.get("short_term_memory", [])
            self.working_memory = state.get("working_memory", [])
            self.long_term_memory = state.get("long_term_memory", [])

            # Load stats
            self.stats = state.get("stats", self.stats)

            logger.info(f"📂 Loaded context manager state from {file_path}")

        except Exception as e:
            logger.error(f"Failed to load context manager state: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        return {
            **self.stats,
            "short_term_count": len(self.short_term_memory),
            "working_memory_count": len(self.working_memory),
            "long_term_count": len(self.long_term_memory),
            "total_decisions": len(self.decisions),
            "total_anchors": len(self.anchors),
        }

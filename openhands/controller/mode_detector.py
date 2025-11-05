"""Mode detector for intelligent agent mode selection.

This module provides automatic detection of whether a task should use
simple (autonomous) mode or enterprise (MetaSOP) mode based on task complexity.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)


class ModeDetector:
    """Detector for automatically selecting appropriate agent mode.

    Analyzes user requests to determine whether they should use:
    - Simple mode: Fast autonomous execution for straightforward tasks
    - Enterprise mode: Multi-role MetaSOP orchestration for complex features
    """

    # Keywords that indicate complex, enterprise-level work
    COMPLEXITY_INDICATORS = {
        "high": ["feature", "system", "architecture", "integration", "infrastructure", "microservice"],
        "medium": ["test", "qa", "validate", "compliance", "audit", "security", "refactor"],
        "low": [],
    }

    # Keywords that indicate simple, quick tasks
    SIMPLICITY_INDICATORS = ["fix", "bug", "typo", "quick", "simple", "small", "minor", "hotfix"]

    # Keywords that indicate need for quality gates
    QUALITY_INDICATORS = ["production", "deploy", "release", "critical", "enterprise", "regulated"]

    @staticmethod
    def detect_mode(user_request: str, auto_detect: bool = True) -> str:
        """Auto-detect appropriate mode based on user request.

        Args:
            user_request: The user's task description
            auto_detect: Whether to enable auto-detection (if False, returns "ask_user")

        Returns:
            "simple" for simple mode, "enterprise" for enterprise mode,
            or "ask_user" if ambiguous
        """
        if not auto_detect:
            return "ask_user"

        complexity_score = ModeDetector._calculate_complexity(user_request)

        logger.debug(
            "Mode detection: complexity_score=%d for request: %s",
            complexity_score,
            user_request[:100],
        )

        if complexity_score < 3:
            logger.info("Auto-detected SIMPLE mode (score: %d)", complexity_score)
            return "simple"
        if complexity_score >= 7:
            logger.info("Auto-detected ENTERPRISE mode (score: %d)", complexity_score)
            return "enterprise"
        logger.info("Ambiguous complexity (score: %d), asking user", complexity_score)
        return "ask_user"

    @staticmethod
    def _calculate_complexity(request: str) -> int:
        """Calculate task complexity score (0-10).

        Args:
            request: The user's task description

        Returns:
            Complexity score from 0 (very simple) to 10 (very complex)
        """
        request_lower = request.lower()

        score = 5  # Start neutral
        score += ModeDetector._score_keyword_matches(request_lower)
        score += ModeDetector._score_task_indicators(request_lower)
        score += ModeDetector._score_request_length(request)

        # Clamp score between 0 and 10
        final_score = max(0, min(10, score))
        logger.debug("Final complexity score: %d", final_score)
        return final_score

    @staticmethod
    def _score_keyword_matches(request_lower: str) -> int:
        """Score based on complexity keyword matches.

        Args:
            request_lower: Lowercased request text

        Returns:
            Score adjustment based on keyword matches
        """
        score = 0

        # High complexity indicators (+3 each)
        for keyword in ModeDetector.COMPLEXITY_INDICATORS["high"]:
            if keyword in request_lower:
                score += 3
                logger.debug("Found high complexity keyword: %s (+3)", keyword)

        # Medium complexity indicators (+2 each)
        for keyword in ModeDetector.COMPLEXITY_INDICATORS["medium"]:
            if keyword in request_lower:
                score += 2
                logger.debug("Found medium complexity keyword: %s (+2)", keyword)

        # Quality/enterprise indicators (+2 each)
        for keyword in ModeDetector.QUALITY_INDICATORS:
            if keyword in request_lower:
                score += 2
                logger.debug("Found quality indicator: %s (+2)", keyword)

        # Simplicity indicators (-2 each)
        for keyword in ModeDetector.SIMPLICITY_INDICATORS:
            if keyword in request_lower:
                score -= 2
                logger.debug("Found simplicity keyword: %s (-2)", keyword)

        return score

    @staticmethod
    def _score_task_indicators(request_lower: str) -> int:
        """Score based on task complexity indicators.

        Args:
            request_lower: Lowercased request text

        Returns:
            Score adjustment based on task indicators
        """
        score = 0

        # Check for multiple tasks ("and" conjunctions)
        and_count = request_lower.count(" and ")
        if and_count > 2:
            score += 2
            logger.debug("Multiple 'and' conjunctions found (+2)")

        # Check for mentions of multiple files/components
        file_mentions = len(re.findall(r"\b\w+\.(py|js|tsx|ts|java|go|rs)\b", request_lower))
        if file_mentions > 3:
            score += 2
            logger.debug("Multiple file mentions found: %d (+2)", file_mentions)

        return score

    @staticmethod
    def _score_request_length(request: str) -> int:
        """Score based on request length.

        Args:
            request: The request text

        Returns:
            Score adjustment based on length
        """
        word_count = len(request.split())

        if word_count > 50:
            logger.debug("Long request: %d words (+1)", word_count)
            return 1
        if word_count < 10:
            logger.debug("Short request: %d words (-1)", word_count)
            return -1

        return 0

    @staticmethod
    def get_mode_recommendation(user_request: str) -> dict:
        """Get detailed mode recommendation with reasoning.

        Args:
            user_request: The user's task description

        Returns:
            Dictionary containing recommended mode and reasoning
        """
        complexity_score = ModeDetector._calculate_complexity(user_request)
        mode = ModeDetector.detect_mode(user_request)

        # Generate reasoning
        reasons = []
        request_lower = user_request.lower()

        # Identify what triggered the recommendation
        for keyword in ModeDetector.COMPLEXITY_INDICATORS["high"]:
            if keyword in request_lower:
                reasons.append(f"Detected enterprise keyword: '{keyword}'")

        for keyword in ModeDetector.QUALITY_INDICATORS:
            if keyword in request_lower:
                reasons.append(f"Quality/compliance requirement: '{keyword}'")

        for keyword in ModeDetector.SIMPLICITY_INDICATORS:
            if keyword in request_lower:
                reasons.append(f"Simple task indicator: '{keyword}'")

        if not reasons:
            reasons.append("Based on overall complexity analysis")

        return {
            "mode": mode,
            "complexity_score": complexity_score,
            "confidence": "high" if mode != "ask_user" else "low",
            "reasons": reasons[:3],  # Limit to top 3 reasons
        }

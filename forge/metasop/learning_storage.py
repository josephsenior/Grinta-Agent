"""Learning Storage System for MetaSOP Multi-Agent Orchestration.

Provides persistent storage for learned patterns, causal relationships,
and performance metrics across sessions.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from forge.core.logger import forge_logger as logger


class LearningStorage:
    """Storage manager for learned patterns and performance data."""
    
    def __init__(self, base_path: str = "~/.Forge/learning/"):
        """Initialize learning storage.
        
        Args:
            base_path: Base directory for storing learning data

        """
        self.base_path = Path(base_path).expanduser().resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Define storage paths
        self.causal_patterns_path = self.base_path / "causal_patterns.json"
        self.parallel_stats_path = self.base_path / "parallel_stats.json"
        self.performance_history_path = self.base_path / "performance_history.json"
        
        logger.info(f"Learning storage initialized at {self.base_path}")

    def save_causal_patterns(self, patterns: Dict[str, Any]) -> None:
        """Save causal patterns to persistent storage.
        
        Args:
            patterns: Dictionary of learned causal patterns

        """
        try:
            with open(self.causal_patterns_path, 'w') as f:
                json.dump(patterns, f, indent=2)
            logger.debug(f"Saved causal patterns to {self.causal_patterns_path}")
        except Exception as e:
            logger.error(f"Failed to save causal patterns: {e}")

    def load_causal_patterns(self) -> Dict[str, Any]:
        """Load causal patterns from persistent storage.
        
        Returns:
            Dictionary of learned causal patterns

        """
        try:
            if self.causal_patterns_path.exists():
                with open(self.causal_patterns_path, 'r') as f:
                    patterns = json.load(f)
                logger.debug(f"Loaded causal patterns from {self.causal_patterns_path}")
                return patterns
        except Exception as e:
            logger.error(f"Failed to load causal patterns: {e}")
        
        # Return empty patterns if loading fails
        return {}

    def save_parallel_stats(self, stats: Dict[str, Any]) -> None:
        """Save parallel execution statistics.
        
        Args:
            stats: Dictionary of parallel execution statistics

        """
        try:
            # Load existing stats and merge
            existing_stats = self.load_parallel_stats()
            existing_stats.update(stats)
            
            with open(self.parallel_stats_path, 'w') as f:
                json.dump(existing_stats, f, indent=2)
            logger.debug(f"Saved parallel stats to {self.parallel_stats_path}")
        except Exception as e:
            logger.error(f"Failed to save parallel stats: {e}")

    def load_parallel_stats(self) -> Dict[str, Any]:
        """Load parallel execution statistics.
        
        Returns:
            Dictionary of parallel execution statistics

        """
        try:
            if self.parallel_stats_path.exists():
                with open(self.parallel_stats_path, 'r') as f:
                    stats = json.load(f)
                logger.debug(f"Loaded parallel stats from {self.parallel_stats_path}")
                return stats
        except Exception as e:
            logger.error(f"Failed to load parallel stats: {e}")
        
        return {}

    def save_performance_history(self, history: List[Dict[str, Any]]) -> None:
        """Save performance history for trend analysis.
        
        Args:
            history: List of performance measurements over time

        """
        try:
            # Load existing history and append new entries
            existing_history = self.load_performance_history()
            existing_history.extend(history)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(existing_history) > 1000:
                existing_history = existing_history[-1000:]
            
            with open(self.performance_history_path, 'w') as f:
                json.dump(existing_history, f, indent=2)
            logger.debug(f"Saved performance history to {self.performance_history_path}")
        except Exception as e:
            logger.error(f"Failed to save performance history: {e}")

    def load_performance_history(self) -> List[Dict[str, Any]]:
        """Load performance history.
        
        Returns:
            List of performance measurements over time

        """
        try:
            if self.performance_history_path.exists():
                with open(self.performance_history_path, 'r') as f:
                    history = json.load(f)
                logger.debug(f"Loaded performance history from {self.performance_history_path}")
                return history
        except Exception as e:
            logger.error(f"Failed to load performance history: {e}")
        
        return []

    def get_learning_summary(self) -> Dict[str, Any]:
        """Get a summary of all learning data.
        
        Returns:
            Summary of stored learning data

        """
        try:
            causal_patterns = self.load_causal_patterns()
            parallel_stats = self.load_parallel_stats()
            performance_history = self.load_performance_history()
            
            return {
                "causal_patterns_count": len(causal_patterns.get("conflict_patterns", {})),
                "parallel_sessions": parallel_stats.get("total_sessions", 0),
                "performance_entries": len(performance_history),
                "avg_speedup": parallel_stats.get("avg_speedup", 1.0),
                "learning_data_size": self._calculate_storage_size()
            }
        except Exception as e:
            logger.error(f"Failed to generate learning summary: {e}")
            return {}

    def _calculate_storage_size(self) -> int:
        """Calculate total size of learning data in bytes."""
        total_size = 0
        for path in [self.causal_patterns_path, self.parallel_stats_path, self.performance_history_path]:
            if path.exists():
                total_size += path.stat().st_size
        return total_size

    def clear_learning_data(self) -> None:
        """Clear all learning data (for testing or reset)."""
        try:
            for path in [self.causal_patterns_path, self.parallel_stats_path, self.performance_history_path]:
                if path.exists():
                    path.unlink()
            logger.info("Cleared all learning data")
        except Exception as e:
            logger.error(f"Failed to clear learning data: {e}")

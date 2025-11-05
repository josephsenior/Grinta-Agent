"""
Context Playbook - Structured knowledge management system

Manages evolving playbooks that accumulate strategies and insights
through incremental updates that prevent context collapse.
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import re

from openhands.core.logger import openhands_logger as logger


class BulletSection(Enum):
    """Sections for organizing knowledge in the context playbook"""
    STRATEGIES_AND_HARD_RULES = "strategies_and_hard_rules"
    APIS_TO_USE = "apis_to_use_for_specific_information"
    VERIFICATION_CHECKLIST = "verification_checklist"
    COMMON_MISTAKES = "common_mistakes"
    DOMAIN_INSIGHTS = "domain_specific_insights"
    TOOLS_AND_UTILITIES = "tools_and_utilities"
    CODE_PATTERNS = "code_patterns"
    DEBUGGING_TIPS = "debugging_tips"


@dataclass
class BulletPoint:
    """A single knowledge item in the context playbook"""
    id: str
    content: str
    section: BulletSection
    helpful_count: int = 0
    harmful_count: int = 0
    created_at: datetime = None
    last_updated: datetime = None
    tags: List[str] = None
    usage_count: int = 0
    last_used: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = datetime.now()
        if self.tags is None:
            self.tags = []
    
    @property
    def helpfulness_score(self) -> float:
        """Calculate helpfulness score based on usage feedback"""
        total_feedback = self.helpful_count + self.harmful_count
        if total_feedback == 0:
            return 0.5  # Neutral score for unused bullets
        return self.helpful_count / total_feedback
    
    @property
    def is_stale(self) -> bool:
        """Check if bullet is stale (not used recently)"""
        if self.last_used is None:
            return self.last_updated < datetime.now() - timedelta(days=30)
        return self.last_used < datetime.now() - timedelta(days=14)
    
    def mark_used(self):
        """Mark bullet as used and update timestamps"""
        self.usage_count += 1
        self.last_used = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'id': self.id,
            'content': self.content,
            'section': self.section.value,
            'helpful_count': self.helpful_count,
            'harmful_count': self.harmful_count,
            'created_at': self.created_at.isoformat(),
            'last_updated': self.last_updated.isoformat(),
            'tags': self.tags,
            'usage_count': self.usage_count,
            'last_used': self.last_used.isoformat() if self.last_used else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BulletPoint':
        """Create from dictionary for deserialization"""
        return cls(
            id=data['id'],
            content=data['content'],
            section=BulletSection(data['section']),
            helpful_count=data['helpful_count'],
            harmful_count=data['harmful_count'],
            created_at=datetime.fromisoformat(data['created_at']),
            last_updated=datetime.fromisoformat(data['last_updated']),
            tags=data['tags'],
            usage_count=data['usage_count'],
            last_used=datetime.fromisoformat(data['last_used']) if data['last_used'] else None
        )


class ContextPlaybook:
    """
    Manages structured context playbooks that evolve over time
    Prevents context collapse through incremental updates
    """
    
    def __init__(self, max_bullets: int = 1000, enable_grow_and_refine: bool = True):
        self.max_bullets = max_bullets
        self.enable_grow_and_refine = enable_grow_and_refine
        self.bullets: Dict[str, BulletPoint] = {}
        self.sections: Dict[BulletSection, List[str]] = {
            section: [] for section in BulletSection
        }
        self.performance_metrics = {
            'total_updates': 0,
            'successful_insights': 0,
            'failed_insights': 0,
            'bullets_added': 0,
            'bullets_removed': 0,
            'redundancy_checks': 0,
            'last_cleanup': datetime.now().isoformat()
        }
        self._content_hash_cache: Dict[str, str] = {}
    
    def add_bullet(self, content: str, section: BulletSection, 
                   bullet_id: Optional[str] = None, tags: List[str] = None) -> str:
        """Add a new bullet point to the playbook"""
        if bullet_id is None:
            bullet_id = f"ctx-{len(self.bullets):05d}"
        
        if bullet_id in self.bullets:
            raise ValueError(f"Bullet ID {bullet_id} already exists")
        
        # Check for redundancy if grow-and-refine is enabled
        if self.enable_grow_and_refine:
            if self._is_redundant(content, section):
                logger.debug(f"Skipping redundant bullet: {content[:50]}...")
                return None
        
        bullet = BulletPoint(
            id=bullet_id,
            content=content,
            section=section,
            tags=tags or []
        )
        
        self.bullets[bullet_id] = bullet
        self.sections[section].append(bullet_id)
        self.performance_metrics['total_updates'] += 1
        self.performance_metrics['bullets_added'] += 1
        
        # Update content hash cache
        self._content_hash_cache[bullet_id] = self._compute_content_hash(content)
        
        logger.debug(f"Added bullet {bullet_id} to section {section.value}")
        return bullet_id
    
    def update_bullet(self, bullet_id: str, content: str = None, 
                     helpful: bool = None, harmful: bool = None) -> bool:
        """Update an existing bullet point"""
        if bullet_id not in self.bullets:
            return False
        
        bullet = self.bullets[bullet_id]
        
        if content is not None:
            bullet.content = content
            bullet.last_updated = datetime.now()
            # Update content hash cache
            self._content_hash_cache[bullet_id] = self._compute_content_hash(content)
        
        if helpful:
            bullet.helpful_count += 1
            self.performance_metrics['successful_insights'] += 1
        
        if harmful:
            bullet.harmful_count += 1
            self.performance_metrics['failed_insights'] += 1
        
        return True
    
    def get_relevant_bullets(self, query: str, section: BulletSection = None, 
                           limit: int = 10, min_helpfulness: float = 0.0) -> List[BulletPoint]:
        """Retrieve relevant bullet points for a query"""
        if section:
            bullet_ids = self.sections[section]
        else:
            bullet_ids = list(self.bullets.keys())
        
        # Filter by helpfulness score
        relevant_bullets = []
        for bullet_id in bullet_ids:
            bullet = self.bullets[bullet_id]
            if bullet.helpfulness_score >= min_helpfulness:
                # Basic keyword matching (can be enhanced with embeddings)
                query_words = set(word.lower() for word in query.split())
                content_words = set(word.lower() for word in bullet.content.split())
                
                # Calculate relevance score
                overlap = len(query_words.intersection(content_words))
                if overlap > 0 or len(query_words) == 0:
                    relevant_bullets.append((bullet, overlap))
        
        # Sort by relevance score (overlap) then by helpfulness
        relevant_bullets.sort(key=lambda x: (x[1], x[0].helpfulness_score), reverse=True)
        
        # Mark bullets as used
        result = []
        for bullet, _ in relevant_bullets[:limit]:
            bullet.mark_used()
            result.append(bullet)
        
        return result
    
    def get_playbook_content(self, sections: List[BulletSection] = None, 
                           max_bullets: int = 50) -> str:
        """Get formatted playbook content for LLM consumption"""
        if sections is None:
            sections = list(BulletSection)
        
        content = "ACE PLAYBOOK:\n"
        content += "=" * 50 + "\n\n"
        
        total_bullets = 0
        for section in sections:
            if section in self.sections and self.sections[section]:
                section_bullets = []
                for bullet_id in self.sections[section]:
                    bullet = self.bullets[bullet_id]
                    section_bullets.append(bullet)
                
                # Sort by helpfulness score
                section_bullets.sort(key=lambda b: b.helpfulness_score, reverse=True)
                
                if section_bullets:
                    content += f"## {section.value.replace('_', ' ').title()}\n"
                    for bullet in section_bullets[:max_bullets // len(sections)]:
                        content += f"[{bullet.id}] helpful={bullet.helpful_count} harmful={bullet.harmful_count} :: {bullet.content}\n"
                        total_bullets += 1
                        if total_bullets >= max_bullets:
                            break
                    content += "\n"
                
                if total_bullets >= max_bullets:
                    break
        
        return content
    
    def cleanup_old_bullets(self, max_age_days: int = 30, 
                          min_usage_count: int = 1) -> int:
        """Remove old, unhelpful bullet points"""
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        to_remove = []
        for bullet_id, bullet in self.bullets.items():
            if (bullet.last_updated < cutoff_date and 
                bullet.usage_count < min_usage_count and
                bullet.helpfulness_score < 0.3):
                to_remove.append(bullet_id)
        
        for bullet_id in to_remove:
            self.remove_bullet(bullet_id)
        
        self.performance_metrics['last_cleanup'] = datetime.now().isoformat()
        return len(to_remove)
    
    def remove_bullet(self, bullet_id: str) -> bool:
        """Remove a bullet point from the playbook"""
        if bullet_id not in self.bullets:
            return False
        
        bullet = self.bullets[bullet_id]
        self.sections[bullet.section].remove(bullet_id)
        del self.bullets[bullet_id]
        
        # Remove from content hash cache
        if bullet_id in self._content_hash_cache:
            del self._content_hash_cache[bullet_id]
        
        self.performance_metrics['bullets_removed'] += 1
        return True
    
    def _is_redundant(self, content: str, section: BulletSection) -> bool:
        """Check if content is redundant with existing bullets"""
        self.performance_metrics['redundancy_checks'] += 1
        
        content_hash = self._compute_content_hash(content)
        
        # Check for exact duplicates
        for bullet_id, bullet in self.bullets.items():
            if bullet.section == section:
                if self._content_hash_cache.get(bullet_id) == content_hash:
                    return True
                
                # Check for high similarity (simple approach)
                if self._compute_similarity(content, bullet.content) > 0.8:
                    return True
        
        return False
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute hash of content for duplicate detection"""
        # Normalize content for comparison
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _compute_similarity(self, content1: str, content2: str) -> float:
        """Compute simple similarity between two content strings"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def grow_and_refine(self) -> Dict[str, int]:
        """Apply grow-and-refine mechanism to maintain playbook quality"""
        if not self.enable_grow_and_refine:
            return {'refined': 0, 'removed': 0}
        
        # Remove stale bullets
        removed = self.cleanup_old_bullets()
        
        # If we're over the limit, remove least helpful bullets
        if len(self.bullets) > self.max_bullets:
            bullets_by_score = sorted(
                self.bullets.items(),
                key=lambda x: (x[1].helpfulness_score, x[1].usage_count)
            )
            
            excess = len(self.bullets) - self.max_bullets
            for bullet_id, _ in bullets_by_score[:excess]:
                self.remove_bullet(bullet_id)
                removed += 1
        
        return {'refined': 0, 'removed': removed}
    
    def export_playbook(self) -> Dict[str, Any]:
        """Export playbook for persistence"""
        return {
            'bullets': {bid: bullet.to_dict() for bid, bullet in self.bullets.items()},
            'sections': {section.value: bullet_ids for section, bullet_ids in self.sections.items()},
            'performance_metrics': self.performance_metrics,
            'exported_at': datetime.now().isoformat(),
            'version': '1.0'
        }
    
    def import_playbook(self, data: Dict[str, Any]):
        """Import playbook from persistence"""
        self.bullets = {}
        self.sections = {section: [] for section in BulletSection}
        
        # Import bullets
        for bullet_id, bullet_data in data['bullets'].items():
            bullet = BulletPoint.from_dict(bullet_data)
            self.bullets[bullet_id] = bullet
            self.sections[bullet.section].append(bullet_id)
            
            # Rebuild content hash cache
            self._content_hash_cache[bullet_id] = self._compute_content_hash(bullet.content)
        
        # Import performance metrics
        self.performance_metrics = data.get('performance_metrics', {})
        
        logger.info(f"Imported playbook with {len(self.bullets)} bullets")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get playbook statistics for monitoring"""
        total_bullets = len(self.bullets)
        if total_bullets == 0:
            return {'total_bullets': 0, 'sections': {}, 'performance': self.performance_metrics}
        
        section_stats = {}
        for section, bullet_ids in self.sections.items():
            if bullet_ids:
                bullets = [self.bullets[bid] for bid in bullet_ids]
                section_stats[section.value] = {
                    'count': len(bullets),
                    'avg_helpfulness': sum(b.helpfulness_score for b in bullets) / len(bullets),
                    'total_usage': sum(b.usage_count for b in bullets)
                }
        
        return {
            'total_bullets': total_bullets,
            'sections': section_stats,
            'performance': self.performance_metrics,
            'avg_helpfulness': sum(b.helpfulness_score for b in self.bullets.values()) / total_bullets,
            'total_usage': sum(b.usage_count for b in self.bullets.values())
        }

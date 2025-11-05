"""
Unit tests for ContextPlaybook
"""

import pytest
from datetime import datetime, timedelta
from openhands.metasop.ace.context_playbook import ContextPlaybook, BulletPoint, BulletSection


class TestBulletPoint:
    """Test BulletPoint functionality"""
    
    def test_bullet_point_creation(self):
        """Test creating a bullet point"""
        bullet = BulletPoint(
            id="test-001",
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        assert bullet.id == "test-001"
        assert bullet.content == "Test strategy"
        assert bullet.section == BulletSection.STRATEGIES_AND_HARD_RULES
        assert bullet.helpful_count == 0
        assert bullet.harmful_count == 0
        assert bullet.usage_count == 0
        assert bullet.tags == []
    
    def test_helpfulness_score(self):
        """Test helpfulness score calculation"""
        bullet = BulletPoint(
            id="test-001",
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # No feedback yet
        assert bullet.helpfulness_score == 0.5
        
        # Add helpful feedback
        bullet.helpful_count = 3
        bullet.harmful_count = 1
        assert bullet.helpfulness_score == 0.75
    
    def test_mark_used(self):
        """Test marking bullet as used"""
        bullet = BulletPoint(
            id="test-001",
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        initial_usage = bullet.usage_count
        bullet.mark_used()
        
        assert bullet.usage_count == initial_usage + 1
        assert bullet.last_used is not None
    
    def test_is_stale(self):
        """Test stale detection"""
        bullet = BulletPoint(
            id="test-001",
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Not stale if recently updated
        assert not bullet.is_stale
        
        # Make it stale
        bullet.last_updated = datetime.now() - timedelta(days=35)
        assert bullet.is_stale


class TestContextPlaybook:
    """Test ContextPlaybook functionality"""
    
    def test_playbook_creation(self):
        """Test creating a context playbook"""
        playbook = ContextPlaybook()
        
        assert len(playbook.bullets) == 0
        assert len(playbook.sections) == len(BulletSection)
        assert playbook.performance_metrics['total_updates'] == 0
    
    def test_add_bullet(self):
        """Test adding a bullet point"""
        playbook = ContextPlaybook()
        
        bullet_id = playbook.add_bullet(
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            tags=["test", "strategy"]
        )
        
        assert bullet_id is not None
        assert bullet_id in playbook.bullets
        assert bullet_id in playbook.sections[BulletSection.STRATEGIES_AND_HARD_RULES]
        
        bullet = playbook.bullets[bullet_id]
        assert bullet.content == "Test strategy"
        assert bullet.tags == ["test", "strategy"]
    
    def test_update_bullet(self):
        """Test updating a bullet point"""
        playbook = ContextPlaybook()
        
        bullet_id = playbook.add_bullet(
            content="Test strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Update content
        success = playbook.update_bullet(bullet_id, content="Updated strategy")
        assert success
        assert playbook.bullets[bullet_id].content == "Updated strategy"
        
        # Mark as helpful
        success = playbook.update_bullet(bullet_id, helpful=True)
        assert success
        assert playbook.bullets[bullet_id].helpful_count == 1
    
    def test_get_relevant_bullets(self):
        """Test retrieving relevant bullets"""
        playbook = ContextPlaybook()
        
        # Add some bullets
        bullet1 = playbook.add_bullet(
            content="Python coding strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        bullet2 = playbook.add_bullet(
            content="JavaScript debugging tips",
            section=BulletSection.DEBUGGING_TIPS
        )
        bullet3 = playbook.add_bullet(
            content="Database optimization",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Search for Python-related bullets
        relevant = playbook.get_relevant_bullets("Python coding", limit=5)
        
        assert len(relevant) >= 1
        assert any("Python" in bullet.content for bullet in relevant)
    
    def test_get_playbook_content(self):
        """Test getting formatted playbook content"""
        playbook = ContextPlaybook()
        
        # Add some bullets
        playbook.add_bullet(
            content="Test strategy 1",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        playbook.add_bullet(
            content="Test strategy 2",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        content = playbook.get_playbook_content()
        
        assert "ACE PLAYBOOK:" in content
        assert "Test strategy 1" in content
        assert "Test strategy 2" in content
    
    def test_cleanup_old_bullets(self):
        """Test cleaning up old bullets"""
        playbook = ContextPlaybook()
        
        # Add a bullet
        bullet_id = playbook.add_bullet(
            content="Old strategy",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Make it old and unhelpful
        bullet = playbook.bullets[bullet_id]
        bullet.last_updated = datetime.now() - timedelta(days=35)
        bullet.usage_count = 0
        bullet.harmful_count = 2
        bullet.helpful_count = 0
        
        # Cleanup
        removed_count = playbook.cleanup_old_bullets(max_age_days=30, min_usage_count=1)
        
        assert removed_count == 1
        assert bullet_id not in playbook.bullets
    
    def test_grow_and_refine(self):
        """Test grow-and-refine mechanism"""
        playbook = ContextPlaybook(max_bullets=3)
        
        # Add bullets up to limit
        for i in range(3):
            playbook.add_bullet(
                content=f"Strategy {i}",
                section=BulletSection.STRATEGIES_AND_HARD_RULES
            )
        
        # Add one more (should trigger grow-and-refine)
        playbook.add_bullet(
            content="Strategy 3",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Apply grow-and-refine
        stats = playbook.grow_and_refine()
        
        # Should have removed some bullets to stay under limit
        assert len(playbook.bullets) <= 3
        assert stats['removed'] >= 1
    
    def test_export_import_playbook(self):
        """Test exporting and importing playbook"""
        playbook = ContextPlaybook()
        
        # Add some bullets
        bullet1 = playbook.add_bullet(
            content="Test strategy 1",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            tags=["test"]
        )
        bullet2 = playbook.add_bullet(
            content="Test strategy 2",
            section=BulletSection.DEBUGGING_TIPS,
            tags=["debug"]
        )
        
        # Mark as helpful
        playbook.update_bullet(bullet1, helpful=True)
        playbook.update_bullet(bullet2, harmful=True)
        
        # Export
        exported = playbook.export_playbook()
        
        assert "bullets" in exported
        assert "sections" in exported
        assert "performance_metrics" in exported
        assert bullet1 in exported["bullets"]
        assert bullet2 in exported["bullets"]
        
        # Create new playbook and import
        new_playbook = ContextPlaybook()
        new_playbook.import_playbook(exported)
        
        assert len(new_playbook.bullets) == 2
        assert bullet1 in new_playbook.bullets
        assert bullet2 in new_playbook.bullets
        assert new_playbook.bullets[bullet1].helpful_count == 1
        assert new_playbook.bullets[bullet2].harmful_count == 1
    
    def test_redundancy_detection(self):
        """Test redundancy detection"""
        playbook = ContextPlaybook(enable_grow_and_refine=True)
        
        # Add first bullet
        bullet1 = playbook.add_bullet(
            content="Python coding best practices",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Try to add similar bullet (should be rejected)
        bullet2 = playbook.add_bullet(
            content="Python coding best practices",  # Exact duplicate
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        
        # Should be None due to redundancy
        assert bullet2 is None
        assert len(playbook.bullets) == 1
    
    def test_statistics(self):
        """Test getting playbook statistics"""
        playbook = ContextPlaybook()
        
        # Add some bullets
        bullet1 = playbook.add_bullet(
            content="Strategy 1",
            section=BulletSection.STRATEGIES_AND_HARD_RULES
        )
        bullet2 = playbook.add_bullet(
            content="Strategy 2",
            section=BulletSection.DEBUGGING_TIPS
        )
        
        # Mark as helpful
        playbook.update_bullet(bullet1, helpful=True)
        playbook.update_bullet(bullet2, helpful=True)
        
        stats = playbook.get_statistics()
        
        assert stats['total_bullets'] == 2
        assert 'sections' in stats
        assert 'performance' in stats
        assert stats['avg_helpfulness'] > 0

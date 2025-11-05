"""
Playbook Inspection Example

This example shows how to inspect and analyze ACE playbooks
to understand what the agent has learned and how it's performing.
"""

import json
from datetime import datetime
from openhands.metasop.ace import ACEFramework, ContextPlaybook, ACEConfig
from openhands.metasop.ace.context_playbook import BulletSection


def inspect_playbook(playbook_path: str):
    """Inspect and analyze a saved playbook."""
    
    print(f"Inspecting playbook: {playbook_path}")
    print("=" * 50)
    
    # Load the playbook
    try:
        with open(playbook_path, 'r') as f:
            playbook_data = json.load(f)
    except FileNotFoundError:
        print(f"Playbook file not found: {playbook_path}")
        return None
    except json.JSONDecodeError:
        print(f"Invalid JSON in playbook file: {playbook_path}")
        return None
    
    # Create context playbook and load data
    playbook = ContextPlaybook()
    playbook.import_playbook(playbook_data)
    
    # Get statistics
    stats = playbook.get_statistics()
    
    print(f"Playbook Statistics:")
    print(f"  Total bullets: {stats['total_bullets']}")
    print(f"  Average helpfulness: {stats['avg_helpfulness']:.2f}")
    print(f"  Total usage: {stats['total_usage']}")
    
    # Show section breakdown
    if 'sections' in stats:
        print(f"\nSection Breakdown:")
        for section, section_stats in stats['sections'].items():
            print(f"  {section}:")
            print(f"    Count: {section_stats['count']}")
            print(f"    Avg helpfulness: {section_stats['avg_helpfulness']:.2f}")
            print(f"    Total usage: {section_stats['total_usage']}")
    
    # Show performance metrics
    if 'performance' in stats:
        perf = stats['performance']
        print(f"\nPerformance Metrics:")
        print(f"  Total updates: {perf['total_updates']}")
        print(f"  Successful insights: {perf['successful_insights']}")
        print(f"  Failed insights: {perf['failed_insights']}")
        print(f"  Bullets added: {perf['bullets_added']}")
        print(f"  Bullets removed: {perf['bullets_removed']}")
        print(f"  Redundancy checks: {perf['redundancy_checks']}")
        print(f"  Last cleanup: {perf['last_cleanup']}")
    
    return playbook


def analyze_bullet_quality(playbook: ContextPlaybook):
    """Analyze the quality of bullets in the playbook."""
    
    print(f"\nBullet Quality Analysis:")
    print("-" * 30)
    
    # Analyze helpfulness distribution
    helpfulness_scores = []
    for bullet in playbook.bullets.values():
        helpfulness_scores.append(bullet.helpfulness_score)
    
    if helpfulness_scores:
        avg_helpfulness = sum(helpfulness_scores) / len(helpfulness_scores)
        min_helpfulness = min(helpfulness_scores)
        max_helpfulness = max(helpfulness_scores)
        
        print(f"Helpfulness Score Distribution:")
        print(f"  Average: {avg_helpfulness:.2f}")
        print(f"  Min: {min_helpfulness:.2f}")
        print(f"  Max: {max_helpfulness:.2f}")
        
        # Count by helpfulness ranges
        excellent = sum(1 for score in helpfulness_scores if score >= 0.8)
        good = sum(1 for score in helpfulness_scores if 0.6 <= score < 0.8)
        neutral = sum(1 for score in helpfulness_scores if 0.4 <= score < 0.6)
        poor = sum(1 for score in helpfulness_scores if score < 0.4)
        
        total = len(helpfulness_scores)
        print(f"\nQuality Distribution:")
        print(f"  Excellent (≥0.8): {excellent} ({excellent/total*100:.1f}%)")
        print(f"  Good (0.6-0.8): {good} ({good/total*100:.1f}%)")
        print(f"  Neutral (0.4-0.6): {neutral} ({neutral/total*100:.1f}%)")
        print(f"  Poor (<0.4): {poor} ({poor/total*100:.1f}%)")
    
    # Analyze usage patterns
    usage_counts = [bullet.usage_count for bullet in playbook.bullets.values()]
    if usage_counts:
        avg_usage = sum(usage_counts) / len(usage_counts)
        max_usage = max(usage_counts)
        
        print(f"\nUsage Patterns:")
        print(f"  Average usage: {avg_usage:.1f}")
        print(f"  Max usage: {max_usage}")
        
        # Find most and least used bullets
        most_used = max(playbook.bullets.values(), key=lambda b: b.usage_count)
        least_used = min(playbook.bullets.values(), key=lambda b: b.usage_count)
        
        print(f"\nMost Used Bullet:")
        print(f"  ID: {most_used.id}")
        print(f"  Usage: {most_used.usage_count}")
        print(f"  Content: {most_used.content[:100]}...")
        
        print(f"\nLeast Used Bullet:")
        print(f"  ID: {least_used.id}")
        print(f"  Usage: {least_used.usage_count}")
        print(f"  Content: {least_used.content[:100]}...")


def show_top_strategies(playbook: ContextPlaybook, section: BulletSection = None, limit: int = 10):
    """Show the top strategies by helpfulness score."""
    
    print(f"\nTop Strategies (by helpfulness):")
    print("-" * 40)
    
    # Get bullets from specific section or all sections
    if section:
        bullets = [playbook.bullets[bid] for bid in playbook.sections[section]]
    else:
        bullets = list(playbook.bullets.values())
    
    # Sort by helpfulness score
    sorted_bullets = sorted(bullets, key=lambda b: b.helpfulness_score, reverse=True)
    
    for i, bullet in enumerate(sorted_bullets[:limit], 1):
        print(f"{i:2d}. [{bullet.id}] Score: {bullet.helpfulness_score:.2f}")
        print(f"    Section: {bullet.section.value}")
        print(f"    Usage: {bullet.usage_count}, Helpful: {bullet.helpful_count}, Harmful: {bullet.harmful_count}")
        print(f"    Content: {bullet.content[:150]}...")
        if bullet.tags:
            print(f"    Tags: {', '.join(bullet.tags)}")
        print()


def show_recent_insights(playbook: ContextPlaybook, days: int = 7, limit: int = 10):
    """Show recent insights added to the playbook."""
    
    print(f"\nRecent Insights (last {days} days):")
    print("-" * 40)
    
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_bullets = [
        bullet for bullet in playbook.bullets.values()
        if bullet.created_at >= cutoff_date
    ]
    
    # Sort by creation date (newest first)
    recent_bullets.sort(key=lambda b: b.created_at, reverse=True)
    
    for i, bullet in enumerate(recent_bullets[:limit], 1):
        print(f"{i:2d}. [{bullet.id}] Created: {bullet.created_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Section: {bullet.section.value}")
        print(f"    Content: {bullet.content[:150]}...")
        print()


def export_playbook_analysis(playbook: ContextPlaybook, output_path: str):
    """Export detailed playbook analysis to a file."""
    
    analysis = {
        "timestamp": datetime.now().isoformat(),
        "statistics": playbook.get_statistics(),
        "bullets": []
    }
    
    # Add detailed bullet information
    for bullet in playbook.bullets.values():
        bullet_info = {
            "id": bullet.id,
            "content": bullet.content,
            "section": bullet.section.value,
            "helpful_count": bullet.helpful_count,
            "harmful_count": bullet.harmful_count,
            "helpfulness_score": bullet.helpfulness_score,
            "usage_count": bullet.usage_count,
            "created_at": bullet.created_at.isoformat(),
            "last_updated": bullet.last_updated.isoformat(),
            "last_used": bullet.last_used.isoformat() if bullet.last_used else None,
            "tags": bullet.tags,
            "is_stale": bullet.is_stale
        }
        analysis["bullets"].append(bullet_info)
    
    # Save analysis
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    print(f"Detailed analysis exported to: {output_path}")


def main():
    """Main function to demonstrate playbook inspection."""
    
    print("ACE Framework - Playbook Inspection Example")
    print("=" * 50)
    
    # Example playbook path (you would replace this with actual path)
    playbook_path = "example_playbook.json"
    
    # Inspect the playbook
    playbook = inspect_playbook(playbook_path)
    
    if playbook is None:
        print("Creating a sample playbook for demonstration...")
        
        # Create a sample playbook
        config = ACEConfig(enable_ace=True)
        sample_playbook = ContextPlaybook(max_bullets=100)
        
        # Add some sample bullets
        sample_playbook.add_bullet(
            content="Always validate user input before processing",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            tags=["security", "validation"]
        )
        
        sample_playbook.add_bullet(
            content="Use prepared statements for database queries",
            section=BulletSection.STRATEGIES_AND_HARD_RULES,
            tags=["security", "database"]
        )
        
        sample_playbook.add_bullet(
            content="Check for null pointer exceptions in Java code",
            section=BulletSection.COMMON_MISTAKES,
            tags=["java", "debugging"]
        )
        
        # Mark some as helpful
        sample_playbook.update_bullet(list(sample_playbook.bullets.keys())[0], helpful=True)
        sample_playbook.update_bullet(list(sample_playbook.bullets.keys())[1], helpful=True)
        
        # Save sample playbook
        sample_playbook.export_playbook()
        with open(playbook_path, 'w') as f:
            json.dump(sample_playbook.export_playbook(), f, indent=2)
        
        print(f"Sample playbook created: {playbook_path}")
        playbook = sample_playbook
    
    # Analyze bullet quality
    analyze_bullet_quality(playbook)
    
    # Show top strategies
    show_top_strategies(playbook, limit=5)
    
    # Show recent insights
    show_recent_insights(playbook, days=30, limit=5)
    
    # Export detailed analysis
    export_playbook_analysis(playbook, "playbook_analysis.json")
    
    print("\nPlaybook inspection completed!")


if __name__ == "__main__":
    main()

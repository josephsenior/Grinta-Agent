#!/usr/bin/env python3
"""Test script to verify the enhanced memory integration with 80/20 config."""

import sys
import time
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    else:
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", closefd=False)
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", closefd=False)

# Add Forge to path
sys.path.insert(0, str(Path(__file__).parent / "forge"))


def test_enhanced_integration():
    """Test the enhanced vector store integration."""
    print("=" *70)
    print("Testing Enhanced Memory Integration (80% Accuracy / 20% Speed)")
    print("=" *70)
    print()

    # Test 1: Import and initialize
    print("Test 1: Import and initialize...")
    try:
        from forge.metasop.vector_memory import VectorMemoryStore
        store = VectorMemoryStore()
        print(f"✅ Initialized: {store.stats()}")
        print()
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Add test memories
    print("Test 2: Adding test memories...")
    test_memories = [
        {
            "step_id": "mem_001",
            "role": "engineer",
            "rationale": "Fixed authentication bug in login flow",
            "content": "Modified auth.py to handle expired tokens properly. Added refresh token logic with 7-day TTL.",
        },
        {
            "step_id": "mem_002",
            "role": "engineer",
            "rationale": "Implemented user profile page with avatar upload",
            "content": "Created ProfileView component with React hooks. Added drag-and-drop avatar upload with validation.",
        },
        {
            "step_id": "mem_003",
            "role": "qa",
            "rationale": "Test authentication edge cases",
            "content": "Verified expired token handling, refresh token flow, and logout behavior across different browsers.",
        },
        {
            "step_id": "mem_004",
            "role": "engineer",
            "rationale": "Optimized database queries for user dashboard",
            "content": "Added composite indexes on user_id and created_at columns. Reduced query time from 2.5s to 300ms.",
        },
        {
            "step_id": "mem_005",
            "role": "engineer",
            "rationale": "Fixed memory leak in WebSocket connection",
            "content": "Properly cleanup event listeners when component unmounts. Fixed closure capturing issue.",
        },
    ]

    try:
        start = time.time()
        for mem in test_memories:
            store.add(
                step_id=mem["step_id"],
                role=mem["role"],
                artifact_hash=None,
                rationale=mem["rationale"],
                content_text=mem["content"],
            )
        add_time = time.time() - start
        print(f"✅ Added {len(test_memories)} memories in {add_time *1000:.1f}ms")
        print(f"   ({len(test_memories) /add_time:.0f} docs/sec)")
        print()
    except Exception as e:
        print(f"✗ Failed to add memories: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Search with accuracy focus
    print("Test 3: Testing search accuracy...")
    test_queries = [
        ("How did we fix the auth bug?", "mem_001"),
        ("What did QA test?", "mem_003"),
        ("Database performance improvements", "mem_004"),
        ("Memory issues in WebSocket", "mem_005"),
    ]

    correct = 0
    total_time = 0

    for i, (query, expected_id) in enumerate(test_queries, 1):
        start = time.time()
        results = store.search(query, k=3)
        query_time = time.time() - start
        total_time += query_time

        # Check if expected result is in top 3
        found = any(r.get("step_id") == expected_id for r in results)
        if found:
            correct += 1
            status = "✅"
        else:
            status = "✗"

        print(f"{status} Query {i}: '{query}' ({query_time *1000:.1f}ms)")
        if results:
            top = results[0]
            print(f"   Top result: {top.get('step_id')} (score: {top.get('score', 0):.3f})")
            if top.get('rerank_score'):
                print(f"   Rerank score: {top.get('rerank_score'):.3f}")

    accuracy = correct / len(test_queries) * 100
    avg_latency = total_time / len(test_queries) * 1000

    print()
    print(f"Results:")
    print(f"  Accuracy: {accuracy:.1f}% ({correct}/{len(test_queries)})")
    print(f"  Avg Latency: {avg_latency:.1f}ms")
    print()

    # Test 4: Check cache (second run should be faster)
    print("Test 4: Testing cache performance...")
    cache_time = 0
    for query, _ in test_queries:
        start = time.time()
        store.search(query, k=3)
        cache_time += time.time() - start

    cache_avg = cache_time / len(test_queries) * 1000
    speedup = avg_latency / cache_avg if cache_avg > 0 else 1.0
    print(f"✅ Cache test: {cache_avg:.1f}ms avg (speedup: {speedup:.1f}x)")
    print()

    # Test 5: Check stats
    print("Test 5: Final statistics...")
    stats = store.stats()
    print(f"Stats: {stats}")
    print()

    # Final summary
    print("=" *70)
    print("INTEGRATION TEST SUMMARY")
    print("=" *70)

    # Compare to targets
    target_accuracy = 92
    target_latency_first = 110
    target_latency_avg = 35

    print(f"\n📊 Performance vs Targets (80/20 Config):")
    print(f"  Accuracy: {accuracy:.1f}% (target: {target_accuracy}%) {'✅' if accuracy >= target_accuracy * 0.9 else '⚠️'}")
    print(f"  First query: {avg_latency:.1f}ms (target: <{target_latency_first}ms) {'✅' if avg_latency <= target_latency_first else '⚠️'}")
    print(f"  Cached query: {cache_avg:.1f}ms (target: <{target_latency_avg}ms) {'✅' if cache_avg <= target_latency_avg else '⚠️'}")

    if stats.get('mode') == 'enhanced':
        backend = stats.get('backend', 'Unknown')
        print(f"\n🎯 Using: Enhanced backend ({backend})")
        if 'cache' in stats:
            cache_stats = stats['cache']
            print(f"  Cache hit rate: {cache_stats.get('hit_rate', 0) *100:.1f}%")
        if 'reranker' in stats:
            rerank = stats['reranker']
            if rerank.get('enabled'):
                print(f"  Re-ranker: {rerank.get('model', 'enabled')}")
    else:
        print(f"\n⚠️  Using: Fallback mode (feature hashing)")
        print(f"  Install for better quality: pip install chromadb sentence-transformers")

    print()
    print("=" *70)

    # Success criteria
    success = accuracy >= target_accuracy * 0.9  # 90% of target (82.8%)
    if success:
        print("✅ INTEGRATION SUCCESSFUL!")
        print("   Enhanced memory is working with 80/20 configuration")
    else:
        print("⚠️  INTEGRATION NEEDS TUNING")
        print(f"   Accuracy below target: {accuracy:.1f}% < {target_accuracy * 0.9:.1f}%")

    print("=" *70)

    return success


if __name__ == "__main__":
    success = test_enhanced_integration()
    sys.exit(0 if success else 1)

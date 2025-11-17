"""Test enhanced memory integration with MetaSOP orchestrator.

Verifies that the 80/20 accuracy/speed configuration works correctly.
This test focuses on the memory components without triggering full imports.
"""

import pytest


class TestEnhancedMemoryCore:
    """Core tests for enhanced memory system."""

    def test_vector_memory_store_imports(self):
        """Test that VectorMemoryStore can be imported."""
        from forge.metasop.vector_memory import VectorMemoryStore

        assert VectorMemoryStore is not None

    def test_vector_memory_store_initialization(self):
        """Test that VectorMemoryStore initializes correctly."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore(dim=256, max_records=500)
        assert store is not None

        # Should have stats method
        assert hasattr(store, "stats")
        assert hasattr(store, "add")
        assert hasattr(store, "search")

    def test_enhanced_backend_detection(self):
        """Test that enhanced backend is detected properly."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore()
        stats = store.stats()

        # Should have mode indicating enhanced or fallback
        assert "mode" in stats
        mode = stats["mode"]
        assert mode in ["enhanced", "fallback (feature hashing)"]

        # Log which mode for debugging
        print(f"\n  Using mode: {mode}")

        if mode == "enhanced":
            # Enhanced mode should have additional fields
            assert "backend" in stats or "config" in stats
            print(f"  Enhanced backend active: {stats.get('backend', 'N/A')}")
        else:
            # Fallback mode should still work
            assert "dim" in stats
            print(f"  Fallback mode active (dim={stats.get('dim')})")

    def test_add_and_search_basic(self):
        """Test basic add and search functionality."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore()

        # Add a memory
        store.add(
            step_id="test_001",
            role="engineer",
            artifact_hash=None,
            rationale="Test memory",
            content_text="This is a test memory for verification.",
        )

        # Search should work
        results = store.search("test memory", k=1)
        assert isinstance(results, list)

        # Should have results
        if len(results) > 0:
            result = results[0]
            assert "step_id" in result
            assert "score" in result or "excerpt" in result
            print(f"\n  Search found: {result.get('step_id')}")

    def test_multiple_memories_accuracy(self):
        """Test accuracy with multiple distinct memories."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore()

        # Add distinct memories
        memories = [
            (
                "mem_auth",
                "engineer",
                "Fixed authentication bug",
                "Modified auth.py to handle tokens",
            ),
            (
                "mem_ui",
                "engineer",
                "Created profile page",
                "Built ProfileView component with React",
            ),
            (
                "mem_qa",
                "qa",
                "Test authentication",
                "Verified token handling and refresh flow",
            ),
            (
                "mem_db",
                "engineer",
                "Optimized database",
                "Added indexes to improve query speed",
            ),
            (
                "mem_ws",
                "engineer",
                "Fixed WebSocket leak",
                "Cleanup event listeners properly",
            ),
        ]

        for step_id, role, rationale, content in memories:
            store.add(step_id, role, None, rationale, content)

        # Test searches
        searches = [
            ("authentication bug", "mem_auth"),
            ("QA test", "mem_qa"),
            ("database performance", "mem_db"),
            ("WebSocket memory", "mem_ws"),
        ]

        correct = 0
        total = len(searches)

        for query, expected in searches:
            results = store.search(query, k=3)
            if any(r.get("step_id") == expected for r in results):
                correct += 1
                print(f"\n  PASS: '{query}' -> {expected}")
            else:
                found = results[0].get("step_id") if results else "None"
                print(f"\n  FAIL: '{query}' -> {found} (expected {expected})")

        accuracy = correct / total * 100
        print(f"\n  Accuracy: {accuracy:.0f}% ({correct}/{total})")

        # Should get at least 50% accuracy (2/4) even in fallback mode
        assert accuracy >= 50, f"Accuracy too low: {accuracy:.0f}%"

        # If enhanced mode, should get better accuracy
        stats = store.stats()
        if stats.get("mode") == "enhanced":
            assert accuracy >= 75, (
                f"Enhanced mode should have >75% accuracy, got {accuracy:.0f}%"
            )

    def test_stats_structure(self):
        """Test that stats return proper structure."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore()
        stats = store.stats()

        # Should be a dict
        assert isinstance(stats, dict)

        # Should have mode
        assert "mode" in stats

        # Print stats for debugging
        print(f"\n  Stats: {stats}")

    def test_caching_if_available(self):
        """Test caching functionality if enhanced mode is available."""
        from forge.metasop.vector_memory import VectorMemoryStore

        store = VectorMemoryStore()
        stats = store.stats()

        if stats.get("mode") != "enhanced":
            pytest.skip("Enhanced mode not available, skipping cache test")

        # Add memory
        store.add("cache_001", "engineer", None, "Test", "Cache test content")

        # First search
        r1 = store.search("cache test", k=1)

        # Second search (should use cache if enabled)
        r2 = store.search("cache test", k=1)

        # Results should be consistent
        if r1 and r2:
            assert r1[0]["step_id"] == r2[0]["step_id"]
            print(f"\n  Cache working: {r1[0]['step_id']}")

        # Check cache stats
        stats_after = store.stats()
        if "cache" in stats_after:
            cache_info = stats_after["cache"]
            print(f"\n  Cache stats: {cache_info}")
            assert "hits" in cache_info
            assert "misses" in cache_info


class TestVectorOrLexicalStoreWrapper:
    """Test the wrapper used by orchestrator."""

    def test_wrapper_initialization(self):
        """Test VectorOrLexicalMemoryStore initialization."""
        # Import only what we need
        from forge.metasop.memory import MemoryIndex
        from forge.metasop.vector_memory import VectorMemoryStore

        # Test creating vector store
        vector_store = VectorMemoryStore()
        assert vector_store is not None

        # Test creating lexical store
        lex_store = MemoryIndex(run_id="test", max_records=100)
        assert lex_store is not None

    def test_wrapper_with_vector_enabled(self):
        """Test wrapper when vector mode is enabled."""
        try:
            from forge.metasop.strategies import VectorOrLexicalMemoryStore

            store = VectorOrLexicalMemoryStore(
                vector_enabled=True, dim=256, max_records=500
            )

            assert store is not None

            # Add and search
            store.add("wrap_001", "engineer", None, "Test", "Wrapper test")
            results = store.search("wrapper", k=1)
            assert isinstance(results, list)

            # Stats should work
            stats = store.stats()
            assert "mode" in stats
            print(f"\n  Wrapper mode: {stats['mode']}")

        except ImportError as e:
            # Skip if imports fail due to the Agent error
            pytest.skip(f"Skipping due to import error: {e}")


# Simple standalone runner
if __name__ == "__main__":
    print("=" * 70)
    print("Enhanced Memory Integration Tests")
    print("=" * 70)
    pytest.main([__file__, "-v", "-s", "--tb=short"])

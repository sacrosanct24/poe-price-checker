"""
Performance tests to validate optimization improvements.

These tests ensure that the regex compilation and caching optimizations
provide measurable performance improvements.
"""
import time
import pytest
from pathlib import Path

from core.item_parser import ItemParser
from core.rare_evaluation import RareItemEvaluator


class TestRareItemEvaluatorPerformance:
    """Test performance of rare item evaluation with optimizations."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance (with pre-compiled patterns)."""
        return RareItemEvaluator()

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return ItemParser()

    @pytest.fixture
    def sample_rare_items(self, parser):
        """Create sample rare items for testing."""
        items = []
        
        # Sample 1: Good rare helmet
        items.append(parser.parse("""Rarity: RARE
Doom Visor
Hubris Circlet
--------
Item Level: 86
--------
+45 to maximum Energy Shield (implicit)
--------
+78 to maximum Life
+42% to Fire Resistance
+38% to Cold Resistance
+15% to Chaos Resistance
+85 to maximum Energy Shield
"""))
        
        # Sample 2: Rare ring
        items.append(parser.parse("""Rarity: RARE
Vortex Band
Vermillion Ring
--------
Item Level: 84
--------
+10 to Strength (implicit)
--------
+65 to maximum Life
+38% to Fire Resistance
+42% to Lightning Resistance
+12% to Chaos Resistance
7% increased Rarity of Items found
"""))
        
        # Sample 3: Rare boots
        items.append(parser.parse("""Rarity: RARE
Storm Tread
Two-Toned Boots
--------
Item Level: 85
--------
+15% to Cold and Lightning Resistances (implicit)
--------
+75 to maximum Life
+30% to Fire Resistance
+28% to Cold Resistance
30% increased Movement Speed
"""))
        
        # Sample 4: Rare body armour
        items.append(parser.parse("""Rarity: RARE
Gale Shell
Vaal Regalia
--------
Item Level: 86
--------
+100 to maximum Energy Shield
--------
+85 to maximum Life
+45% to Fire Resistance
+38% to Cold Resistance
+12% to Chaos Resistance
+120 to maximum Energy Shield
"""))
        
        # Sample 5: Rare gloves
        items.append(parser.parse("""Rarity: RARE
Thunder Grasp
Sorcerer Gloves
--------
Item Level: 84
--------
+48 to maximum Energy Shield (implicit)
--------
+72 to maximum Life
+40% to Cold Resistance
+35% to Lightning Resistance
+65 to maximum Energy Shield
"""))
        
        return [item for item in items if item is not None]

    def test_pre_compiled_patterns_exist(self, evaluator):
        """Verify that patterns are pre-compiled during initialization."""
        assert hasattr(evaluator, '_compiled_patterns')
        assert hasattr(evaluator, '_compiled_influence_patterns')
        assert len(evaluator._compiled_patterns) > 0
        
    def test_cached_slot_determination(self, evaluator):
        """Test that slot determination uses caching."""
        # The cached method should exist
        assert hasattr(evaluator, '_determine_slot_from_base_type')
        
        # Test caching works
        base_type = "Hubris Circlet"
        
        # First call - cache miss
        result1 = evaluator._determine_slot_from_base_type(base_type)
        assert result1 == "helmet"
        
        # Second call - cache hit (should be instant)
        result2 = evaluator._determine_slot_from_base_type(base_type)
        assert result2 == result1
        
    def test_evaluation_performance(self, evaluator, sample_rare_items):
        """Test that evaluation is reasonably fast with optimizations."""
        # Warm up
        for item in sample_rare_items[:2]:
            evaluator.evaluate(item)
        
        # Time evaluation of multiple items
        start_time = time.time()
        
        results = []
        for item in sample_rare_items:
            result = evaluator.evaluate(item)
            results.append(result)
        
        elapsed_time = time.time() - start_time
        
        # With optimizations, should evaluate 5 items in under 0.5 seconds
        # (This is a reasonable threshold for optimized regex matching)
        assert elapsed_time < 0.5, f"Evaluation took {elapsed_time:.3f}s (expected < 0.5s)"
        
        # Verify results are valid
        assert len(results) == len(sample_rare_items)
        for result in results:
            assert result.total_score >= 0
            assert result.tier in ["excellent", "good", "average", "vendor", "not_rare"]
            
    def test_bulk_evaluation_performance(self, evaluator, sample_rare_items):
        """Test performance when evaluating many items (simulating bulk operation)."""
        # Create a larger dataset by repeating items
        bulk_items = sample_rare_items * 10  # 50 items total
        
        start_time = time.time()
        
        results = []
        for item in bulk_items:
            result = evaluator.evaluate(item)
            results.append(result)
        
        elapsed_time = time.time() - start_time
        items_per_second = len(bulk_items) / elapsed_time
        
        # Should process at least 20 items per second with optimizations
        assert items_per_second > 20, \
            f"Only processed {items_per_second:.1f} items/sec (expected > 20)"
        
        # Log performance metrics
        print("\nBulk evaluation performance:")
        print(f"  Items evaluated: {len(bulk_items)}")
        print(f"  Time elapsed: {elapsed_time:.3f}s")
        print(f"  Items/second: {items_per_second:.1f}")
        
    def test_no_regex_compilation_in_hot_path(self, evaluator, sample_rare_items, monkeypatch):
        """Verify that regex compilation doesn't happen during evaluation."""
        import re
        
        # Track regex compilation calls
        compile_calls = []
        original_compile = re.compile
        
        def tracked_compile(*args, **kwargs):
            compile_calls.append(args[0] if args else None)
            return original_compile(*args, **kwargs)
        
        monkeypatch.setattr(re, 'compile', tracked_compile)
        
        # Evaluate items - should use pre-compiled patterns
        for item in sample_rare_items:
            evaluator.evaluate(item)
        
        # Should have zero regex compilations during evaluation
        assert len(compile_calls) == 0, \
            f"Unexpected regex compilations during evaluation: {len(compile_calls)}"


class TestPriceIntegratorPerformance:
    """Test performance optimizations in price integrator."""

    def test_cached_item_class_determination(self):
        """Test that item class determination uses caching."""
        from core.price_integrator import PriceIntegrator
        
        integrator = PriceIntegrator(league="Standard")
        
        # Test various base types
        base_types = [
            "Hubris Circlet",
            "Vaal Regalia",
            "Two-Toned Boots",
            "Vermillion Ring",
            "Stygian Vise",
        ]
        
        # First pass - populate cache
        results1 = [integrator._get_item_class_from_base(bt) for bt in base_types]

        # Second pass - should use cache and return identical results
        results2 = [integrator._get_item_class_from_base(bt) for bt in base_types]

        # Third pass - verify consistency
        results3 = [integrator._get_item_class_from_base(bt) for bt in base_types]

        # Results should be identical (caching returns consistent values)
        assert results1 == results2 == results3, "Cache should return consistent results"

        # Verify we got valid results
        assert all(r is not None for r in results1), "All lookups should return a result"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

"""Integration tests: generate pieces and check for faults.

Verifies the full pipeline produces valid output.
"""
import pytest
from fractions import Fraction
from builder.faults import find_faults_from_composition, Fault
from planner.planner import generate
from shared.constants import VOICE_RANGES


# Standard actuator ranges for 2-voice texture
STANDARD_RANGES: dict[str, tuple[int, int]] = {
    "upper": VOICE_RANGES[0],
    "lower": VOICE_RANGES[3],
}

# Fault categories that are acceptable in small numbers
TOLERABLE_FAULTS: frozenset[str] = frozenset({
    "cross_relation",      # Chromaticism is stylistically valid
    "parallel_rhythm",     # Common in homophonic passages
    "ugly_leap",           # Acceptable if melodically justified
})

# Fault categories that should be zero
ZERO_TOLERANCE_FAULTS: frozenset[str] = frozenset({
    "parallel_fifth",
    "parallel_octave",
    "parallel_unison",
    "grotesque_leap",
})


def _count_by_category(faults: list[Fault]) -> dict[str, int]:
    """Count faults by category."""
    counts: dict[str, int] = {}
    for f in faults:
        counts[f.category] = counts.get(f.category, 0) + 1
    return counts


class TestIntegration:
    """Integration tests for full pipeline."""

    def test_invention_generates(self) -> None:
        """Invention genre produces output with both voices."""
        result = generate("invention", "Zaertlichkeit")
        assert "upper" in result.voices
        assert "lower" in result.voices
        assert len(result.voices["upper"]) > 0
        assert len(result.voices["lower"]) > 0
        assert result.metre == "4/4"
        assert result.tempo > 0

    def test_invention_no_grotesque_leaps(self) -> None:
        """Invention has no grotesque leaps (>19 semitones)."""
        result = generate("invention", "Zaertlichkeit")
        faults = find_faults_from_composition(result, STANDARD_RANGES)
        counts = _count_by_category(faults)
        assert counts.get("grotesque_leap", 0) == 0

    def test_invention_no_parallel_perfects(self) -> None:
        """Invention has no parallel fifths/octaves/unisons."""
        result = generate("invention", "Zaertlichkeit")
        faults = find_faults_from_composition(result, STANDARD_RANGES)
        counts = _count_by_category(faults)
        assert counts.get("parallel_fifth", 0) == 0
        assert counts.get("parallel_octave", 0) == 0
        assert counts.get("parallel_unison", 0) == 0

    def test_invention_limited_tessitura_faults(self) -> None:
        """Invention has limited tessitura excursions."""
        result = generate("invention", "Zaertlichkeit")
        faults = find_faults_from_composition(result, STANDARD_RANGES)
        counts = _count_by_category(faults)
        # Allow some tessitura faults (planner may place anchors near edges)
        assert counts.get("tessitura_excursion", 0) <= 5

    def test_different_affects_produce_output(self) -> None:
        """Different affects all produce valid output."""
        affects: list[str] = ["Zaertlichkeit", "Freudigkeit", "Dolore"]
        for affect in affects:
            result = generate("invention", affect)
            assert len(result.voices["upper"]) > 0, f"No upper notes for {affect}"
            assert len(result.voices["lower"]) > 0, f"No lower notes for {affect}"

    def test_fault_summary(self) -> None:
        """Print fault summary for diagnostic purposes."""
        result = generate("invention", "Zaertlichkeit")
        faults = find_faults_from_composition(result, STANDARD_RANGES)
        counts = _count_by_category(faults)
        print(f"\nFault summary ({len(faults)} total):")
        for cat, count in sorted(counts.items()):
            print(f"  {cat}: {count}")
        # This test always passes - it's for diagnostic output
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

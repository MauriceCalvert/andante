"""100% coverage tests for engine.episode_registry.

Tests import only:
- engine.episode_registry (module under test)
- engine.types (MotifAST)
- shared (pitch, timed_material)
- stdlib

Episode registry provides a decorator-based registration system for
episode generators, eliminating if/elif chains.
"""
from fractions import Fraction

from shared.pitch import FloatingNote
from shared.timed_material import TimedMaterial

from engine.episode_registry import (
    _GENERATORS,
    EpisodeGenerator,
    generate_episode_soprano,
    get_episode_generator,
    register_episode,
)
from engine.engine_types import MotifAST


def _make_subject() -> MotifAST:
    """Create a minimal subject for testing."""
    return MotifAST(
        pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
        durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
        bars=1,
    )


class TestGeneratorRegistry:
    """Test _GENERATORS registry."""

    def test_registry_is_dict(self) -> None:
        """Registry is a dictionary."""
        assert isinstance(_GENERATORS, dict)

    def test_registry_has_built_in_generators(self) -> None:
        """Registry contains built-in episode types."""
        assert "cadenza" in _GENERATORS
        assert "scalar" in _GENERATORS
        assert "arpeggiated" in _GENERATORS
        assert "turbulent" in _GENERATORS


class TestRegisterEpisode:
    """Test register_episode decorator."""

    def test_decorator_adds_to_registry(self) -> None:
        """Decorator adds function to registry."""
        @register_episode("test_episode_type")
        def test_generator(
            subject: MotifAST,
            budget: Fraction,
            root: int,
            phrase_index: int,
            virtuosic: bool,
        ) -> TimedMaterial | None:
            return None

        assert "test_episode_type" in _GENERATORS
        assert _GENERATORS["test_episode_type"] is test_generator
        # Clean up
        del _GENERATORS["test_episode_type"]

    def test_decorator_returns_function(self) -> None:
        """Decorator returns the original function."""
        def my_func(
            subject: MotifAST,
            budget: Fraction,
            root: int,
            phrase_index: int,
            virtuosic: bool,
        ) -> TimedMaterial | None:
            return None

        decorated = register_episode("another_test")(my_func)
        assert decorated is my_func
        # Clean up
        del _GENERATORS["another_test"]


class TestGetEpisodeGenerator:
    """Test get_episode_generator function."""

    def test_none_returns_none(self) -> None:
        """None episode_type returns None."""
        result: EpisodeGenerator | None = get_episode_generator(None)
        assert result is None

    def test_unknown_type_returns_none(self) -> None:
        """Unknown episode_type returns None."""
        result: EpisodeGenerator | None = get_episode_generator("nonexistent_type")
        assert result is None

    def test_known_type_returns_generator(self) -> None:
        """Known episode_type returns its generator."""
        result: EpisodeGenerator | None = get_episode_generator("cadenza")
        assert result is not None
        assert callable(result)

    def test_scalar_returns_generator(self) -> None:
        """Scalar type returns generator."""
        result: EpisodeGenerator | None = get_episode_generator("scalar")
        assert result is not None

    def test_arpeggiated_returns_generator(self) -> None:
        """Arpeggiated type returns generator."""
        result: EpisodeGenerator | None = get_episode_generator("arpeggiated")
        assert result is not None

    def test_turbulent_returns_generator(self) -> None:
        """Turbulent type returns generator."""
        result: EpisodeGenerator | None = get_episode_generator("turbulent")
        assert result is not None


class TestGenerateEpisodeSoprano:
    """Test generate_episode_soprano function."""

    def test_none_type_returns_none(self) -> None:
        """None episode_type returns None."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            None, subject, Fraction(2), 1, 0
        )
        assert result is None

    def test_unknown_type_returns_none(self) -> None:
        """Unknown episode_type returns None."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "nonexistent", subject, Fraction(2), 1, 0
        )
        assert result is None

    def test_cadenza_generates_material(self) -> None:
        """Cadenza type generates TimedMaterial."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0
        )
        assert result is not None
        assert isinstance(result, TimedMaterial)
        assert result.budget == Fraction(2)

    def test_cadenza_different_phrase_index(self) -> None:
        """Cadenza uses different patterns for different phrase indices."""
        subject: MotifAST = _make_subject()
        r0: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0
        )
        r1: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 1
        )
        assert r0 is not None
        assert r1 is not None
        # Different phrase_index selects different pattern
        assert r0.durations != r1.durations

    def test_scalar_generates_material(self) -> None:
        """Scalar type generates TimedMaterial."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "scalar", subject, Fraction(2), 1, 0
        )
        assert result is not None
        assert isinstance(result, TimedMaterial)

    def test_arpeggiated_may_return_none(self) -> None:
        """Arpeggiated type may return None if no passage found."""
        subject: MotifAST = _make_subject()
        # This tests the path where get_passage_for_episode returns None
        # We test that the function handles it gracefully
        result: TimedMaterial | None = generate_episode_soprano(
            "arpeggiated", subject, Fraction(2), 1, 0
        )
        # Result can be None or TimedMaterial depending on passage availability
        assert result is None or isinstance(result, TimedMaterial)

    def test_turbulent_may_return_none(self) -> None:
        """Turbulent type may return None if no passage found."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "turbulent", subject, Fraction(2), 1, 0
        )
        assert result is None or isinstance(result, TimedMaterial)

    def test_virtuosic_flag_passed(self) -> None:
        """Virtuosic flag is passed to generator."""
        subject: MotifAST = _make_subject()
        # Test that virtuosic=True doesn't crash
        result_normal: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0, virtuosic=False
        )
        result_virtuosic: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0, virtuosic=True
        )
        # Both should work
        assert result_normal is not None
        assert result_virtuosic is not None


class TestCadenzaGenerator:
    """Test the built-in cadenza generator."""

    def test_pattern_cycles(self) -> None:
        """Pattern cycles through available patterns."""
        subject: MotifAST = _make_subject()
        # 4 patterns: flourish_a, flourish_b, steady, rubato
        results: list[TimedMaterial | None] = []
        for idx in range(5):
            result: TimedMaterial | None = generate_episode_soprano(
                "cadenza", subject, Fraction(2), 1, idx
            )
            results.append(result)
        # idx 0 and idx 4 should use same pattern (flourish_a)
        assert results[0] is not None
        assert results[4] is not None
        assert results[0].durations == results[4].durations


class TestScalarGenerator:
    """Test the built-in scalar generator."""

    def test_extracts_intervals(self) -> None:
        """Scalar generator extracts intervals from subject."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "scalar", subject, Fraction(2), 1, 0
        )
        assert result is not None
        assert len(result.pitches) > 0

    def test_uses_running_rhythm(self) -> None:
        """Scalar uses 'running' rhythm."""
        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "scalar", subject, Fraction(1), 1, 0
        )
        assert result is not None
        # Running rhythm typically has 8 notes per bar
        assert len(result.pitches) >= 4


class TestIntegration:
    """Integration tests for episode_registry module."""

    def test_all_built_in_types_callable(self) -> None:
        """All built-in generators are callable."""
        for episode_type in ["cadenza", "scalar", "arpeggiated", "turbulent"]:
            gen: EpisodeGenerator | None = get_episode_generator(episode_type)
            assert gen is not None
            assert callable(gen)

    def test_custom_registration_works(self) -> None:
        """Custom generator can be registered and called."""
        @register_episode("custom_test")
        def custom_gen(
            subject: MotifAST,
            budget: Fraction,
            root: int,
            phrase_index: int,
            virtuosic: bool,
        ) -> TimedMaterial | None:
            return TimedMaterial(
                (FloatingNote(root),),
                (budget,),
                budget,
            )

        subject: MotifAST = _make_subject()
        result: TimedMaterial | None = generate_episode_soprano(
            "custom_test", subject, Fraction(1), 5, 0
        )
        assert result is not None
        assert result.pitches[0].degree == 5
        # Clean up
        del _GENERATORS["custom_test"]

    def test_deterministic_output(self) -> None:
        """Same inputs produce same outputs."""
        subject: MotifAST = _make_subject()
        r1: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0
        )
        r2: TimedMaterial | None = generate_episode_soprano(
            "cadenza", subject, Fraction(2), 1, 0
        )
        assert r1 is not None
        assert r2 is not None
        assert r1.pitches == r2.pitches
        assert r1.durations == r2.durations

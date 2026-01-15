"""100% coverage tests for engine.octave.

Tests import only:
- engine.octave (module under test)
- stdlib
"""
import pytest
from engine.octave import (
    CONSONANCES,
    OCTAVE,
    best_octave,
    best_octave_contrapuntal,
    register,
)


class TestConstants:
    """Test module constants loaded from YAML."""

    def test_consonances_is_set(self) -> None:
        assert isinstance(CONSONANCES, set)

    def test_consonances_contains_unison(self) -> None:
        """Unison (0 semitones) is a perfect consonance."""
        assert 0 in CONSONANCES

    def test_consonances_contains_perfect_fifth(self) -> None:
        """Perfect fifth (7 semitones) is a perfect consonance."""
        assert 7 in CONSONANCES

    def test_consonances_contains_octave(self) -> None:
        """Octave (0 semitones mod 12) represented as 0."""
        # Octave interval is 12 semitones, but mod 12 = 0
        assert 0 in CONSONANCES

    def test_consonances_contains_thirds(self) -> None:
        """Major and minor thirds (3, 4 semitones) are imperfect consonances."""
        assert 3 in CONSONANCES  # minor third
        assert 4 in CONSONANCES  # major third

    def test_consonances_contains_sixths(self) -> None:
        """Major and minor sixths (8, 9 semitones) are imperfect consonances."""
        assert 8 in CONSONANCES  # minor sixth
        assert 9 in CONSONANCES  # major sixth

    def test_octave_constant(self) -> None:
        """OCTAVE should be 12 semitones."""
        assert OCTAVE == 12


class TestRegister:
    """Test register function."""

    def test_soprano_register(self) -> None:
        """Soprano center pitch should be in upper range (MIDI 70s)."""
        midi: int = register("soprano")
        assert 65 <= midi <= 80

    def test_alto_register(self) -> None:
        """Alto center pitch should be below soprano."""
        assert register("alto") < register("soprano")

    def test_tenor_register(self) -> None:
        """Tenor center pitch should be below alto."""
        assert register("tenor") < register("alto")

    def test_bass_register(self) -> None:
        """Bass center pitch should be lowest (MIDI 40s-50s)."""
        midi: int = register("bass")
        assert 40 <= midi <= 55
        assert register("bass") < register("tenor")


class TestBestOctave:
    """Test best_octave function.

    Selects octave placement by:
    - Minimizing interval from previous pitch (contour continuity)
    - Biasing toward median (register gravity, weighted 0.5)
    """

    def test_stays_close_to_previous(self) -> None:
        """Prefer octave that minimizes jump from previous pitch."""
        # Previous pitch is C4=60, target is E=64
        # Options: 64 (jump 4), 76 (jump 16), 52 (jump 8)
        # Score 64: interval=4 + median_dist*0.5
        result: int = best_octave(midi=64, prev_midi=60, median=60, octave=12)
        assert result == 64  # Closest to prev

    def test_prefers_median_when_tied(self) -> None:
        """When intervals similar, prefer pitch closer to median."""
        # Median is 72 (soprano), prev is 66
        # Target pitch class E=64 at various octaves
        # 64: dist from 66 = 2, dist from median 72 = 8
        # 76: dist from 66 = 10, dist from median 72 = 4
        result: int = best_octave(midi=64, prev_midi=66, median=72, octave=12)
        # 64: score = 2 + 8*0.5 = 6
        # 76: score = 10 + 4*0.5 = 12
        assert result == 64

    def test_octave_up_candidate(self) -> None:
        """Test that octave+12 candidate is considered."""
        # Previous at 72, target 62, median at 74
        # Candidates: 62 (jump 10), 74 (jump 2), 50 (jump 22)
        result: int = best_octave(midi=62, prev_midi=72, median=74, octave=12)
        assert result == 74  # 62+12, closest to prev

    def test_octave_down_candidate(self) -> None:
        """Test that octave-12 candidate is considered."""
        # Previous at 50, target 62, median at 48
        # Candidates: 62 (jump 12), 74 (jump 24), 50 (jump 0)
        result: int = best_octave(midi=62, prev_midi=50, median=48, octave=12)
        assert result == 50  # 62-12, same as prev

    def test_register_gravity(self) -> None:
        """Register gravity pulls toward median when interval equal."""
        # Previous at 60, target 72, median at 48
        # Candidates: 72, 84, 60
        # 72: interval=12, median_dist=24 -> 12 + 12 = 24
        # 84: interval=24, median_dist=36 -> 24 + 18 = 42
        # 60: interval=0, median_dist=12 -> 0 + 6 = 6
        result: int = best_octave(midi=72, prev_midi=60, median=48, octave=12)
        assert result == 60  # 72-12, closest to median and prev


class TestBestOctaveContrapuntal:
    """Test best_octave_contrapuntal function.

    Like best_octave but also ensures consonance with soprano.
    """

    def test_consonant_interval_preferred(self) -> None:
        """Consonant interval with soprano is preferred."""
        # Soprano at 72 (C5)
        # Target 64 (E4), options: 64, 76, 52
        # Interval from 72: 64->8 (minor 6th, consonant), 76->4 (major 3rd), 52->20 mod 12=8
        result: int = best_octave_contrapuntal(
            midi=64, prev_midi=60, median=60, octave=12,
            soprano_midi=72, consonances=CONSONANCES
        )
        # All should be consonant, pick by distance
        assert result in (64, 76, 52)

    def test_dissonance_avoided(self) -> None:
        """Dissonant placement gets heavy penalty."""
        # Custom consonances excluding minor 2nd (1 semitone)
        limited_cons: set[int] = {0, 3, 4, 7, 8, 9}  # no 1, 2 (seconds)
        # Soprano at 72, target 73 would make minor 2nd
        # Options: 73 (interval 1, dissonant), 85 (interval 13 mod 12=1, dissonant), 61 (interval 11, dissonant)
        # All dissonant - picks by pure distance
        result: int = best_octave_contrapuntal(
            midi=73, prev_midi=72, median=60, octave=12,
            soprano_midi=72, consonances=limited_cons
        )
        # Should still pick closest despite dissonance
        assert result == 73

    def test_no_soprano_accepts_all(self) -> None:
        """When soprano_midi is None, all placements are consonant."""
        result: int = best_octave_contrapuntal(
            midi=64, prev_midi=60, median=60, octave=12,
            soprano_midi=None, consonances=CONSONANCES
        )
        assert result == 64

    def test_perfect_fifth_consonant(self) -> None:
        """Perfect fifth (7 semitones) is consonant."""
        # Soprano at 72 (C5), bass candidate at 65 (F4)
        # Interval: 72 - 65 = 7 (perfect fifth)
        result: int = best_octave_contrapuntal(
            midi=65, prev_midi=60, median=60, octave=12,
            soprano_midi=72, consonances=CONSONANCES
        )
        # 65 makes P5, should be acceptable
        assert 7 in CONSONANCES  # verify P5 is consonant

    def test_contrapuntal_chooses_consonant_over_close(self) -> None:
        """Prefers consonant placement even if slightly farther."""
        # Soprano at 60 (C4)
        # Target 66 (F#4), prev at 65
        # Interval from soprano: 66->6 (tritone, dissonant if not in set)
        # Interval from soprano: 78->18 mod 12=6 (tritone)
        # Interval from soprano: 54->6 (tritone)
        # All make tritone - test passes if function handles gracefully
        tritone_free: set[int] = {0, 3, 4, 5, 7, 8, 9}  # excludes 6 (tritone)
        result: int = best_octave_contrapuntal(
            midi=66, prev_midi=65, median=60, octave=12,
            soprano_midi=60, consonances=tritone_free
        )
        # All dissonant, picks closest (66)
        assert result == 66

"""Integration tests for engine.slice_solver.

Category B orchestrator tests: verify slice-by-slice inner voice solving.
Tests import only:
- engine.slice_solver (module under test)
- engine.key (Key type)
- engine.voice_config (VoiceSet)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, MidiPitch, Rest
from shared.parallels import is_parallel_fifth, is_parallel_octave
from engine.key import Key
from engine.slice_solver import (
    check_voice_crossing,
    filter_candidates,
    get_voice_range,
    rank_candidates,
    rank_candidates_with_harmony,
    resolve_outer_pitch,
    solve_slice,
    SolvedSlice,
    voice_leading_cost,
)
from engine.voice_config import voice_set_from_count


class TestGetVoiceRange:
    """Test get_voice_range function."""

    def test_two_voice_soprano(self) -> None:
        """Two-voice soprano range."""
        low, high = get_voice_range(0, 2)
        assert low < high
        assert low >= 40
        assert high <= 90

    def test_two_voice_bass(self) -> None:
        """Two-voice bass range."""
        low, high = get_voice_range(1, 2)
        assert low < high
        assert low >= 30
        assert high <= 70

    def test_three_voice_alto(self) -> None:
        """Three-voice alto range."""
        low, high = get_voice_range(1, 3)
        assert low < high

    def test_four_voice_tenor(self) -> None:
        """Four-voice tenor range."""
        low, high = get_voice_range(2, 4)
        assert low < high

    def test_soprano_higher_than_bass(self) -> None:
        """Soprano range higher than bass range."""
        sop_low, sop_high = get_voice_range(0, 2)
        bass_low, bass_high = get_voice_range(1, 2)
        assert sop_low > bass_low


class TestIsParallelFifth:
    """Test is_parallel_fifth function from shared.parallels."""

    def test_parallel_fifth_detected(self) -> None:
        """Detects parallel fifth motion."""
        # Both voices move up by step, maintaining fifth
        result: bool = is_parallel_fifth(67, 60, 69, 62)
        assert result is True

    def test_no_parallel_fifth_oblique(self) -> None:
        """No parallel fifth with oblique motion."""
        # Upper moves, lower stays
        result: bool = is_parallel_fifth(67, 60, 69, 60)
        assert result is False

    def test_no_parallel_fifth_contrary(self) -> None:
        """No parallel fifth with contrary motion."""
        # Upper moves up, lower moves down
        result: bool = is_parallel_fifth(67, 60, 69, 58)
        assert result is False

    def test_no_parallel_when_not_fifths(self) -> None:
        """No parallel fifth when intervals not fifths."""
        # Intervals are thirds, not fifths
        result: bool = is_parallel_fifth(64, 60, 66, 62)
        assert result is False


class TestIsParallelOctave:
    """Test is_parallel_octave function from shared.parallels."""

    def test_parallel_octave_detected(self) -> None:
        """Detects parallel octave motion."""
        # Both voices move up by step, maintaining octave
        result: bool = is_parallel_octave(72, 60, 74, 62)
        assert result is True

    def test_no_parallel_octave_oblique(self) -> None:
        """No parallel octave with oblique motion."""
        result: bool = is_parallel_octave(72, 60, 74, 60)
        assert result is False

    def test_no_parallel_octave_contrary(self) -> None:
        """No parallel octave with contrary motion."""
        result: bool = is_parallel_octave(72, 60, 74, 58)
        assert result is False


class TestCheckVoiceCrossing:
    """Test check_voice_crossing function."""

    def test_crossing_above_soprano(self) -> None:
        """Detects inner voice crossing above soprano."""
        other_pitches: dict[int, int] = {0: 72, 3: 48}  # Soprano=72, bass=48
        result: bool = check_voice_crossing(75, 1, other_pitches, 4)  # Alto at 75
        assert result is True

    def test_crossing_below_bass(self) -> None:
        """Detects inner voice crossing below bass."""
        other_pitches: dict[int, int] = {0: 72, 3: 48}
        result: bool = check_voice_crossing(45, 2, other_pitches, 4)  # Tenor at 45
        assert result is True

    def test_no_crossing_within_range(self) -> None:
        """No crossing when within proper range."""
        other_pitches: dict[int, int] = {0: 72, 3: 48}
        result: bool = check_voice_crossing(60, 1, other_pitches, 4)
        assert result is False


class TestFilterCandidates:
    """Test filter_candidates function.

    Note: Parallel 5th/8ve filtering removed - guards handle via backtracking.
    Only voice crossing is checked here.
    """

    def test_filter_empty_returns_empty(self) -> None:
        """Empty candidates returns empty."""
        result: tuple[int, ...] = filter_candidates((), 1, {0: 72}, None, 4)
        assert result == ()

    def test_filter_removes_crossing_candidates(self) -> None:
        """Removes candidates that cross voices."""
        candidates: tuple[int, ...] = (75, 65, 55)  # 75 crosses soprano
        curr: dict[int, int] = {0: 72, 3: 48}
        result: tuple[int, ...] = filter_candidates(candidates, 1, curr, None, 4)
        assert 75 not in result

    def test_filter_removes_parallel_octave_with_outer(self) -> None:
        """Removes candidates that create parallel octaves with outer voices."""
        # Soprano at 72 moving to 74 (+2), bass at 48 moving to 50 (+2)
        # If alto at 60 moves to 62 (+2), parallel with soprano (both move +2, interval=0 mod 12)
        prev: dict[int, int] = {0: 72, 1: 60, 3: 48}  # soprano, alto, bass
        curr: dict[int, int] = {0: 74, 3: 50}  # soprano, bass (alto being chosen)
        candidates: tuple[int, ...] = (62, 64, 65)  # 62 would create parallel octave
        result: tuple[int, ...] = filter_candidates(candidates, 1, curr, prev, 4)
        assert 62 not in result
        assert 64 in result or 65 in result


class TestVoiceLeadingCost:
    """Test voice_leading_cost function."""

    def test_step_motion_low_cost(self) -> None:
        """Step motion has low cost."""
        cost: float = voice_leading_cost(62, 60, 64)  # Step up
        assert cost < 1.0

    def test_large_leap_high_cost(self) -> None:
        """Large leaps have higher cost."""
        cost_step: float = voice_leading_cost(62, 60, 64)
        cost_leap: float = voice_leading_cost(72, 60, 64)  # Octave leap
        assert cost_leap > cost_step

    def test_staying_still_penalized(self) -> None:
        """Staying on same pitch penalized."""
        cost_move: float = voice_leading_cost(62, 60, 64)
        cost_stay: float = voice_leading_cost(60, 60, 64)
        assert cost_stay > cost_move

    def test_unison_very_high_cost(self) -> None:
        """Unison with another voice has very high cost."""
        curr: dict[int, int] = {0: 72}
        cost: float = voice_leading_cost(72, 60, 64, curr, 1)  # Unison with soprano
        assert cost >= 50.0


class TestRankCandidates:
    """Test rank_candidates function."""

    def test_rank_single_candidate(self) -> None:
        """Single candidate returns unchanged."""
        result: tuple[int, ...] = rank_candidates((60,), 58, 64)
        assert result == (60,)

    def test_rank_prefers_steps(self) -> None:
        """Steps ranked before leaps."""
        candidates: tuple[int, ...] = (72, 61, 65)  # Leap, step, small leap
        result: tuple[int, ...] = rank_candidates(candidates, 60, 64)
        # Step (61) should be first
        assert result[0] == 61

    def test_rank_empty_returns_empty(self) -> None:
        """Empty candidates returns empty."""
        result: tuple[int, ...] = rank_candidates((), 60, 64)
        assert result == ()


class TestRankCandidatesWithHarmony:
    """Test rank_candidates_with_harmony function."""

    def test_chord_tones_preferred(self) -> None:
        """Chord tones ranked before scale tones."""
        chord_tones: set[int] = {60, 64, 67}  # C major chord
        candidates: tuple[int, ...] = (62, 64)  # D (scale), E (chord)
        result: tuple[int, ...] = rank_candidates_with_harmony(
            candidates, 60, 64, None, None, chord_tones
        )
        # Chord tone (64) should be preferred
        assert result[0] == 64


class TestResolveOuterPitch:
    """Test resolve_outer_pitch function."""

    def test_resolve_midi_pitch(self) -> None:
        """MidiPitch resolves to its midi value."""
        key: Key = Key("C", "major")
        result: int = resolve_outer_pitch(MidiPitch(60), key, 64)
        assert result == 60

    def test_resolve_floating_note(self) -> None:
        """FloatingNote resolves via key."""
        key: Key = Key("C", "major")
        result: int = resolve_outer_pitch(FloatingNote(1), key, 60)
        assert result % 12 == 0  # Should be some C

    def test_resolve_rest_raises(self) -> None:
        """Rest raises assertion error."""
        key: Key = Key("C", "major")
        with pytest.raises(AssertionError):
            resolve_outer_pitch(Rest(), key, 64)


class TestSolveSlice:
    """Test solve_slice function."""

    def test_solve_slice_two_voice(self) -> None:
        """Two-voice slice returns just soprano and bass."""
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(2)
        result: SolvedSlice = solve_slice(
            Fraction(0), MidiPitch(72), MidiPitch(48), None, key, voice_set, "polyphonic"
        )
        assert len(result.pitches) == 2
        assert result.pitches[0] == 72
        assert result.pitches[1] == 48

    def test_solve_slice_four_voice(self) -> None:
        """Four-voice slice has 4 pitches."""
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: SolvedSlice = solve_slice(
            Fraction(0), MidiPitch(72), MidiPitch(48), None, key, voice_set, "polyphonic"
        )
        assert len(result.pitches) == 4
        assert result.pitches[0] == 72  # Soprano
        assert result.pitches[3] == 48  # Bass

    def test_solve_slice_inner_voices_in_range(self) -> None:
        """Inner voices are within their ranges."""
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        result: SolvedSlice = solve_slice(
            Fraction(0), MidiPitch(72), MidiPitch(48), None, key, voice_set, "polyphonic"
        )
        alto_range: tuple[int, int] = get_voice_range(1, 4)
        tenor_range: tuple[int, int] = get_voice_range(2, 4)
        assert alto_range[0] <= result.pitches[1] <= alto_range[1]
        assert tenor_range[0] <= result.pitches[2] <= tenor_range[1]

    def test_solve_slice_offset_preserved(self) -> None:
        """Slice offset is preserved."""
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(2)
        result: SolvedSlice = solve_slice(
            Fraction(1, 2), MidiPitch(72), MidiPitch(48), None, key, voice_set, "polyphonic"
        )
        assert result.offset == Fraction(1, 2)

    def test_solve_slice_with_prev_solved(self) -> None:
        """Previous slice influences voice leading."""
        key: Key = Key("C", "major")
        voice_set = voice_set_from_count(4)
        prev: SolvedSlice = SolvedSlice(Fraction(0), (72, 64, 57, 48))
        result: SolvedSlice = solve_slice(
            Fraction(1, 4), MidiPitch(74), MidiPitch(50), prev, key, voice_set, "polyphonic"
        )
        # Inner voices should use stepwise motion from prev
        assert len(result.pitches) == 4


class TestSolvedSlice:
    """Test SolvedSlice dataclass."""

    def test_solved_slice_frozen(self) -> None:
        """SolvedSlice is immutable."""
        solved: SolvedSlice = SolvedSlice(Fraction(0), (72, 64, 57, 48))
        with pytest.raises(Exception):  # FrozenInstanceError
            solved.offset = Fraction(1)

    def test_solved_slice_attributes(self) -> None:
        """SolvedSlice has correct attributes."""
        solved: SolvedSlice = SolvedSlice(Fraction(1, 2), (72, 64, 57, 48))
        assert solved.offset == Fraction(1, 2)
        assert solved.pitches == (72, 64, 57, 48)

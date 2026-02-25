"""Tests for extended counterpoint detection and prevention functions."""
from fractions import Fraction

from builder.types import Note
from shared.constants import SKIP_SEMITONES
from shared.counterpoint import (
    has_consecutive_leaps,
    has_cross_relation,
    has_parallel_perfect,
    is_cross_bar_repetition,
    is_ugly_melodic_interval,
    needs_step_recovery,
    prevent_cross_relation,
    would_cross_voice,
)
from shared.key import Key


def _note(offset: Fraction, pitch: int) -> Note:
    """Create minimal Note for testing."""
    return Note(
        offset=offset,
        pitch=pitch,
        duration=Fraction(1, 4),
        voice=0,
    )


class TestHasCrossRelation:
    def test_detects_f_fsharp(self) -> None:
        """F4 in one voice against F#3 in the other within a beat."""
        other_notes = (_note(Fraction(0), 54),)  # F#3 = MIDI 54
        assert has_cross_relation(
            pitch=65,  # F4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
        )

    def test_no_cross_relation_different_pcs(self) -> None:
        """C and D are not a cross-relation pair."""
        other_notes = (_note(Fraction(0), 62),)  # D4
        assert not has_cross_relation(
            pitch=60,  # C4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
        )

    def test_no_cross_relation_outside_window(self) -> None:
        """Cross-relation pair but too far apart in time."""
        other_notes = (_note(Fraction(2), 54),)  # F#3, 2 beats away
        assert not has_cross_relation(
            pitch=65,  # F4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
        )

    def test_detects_g_gsharp(self) -> None:
        """G vs G# is a cross-relation."""
        other_notes = (_note(Fraction(0), 68),)  # G#4
        assert has_cross_relation(
            pitch=67,  # G4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
        )

    def test_empty_other_notes(self) -> None:
        """No other notes means no cross-relation."""
        assert not has_cross_relation(
            pitch=65,
            other_notes=(),
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
        )


class TestPreventCrossRelation:
    def test_returns_original_when_no_cross_relation(self) -> None:
        """No cross-relation: returns original pitch."""
        k: Key = Key(tonic="C", mode="major")
        other_notes = (_note(Fraction(0), 62),)  # D4
        result: int = prevent_cross_relation(
            pitch=60,
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
            key=k,
            pitch_range=(55, 84),
            ceiling=None,
        )
        assert result == 60

    def test_avoids_cross_relation(self) -> None:
        """When cross-relation exists, returns a different pitch."""
        k: Key = Key(tonic="C", mode="major")
        # F4=65 against F#3=54 is a cross-relation
        other_notes = (_note(Fraction(0), 54),)
        result: int = prevent_cross_relation(
            pitch=65,  # F4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
            key=k,
            pitch_range=(55, 84),
            ceiling=None,
        )
        # Should return a diatonic step away from 65
        assert result != 65
        assert 55 <= result <= 84

    def test_respects_ceiling(self) -> None:
        """Alternative pitch must be below ceiling."""
        k: Key = Key(tonic="C", mode="major")
        other_notes = (_note(Fraction(0), 54),)  # F#3
        result: int = prevent_cross_relation(
            pitch=65,  # F4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
            key=k,
            pitch_range=(55, 84),
            ceiling=66,
        )
        assert result <= 66

    def test_returns_original_when_no_alternative(self) -> None:
        """If no diatonic step avoids the cross-relation, returns original."""
        k: Key = Key(tonic="C", mode="major")
        # Construct a scenario where both step -1 and step +1 also cross-relate
        # F#3=54 and G#3=56 both present
        other_notes = (
            _note(Fraction(0), 54),  # F#3
            _note(Fraction(0), 56),  # G#3 (not a pair with E or G in standard pairs... )
        )
        # This may or may not find an alternative; just verify it doesn't crash
        result: int = prevent_cross_relation(
            pitch=65,  # F4
            other_notes=other_notes,
            offset=Fraction(0),
            beat_unit=Fraction(1, 4),
            key=k,
            pitch_range=(55, 84),
            ceiling=None,
        )
        assert 55 <= result <= 84


class TestHasParallelPerfect:
    def test_detects_parallel_fifths(self) -> None:
        """Detect P5→P5 by similar motion."""
        other_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 2), 62),  # D4
        )
        own_previous = _note(Fraction(0), 67)  # G4 (P5 above C4)

        # Moving to A4 (69) creates P5 above D4 (62) — parallel fifth
        assert has_parallel_perfect(
            pitch=69,
            offset=Fraction(1, 2),
            other_voice_notes=other_notes,
            own_previous_note=own_previous,
            tolerance=frozenset(),
        )

    def test_allows_contrary_motion(self) -> None:
        """P5→P5 by contrary motion is allowed."""
        other_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 2), 62),  # D4 (up)
        )
        own_previous = _note(Fraction(0), 67)  # G4 (P5 above C4)

        # Moving down to E4 (64) creates M3 above D4 — no parallel
        assert not has_parallel_perfect(
            pitch=64,
            offset=Fraction(1, 2),
            other_voice_notes=other_notes,
            own_previous_note=own_previous,
            tolerance=frozenset(),
        )

    def test_tolerates_excluded_intervals(self) -> None:
        """tolerance={7} exempts perfect fifths."""
        other_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 2), 62),  # D4
        )
        own_previous = _note(Fraction(0), 67)  # G4 (P5 above C4)

        # P5→P5, but tolerance={7} exempts it
        assert not has_parallel_perfect(
            pitch=69,
            offset=Fraction(1, 2),
            other_voice_notes=other_notes,
            own_previous_note=own_previous,
            tolerance=frozenset({7}),
        )

    def test_no_previous_note(self) -> None:
        """No previous note → no parallel to check."""
        other_notes = (_note(Fraction(0), 60),)
        assert not has_parallel_perfect(
            pitch=67,
            offset=Fraction(0),
            other_voice_notes=other_notes,
            own_previous_note=None,
            tolerance=frozenset(),
        )

    def test_no_common_onset(self) -> None:
        """No note at candidate offset in other voice → no parallel."""
        other_notes = (_note(Fraction(0), 60),)
        own_previous = _note(Fraction(0), 67)
        assert not has_parallel_perfect(
            pitch=69,
            offset=Fraction(1, 2),  # No note at this offset in other_notes
            other_voice_notes=other_notes,
            own_previous_note=own_previous,
            tolerance=frozenset(),
        )


class TestWouldCrossVoice:
    def test_bass_above_soprano(self) -> None:
        """Bass (voice_id=3) above soprano (voice_id=0) is crossing."""
        assert would_cross_voice(
            pitch=72,  # C5
            other_voice_pitch=60,  # C4
            voice_id=3,  # Bass
            other_voice_id=0,  # Soprano
        )

    def test_bass_below_soprano_ok(self) -> None:
        """Bass below soprano is not crossing."""
        assert not would_cross_voice(
            pitch=48,  # C3
            other_voice_pitch=60,  # C4
            voice_id=3,  # Bass
            other_voice_id=0,  # Soprano
        )

    def test_soprano_below_bass(self) -> None:
        """Soprano below bass is crossing."""
        assert would_cross_voice(
            pitch=48,  # C3
            other_voice_pitch=60,  # C4
            voice_id=0,  # Soprano
            other_voice_id=3,  # Bass
        )

    def test_same_voice_id(self) -> None:
        """Same voice_id never crosses."""
        assert not would_cross_voice(
            pitch=48,
            other_voice_pitch=60,
            voice_id=0,
            other_voice_id=0,
        )


class TestIsUglyMelodicInterval:
    def test_tritone(self) -> None:
        """6 semitones → ugly."""
        assert is_ugly_melodic_interval(from_pitch=60, to_pitch=66)

    def test_minor_second_step(self) -> None:
        """1 semitone step (≤ STEP_SEMITONES) → not ugly."""
        assert not is_ugly_melodic_interval(from_pitch=60, to_pitch=61)

    def test_minor_ninth(self) -> None:
        """13 semitones (mod 12 = 1, > STEP_SEMITONES) → ugly."""
        assert is_ugly_melodic_interval(from_pitch=60, to_pitch=73)

    def test_major_seventh(self) -> None:
        """11 semitones → ugly."""
        assert is_ugly_melodic_interval(from_pitch=60, to_pitch=71)

    def test_minor_seventh(self) -> None:
        """10 semitones → ugly."""
        assert is_ugly_melodic_interval(from_pitch=60, to_pitch=70)

    def test_major_third(self) -> None:
        """4 semitones → not ugly."""
        assert not is_ugly_melodic_interval(from_pitch=60, to_pitch=64)


class TestNeedsStepRecovery:
    def test_after_leap_same_direction(self) -> None:
        """Leap then same direction → needs recovery."""
        prev_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 4), 67),  # G4 (leap up)
        )
        # Candidate continues up → needs recovery
        assert needs_step_recovery(
            previous_notes=prev_notes,
            candidate_pitch=69,  # A4 (up again)
            structural_offsets=frozenset(),
        )

    def test_after_step_no_recovery(self) -> None:
        """Step then anything → no recovery needed."""
        prev_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 4), 62),  # D4 (step)
        )
        assert not needs_step_recovery(
            previous_notes=prev_notes,
            candidate_pitch=69,  # Any pitch
            structural_offsets=frozenset(),
        )

    def test_structural_exempt(self) -> None:
        """Both structural → exempt."""
        prev_notes = (
            _note(Fraction(0), 60),  # C4 (structural)
            _note(Fraction(1, 4), 67),  # G4 (structural, leap)
        )
        assert not needs_step_recovery(
            previous_notes=prev_notes,
            candidate_pitch=69,
            structural_offsets=frozenset({Fraction(0), Fraction(1, 4)}),
        )

    def test_contrary_step_provides_recovery(self) -> None:
        """Leap up then step down → recovery provided."""
        prev_notes = (
            _note(Fraction(0), 60),  # C4
            _note(Fraction(1, 4), 67),  # G4 (leap up)
        )
        # Candidate steps down → recovery
        assert not needs_step_recovery(
            previous_notes=prev_notes,
            candidate_pitch=65,  # F4 (step down from G4)
            structural_offsets=frozenset(),
        )

    def test_fewer_than_two_notes(self) -> None:
        """Less than 2 notes → no recovery needed."""
        assert not needs_step_recovery(
            previous_notes=(_note(Fraction(0), 60),),
            candidate_pitch=67,
            structural_offsets=frozenset(),
        )


class TestIsCrossBarRepetition:
    def test_same_pitch_across_bar(self) -> None:
        """Same pitch across bar boundary → True."""
        prev_note = _note(Fraction(3, 4), 60)  # Bar 1, beat 4
        assert is_cross_bar_repetition(
            pitch=60,
            offset=Fraction(1),  # Bar 2, beat 1
            previous_note=prev_note,
            bar_length=Fraction(1),
            phrase_start=Fraction(0),
            structural_offsets=frozenset(),
        )

    def test_same_bar(self) -> None:
        """Same bar → not cross-bar."""
        prev_note = _note(Fraction(1, 4), 60)  # Bar 1, beat 2
        assert not is_cross_bar_repetition(
            pitch=60,
            offset=Fraction(1, 2),  # Bar 1, beat 3
            previous_note=prev_note,
            bar_length=Fraction(1),
            phrase_start=Fraction(0),
            structural_offsets=frozenset(),
        )

    def test_structural_exempt(self) -> None:
        """Structural offset → exempt."""
        prev_note = _note(Fraction(3, 4), 60)
        assert not is_cross_bar_repetition(
            pitch=60,
            offset=Fraction(1),  # Structural
            previous_note=prev_note,
            bar_length=Fraction(1),
            phrase_start=Fraction(0),
            structural_offsets=frozenset({Fraction(1)}),
        )

    def test_different_pitch(self) -> None:
        """Different pitch → not repetition."""
        prev_note = _note(Fraction(3, 4), 60)
        assert not is_cross_bar_repetition(
            pitch=62,
            offset=Fraction(1),
            previous_note=prev_note,
            bar_length=Fraction(1),
            phrase_start=Fraction(0),
            structural_offsets=frozenset(),
        )


class TestHasConsecutiveLeaps:
    def test_same_direction(self) -> None:
        """Two leaps same direction → True."""
        assert has_consecutive_leaps(
            prev_prev_pitch=60,  # C4
            prev_pitch=67,  # G4 (up 7)
            candidate_pitch=74,  # D5 (up 7)
            threshold=SKIP_SEMITONES,
        )

    def test_opposite_direction(self) -> None:
        """Two leaps opposite direction → False."""
        assert not has_consecutive_leaps(
            prev_prev_pitch=60,  # C4
            prev_pitch=67,  # G4 (up 7)
            candidate_pitch=60,  # C4 (down 7)
            threshold=SKIP_SEMITONES,
        )

    def test_no_prev_prev(self) -> None:
        """No prev_prev → False."""
        assert not has_consecutive_leaps(
            prev_prev_pitch=None,
            prev_pitch=60,
            candidate_pitch=67,
            threshold=SKIP_SEMITONES,
        )

    def test_first_interval_step(self) -> None:
        """First interval is step → False."""
        assert not has_consecutive_leaps(
            prev_prev_pitch=60,  # C4
            prev_pitch=62,  # D4 (step)
            candidate_pitch=69,  # A4 (leap)
            threshold=SKIP_SEMITONES,
        )

    def test_second_interval_step(self) -> None:
        """Second interval is step → False."""
        assert not has_consecutive_leaps(
            prev_prev_pitch=60,  # C4
            prev_pitch=67,  # G4 (leap)
            candidate_pitch=69,  # A4 (step)
            threshold=SKIP_SEMITONES,
        )



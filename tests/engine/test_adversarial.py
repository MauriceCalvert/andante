"""Adversarial tests that challenge assumptions in the codebase.

These tests:
1. Challenge mathematical/musical logic
2. Test edge cases that might break invariants
3. Question design decisions
4. Look for hidden bugs through unexpected inputs

Tests import only:
- shared (shared types)
- engine modules under test (harmonic_context, arc_loader)
- stdlib

Note: We test VoiceTreatmentSpec attributes directly without importing the type.
"""
from fractions import Fraction

import pytest
from shared.key import Key
from shared.pitch import FloatingNote, MidiPitch

from engine.harmonic_context import (
    HarmonicContext,
    infer_harmony_from_outer,
    degree_to_pc,
    infer_chord_from_bass,
    generate_chord_tone_candidates,
    generate_scale_candidates,
)
from engine.arc_loader import (
    load_arc,
    get_default_treatment_for_voice,
    voice_names_for_count,
)


class TestMidiToDegreeConversion:
    """Verify MidiPitch to degree conversion works correctly.

    The conversion maps MIDI pitch class to scale degree using the key.
    """

    # Known MIDI values for C major scale from C4
    MIDI_TO_DEGREE_C_MAJOR = {
        60: 1,  # C4 = tonic
        62: 2,  # D4 = supertonic
        64: 3,  # E4 = mediant
        65: 4,  # F4 = subdominant
        67: 5,  # G4 = dominant
        69: 6,  # A4 = submediant
        71: 7,  # B4 = leading tone
        72: 1,  # C5 = tonic (octave)
    }

    def test_c4_is_degree_1(self) -> None:
        """C4 (MIDI 60) is degree 1 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(60), key)
        assert hc.bass_degree == 1

    def test_d4_is_degree_2(self) -> None:
        """D4 (MIDI 62) is degree 2 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(62), key)
        assert hc.bass_degree == 2

    def test_e4_is_degree_3(self) -> None:
        """E4 (MIDI 64) is degree 3 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(64), key)
        assert hc.bass_degree == 3

    def test_f4_is_degree_4(self) -> None:
        """F4 (MIDI 65) is degree 4 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(65), key)
        assert hc.bass_degree == 4

    def test_g4_is_degree_5(self) -> None:
        """G4 (MIDI 67) is degree 5 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(67), key)
        assert hc.bass_degree == 5

    def test_a4_is_degree_6(self) -> None:
        """A4 (MIDI 69) is degree 6 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(69), key)
        assert hc.bass_degree == 6

    def test_b4_is_degree_7(self) -> None:
        """B4 (MIDI 71) is degree 7 in C major."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(71), key)
        assert hc.bass_degree == 7

    def test_chromatic_notes_default_to_tonic(self) -> None:
        """Chromatic notes (not in scale) default to degree 1."""
        key = Key(tonic="C", mode="major")
        # C# (MIDI 61) - not in C major scale
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(61), key)
        assert hc.bass_degree == 1  # Fallback to tonic

    def test_g_major_correct_degrees(self) -> None:
        """Test correct degree inference in G major."""
        key = Key(tonic="G", mode="major")
        # G4 (MIDI 67) is degree 1 in G major
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(67), key)
        assert hc.bass_degree == 1
        # A4 (MIDI 69) is degree 2 in G major
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(69), key)
        assert hc.bass_degree == 2


class TestChordInferenceEdgeCases:
    """Test edge cases in chord inference that might produce wrong results."""

    def test_diminished_triad_on_degree_7(self) -> None:
        """Degree 7 produces diminished triad - is tritone handled?"""
        key = Key(tonic="C", mode="major")
        chord_tones = infer_chord_from_bass(7, key)
        # B-D-F: pitch classes 11, 2, 5
        # Root should be B (11), third is D (2), fifth is F (5)
        assert 11 in chord_tones  # B
        assert 2 in chord_tones   # D
        assert 5 in chord_tones   # F

    def test_minor_key_chord_quality(self) -> None:
        """Minor key i chord should have minor third."""
        key = Key(tonic="A", mode="minor")
        chord_tones = infer_chord_from_bass(1, key)
        # A minor: A-C-E (pitch classes 9, 0, 4)
        assert 9 in chord_tones  # A
        assert 0 in chord_tones  # C
        assert 4 in chord_tones  # E


class TestCandidateGenerationBugs:
    """Test edge cases in candidate generation."""

    def test_narrow_range_might_miss_candidates(self) -> None:
        """Very narrow voice range might produce no candidates."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(FloatingNote(1), FloatingNote(1), key)
        # C major I chord: C-E-G (pc 0, 4, 7)
        # Very narrow range that might not contain any chord tones
        candidates = generate_chord_tone_candidates(hc, 61, 63, key)
        # MIDI 61=C#, 62=D, 63=Eb - none are C, E, or G
        assert candidates == ()

    def test_candidates_sorted(self) -> None:
        """Candidates should be sorted by pitch."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(FloatingNote(1), FloatingNote(1), key)
        candidates = generate_chord_tone_candidates(hc, 48, 84, key)
        assert candidates == tuple(sorted(candidates))

    def test_scale_candidates_all_seven_degrees(self) -> None:
        """Scale candidates should include all 7 scale degrees."""
        key = Key(tonic="C", mode="major")
        hc = infer_harmony_from_outer(FloatingNote(1), FloatingNote(1), key)
        candidates = generate_scale_candidates(hc, 60, 72, key)
        pcs = set(c % 12 for c in candidates)
        # C major: C(0), D(2), E(4), F(5), G(7), A(9), B(11)
        expected_pcs = {0, 2, 4, 5, 7, 9, 11}
        assert pcs == expected_pcs


class TestFugalConventionAssumptions:
    """Challenge assumptions in fugal voice handling."""

    def test_alto_delay_half_bar_assumption(self) -> None:
        """Is 1/2 bar delay always appropriate for alto entry?

        In real fugues, delay depends on subject length and tempo.
        A 1-bar subject typically has answer at 1 bar, not 1/2 bar.
        """
        spec = get_default_treatment_for_voice(0, 1, 4, ("statement",))
        assert spec.delay == Fraction(1, 2)
        # Is this musically correct? Real answer: depends on subject

    def test_tenor_delay_one_bar_assumption(self) -> None:
        """Is 1 bar delay always appropriate for tenor entry?"""
        spec = get_default_treatment_for_voice(0, 2, 4, ("statement",))
        assert spec.delay == Fraction(1)

    def test_bass_states_subject(self) -> None:
        """Bass states subject like all other voices.

        In real fugues, ALL voices eventually state the subject.
        Bass derives from subject at lower interval.
        """
        for phrase in range(10):
            spec = get_default_treatment_for_voice(phrase, 3, 4, ("statement",))
            assert spec.source == "subject"
            assert spec.interval == -7  # Octave below

    def test_answer_interval_convention(self) -> None:
        """The 'answer at 4th below' convention.

        interval=-3 means 3 scale degrees down.
        In music theory: 4th below means 5 semitones down.
        These are different measurements!
        """
        spec = get_default_treatment_for_voice(0, 1, 4, ("statement",))
        assert spec.interval == -3
        # -3 scale degrees from 1: 1->7->6->5 = scale degree 5
        # Which IS the 4th below (or 5th above) - so this is correct!


class TestVoiceCountEdgeCases:
    """Test voice count boundaries."""

    def test_voice_names_boundaries(self) -> None:
        """voice_names_for_count only handles 2, 3, 4 voices."""
        assert len(voice_names_for_count(2)) == 2
        assert len(voice_names_for_count(3)) == 3
        assert len(voice_names_for_count(4)) == 4

    def test_voice_names_1_raises(self) -> None:
        """1 voice is unsupported."""
        with pytest.raises(ValueError):
            voice_names_for_count(1)

    def test_voice_names_5_raises(self) -> None:
        """5 voices unsupported - but Bach wrote 5-voice fugues!"""
        with pytest.raises(ValueError):
            voice_names_for_count(5)

    def test_default_treatment_5_voices_returns_rest(self) -> None:
        """5-voice scenario falls through to rest."""
        spec = get_default_treatment_for_voice(0, 2, 5, ("statement",))
        assert spec.is_rest


class TestKeyModeBugs:
    """Test key and mode handling edge cases."""

    def test_all_tonics_produce_valid_scales(self) -> None:
        """Every tonic should produce a 7-note scale."""
        for tonic in ["C", "D", "E", "F", "G", "A", "B",
                      "C#", "D#", "F#", "G#", "A#",
                      "Db", "Eb", "Gb", "Ab", "Bb"]:
            for mode in ["major", "minor"]:
                key = Key(tonic=tonic, mode=mode)
                assert len(key.scale) == 7

    def test_enharmonic_keys_same_scale(self) -> None:
        """C# and Db should produce same pitch classes."""
        c_sharp = Key(tonic="C#", mode="major")
        d_flat = Key(tonic="Db", mode="major")
        # Scale degrees are relative, but tonic_pc should match
        assert c_sharp.tonic_pc == d_flat.tonic_pc


class TestDegreeConversionMath:
    """Test degree_to_pc math for correctness."""

    def test_c_major_scale_degrees(self) -> None:
        """C major scale degrees map to correct pitch classes."""
        key = Key(tonic="C", mode="major")
        expected = {1: 0, 2: 2, 3: 4, 4: 5, 5: 7, 6: 9, 7: 11}
        for degree, expected_pc in expected.items():
            actual_pc = degree_to_pc(degree, key)
            assert actual_pc == expected_pc, \
                f"Degree {degree}: expected pc {expected_pc}, got {actual_pc}"

    def test_g_major_scale_degrees(self) -> None:
        """G major scale degrees map to correct pitch classes."""
        key = Key(tonic="G", mode="major")
        # G major: G(7), A(9), B(11), C(0), D(2), E(4), F#(6)
        expected = {1: 7, 2: 9, 3: 11, 4: 0, 5: 2, 6: 4, 7: 6}
        for degree, expected_pc in expected.items():
            actual_pc = degree_to_pc(degree, key)
            assert actual_pc == expected_pc, \
                f"Degree {degree}: expected pc {expected_pc}, got {actual_pc}"

    def test_a_minor_scale_degrees(self) -> None:
        """A minor (natural) scale degrees map to correct pitch classes."""
        key = Key(tonic="A", mode="minor")
        # A natural minor: A(9), B(11), C(0), D(2), E(4), F(5), G(7)
        expected = {1: 9, 2: 11, 3: 0, 4: 2, 5: 4, 6: 5, 7: 7}
        for degree, expected_pc in expected.items():
            actual_pc = degree_to_pc(degree, key)
            assert actual_pc == expected_pc, \
                f"Degree {degree}: expected pc {expected_pc}, got {actual_pc}"


class TestRobustnessToUnexpectedInput:
    """Test how code handles unexpected (but possible) inputs."""

    def test_empty_treatments_tuple(self) -> None:
        """Empty treatments should still produce valid specs."""
        spec = get_default_treatment_for_voice(0, 0, 2, ())
        assert spec.treatment == "statement"  # Defaults to statement

    def test_very_long_treatments_tuple(self) -> None:
        """Long treatments tuple should cycle correctly."""
        treatments = tuple(f"t{i}" for i in range(100))
        spec = get_default_treatment_for_voice(50, 0, 2, treatments)
        # Should cycle: phrase 50 in outer voice uses treatments[50 % 100]
        assert spec.treatment == "t50"

    def test_phrase_index_very_large(self) -> None:
        """Large phrase indices should not crash."""
        spec = get_default_treatment_for_voice(1000, 0, 2, ("statement", "sequence"))
        # Should cycle: 1000 % 2 = 0 -> statement
        assert spec.treatment == "statement"

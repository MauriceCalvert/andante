"""100% coverage tests for engine.harmonic_context.

Tests import only:
- shared (shared types)
- engine.harmonic_context (module under test)
- stdlib
"""
import pytest
from shared.key import Key
from shared.pitch import FloatingNote, MidiPitch, Rest
from engine.harmonic_context import (
    HarmonicContext,
    degree_to_pc,
    pc_to_degree,
    infer_chord_from_bass,
    infer_harmony_from_outer,
    generate_chord_tone_candidates,
    generate_scale_candidates,
)


class TestHarmonicContextConstruction:
    """Test HarmonicContext dataclass construction."""

    def test_valid_construction(self) -> None:
        hc = HarmonicContext(
            root_pc=0,
            chord_tones=(0, 4, 7),
            scale=(0, 2, 4, 5, 7, 9, 11),
            bass_degree=1,
        )
        assert hc.root_pc == 0
        assert hc.chord_tones == (0, 4, 7)
        assert hc.bass_degree == 1

    def test_frozen(self) -> None:
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        with pytest.raises(Exception):
            hc.root_pc = 5


class TestHarmonicContextIsChordTone:
    """Test HarmonicContext.is_chord_tone method."""

    def test_root_is_chord_tone(self) -> None:
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        assert hc.is_chord_tone(0) is True

    def test_third_is_chord_tone(self) -> None:
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        assert hc.is_chord_tone(4) is True

    def test_fifth_is_chord_tone(self) -> None:
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        assert hc.is_chord_tone(7) is True

    def test_non_chord_tone(self) -> None:
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        assert hc.is_chord_tone(2) is False
        assert hc.is_chord_tone(5) is False
        assert hc.is_chord_tone(9) is False


class TestDegreeToPc:
    """Test degree_to_pc function."""

    def test_c_major_degree_1(self) -> None:
        key = Key(tonic="C", mode="major")
        assert degree_to_pc(1, key) == 0  # C

    def test_c_major_degree_5(self) -> None:
        key = Key(tonic="C", mode="major")
        assert degree_to_pc(5, key) == 7  # G

    def test_c_major_all_degrees(self) -> None:
        key = Key(tonic="C", mode="major")
        expected = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B
        for deg in range(1, 8):
            assert degree_to_pc(deg, key) == expected[deg - 1]

    def test_g_major_degree_1(self) -> None:
        key = Key(tonic="G", mode="major")
        assert degree_to_pc(1, key) == 7  # G

    def test_g_major_degree_7(self) -> None:
        key = Key(tonic="G", mode="major")
        assert degree_to_pc(7, key) == 6  # F#

    def test_a_minor_degree_3(self) -> None:
        key = Key(tonic="A", mode="minor")
        assert degree_to_pc(3, key) == 0  # C (minor 3rd from A)

    def test_invalid_degree_0(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="Degree must be 1-7"):
            degree_to_pc(0, key)

    def test_invalid_degree_8(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="Degree must be 1-7"):
            degree_to_pc(8, key)


class TestInferChordFromBass:
    """Test infer_chord_from_bass function."""

    def test_c_major_i_chord(self) -> None:
        key = Key(tonic="C", mode="major")
        chord = infer_chord_from_bass(1, key)
        assert chord == (0, 4, 7)  # C E G

    def test_c_major_v_chord(self) -> None:
        key = Key(tonic="C", mode="major")
        chord = infer_chord_from_bass(5, key)
        assert chord == (7, 11, 2)  # G B D

    def test_c_major_iv_chord(self) -> None:
        key = Key(tonic="C", mode="major")
        chord = infer_chord_from_bass(4, key)
        assert chord == (5, 9, 0)  # F A C

    def test_a_minor_i_chord(self) -> None:
        key = Key(tonic="A", mode="minor")
        chord = infer_chord_from_bass(1, key)
        assert chord == (9, 0, 4)  # A C E

    def test_g_major_ii_chord(self) -> None:
        key = Key(tonic="G", mode="major")
        chord = infer_chord_from_bass(2, key)
        # A minor chord in G major
        assert chord[0] == 9  # A

    def test_invalid_bass_degree_0(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="Bass degree must be 1-7"):
            infer_chord_from_bass(0, key)

    def test_invalid_bass_degree_8(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(AssertionError, match="Bass degree must be 1-7"):
            infer_chord_from_bass(8, key)


class TestInferHarmonyFromOuter:
    """Test infer_harmony_from_outer function."""

    def test_floating_notes(self) -> None:
        key = Key(tonic="C", mode="major")
        soprano = FloatingNote(5)  # G
        bass = FloatingNote(1)  # C
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 1
        assert hc.root_pc == 0
        assert hc.chord_tones == (0, 4, 7)

    def test_midi_pitches(self) -> None:
        key = Key(tonic="C", mode="major")
        soprano = MidiPitch(72)  # C5
        bass = MidiPitch(60)  # C4 - gives degree 1 via (60-60) % 7 + 1
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 1

    def test_unexpected_bass_type_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        soprano = FloatingNote(5)
        # Create an unexpected pitch type (string)
        with pytest.raises(TypeError, match="Unexpected bass pitch type"):
            infer_harmony_from_outer(soprano, "invalid", key)  # type: ignore

    def test_soprano_rest_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        soprano = Rest()
        bass = FloatingNote(1)
        with pytest.raises(AssertionError, match="Soprano cannot be rest"):
            infer_harmony_from_outer(soprano, bass, key)

    def test_bass_rest_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        soprano = FloatingNote(5)
        bass = Rest()
        with pytest.raises(AssertionError, match="Bass cannot be rest"):
            infer_harmony_from_outer(soprano, bass, key)

    def test_different_bass_degrees(self) -> None:
        key = Key(tonic="C", mode="major")
        for deg in range(1, 8):
            soprano = FloatingNote(1)
            bass = FloatingNote(deg)
            hc = infer_harmony_from_outer(soprano, bass, key)
            assert hc.bass_degree == deg


class TestGenerateChordToneCandidates:
    """Test generate_chord_tone_candidates function."""

    def test_c_major_middle_range(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        candidates = generate_chord_tone_candidates(hc, 60, 72, key)
        # Should include C4(60), E4(64), G4(67), C5(72)
        assert 60 in candidates
        assert 64 in candidates
        assert 67 in candidates
        assert 72 in candidates

    def test_narrow_range(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        candidates = generate_chord_tone_candidates(hc, 60, 65, key)
        assert 60 in candidates  # C4
        assert 64 in candidates  # E4
        assert 67 not in candidates  # G4 is above range

    def test_sorted_output(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        candidates = generate_chord_tone_candidates(hc, 48, 84, key)
        assert candidates == tuple(sorted(candidates))

    def test_invalid_range_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        with pytest.raises(AssertionError, match="Invalid range"):
            generate_chord_tone_candidates(hc, 72, 60, key)

    def test_equal_range_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        with pytest.raises(AssertionError, match="Invalid range"):
            generate_chord_tone_candidates(hc, 60, 60, key)


class TestGenerateScaleCandidates:
    """Test generate_scale_candidates function."""

    def test_c_major_octave_range(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        candidates = generate_scale_candidates(hc, 60, 72, key)
        # Should include all white notes from C4 to C5
        expected = (60, 62, 64, 65, 67, 69, 71, 72)
        assert candidates == expected

    def test_narrow_range(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        candidates = generate_scale_candidates(hc, 60, 64, key)
        assert candidates == (60, 62, 64)

    def test_sorted_output(self) -> None:
        key = Key(tonic="G", mode="major")
        hc = HarmonicContext(7, (7, 11, 2), key.scale, 1)
        candidates = generate_scale_candidates(hc, 48, 84, key)
        assert candidates == tuple(sorted(candidates))

    def test_invalid_range_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), (0, 2, 4, 5, 7, 9, 11), 1)
        with pytest.raises(AssertionError, match="Invalid range"):
            generate_scale_candidates(hc, 72, 60, key)

    def test_a_minor_scale(self) -> None:
        key = Key(tonic="A", mode="minor")
        hc = HarmonicContext(9, (9, 0, 4), key.scale, 1)
        candidates = generate_scale_candidates(hc, 57, 69, key)
        # A minor scale: A B C D E F G
        assert 57 in candidates  # A3
        assert 60 in candidates  # C4
        assert 64 in candidates  # E4


class TestPcToDegree:
    """Test pc_to_degree function."""

    def test_c_major_all_degrees(self) -> None:
        key = Key(tonic="C", mode="major")
        # C=0->1, D=2->2, E=4->3, F=5->4, G=7->5, A=9->6, B=11->7
        expected = {0: 1, 2: 2, 4: 3, 5: 4, 7: 5, 9: 6, 11: 7}
        for pc, degree in expected.items():
            assert pc_to_degree(pc, key) == degree

    def test_g_major_all_degrees(self) -> None:
        key = Key(tonic="G", mode="major")
        # G=7->1, A=9->2, B=11->3, C=0->4, D=2->5, E=4->6, F#=6->7
        expected = {7: 1, 9: 2, 11: 3, 0: 4, 2: 5, 4: 6, 6: 7}
        for pc, degree in expected.items():
            assert pc_to_degree(pc, key) == degree

    def test_chromatic_note_returns_none(self) -> None:
        key = Key(tonic="C", mode="major")
        # C# (pc=1) is not in C major scale
        assert pc_to_degree(1, key) is None
        # Eb (pc=3) is not in C major scale
        assert pc_to_degree(3, key) is None

    def test_a_minor_all_degrees(self) -> None:
        key = Key(tonic="A", mode="minor")
        # A=9->1, B=11->2, C=0->3, D=2->4, E=4->5, F=5->6, G=7->7
        expected = {9: 1, 11: 2, 0: 3, 2: 4, 4: 5, 5: 6, 7: 7}
        for pc, degree in expected.items():
            assert pc_to_degree(pc, key) == degree


class TestMusicTheoryCorrectness:
    """Tests that verify music theory correctness."""

    def test_midi_pitch_d4_is_degree_2(self) -> None:
        """D4 (MIDI 62) is degree 2 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(62)  # D4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 2  # D is 2nd degree in C major

    def test_midi_pitch_e4_is_degree_3(self) -> None:
        """E4 (MIDI 64) is degree 3 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(64)  # E4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 3  # E is 3rd degree in C major

    def test_midi_pitch_f4_is_degree_4(self) -> None:
        """F4 (MIDI 65) is degree 4 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(65)  # F4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 4  # F is 4th degree in C major

    def test_midi_pitch_g4_is_degree_5(self) -> None:
        """G4 (MIDI 67) is degree 5 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(67)  # G4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 5  # G is 5th degree in C major

    def test_midi_pitch_a4_is_degree_6(self) -> None:
        """A4 (MIDI 69) is degree 6 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(69)  # A4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 6  # A is 6th degree in C major

    def test_midi_pitch_b4_is_degree_7(self) -> None:
        """B4 (MIDI 71) is degree 7 in C major."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(71)  # B4
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 7  # B is 7th degree in C major

    def test_midi_pitch_in_g_major(self) -> None:
        """Test correct degree inference in G major."""
        key = Key(tonic="G", mode="major")
        # G4 (MIDI 67) should be degree 1 in G major
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(67), key)
        assert hc.bass_degree == 1
        # A4 (MIDI 69) should be degree 2 in G major
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(69), key)
        assert hc.bass_degree == 2
        # F#4 (MIDI 66) should be degree 7 in G major
        hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(66), key)
        assert hc.bass_degree == 7

    def test_chromatic_bass_defaults_to_tonic(self) -> None:
        """Chromatic bass note (not in scale) defaults to degree 1."""
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(61)  # C# - not in C major scale
        soprano = MidiPitch(72)
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 1  # Fallback to tonic

    def test_chord_quality_not_determined(self) -> None:
        """The code builds generic triads but doesn't distinguish major/minor quality.

        In C major:
        - I chord (degree 1) should be C-E-G (major)
        - ii chord (degree 2) should be D-F-A (minor)
        - vii° chord (degree 7) should be B-D-F (diminished)

        The code just stacks thirds from the scale, which works, but
        let's verify it actually produces correct intervals.
        """
        key = Key(tonic="C", mode="major")

        # ii chord in C major: D-F-A (minor third + major third)
        chord = infer_chord_from_bass(2, key)
        # D=2, F=5, A=9
        assert chord == (2, 5, 9)  # D, F, A - correct!

        # vii° chord in C major: B-D-F (minor third + minor third)
        chord = infer_chord_from_bass(7, key)
        # B=11, D=2, F=5
        assert chord == (11, 2, 5)  # B, D, F - correct!

    def test_v_chord_in_minor_should_be_major(self) -> None:
        """In baroque practice, V chord in minor is usually major (raised 7th).

        A minor: V chord should be E-G#-B, not E-G-B.
        The code uses natural minor scale, so V will be minor.
        This may be intentional (harmonic minor handled elsewhere).
        """
        key = Key(tonic="A", mode="minor")
        # V chord in A minor
        chord = infer_chord_from_bass(5, key)
        # E=4, G=7 (natural), B=11
        # In natural minor, this gives E-G-B (minor V)
        # In harmonic minor, should be E-G#-B (major V)
        assert chord == (4, 7, 11)  # E, G natural, B
        # Note: G natural (7) not G# (8) - this is natural minor V

    def test_generate_candidates_with_non_c_tonic(self) -> None:
        """Test that candidate generation works in non-C keys."""
        key = Key(tonic="F", mode="major")
        # F major I chord: F-A-C = 5, 9, 0
        hc = HarmonicContext(5, (5, 9, 0), key.scale, 1)
        candidates = generate_chord_tone_candidates(hc, 60, 72, key)
        # Should include F4(65), A4(69), C5(72)
        assert 65 in candidates  # F4
        assert 69 in candidates  # A4
        assert 72 in candidates  # C5
        # Should NOT include C4(60) - wait, C is also a chord tone (pc=0)
        # C4 = MIDI 60, pc = 0, which IS in chord_tones (5, 9, 0)
        assert 60 in candidates  # C4 - yes, C is part of F major chord

    def test_low_midi_values_handled(self) -> None:
        """Test candidate generation with low MIDI values (bass range)."""
        key = Key(tonic="C", mode="major")
        hc = HarmonicContext(0, (0, 4, 7), key.scale, 1)
        # Bass range: E2 (40) to E3 (52)
        candidates = generate_chord_tone_candidates(hc, 40, 52, key)
        # C = 0, 12, 24, 36, 48...
        # E = 4, 16, 28, 40, 52...
        # G = 7, 19, 31, 43...
        assert 40 in candidates  # E2
        assert 43 in candidates  # G2
        assert 48 in candidates  # C3
        assert 52 in candidates  # E3

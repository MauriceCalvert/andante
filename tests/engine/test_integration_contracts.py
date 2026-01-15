"""Integration contract tests between modules.

Tests that verify:
1. Output of module A matches expected input of module B
2. Data flows correctly through pipeline stages
3. Type contracts are maintained across boundaries

These tests focus on the INTERFACES between modules, not internal logic.
"""
from fractions import Fraction

import pytest
from shared.key import Key
from shared.pitch import FloatingNote, MidiPitch
from shared.types import VoiceMaterial, ExpandedVoices

from engine.harmonic_context import (
    HarmonicContext,
    infer_harmony_from_outer,
    generate_chord_tone_candidates,
)
from engine.arc_loader import (
    load_arc,
    get_default_treatment_for_voice,
    voice_names_for_count,
)
from engine.voice_entry import (
    VoiceTreatmentSpec,
    PhraseVoiceEntry,
    ArcVoiceEntries,
)
from engine.engine_types import (
    PhraseAST,
    EpisodeAST,
    SectionAST,
    PieceAST,
    ExpandedPhrase,
)
from engine.vocabulary import (
    ARTICULATIONS,
    RHYTHMS,
    DEVICES,
    GESTURES,
    ORNAMENTS,
)
from engine.validate import (
    TREATMENTS,
    CADENCES,
    SURPRISES,
    ENERGY_LEVELS,
)


class TestArcLoaderToVoiceEntry:
    """Test that arc_loader output is compatible with voice_entry types."""

    def test_arc_voice_count_matches_voice_names(self) -> None:
        """Arc voice_count must match voice_names_for_count output length."""
        for arc_name in ["imitative", "arch_form", "dialogue", "fugue_4voice", "chorale_4voice"]:
            arc = load_arc(arc_name)
            voice_names = voice_names_for_count(arc.voice_count)
            assert len(voice_names) == arc.voice_count

    def test_default_treatment_produces_valid_spec(self) -> None:
        """get_default_treatment_for_voice returns valid VoiceTreatmentSpec."""
        arc = load_arc("fugue_4voice")
        for phrase_idx in range(3):
            for voice_idx in range(arc.voice_count):
                spec = get_default_treatment_for_voice(
                    phrase_idx, voice_idx, arc.voice_count, arc.treatments
                )
                assert isinstance(spec, VoiceTreatmentSpec)
                assert isinstance(spec.treatment, str)
                assert isinstance(spec.interval, int)
                assert isinstance(spec.delay, Fraction)

    def test_arc_treatments_are_valid_for_phrase_ast(self) -> None:
        """Arc treatments must be valid treatment values for PhraseAST."""
        for arc_name in ["imitative", "arch_form", "fugue_4voice"]:
            arc = load_arc(arc_name)
            for treatment in arc.treatments:
                assert treatment in TREATMENTS or treatment == "statement", \
                    f"Arc {arc_name} has treatment '{treatment}' not in TREATMENTS"


class TestVoiceEntryToHarmonicContext:
    """Test that voice_entry specs work with harmonic_context."""

    def test_voice_spec_interval_valid_for_transposition(self) -> None:
        """VoiceTreatmentSpec intervals are valid for pitch transposition."""
        # 4-voice has inner voices with intervals
        for phrase_idx in range(4):
            for voice_idx in range(4):
                spec = get_default_treatment_for_voice(phrase_idx, voice_idx, 4, ("statement",))
                # Interval should be valid diatonic offset
                assert -14 <= spec.interval <= 14, \
                    f"Interval {spec.interval} out of typical range"

    def test_floating_note_degree_matches_harmonic_context_expectation(self) -> None:
        """FloatingNote degrees align with HarmonicContext bass_degree."""
        key = Key(tonic="C", mode="major")
        for degree in range(1, 8):
            bass = FloatingNote(degree)
            soprano = FloatingNote(1)
            hc = infer_harmony_from_outer(soprano, bass, key)
            assert hc.bass_degree == degree


class TestHarmonicContextToCandidate:
    """Test that HarmonicContext produces valid candidates."""

    def test_chord_tones_within_range(self) -> None:
        """Generated candidates are all within specified range."""
        key = Key(tonic="C", mode="major")
        bass = FloatingNote(1)  # C
        soprano = FloatingNote(5)  # G
        hc = infer_harmony_from_outer(soprano, bass, key)
        voice_low, voice_high = 48, 72
        candidates = generate_chord_tone_candidates(hc, voice_low, voice_high, key)
        for midi in candidates:
            assert voice_low <= midi <= voice_high

    def test_candidates_are_chord_tones(self) -> None:
        """All generated candidates are actual chord tones."""
        key = Key(tonic="C", mode="major")
        bass = FloatingNote(1)
        soprano = FloatingNote(1)
        hc = infer_harmony_from_outer(soprano, bass, key)
        candidates = generate_chord_tone_candidates(hc, 48, 72, key)
        for midi in candidates:
            pc = midi % 12
            assert pc in hc.chord_tones, f"MIDI {midi} (pc={pc}) not in chord tones {hc.chord_tones}"


class TestTypesCompatibility:
    """Test that plannertypes.py structures work together."""

    def test_expanded_phrase_voice_count_consistency(self) -> None:
        """ExpandedPhrase voice count matches VoiceMaterial indices."""
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1)],
            durations=[Fraction(1)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(1)],
            durations=[Fraction(1)],
        )
        voices = ExpandedVoices(voices=[soprano, bass])
        phrase = ExpandedPhrase(0, 1, voices, None, "I")
        assert len(phrase.voices.voices) == 2
        assert phrase.voices.voices[0].voice_index == 0
        assert phrase.voices.voices[1].voice_index == 1

    def test_piece_ast_section_consistency(self) -> None:
        """PieceAST sections have consistent structure."""
        phrase = PhraseAST(0, 4, "I", "authentic", "statement", None)
        episode = EpisodeAST("thematic", 4, "polyphonic", (phrase,))
        section = SectionAST("A", ("I",), "authentic", (episode,))
        piece = PieceAST(
            key="C", mode="major", metre="4/4", tempo="allegro",
            voices=2, subject=None, sections=(section,), arc="standard"
        )
        assert len(piece.sections) == 1
        assert len(piece.sections[0].episodes) == 1
        assert len(piece.sections[0].episodes[0].phrases) == 1


class TestVocabularyToValidate:
    """Test that vocabulary definitions match validation constraints."""

    def test_rhythm_names_match_validator(self) -> None:
        """Vocabulary RHYTHMS keys should be valid for validator."""
        from engine.validate import RHYTHMS as VALID_RHYTHMS
        for rhythm_name in RHYTHMS:
            assert rhythm_name in VALID_RHYTHMS, \
                f"Vocabulary rhythm '{rhythm_name}' not in validator"

    def test_device_names_match_validator(self) -> None:
        """Vocabulary DEVICES keys should be valid for validator."""
        from engine.validate import DEVICES as VALID_DEVICES
        for device_name in DEVICES:
            assert device_name in VALID_DEVICES, \
                f"Vocabulary device '{device_name}' not in validator"

    def test_gesture_names_match_validator(self) -> None:
        """Vocabulary GESTURES keys should be valid for validator."""
        from engine.validate import GESTURES as VALID_GESTURES
        for gesture_name in GESTURES:
            assert gesture_name in VALID_GESTURES, \
                f"Vocabulary gesture '{gesture_name}' not in validator"


class TestCrossModuleMusicTheory:
    """Test music theory consistency across modules."""

    def test_key_scale_consistency_with_harmonic_context(self) -> None:
        """Key.scale length matches HarmonicContext expectations."""
        for tonic in ["C", "G", "D", "F"]:
            for mode in ["major", "minor"]:
                key = Key(tonic=tonic, mode=mode)
                assert len(key.scale) == 7, f"Key {tonic} {mode} scale not 7 degrees"
                # HarmonicContext expects degrees 1-7
                for degree in range(1, 8):
                    bass = FloatingNote(degree)
                    soprano = FloatingNote(1)
                    hc = infer_harmony_from_outer(soprano, bass, key)
                    assert 1 <= hc.bass_degree <= 7

    def test_chord_tones_are_valid_pitch_classes(self) -> None:
        """Chord tones are always valid pitch classes (0-11)."""
        key = Key(tonic="C", mode="major")
        for degree in range(1, 8):
            bass = FloatingNote(degree)
            soprano = FloatingNote(1)
            hc = infer_harmony_from_outer(soprano, bass, key)
            for pc in hc.chord_tones:
                assert 0 <= pc <= 11, f"Invalid pitch class {pc}"


class TestArcVoiceEntriesContract:
    """Test ArcVoiceEntries contract with arc_loader."""

    def test_arc_with_explicit_entries_parses_correctly(self) -> None:
        """Arcs with voice_entries should parse into ArcVoiceEntries."""
        arc = load_arc("fugue_4voice")
        assert arc.has_explicit_entries is True
        assert arc.voice_entries.has_explicit_entries()

    def test_arc_without_explicit_entries_is_empty(self) -> None:
        """Arcs without voice_entries should have empty ArcVoiceEntries."""
        arc = load_arc("imitative")
        assert arc.has_explicit_entries is False
        assert not arc.voice_entries.has_explicit_entries()

    def test_voice_entry_voice_count_matches_arc(self) -> None:
        """ArcVoiceEntries.voice_count matches ArcDefinition.voice_count."""
        for arc_name in ["imitative", "fugue_4voice", "dialogue"]:
            arc = load_arc(arc_name)
            assert arc.voice_entries.voice_count == arc.voice_count


class TestTreatmentConsistency:
    """Test treatment values are consistent across modules."""

    def test_arc_treatments_subset_of_global_treatments(self) -> None:
        """Arc treatments must be subset of global TREATMENTS."""
        for arc_name in ["imitative", "arch_form", "fugue_4voice"]:
            arc = load_arc(arc_name)
            for t in arc.treatments:
                # statement is always valid even if not in file
                assert t in TREATMENTS or t == "statement", \
                    f"Arc '{arc_name}' uses unknown treatment '{t}'"

    def test_voice_spec_treatment_values(self) -> None:
        """VoiceTreatmentSpec treatments are valid."""
        valid_treatments = TREATMENTS | {"rest", "chordal", "imitation", "statement"}
        for voice_idx in range(4):
            spec = get_default_treatment_for_voice(0, voice_idx, 4, ("statement",))
            assert spec.treatment in valid_treatments, \
                f"Voice {voice_idx} has invalid treatment '{spec.treatment}'"


class TestDataFlowIntegrity:
    """Test that data flows correctly through potential pipeline stages."""

    def test_phrase_ast_to_expanded_phrase_compatibility(self) -> None:
        """PhraseAST fields should map to ExpandedPhrase fields."""
        ast = PhraseAST(
            index=0,
            bars=4,
            tonal_target="V",
            cadence="half",
            treatment="sequence",
            surprise=None,
        )
        # Create compatible ExpandedPhrase
        soprano = VoiceMaterial(0, [FloatingNote(1)], [Fraction(4)])
        bass = VoiceMaterial(1, [FloatingNote(5)], [Fraction(4)])
        voices = ExpandedVoices(voices=[soprano, bass])
        expanded = ExpandedPhrase(
            index=ast.index,
            bars=ast.bars,
            voices=voices,
            cadence=ast.cadence,
            tonal_target=ast.tonal_target,
        )
        assert expanded.index == ast.index
        assert expanded.bars == ast.bars
        assert expanded.cadence == ast.cadence
        assert expanded.tonal_target == ast.tonal_target


class TestMidiPitchConversion:
    """Test MidiPitch to degree conversion works correctly."""

    def test_midi_pitch_conversion_correct(self) -> None:
        """MidiPitch to degree conversion uses pitch class lookup.

        MIDI 62 (D4) is correctly identified as degree 2 in C major.
        """
        key = Key(tonic="C", mode="major")
        bass = MidiPitch(62)  # D4
        soprano = MidiPitch(72)  # C5
        hc = infer_harmony_from_outer(soprano, bass, key)
        assert hc.bass_degree == 2, "D is 2nd degree in C major"

    def test_all_c_major_degrees_from_midi(self) -> None:
        """Verify all C major scale degrees are correctly inferred from MIDI."""
        key = Key(tonic="C", mode="major")
        midi_to_degree = {60: 1, 62: 2, 64: 3, 65: 4, 67: 5, 69: 6, 71: 7}
        for midi, expected_degree in midi_to_degree.items():
            hc = infer_harmony_from_outer(MidiPitch(72), MidiPitch(midi), key)
            assert hc.bass_degree == expected_degree, \
                f"MIDI {midi} should be degree {expected_degree}"

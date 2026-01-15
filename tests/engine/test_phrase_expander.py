"""Integration tests for engine.phrase_expander.

Category B orchestrator tests: verify phrase expansion orchestration.
Tests import only:
- engine.phrase_expander (module under test)
- engine.types (data types)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.timed_material import TimedMaterial
from shared.types import ExpandedVoices, VoiceMaterial
from engine.phrase_expander import resolve_overrides, _build_nvoice_phrase
from engine.engine_types import ExpandedPhrase, PhraseAST


class TestResolveOverrides:
    """Test resolve_overrides function."""

    def test_resolve_overrides_no_surprises(self) -> None:
        """Treatment and rhythm from phrase when no surprises."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence=None,
            treatment="statement", surprise=None,
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, None)
        assert treatment == "statement"
        assert rhythm is None
        assert cadence is None

    def test_resolve_overrides_with_explicit_rhythm(self) -> None:
        """Explicit rhythm in phrase is preserved."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence=None,
            treatment="statement", surprise=None, rhythm="dotted",
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, None)
        assert rhythm == "dotted"

    def test_resolve_overrides_with_explicit_cadence(self) -> None:
        """Explicit cadence in phrase is preserved."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence="half",
            treatment="statement", surprise=None,
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, None)
        assert cadence == "half"

    def test_resolve_overrides_surprise_deceptive_overrides_cadence(self) -> None:
        """Deceptive surprise overrides to deceptive cadence."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence="authentic",
            treatment="statement", surprise="deceptive_cadence",
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, None)
        assert cadence == "deceptive"

    def test_resolve_overrides_energy_provides_rhythm(self) -> None:
        """Energy level can provide rhythm when none specified."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence=None,
            treatment="statement", surprise=None, energy="rising",
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, None)
        # Rising energy may affect rhythm selection
        # Actual value depends on energy.py config

    def test_resolve_overrides_episode_type_affects_treatment(self) -> None:
        """Episode type can affect treatment resolution."""
        phrase: PhraseAST = PhraseAST(
            index=0, bars=4, tonal_target="I", cadence=None,
            treatment="statement", surprise=None,
        )
        treatment, rhythm, cadence = resolve_overrides(phrase, "sequential")
        # Treatment should still be statement unless episode overrides
        assert isinstance(treatment, str)


class TestBuildNvoicePhrase:
    """Test _build_nvoice_phrase function."""

    def test_build_phrase_two_voices(self) -> None:
        """Build phrase from two voice materials."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(1)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5), FloatingNote(1), FloatingNote(1)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.index == 0
        assert expanded.tonal_target == "I"
        assert expanded.voices.count == 2
        assert len(expanded.voices.soprano.pitches) == 4

    def test_build_phrase_preserves_phrase_metadata(self) -> None:
        """Built phrase preserves all metadata from PhraseAST."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(1, 2), Fraction(1, 2)),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5)),
            durations=(Fraction(1, 2), Fraction(1, 2)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=5,
            bars=1,
            tonal_target="V",
            cadence="half",
            treatment="sequence",
            surprise=None,
            is_climax=True,
            articulation="legato",
            gesture="question",
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence="half",
            energy="high",
            texture="polyphonic",
            episode_type="development",
            metre="4/4",
            total_phrases=10,
        )
        assert expanded.index == 5
        assert expanded.tonal_target == "V"
        assert expanded.cadence == "half"
        assert expanded.is_climax is True
        assert expanded.articulation == "legato"
        assert expanded.gesture == "question"
        assert expanded.energy == "high"
        assert expanded.texture == "polyphonic"
        assert expanded.episode_type == "development"

    def test_build_phrase_four_voices(self) -> None:
        """Build phrase with four voice materials."""
        voices: list[TimedMaterial] = []
        for i in range(4):
            mat: TimedMaterial = TimedMaterial(
                pitches=(FloatingNote(1 + i), FloatingNote(2 + i)),
                durations=(Fraction(1, 2), Fraction(1, 2)),
                budget=Fraction(1),
            )
            voices.append(mat)
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=tuple(voices),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.voices.count == 4
        for i, voice in enumerate(expanded.voices.voices):
            assert voice.voice_index == i

    def test_build_phrase_applies_rhythm(self) -> None:
        """Rhythm parameter is applied to voice materials."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5), FloatingNote(1), FloatingNote(5)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm="dotted",  # Apply dotted rhythm
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        # Dotted rhythm changes durations
        sop_durs = expanded.voices.soprano.durations
        assert sum(sop_durs) == Fraction(1)  # Budget preserved

    def test_build_phrase_triple_metre_hemiola(self) -> None:
        """Hemiola can be triggered in triple metre."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=tuple(FloatingNote(d) for d in [1, 2, 3]),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(3, 4),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=tuple(FloatingNote(d) for d in [1, 5, 1]),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            budget=Fraction(3, 4),
        )
        phrase: PhraseAST = PhraseAST(
            index=9,  # Near end, might trigger hemiola
            bars=1,
            tonal_target="I",
            cadence="authentic",
            treatment="statement",
            surprise=None,
            is_climax=True,  # Climax can trigger hemiola
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(3, 4),
            rhythm=None,
            cadence="authentic",
            energy="high",
            texture="polyphonic",
            episode_type=None,
            metre="3/4",  # Triple metre allows hemiola
            total_phrases=10,
        )
        # Result should still be valid phrase
        assert expanded.index == 9


class TestVoiceMaterialConsistency:
    """Test that voice material indices are consistent."""

    def test_voice_indices_sequential(self) -> None:
        """Voice materials have sequential indices from 0."""
        voices: list[TimedMaterial] = []
        for _ in range(3):
            mat: TimedMaterial = TimedMaterial(
                pitches=(FloatingNote(1),),
                durations=(Fraction(1),),
                budget=Fraction(1),
            )
            voices.append(mat)
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=tuple(voices),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        for i, voice in enumerate(expanded.voices.voices):
            assert voice.voice_index == i, f"Voice {i} has wrong index {voice.voice_index}"

    def test_soprano_is_first_voice(self) -> None:
        """Soprano is always voice index 0."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(5),),  # High note
            durations=(Fraction(1),),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1),),  # Low note
            durations=(Fraction(1),),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.voices.soprano.voice_index == 0
        assert expanded.voices.soprano.pitches[0] == FloatingNote(5)

    def test_bass_is_last_voice(self) -> None:
        """Bass is always the last voice."""
        voices: list[TimedMaterial] = []
        for i in range(4):
            mat: TimedMaterial = TimedMaterial(
                pitches=(FloatingNote(5 - i),),  # Descending pitches
                durations=(Fraction(1),),
                budget=Fraction(1),
            )
            voices.append(mat)
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=tuple(voices),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.voices.bass.voice_index == 3
        assert expanded.voices.bass.pitches[0] == FloatingNote(2)


class TestExpandedPhraseProperties:
    """Test ExpandedPhrase property accessors."""

    def test_soprano_pitches_property(self) -> None:
        """soprano_pitches property returns soprano voice pitches."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(3), FloatingNote(5)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5), FloatingNote(1)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.soprano_pitches == (FloatingNote(1), FloatingNote(3), FloatingNote(5))

    def test_soprano_durations_property(self) -> None:
        """soprano_durations property returns soprano voice durations."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(2)),
            durations=(Fraction(3, 4), Fraction(1, 4)),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(5)),
            durations=(Fraction(1, 2), Fraction(1, 2)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.soprano_durations == (Fraction(3, 4), Fraction(1, 4))

    def test_bass_pitches_property(self) -> None:
        """bass_pitches property returns bass voice pitches."""
        sop_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(5),),
            durations=(Fraction(1),),
            budget=Fraction(1),
        )
        bass_mat: TimedMaterial = TimedMaterial(
            pitches=(FloatingNote(1), FloatingNote(4), FloatingNote(5)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            budget=Fraction(1),
        )
        phrase: PhraseAST = PhraseAST(
            index=0, bars=1, tonal_target="I", cadence=None, treatment="statement", surprise=None,
        )
        expanded: ExpandedPhrase = _build_nvoice_phrase(
            phrase=phrase,
            voice_materials=(sop_mat, bass_mat),
            main_budget=Fraction(1),
            rhythm=None,
            cadence=None,
            energy="moderate",
            texture="polyphonic",
            episode_type=None,
            metre="4/4",
            total_phrases=1,
        )
        assert expanded.bass_pitches == (FloatingNote(1), FloatingNote(4), FloatingNote(5))

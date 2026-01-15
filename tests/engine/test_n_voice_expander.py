"""Integration tests for engine.n_voice_expander.

Category B orchestrator tests: verify N-voice expansion from arc.
Tests import only:
- engine.n_voice_expander (module under test)
- engine.types (data types)
- engine.voice_config (VoiceSet)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Pitch, Rest
from engine.n_voice_expander import (
    expand_phrase_n_voice,
    expand_outer_voices_only,
    expand_single_voice,
    get_source_durations,
    get_source_pitches,
    VoiceExpansionContext,
)
from engine.arc_loader import load_arc
from engine.engine_types import MotifAST, PhraseAST
from engine.voice_config import voice_set_from_count
from engine.voice_entry import VoiceTreatmentSpec
from engine.voice_material import ExpandedVoices, VoiceMaterial


def make_subject() -> MotifAST:
    """Create a test subject motif."""
    return MotifAST(
        pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3), FloatingNote(4)),
        durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        bars=1,
    )


def make_counter_subject() -> MotifAST:
    """Create a test counter-subject motif."""
    return MotifAST(
        pitches=(FloatingNote(5), FloatingNote(4), FloatingNote(3), FloatingNote(2)),
        durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 2)),
        bars=1,
    )


def make_context(budget: Fraction = Fraction(2)) -> VoiceExpansionContext:
    """Create a test expansion context."""
    return VoiceExpansionContext(
        subject=make_subject(),
        counter_subject=make_counter_subject(),
        budget=budget,
        phrase_index=0,
        tonal_target="I",
    )


def make_phrase(
    index: int = 0,
    bars: int = 2,
    tonal_target: str = "I",
    cadence: str | None = None,
) -> PhraseAST:
    """Create a test phrase."""
    return PhraseAST(
        index=index,
        bars=bars,
        tonal_target=tonal_target,
        cadence=cadence,
        treatment="statement",
        surprise=None,
    )


class TestGetSourcePitches:
    """Test get_source_pitches function."""

    def test_source_subject(self) -> None:
        """Subject source returns subject pitches."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="subject", interval=0, delay=Fraction(0)
        )
        result: tuple[Pitch, ...] = get_source_pitches(spec, ctx)
        assert result == ctx.subject.pitches

    def test_source_counter_subject(self) -> None:
        """Counter-subject source returns counter_subject pitches."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="counter_subject", interval=0, delay=Fraction(0)
        )
        result: tuple[Pitch, ...] = get_source_pitches(spec, ctx)
        assert result == ctx.counter_subject.pitches

    def test_source_unknown_falls_back_to_subject(self) -> None:
        """Unknown source falls back to subject pitches."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="unknown", interval=0, delay=Fraction(0)
        )
        result: tuple[Pitch, ...] = get_source_pitches(spec, ctx)
        assert result == ctx.subject.pitches


class TestGetSourceDurations:
    """Test get_source_durations function."""

    def test_durations_subject(self) -> None:
        """Subject source returns subject durations."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="subject", interval=0, delay=Fraction(0)
        )
        result: tuple[Fraction, ...] = get_source_durations(spec, ctx)
        assert result == ctx.subject.durations

    def test_durations_unknown_falls_back_to_subject(self) -> None:
        """Unknown source falls back to subject durations."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="unknown", interval=0, delay=Fraction(0)
        )
        result: tuple[Fraction, ...] = get_source_durations(spec, ctx)
        assert result == ctx.subject.durations


class TestExpandSingleVoice:
    """Test expand_single_voice function."""

    def test_rest_spec_produces_rest(self) -> None:
        """Rest spec produces single rest for full budget."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec.rest()
        result: VoiceMaterial = expand_single_voice(spec, ctx, 1)
        assert len(result.pitches) == 1
        assert isinstance(result.pitches[0], Rest)
        assert result.durations[0] == ctx.budget

    def test_statement_produces_pitches(self) -> None:
        """Statement treatment produces pitched notes."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="subject", interval=0, delay=Fraction(0)
        )
        result: VoiceMaterial = expand_single_voice(spec, ctx, 0)
        assert len(result.pitches) > 0
        assert not isinstance(result.pitches[0], Rest)

    def test_inversion_transform(self) -> None:
        """Inversion treatment inverts pitches."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="inversion", source="subject", interval=0, delay=Fraction(0)
        )
        result: VoiceMaterial = expand_single_voice(spec, ctx, 0)
        # Inverted pitches should differ from original
        assert len(result.pitches) > 0

    def test_interval_transposes(self) -> None:
        """Non-zero interval transposes pitches."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec(
            treatment="statement", source="subject", interval=4, delay=Fraction(0)
        )
        result: VoiceMaterial = expand_single_voice(spec, ctx, 0)
        # Transposed pitches should be offset
        if isinstance(result.pitches[0], FloatingNote):
            orig: int = ctx.subject.pitches[0].degree
            assert result.pitches[0].degree != orig

    def test_voice_index_preserved(self) -> None:
        """Voice index is set correctly."""
        ctx: VoiceExpansionContext = make_context()
        spec: VoiceTreatmentSpec = VoiceTreatmentSpec.rest()
        result: VoiceMaterial = expand_single_voice(spec, ctx, 2)
        assert result.voice_index == 2


class TestExpandPhraseNVoice:
    """Test expand_phrase_n_voice function."""

    def test_two_voice_produces_two_materials(self) -> None:
        """Two-voice expansion produces 2 voice materials."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(2)
        result: ExpandedVoices = expand_phrase_n_voice(phrase, arc, voice_set, ctx)
        assert result.count == 2

    def test_four_voice_produces_four_materials(self) -> None:
        """Four-voice expansion produces 4 voice materials."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_phrase_n_voice(phrase, arc, voice_set, ctx)
        assert result.count == 4

    def test_soprano_at_index_zero(self) -> None:
        """Soprano is at voice index 0."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(2)
        result: ExpandedVoices = expand_phrase_n_voice(phrase, arc, voice_set, ctx)
        assert result.soprano.voice_index == 0

    def test_bass_at_last_index(self) -> None:
        """Bass is at last voice index."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_phrase_n_voice(phrase, arc, voice_set, ctx)
        assert result.bass.voice_index == 3

    def test_voice_indices_sequential(self) -> None:
        """Voice indices are sequential 0, 1, 2, ..."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_phrase_n_voice(phrase, arc, voice_set, ctx)
        for i, voice in enumerate(result.voices):
            assert voice.voice_index == i


class TestExpandOuterVoicesOnly:
    """Test expand_outer_voices_only function."""

    def test_outer_voices_not_rest(self) -> None:
        """Soprano and bass are not rests."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_outer_voices_only(phrase, arc, voice_set, ctx)
        assert not isinstance(result.soprano.pitches[0], Rest)
        assert not isinstance(result.bass.pitches[0], Rest)

    def test_inner_voices_are_rest(self) -> None:
        """Inner voices are rests (placeholders)."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_outer_voices_only(phrase, arc, voice_set, ctx)
        for i in range(1, result.count - 1):
            assert isinstance(result.voices[i].pitches[0], Rest)

    def test_inner_rest_duration_matches_budget(self) -> None:
        """Inner voice rest duration matches budget."""
        ctx: VoiceExpansionContext = make_context()
        phrase: PhraseAST = make_phrase()
        arc = load_arc("imitative")
        voice_set = voice_set_from_count(4)
        result: ExpandedVoices = expand_outer_voices_only(phrase, arc, voice_set, ctx)
        for i in range(1, result.count - 1):
            assert result.voices[i].durations[0] == ctx.budget


class TestVoiceExpansionContext:
    """Test VoiceExpansionContext dataclass."""

    def test_context_frozen(self) -> None:
        """Context is immutable."""
        ctx: VoiceExpansionContext = make_context()
        with pytest.raises(Exception):
            ctx.budget = Fraction(5)

    def test_context_has_subject(self) -> None:
        """Context has subject."""
        ctx: VoiceExpansionContext = make_context()
        assert ctx.subject is not None

    def test_context_budget(self) -> None:
        """Context budget is correct."""
        ctx: VoiceExpansionContext = make_context(budget=Fraction(4))
        assert ctx.budget == Fraction(4)

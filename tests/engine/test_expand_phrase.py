"""Integration tests for engine.expand_phrase.

Category B orchestrator tests: verify single phrase expansion.
Tests import only:
- engine.expand_phrase (module under test)
- engine.types (data types)
- engine.key (Key type)
- planner.subject (Subject type)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Pitch
from engine.expand_phrase import expand_phrase
from engine.key import Key
from engine.engine_types import ExpandedPhrase, PhraseAST
from planner.subject import Subject


def make_subject(degrees: tuple[int, ...] = (1, 2, 3, 4), mode: str = "major") -> Subject:
    """Create a test subject."""
    durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in degrees)
    return Subject(degrees=degrees, durations=durations, bars=1, mode=mode)


def make_phrase(
    index: int = 0,
    bars: int = 2,
    tonal_target: str = "I",
    treatment: str = "statement",
    cadence: str | None = None,
    **kwargs,
) -> PhraseAST:
    """Create a test phrase."""
    return PhraseAST(
        index=index,
        bars=bars,
        tonal_target=tonal_target,
        cadence=cadence,
        treatment=treatment,
        surprise=kwargs.get("surprise"),
        is_climax=kwargs.get("is_climax", False),
        articulation=kwargs.get("articulation"),
        rhythm=kwargs.get("rhythm"),
        device=kwargs.get("device"),
        gesture=kwargs.get("gesture"),
        energy=kwargs.get("energy"),
    )


class TestExpandPhraseBasic:
    """Test basic expand_phrase functionality."""

    def test_expand_phrase_returns_expanded_phrase(self) -> None:
        """expand_phrase returns ExpandedPhrase instance."""
        phrase: PhraseAST = make_phrase()
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert isinstance(result, ExpandedPhrase)

    def test_expand_phrase_preserves_index(self) -> None:
        """Phrase index is preserved in result."""
        phrase: PhraseAST = make_phrase(index=5)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.index == 5

    def test_expand_phrase_preserves_tonal_target(self) -> None:
        """Tonal target is preserved in result."""
        phrase: PhraseAST = make_phrase(tonal_target="V")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.tonal_target == "V"

    def test_expand_phrase_preserves_cadence(self) -> None:
        """Cadence is preserved in result."""
        phrase: PhraseAST = make_phrase(cadence="half")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.cadence == "half"

    def test_expand_phrase_preserves_is_climax(self) -> None:
        """is_climax flag is preserved in result."""
        phrase: PhraseAST = make_phrase(is_climax=True)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.is_climax is True

    def test_expand_phrase_preserves_articulation(self) -> None:
        """Articulation is preserved in result."""
        phrase: PhraseAST = make_phrase(articulation="legato")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.articulation == "legato"

    def test_expand_phrase_preserves_gesture(self) -> None:
        """Gesture is preserved in result."""
        phrase: PhraseAST = make_phrase(gesture="question")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.gesture == "question"


class TestExpandPhraseBudget:
    """Test that expand_phrase produces correct budget."""

    def test_expand_phrase_two_bar_budget(self) -> None:
        """Two bar phrase produces correct total duration."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected_budget: Fraction = Fraction(2)  # 2 bars * 1 whole note
        soprano_total: Fraction = sum(result.soprano_durations)
        bass_total: Fraction = sum(result.bass_durations)
        assert soprano_total == expected_budget
        assert bass_total == expected_budget

    def test_expand_phrase_four_bar_budget(self) -> None:
        """Four bar phrase produces correct total duration."""
        phrase: PhraseAST = make_phrase(bars=4)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected_budget: Fraction = Fraction(4)
        soprano_total: Fraction = sum(result.soprano_durations)
        bass_total: Fraction = sum(result.bass_durations)
        assert soprano_total == expected_budget
        assert bass_total == expected_budget

    def test_expand_phrase_triple_metre(self) -> None:
        """Triple metre phrase produces correct budget."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject((1, 2, 3))
        result: ExpandedPhrase = expand_phrase(phrase, subj, "3/4")
        expected_budget: Fraction = Fraction(3, 2)  # 2 bars * 3/4
        soprano_total: Fraction = sum(result.soprano_durations)
        bass_total: Fraction = sum(result.bass_durations)
        assert soprano_total == expected_budget
        assert bass_total == expected_budget

    def test_expand_phrase_cut_time(self) -> None:
        """Cut time (2/2) phrase produces correct budget."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "2/2")
        expected_budget: Fraction = Fraction(2)  # 2 bars * 1 whole
        soprano_total: Fraction = sum(result.soprano_durations)
        assert soprano_total == expected_budget


class TestExpandPhraseTreatments:
    """Test different treatment types."""

    def test_expand_phrase_statement_treatment(self) -> None:
        """Statement treatment produces valid output."""
        phrase: PhraseAST = make_phrase(treatment="statement")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.voices.count == 2
        assert len(result.soprano_pitches) > 0

    def test_expand_phrase_sequence_treatment(self) -> None:
        """Sequence treatment produces valid output."""
        phrase: PhraseAST = make_phrase(treatment="sequence", bars=4)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.voices.count == 2
        expected: Fraction = Fraction(4)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_imitation_treatment(self) -> None:
        """Imitation treatment produces valid output."""
        phrase: PhraseAST = make_phrase(treatment="imitation", bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.voices.count == 2


class TestExpandPhraseWithCadence:
    """Test phrase expansion with cadences."""

    def test_expand_phrase_with_half_cadence(self) -> None:
        """Half cadence phrase includes cadence material."""
        phrase: PhraseAST = make_phrase(bars=2, cadence="half")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_with_authentic_cadence(self) -> None:
        """Authentic cadence phrase includes cadence material."""
        phrase: PhraseAST = make_phrase(bars=2, cadence="authentic")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_final_authentic_cadence(self) -> None:
        """Final phrase with authentic cadence uses final cadence treatment."""
        phrase: PhraseAST = make_phrase(bars=2, cadence="authentic")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", is_final=True
        )
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected


class TestExpandPhraseWithDevice:
    """Test phrase expansion with devices."""

    def test_expand_phrase_with_stretto(self) -> None:
        """Stretto device is applied to phrase."""
        phrase: PhraseAST = make_phrase(bars=2, device="stretto")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_with_augmentation(self) -> None:
        """Augmentation device is applied to phrase."""
        phrase: PhraseAST = make_phrase(bars=4, device="augmentation")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(4)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_with_diminution(self) -> None:
        """Diminution device is applied to phrase."""
        phrase: PhraseAST = make_phrase(bars=2, device="diminution")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected


class TestExpandPhraseWithRhythm:
    """Test phrase expansion with rhythm patterns."""

    def test_expand_phrase_with_dotted_rhythm(self) -> None:
        """Dotted rhythm is applied to phrase."""
        phrase: PhraseAST = make_phrase(bars=2, rhythm="dotted")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_with_running_rhythm(self) -> None:
        """Running rhythm is applied to phrase."""
        phrase: PhraseAST = make_phrase(bars=2, rhythm="running")
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected


class TestExpandPhraseEpisodeTypes:
    """Test phrase expansion with different episode types."""

    def test_expand_phrase_statement_episode(self) -> None:
        """Statement episode type produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", episode_type="statement"
        )
        assert result.episode_type == "statement"

    def test_expand_phrase_sequential_episode(self) -> None:
        """Sequential episode type produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", episode_type="sequential"
        )
        assert result.episode_type == "sequential"

    def test_expand_phrase_cadenza_episode(self) -> None:
        """Cadenza episode produces special bass pattern."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", episode_type="cadenza"
        )
        assert result.episode_type == "cadenza"
        expected: Fraction = Fraction(2)
        assert sum(result.bass_durations) == expected


class TestExpandPhraseTextures:
    """Test phrase expansion with different textures."""

    def test_expand_phrase_polyphonic_texture(self) -> None:
        """Polyphonic texture produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", episode_texture="polyphonic"
        )
        assert result.texture == "polyphonic"

    def test_expand_phrase_figured_bass_texture(self) -> None:
        """Figured bass texture produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        key: Key = Key(tonic="C", mode="major")
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", episode_texture="figured_bass", key=key
        )
        assert result.texture == "figured_bass"


class TestExpandPhraseVoiceCount:
    """Test phrase expansion voice count."""

    def test_expand_phrase_two_voices(self) -> None:
        """Two-voice expansion produces 2 voices."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(
            phrase, subj, "4/4", voice_count=2
        )
        assert result.voices.count == 2

    def test_expand_phrase_default_two_voices(self) -> None:
        """Default expansion produces 2 voices."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.voices.count == 2


class TestExpandPhraseOutputTypes:
    """Test that output types are correct."""

    def test_soprano_pitches_are_pitch_type(self) -> None:
        """Soprano pitches are Pitch instances."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        for pitch in result.soprano_pitches:
            assert isinstance(pitch, Pitch)

    def test_soprano_durations_are_fractions(self) -> None:
        """Soprano durations are Fraction instances."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        for dur in result.soprano_durations:
            assert isinstance(dur, Fraction)

    def test_bass_pitches_are_pitch_type(self) -> None:
        """Bass pitches are Pitch instances."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        for pitch in result.bass_pitches:
            assert isinstance(pitch, Pitch)

    def test_bass_durations_are_fractions(self) -> None:
        """Bass durations are Fraction instances."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        for dur in result.bass_durations:
            assert isinstance(dur, Fraction)

    def test_pitch_duration_counts_match(self) -> None:
        """Pitch and duration lists have same length."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert len(result.soprano_pitches) == len(result.soprano_durations)
        assert len(result.bass_pitches) == len(result.bass_durations)


class TestExpandPhraseSeeding:
    """Test seed parameter for deterministic output."""

    def test_same_seed_same_output(self) -> None:
        """Same seed produces identical output."""
        phrase: PhraseAST = make_phrase(bars=2)
        subj: Subject = make_subject()
        result1: ExpandedPhrase = expand_phrase(phrase, subj, "4/4", seed=42)
        result2: ExpandedPhrase = expand_phrase(phrase, subj, "4/4", seed=42)
        assert result1.soprano_pitches == result2.soprano_pitches
        assert result1.soprano_durations == result2.soprano_durations


class TestExpandPhraseMinorMode:
    """Test phrase expansion in minor mode."""

    def test_expand_phrase_minor_mode(self) -> None:
        """Minor mode phrase produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2, tonal_target="i")
        subj: Subject = make_subject(mode="minor")
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.tonal_target == "i"
        expected: Fraction = Fraction(2)
        assert sum(result.soprano_durations) == expected

    def test_expand_phrase_minor_dominant(self) -> None:
        """Minor mode with dominant target produces valid output."""
        phrase: PhraseAST = make_phrase(bars=2, tonal_target="V")
        subj: Subject = make_subject(mode="minor")
        result: ExpandedPhrase = expand_phrase(phrase, subj, "4/4")
        assert result.tonal_target == "V"

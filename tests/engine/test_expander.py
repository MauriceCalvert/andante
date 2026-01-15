"""Integration tests for engine.expander.

Category B orchestrator tests: verify piece-level expansion orchestration.
Tests import only:
- engine.expander (module under test)
- engine.types (data types)
- planner.subject (Subject type)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import Pitch
from engine.expander import expand_piece, bar_duration
from engine.engine_types import (
    EpisodeAST,
    ExpandedPhrase,
    PhraseAST,
    PieceAST,
    SectionAST,
)
from planner.subject import Subject


def make_subject(degrees: tuple[int, ...] = (1, 2, 3, 4), mode: str = "major") -> Subject:
    """Create a test subject."""
    durations: tuple[Fraction, ...] = tuple(Fraction(1, 4) for _ in degrees)
    return Subject(degrees=degrees, durations=durations, bars=1, mode=mode)


def make_phrase(index: int, bars: int = 2, tonal_target: str = "I", cadence: str | None = None) -> PhraseAST:
    """Create a test phrase."""
    return PhraseAST(
        index=index,
        bars=bars,
        tonal_target=tonal_target,
        cadence=cadence,
        treatment="statement",
        surprise=None,
    )


def make_episode(phrases: tuple[PhraseAST, ...], bars: int = 4, episode_type: str = "statement") -> EpisodeAST:
    """Create a test episode."""
    return EpisodeAST(
        type=episode_type,
        bars=bars,
        texture="polyphonic",
        phrases=phrases,
    )


def make_section(episodes: tuple[EpisodeAST, ...], tonal_path: tuple[str, ...] = ("I",)) -> SectionAST:
    """Create a test section."""
    return SectionAST(
        label="A",
        tonal_path=tonal_path,
        final_cadence="authentic",
        episodes=episodes,
    )


def make_piece(sections: tuple[SectionAST, ...], voices: int = 2, mode: str = "major") -> PieceAST:
    """Create a test piece."""
    return PieceAST(
        key="C",
        mode=mode,
        metre="4/4",
        tempo="allegro",
        voices=voices,
        subject=make_subject(mode=mode),
        sections=sections,
        arc="imitative",
    )


class TestBarDuration:
    """Test bar_duration function."""

    def test_bar_duration_common_time(self) -> None:
        """4/4 metre produces 1 whole note bar."""
        assert bar_duration("4/4") == Fraction(1)

    def test_bar_duration_triple_time(self) -> None:
        """3/4 metre produces 3/4 bar."""
        assert bar_duration("3/4") == Fraction(3, 4)

    def test_bar_duration_cut_time(self) -> None:
        """2/2 metre produces 1 whole note bar."""
        assert bar_duration("2/2") == Fraction(1)

    def test_bar_duration_six_eight(self) -> None:
        """6/8 metre produces 3/4 bar."""
        assert bar_duration("6/8") == Fraction(3, 4)


class TestExpandPieceBasic:
    """Test basic expand_piece functionality."""

    def test_expand_piece_single_phrase(self) -> None:
        """Expand piece with single phrase."""
        phrase: PhraseAST = make_phrase(0, bars=2, cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert len(result) == 1
        assert result[0].index == 0

    def test_expand_piece_multiple_phrases(self) -> None:
        """Expand piece with multiple phrases."""
        phrase1: PhraseAST = make_phrase(0, bars=2, tonal_target="I")
        phrase2: PhraseAST = make_phrase(1, bars=2, tonal_target="V", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase1, phrase2), bars=4)
        section: SectionAST = make_section((episode,), tonal_path=("I", "V"))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert len(result) == 2
        assert result[0].index == 0
        assert result[1].index == 1

    def test_expand_piece_preserves_phrase_order(self) -> None:
        """Phrases are expanded in order."""
        phrases: list[PhraseAST] = []
        for i in range(4):
            cadence: str | None = "authentic" if i == 3 else None
            bars: int = 2 if i == 3 else 1  # Final phrase needs 2 bars for cadence
            phrases.append(make_phrase(i, bars=bars, cadence=cadence))
        episode: EpisodeAST = make_episode(tuple(phrases), bars=5)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert len(result) == 4
        for i, exp in enumerate(result):
            assert exp.index == i


class TestExpandPieceMultipleSections:
    """Test expansion with multiple sections."""

    def test_expand_piece_two_sections(self) -> None:
        """Expand piece with two sections."""
        phrase1: PhraseAST = make_phrase(0, bars=2, tonal_target="I")
        episode1: EpisodeAST = make_episode((phrase1,), bars=2)
        section1: SectionAST = make_section((episode1,))
        phrase2: PhraseAST = make_phrase(1, bars=2, tonal_target="I", cadence="authentic")
        episode2: EpisodeAST = make_episode((phrase2,), bars=2)
        section2: SectionAST = make_section((episode2,))
        piece: PieceAST = make_piece((section1, section2))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert len(result) == 2

    def test_expand_piece_multiple_episodes(self) -> None:
        """Expand piece with multiple episodes in section."""
        phrase1: PhraseAST = make_phrase(0, bars=2, tonal_target="I")
        episode1: EpisodeAST = make_episode((phrase1,), bars=2, episode_type="statement")
        phrase2: PhraseAST = make_phrase(1, bars=2, tonal_target="V")
        episode2: EpisodeAST = make_episode((phrase2,), bars=2, episode_type="continuation")
        phrase3: PhraseAST = make_phrase(2, bars=2, tonal_target="I", cadence="authentic")
        episode3: EpisodeAST = make_episode((phrase3,), bars=2, episode_type="statement")
        section: SectionAST = make_section((episode1, episode2, episode3), tonal_path=("I", "V", "I"))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert len(result) == 3


class TestExpandPieceBudgets:
    """Test that expansion produces correct budgets."""

    def test_expand_piece_budgets_sum_correctly(self) -> None:
        """Phrase durations sum to expected total."""
        phrase1: PhraseAST = make_phrase(0, bars=2, tonal_target="I")
        phrase2: PhraseAST = make_phrase(1, bars=3, tonal_target="V", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase1, phrase2), bars=5)
        section: SectionAST = make_section((episode,), tonal_path=("I", "V"))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        total_soprano: Fraction = sum(
            sum(p.soprano_durations) for p in result
        )
        assert total_soprano == Fraction(5)  # 2 + 3 bars

    def test_expand_piece_triple_metre_budget(self) -> None:
        """Triple metre produces correct budgets."""
        phrase: PhraseAST = make_phrase(0, bars=4, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=4)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = PieceAST(
            key="C",
            mode="major",
            metre="3/4",
            tempo="allegro",
            voices=2,
            subject=make_subject((1, 2, 3)),
            sections=(section,),
            arc="imitative",
        )
        result: list[ExpandedPhrase] = expand_piece(piece)
        expected: Fraction = Fraction(3)  # 4 bars * 3/4
        assert sum(result[0].soprano_durations) == expected


class TestExpandPieceVoices:
    """Test expansion with different voice counts."""

    def test_expand_piece_two_voices(self) -> None:
        """Two-voice piece produces 2 voices per phrase."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,), voices=2)
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].voices.count == 2


class TestExpandPieceTonalTargets:
    """Test expansion with different tonal targets."""

    def test_expand_piece_dominant_target(self) -> None:
        """Dominant tonal target is preserved."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="V", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,), tonal_path=("V",))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].tonal_target == "V"

    def test_expand_piece_tonal_path(self) -> None:
        """Tonal path I-V-I is followed."""
        phrase1: PhraseAST = make_phrase(0, bars=1, tonal_target="I")
        phrase2: PhraseAST = make_phrase(1, bars=1, tonal_target="V")
        phrase3: PhraseAST = make_phrase(2, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase1, phrase2, phrase3), bars=4)
        section: SectionAST = make_section((episode,), tonal_path=("I", "V", "I"))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].tonal_target == "I"
        assert result[1].tonal_target == "V"
        assert result[2].tonal_target == "I"


class TestExpandPieceMinorMode:
    """Test expansion in minor mode."""

    def test_expand_piece_minor_mode(self) -> None:
        """Minor mode piece expands correctly."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="i", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,), tonal_path=("i",))
        piece: PieceAST = make_piece((section,), mode="minor")
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].tonal_target == "i"


class TestExpandPieceOutputTypes:
    """Test that output types are correct."""

    def test_output_is_list_of_expanded_phrases(self) -> None:
        """Output is list of ExpandedPhrase."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert isinstance(result, list)
        for exp in result:
            assert isinstance(exp, ExpandedPhrase)

    def test_soprano_pitches_are_pitch_type(self) -> None:
        """Soprano pitches are Pitch instances."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        for pitch in result[0].soprano_pitches:
            assert isinstance(pitch, Pitch)

    def test_durations_are_fractions(self) -> None:
        """Durations are Fraction instances."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        for dur in result[0].soprano_durations:
            assert isinstance(dur, Fraction)

    def test_pitch_duration_counts_match(self) -> None:
        """Pitch and duration counts match for each voice."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        for exp in result:
            assert len(exp.soprano_pitches) == len(exp.soprano_durations)
            assert len(exp.bass_pitches) == len(exp.bass_durations)


class TestExpandPieceEpisodeTypes:
    """Test expansion with different episode types."""

    def test_expand_piece_statement_episode(self) -> None:
        """Statement episode type is preserved."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2, episode_type="statement")
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].episode_type == "statement"

    def test_expand_piece_continuation_episode(self) -> None:
        """Continuation episode type is preserved."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="V", cadence="authentic")
        episode: EpisodeAST = make_episode((phrase,), bars=2, episode_type="continuation")
        section: SectionAST = make_section((episode,), tonal_path=("V",))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].episode_type == "continuation"


class TestExpandPieceTexture:
    """Test expansion with different textures."""

    def test_expand_piece_polyphonic_texture(self) -> None:
        """Polyphonic texture is preserved."""
        phrase: PhraseAST = make_phrase(0, bars=2, tonal_target="I", cadence="authentic")
        episode: EpisodeAST = EpisodeAST(
            type="statement",
            bars=2,
            texture="polyphonic",
            phrases=(phrase,),
        )
        section: SectionAST = make_section((episode,))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        assert result[0].texture == "polyphonic"


class TestExpandPieceIntegrity:
    """Test data integrity through expansion."""

    def test_phrase_metadata_preserved(self) -> None:
        """Phrase metadata is preserved through expansion."""
        phrase: PhraseAST = PhraseAST(
            index=0,
            bars=2,
            tonal_target="V",
            cadence="half",
            treatment="sequence",
            surprise=None,
            is_climax=True,
            articulation="legato",
            gesture="question",
            energy="rising",  # Use valid energy level
        )
        episode: EpisodeAST = make_episode((phrase,), bars=2)
        section: SectionAST = make_section((episode,), tonal_path=("V",))
        piece: PieceAST = make_piece((section,))
        result: list[ExpandedPhrase] = expand_piece(piece)
        exp = result[0]
        assert exp.tonal_target == "V"
        assert exp.cadence == "half"
        assert exp.is_climax is True
        assert exp.articulation == "legato"
        assert exp.gesture == "question"
        assert exp.energy == "rising"

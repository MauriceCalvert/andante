"""100% coverage tests for engine.annotate.

Tests import only:
- engine.annotate (module under test)
- stdlib

Note: We import types from engine.types because annotate.py depends on them.
This is acceptable since we're testing annotate's public interface which consumes these types.
The types are used as test fixtures, not as the module under test.
"""
from fractions import Fraction

import pytest
from engine.annotate import extract_annotations, _level_order

# Import types needed to construct test inputs for annotate module.
# These are the input types that annotate.py accepts, not sibling logic.
from engine.engine_types import (
    Annotation,
    PieceAST,
    SectionAST,
    EpisodeAST,
    PhraseAST,
)


def make_phrase(index: int, bars: int = 4, treatment: str = "statement") -> PhraseAST:
    """Helper to create a phrase."""
    return PhraseAST(
        index=index,
        bars=bars,
        tonal_target="I",
        cadence=None,
        treatment=treatment,
        surprise=None,
    )


def make_episode(
    type_: str = "thematic", bars: int = 8, phrases: tuple[PhraseAST, ...] = ()
) -> EpisodeAST:
    """Helper to create an episode."""
    if not phrases:
        phrases = (make_phrase(0, bars // 2), make_phrase(1, bars // 2))
    return EpisodeAST(
        type=type_,
        bars=bars,
        texture="polyphonic",
        phrases=phrases,
    )


def make_section(
    label: str = "A",
    tonal_path: tuple[str, ...] = ("I",),
    episodes: tuple[EpisodeAST, ...] = (),
) -> SectionAST:
    """Helper to create a section."""
    if not episodes:
        episodes = (make_episode(),)
    return SectionAST(
        label=label,
        tonal_path=tonal_path,
        final_cadence="authentic",
        episodes=episodes,
    )


def make_piece(
    metre: str = "4/4",
    sections: tuple[SectionAST, ...] = (),
) -> PieceAST:
    """Helper to create a piece."""
    if not sections:
        sections = (make_section(),)
    return PieceAST(
        key="C",
        mode="major",
        metre=metre,
        tempo="allegro",
        voices=2,
        subject=None,
        sections=sections,
        arc="standard",
    )


class TestExtractAnnotationsGranularityNone:
    """Test extract_annotations with granularity='none'."""

    def test_returns_empty_tuple(self) -> None:
        piece = make_piece()
        result = extract_annotations(piece, granularity="none")
        assert result == ()


class TestExtractAnnotationsGranularitySection:
    """Test extract_annotations with granularity='section'."""

    def test_single_section(self) -> None:
        piece = make_piece()
        result = extract_annotations(piece, granularity="section")
        assert len(result) == 1
        assert result[0].text == "A: I"
        assert result[0].level == "section"
        assert result[0].offset == Fraction(0)

    def test_two_sections(self) -> None:
        sections = (
            make_section(label="A", tonal_path=("I", "V")),
            make_section(label="B", tonal_path=("vi",)),
        )
        piece = make_piece(sections=sections)
        result = extract_annotations(piece, granularity="section")
        assert len(result) == 2
        assert result[0].text == "A: I"
        assert result[1].text == "B: vi"

    def test_section_empty_tonal_path_defaults_to_I(self) -> None:
        section = make_section(tonal_path=())
        piece = make_piece(sections=(section,))
        result = extract_annotations(piece, granularity="section")
        assert result[0].text == "A: I"


class TestExtractAnnotationsGranularityEpisode:
    """Test extract_annotations with granularity='episode'."""

    def test_includes_section_and_episode(self) -> None:
        episodes = (make_episode(type_="thematic"), make_episode(type_="transitional"))
        section = make_section(episodes=episodes)
        piece = make_piece(sections=(section,))
        result = extract_annotations(piece, granularity="episode")
        # Should have 1 section + 2 episodes
        section_annots = [a for a in result if a.level == "section"]
        episode_annots = [a for a in result if a.level == "episode"]
        assert len(section_annots) == 1
        assert len(episode_annots) == 2
        assert episode_annots[0].text == "thematic"
        assert episode_annots[1].text == "transitional"


class TestExtractAnnotationsGranularityPhrase:
    """Test extract_annotations with granularity='phrase'."""

    def test_default_granularity_is_phrase(self) -> None:
        piece = make_piece()
        result = extract_annotations(piece)  # No granularity specified
        phrase_annots = [a for a in result if a.level == "phrase"]
        assert len(phrase_annots) > 0

    def test_includes_all_levels(self) -> None:
        piece = make_piece()
        result = extract_annotations(piece, granularity="phrase")
        levels = {a.level for a in result}
        assert "section" in levels
        assert "episode" in levels
        assert "phrase" in levels

    def test_phrase_offset_calculation_4_4(self) -> None:
        phrases = (
            make_phrase(0, bars=2, treatment="statement"),
            make_phrase(1, bars=2, treatment="sequence"),
        )
        episode = make_episode(phrases=phrases, bars=4)
        section = make_section(episodes=(episode,))
        piece = make_piece(metre="4/4", sections=(section,))
        result = extract_annotations(piece, granularity="phrase")
        phrase_annots = [a for a in result if a.level == "phrase"]
        assert len(phrase_annots) == 2
        assert phrase_annots[0].offset == Fraction(0)
        # 2 bars of 4/4 = 2 whole notes
        assert phrase_annots[1].offset == Fraction(2)

    def test_phrase_offset_calculation_3_4(self) -> None:
        phrases = (
            make_phrase(0, bars=4, treatment="statement"),
            make_phrase(1, bars=4, treatment="sequence"),
        )
        episode = make_episode(phrases=phrases, bars=8)
        section = make_section(episodes=(episode,))
        piece = make_piece(metre="3/4", sections=(section,))
        result = extract_annotations(piece, granularity="phrase")
        phrase_annots = [a for a in result if a.level == "phrase"]
        # 4 bars of 3/4 = 4 * (3/4) = 3 whole notes
        assert phrase_annots[1].offset == Fraction(3)


class TestExtractAnnotationsSorting:
    """Test that annotations are sorted correctly."""

    def test_sorted_by_offset(self) -> None:
        phrases = (
            make_phrase(0, bars=4),
            make_phrase(1, bars=4),
        )
        episode = make_episode(phrases=phrases, bars=8)
        section = make_section(episodes=(episode,))
        piece = make_piece(sections=(section,))
        result = extract_annotations(piece, granularity="phrase")
        offsets = [a.offset for a in result]
        assert offsets == sorted(offsets)

    def test_same_offset_sorted_by_level(self) -> None:
        piece = make_piece()
        result = extract_annotations(piece, granularity="phrase")
        # At offset 0, section should come before episode, which comes before phrase
        at_zero = [a for a in result if a.offset == Fraction(0)]
        levels = [a.level for a in at_zero]
        assert levels == ["section", "episode", "phrase"]


class TestLevelOrder:
    """Test _level_order function."""

    def test_section_is_0(self) -> None:
        assert _level_order("section") == 0

    def test_episode_is_1(self) -> None:
        assert _level_order("episode") == 1

    def test_phrase_is_2(self) -> None:
        assert _level_order("phrase") == 2

    def test_unknown_is_3(self) -> None:
        assert _level_order("unknown") == 3
        assert _level_order("bar") == 3


class TestExtractAnnotationsInvalidGranularity:
    """Test extract_annotations with invalid granularity."""

    def test_invalid_granularity_skips_section_annotation(self) -> None:
        # Invalid granularity doesn't match any of the if conditions
        # This exercises the branch where granularity check at line 28 is false
        piece = make_piece()
        result = extract_annotations(piece, granularity="invalid")
        # Should return empty since no annotations are added
        assert len(result) == 0


class TestAnnotationDataclass:
    """Test Annotation dataclass."""

    def test_construction(self) -> None:
        ann = Annotation(offset=Fraction(1, 2), text="test", level="phrase")
        assert ann.offset == Fraction(1, 2)
        assert ann.text == "test"
        assert ann.level == "phrase"

    def test_frozen(self) -> None:
        ann = Annotation(offset=Fraction(0), text="test", level="phrase")
        with pytest.raises(Exception):
            ann.text = "modified"

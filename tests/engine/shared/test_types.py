"""100% coverage tests for engine.types.

Tests import only:
- shared (shared types)
- engine (module under test)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Rest
from shared.types import VoiceMaterial, ExpandedVoices
from engine.engine_types import (
    Annotation,
    EpisodeAST,
    ExpandedPhrase,
    MotifAST,
    PhraseAST,
    PieceAST,
    PieceMetrics,
    RealisedNote,
    RealisedPhrase,
    RealisedVoice,
    SectionAST,
)


class TestPhraseAST:
    """Test PhraseAST dataclass."""

    def test_minimal_construction(self) -> None:
        p = PhraseAST(
            index=0,
            bars=4,
            tonal_target="I",
            cadence="authentic",
            treatment="statement",
            surprise=None,
        )
        assert p.index == 0
        assert p.bars == 4
        assert p.is_climax is False

    def test_with_all_fields(self) -> None:
        p = PhraseAST(
            index=1,
            bars=2,
            tonal_target="V",
            cadence="half",
            treatment="sequence",
            surprise="deceptive",
            is_climax=True,
            articulation="legato",
            rhythm="dotted",
            device="stretto",
            gesture="drive",
            energy="peak",
            voice_assignments=("subject", "cs_1"),
        )
        assert p.is_climax is True
        assert p.articulation == "legato"
        assert p.voice_assignments == ("subject", "cs_1")


class TestEpisodeAST:
    """Test EpisodeAST dataclass."""

    def test_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", "authentic", "statement", None)
        e = EpisodeAST(
            type="statement",
            bars=4,
            texture="polyphonic",
            phrases=(phrase,),
        )
        assert e.type == "statement"
        assert e.is_transition is False

    def test_with_transition(self) -> None:
        phrase = PhraseAST(0, 2, "V", None, "sequence", None)
        e = EpisodeAST(
            type="modulating",
            bars=2,
            texture="homophonic",
            phrases=(phrase,),
            is_transition=True,
        )
        assert e.is_transition is True


class TestSectionAST:
    """Test SectionAST dataclass."""

    def test_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", "authentic", "statement", None)
        episode = EpisodeAST("statement", 4, "polyphonic", (phrase,))
        s = SectionAST(
            label="A",
            tonal_path=("I", "V"),
            final_cadence="authentic",
            episodes=(episode,),
        )
        assert s.label == "A"
        assert s.tonal_path == ("I", "V")


class TestMotifAST:
    """Test MotifAST dataclass."""

    def test_construction(self) -> None:
        m = MotifAST(
            pitches=(FloatingNote(1), FloatingNote(2), FloatingNote(3)),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        assert len(m.pitches) == 3
        assert m.bars == 1


class TestPieceAST:
    """Test PieceAST dataclass."""

    def test_minimal_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", "authentic", "statement", None)
        episode = EpisodeAST("statement", 4, "polyphonic", (phrase,))
        section = SectionAST("A", ("I",), "authentic", (episode,))
        p = PieceAST(
            key="C",
            mode="major",
            metre="4/4",
            tempo="allegro",
            voices=2,
            subject=None,  # Simplified for test
            sections=(section,),
            arc="standard",
        )
        assert p.key == "C"
        assert p.upbeat == Fraction(0)
        assert p.form == "through_composed"
        assert p.virtuosic is False


class TestExpandedPhrase:
    """Test ExpandedPhrase dataclass."""

    def test_construction(self) -> None:
        voices = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5), FloatingNote(4)],
            soprano_durations=[Fraction(1, 2), Fraction(1, 2)],
            bass_pitches=[FloatingNote(1), FloatingNote(2)],
            bass_durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        ep = ExpandedPhrase(
            index=0,
            bars=2,
            voices=voices,
            cadence="authentic",
            tonal_target="I",
        )
        assert ep.index == 0
        assert ep.bars == 2
        assert ep.texture == "polyphonic"

    def test_soprano_pitches_property(self) -> None:
        voices = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5), FloatingNote(4), FloatingNote(3)],
            soprano_durations=[Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)],
            bass_pitches=[FloatingNote(1)],
            bass_durations=[Fraction(1)],
        )
        ep = ExpandedPhrase(0, 1, voices, None, "I")
        assert ep.soprano_pitches == (FloatingNote(5), FloatingNote(4), FloatingNote(3))

    def test_soprano_durations_property(self) -> None:
        voices = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(1), FloatingNote(2)],
            soprano_durations=[Fraction(1, 4), Fraction(3, 4)],
            bass_pitches=[FloatingNote(1)],
            bass_durations=[Fraction(1)],
        )
        ep = ExpandedPhrase(0, 1, voices, None, "I")
        assert ep.soprano_durations == (Fraction(1, 4), Fraction(3, 4))

    def test_bass_pitches_property(self) -> None:
        voices = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5)],
            soprano_durations=[Fraction(1)],
            bass_pitches=[FloatingNote(1), FloatingNote(5), FloatingNote(1)],
            bass_durations=[Fraction(1, 4), Fraction(1, 2), Fraction(1, 4)],
        )
        ep = ExpandedPhrase(0, 1, voices, None, "I")
        assert ep.bass_pitches == (FloatingNote(1), FloatingNote(5), FloatingNote(1))

    def test_bass_durations_property(self) -> None:
        voices = ExpandedVoices.from_two_voices(
            soprano_pitches=[FloatingNote(5)],
            soprano_durations=[Fraction(1)],
            bass_pitches=[FloatingNote(1), FloatingNote(2)],
            bass_durations=[Fraction(1, 2), Fraction(1, 2)],
        )
        ep = ExpandedPhrase(0, 1, voices, None, "I")
        assert ep.bass_durations == (Fraction(1, 2), Fraction(1, 2))


class TestRealisedNote:
    """Test RealisedNote dataclass."""

    def test_construction(self) -> None:
        rn = RealisedNote(
            offset=Fraction(0),
            pitch=60,
            duration=Fraction(1, 4),
            voice="soprano",
        )
        assert rn.pitch == 60
        assert rn.voice == "soprano"


class TestRealisedVoice:
    """Test RealisedVoice dataclass."""

    def test_construction(self) -> None:
        notes = [
            RealisedNote(Fraction(0), 60, Fraction(1, 4), "soprano"),
            RealisedNote(Fraction(1, 4), 62, Fraction(1, 4), "soprano"),
        ]
        rv = RealisedVoice(voice_index=0, notes=notes)
        assert rv.voice_index == 0
        assert len(rv.notes) == 2

    def test_note_count_property(self) -> None:
        notes = [
            RealisedNote(Fraction(0), 60, Fraction(1), "bass"),
        ]
        rv = RealisedVoice(voice_index=1, notes=notes)
        assert rv.note_count == 1

    def test_empty_notes(self) -> None:
        rv = RealisedVoice(voice_index=0, notes=[])
        assert rv.note_count == 0


class TestRealisedPhrase:
    """Test RealisedPhrase dataclass."""

    def test_construction(self) -> None:
        soprano_notes = [RealisedNote(Fraction(0), 72, Fraction(1), "soprano")]
        bass_notes = [RealisedNote(Fraction(0), 48, Fraction(1), "bass")]
        rp = RealisedPhrase(
            index=0,
            voices=[
                RealisedVoice(0, soprano_notes),
                RealisedVoice(1, bass_notes),
            ],
        )
        assert rp.index == 0

    def test_soprano_property(self) -> None:
        soprano_notes = [
            RealisedNote(Fraction(0), 72, Fraction(1, 2), "soprano"),
            RealisedNote(Fraction(1, 2), 74, Fraction(1, 2), "soprano"),
        ]
        bass_notes = [RealisedNote(Fraction(0), 48, Fraction(1), "bass")]
        rp = RealisedPhrase(0, [RealisedVoice(0, soprano_notes), RealisedVoice(1, bass_notes)])
        assert rp.soprano == tuple(soprano_notes)

    def test_bass_property(self) -> None:
        soprano_notes = [RealisedNote(Fraction(0), 72, Fraction(1), "soprano")]
        bass_notes = [
            RealisedNote(Fraction(0), 48, Fraction(1, 2), "bass"),
            RealisedNote(Fraction(1, 2), 50, Fraction(1, 2), "bass"),
        ]
        rp = RealisedPhrase(0, [RealisedVoice(0, soprano_notes), RealisedVoice(1, bass_notes)])
        assert rp.bass == tuple(bass_notes)


class TestAnnotation:
    """Test Annotation dataclass."""

    def test_construction(self) -> None:
        a = Annotation(
            offset=Fraction(4),
            text="Section B",
            level="section",
        )
        assert a.offset == Fraction(4)
        assert a.text == "Section B"
        assert a.level == "section"


class TestPieceMetrics:
    """Test PieceMetrics dataclass."""

    def test_construction(self) -> None:
        pm = PieceMetrics(
            total_bars=32,
            subject_bars=16,
            derived_bars=8,
            episode_bars=4,
            free_bars=4,
        )
        assert pm.total_bars == 32

    def test_thematic_ratio_known_value(self) -> None:
        """Thematic ratio = (subject + derived) / total.

        With 16 subject bars and 8 derived bars out of 32 total,
        thematic ratio should be 24/32 = 0.75 (75% thematic).
        """
        pm = PieceMetrics(32, 16, 8, 4, 4)
        assert pm.thematic_ratio == 0.75

    def test_thematic_ratio_zero_total(self) -> None:
        pm = PieceMetrics(0, 0, 0, 0, 0)
        assert pm.thematic_ratio == 0.0

    def test_thematic_ratio_bounded(self) -> None:
        """Domain invariant: thematic ratio must be in [0.0, 1.0]."""
        pm = PieceMetrics(100, 50, 50, 0, 0)  # All thematic
        assert 0.0 <= pm.thematic_ratio <= 1.0
        assert pm.thematic_ratio == 1.0
        pm2 = PieceMetrics(100, 0, 0, 50, 50)  # No thematic
        assert 0.0 <= pm2.thematic_ratio <= 1.0
        assert pm2.thematic_ratio == 0.0

    def test_variety_ratio_known_value(self) -> None:
        """Variety ratio = (derived + episode + free) / total.

        With 8 derived, 4 episode, 4 free out of 32 total,
        variety ratio should be 16/32 = 0.5 (50% variety).
        """
        pm = PieceMetrics(32, 16, 8, 4, 4)
        assert pm.variety_ratio == 0.5

    def test_variety_ratio_zero_total(self) -> None:
        pm = PieceMetrics(0, 0, 0, 0, 0)
        assert pm.variety_ratio == 0.0

    def test_variety_ratio_bounded(self) -> None:
        """Domain invariant: variety ratio must be in [0.0, 1.0]."""
        pm = PieceMetrics(100, 0, 30, 40, 30)  # All variety
        assert 0.0 <= pm.variety_ratio <= 1.0
        assert pm.variety_ratio == 1.0
        pm2 = PieceMetrics(100, 100, 0, 0, 0)  # No variety
        assert 0.0 <= pm2.variety_ratio <= 1.0
        assert pm2.variety_ratio == 0.0

    def test_ratios_typical_baroque_piece(self) -> None:
        """In baroque music, thematic ratio typically 0.5-0.8.

        A fugue with 24 bars subject statements, 16 bars derived,
        8 bars episodic, 4 bars free = 52 total.
        Thematic = (24 + 16) / 52 = 40/52 ≈ 0.77
        Variety = (16 + 8 + 4) / 52 = 28/52 ≈ 0.54
        """
        pm = PieceMetrics(52, 24, 16, 8, 4)
        assert 0.5 <= pm.thematic_ratio <= 0.9
        assert 0.4 <= pm.variety_ratio <= 0.7

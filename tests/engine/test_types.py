"""100% coverage tests for engine.types.

Tests import only:
- engine.types (module under test)
- shared (shared types)
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote
from shared.types import VoiceMaterial
from engine.engine_types import (
    PhraseAST,
    EpisodeAST,
    SectionAST,
    MotifAST,
    PieceAST,
    ExpandedPhrase,
    RealisedNote,
    RealisedVoice,
    RealisedPhrase,
    Annotation,
    PieceMetrics,
)


class TestPhraseAST:
    """Test PhraseAST dataclass."""

    def test_minimal_construction(self) -> None:
        phrase = PhraseAST(
            index=0,
            bars=4,
            tonal_target="I",
            cadence=None,
            treatment="statement",
            surprise=None,
        )
        assert phrase.index == 0
        assert phrase.bars == 4
        assert phrase.tonal_target == "I"
        assert phrase.treatment == "statement"
        assert phrase.is_climax is False

    def test_with_optional_fields(self) -> None:
        phrase = PhraseAST(
            index=1,
            bars=8,
            tonal_target="V",
            cadence="half",
            treatment="sequence",
            surprise="deceptive_cadence",
            is_climax=True,
            articulation="staccato",
            rhythm="dotted",
            device="stretto",
            gesture="drive",
            energy="peak",
            voice_assignments=("soprano", "bass"),
        )
        assert phrase.is_climax is True
        assert phrase.articulation == "staccato"
        assert phrase.voice_assignments == ("soprano", "bass")

    def test_frozen(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        with pytest.raises(Exception):
            phrase.bars = 8


class TestEpisodeAST:
    """Test EpisodeAST dataclass."""

    def test_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        episode = EpisodeAST(
            type="thematic",
            bars=8,
            texture="polyphonic",
            phrases=(phrase,),
        )
        assert episode.type == "thematic"
        assert episode.bars == 8
        assert episode.texture == "polyphonic"
        assert len(episode.phrases) == 1
        assert episode.is_transition is False

    def test_with_transition(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        episode = EpisodeAST(
            type="transitional",
            bars=4,
            texture="homophonic",
            phrases=(phrase,),
            is_transition=True,
        )
        assert episode.is_transition is True


class TestSectionAST:
    """Test SectionAST dataclass."""

    def test_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        episode = EpisodeAST("thematic", 8, "polyphonic", (phrase,))
        section = SectionAST(
            label="A",
            tonal_path=("I", "V"),
            final_cadence="authentic",
            episodes=(episode,),
        )
        assert section.label == "A"
        assert section.tonal_path == ("I", "V")
        assert section.final_cadence == "authentic"
        assert len(section.episodes) == 1


class TestMotifAST:
    """Test MotifAST dataclass."""

    def test_construction(self) -> None:
        pitches = (FloatingNote(1), FloatingNote(3), FloatingNote(5))
        durations = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        motif = MotifAST(
            pitches=pitches,
            durations=durations,
            bars=1,
        )
        assert len(motif.pitches) == 3
        assert motif.bars == 1


class TestPieceAST:
    """Test PieceAST dataclass."""

    def test_minimal_construction(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        episode = EpisodeAST("thematic", 8, "polyphonic", (phrase,))
        section = SectionAST("A", ("I",), "authentic", (episode,))
        piece = PieceAST(
            key="C",
            mode="major",
            metre="4/4",
            tempo="allegro",
            voices=2,
            subject=None,
            sections=(section,),
            arc="standard",
        )
        assert piece.key == "C"
        assert piece.mode == "major"
        assert piece.upbeat == Fraction(0)
        assert piece.form == "through_composed"
        assert piece.virtuosic is False

    def test_with_optional_fields(self) -> None:
        phrase = PhraseAST(0, 4, "I", None, "statement", None)
        episode = EpisodeAST("thematic", 8, "polyphonic", (phrase,))
        section = SectionAST("A", ("I",), "authentic", (episode,))
        piece = PieceAST(
            key="G",
            mode="minor",
            metre="3/4",
            tempo="adagio",
            voices=4,
            subject=None,
            sections=(section,),
            arc="fugue_4voice",
            upbeat=Fraction(1, 4),
            form="binary",
            virtuosic=True,
        )
        assert piece.upbeat == Fraction(1, 4)
        assert piece.form == "binary"
        assert piece.virtuosic is True


class TestExpandedPhrase:
    """Test ExpandedPhrase dataclass."""

    def test_construction(self) -> None:
        from shared.types import ExpandedVoices
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1), Fraction(1)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(1), FloatingNote(5)],
            durations=[Fraction(1), Fraction(1)],
        )
        voices = ExpandedVoices(voices=[soprano, bass])
        phrase = ExpandedPhrase(
            index=0,
            bars=2,
            voices=voices,
            cadence="authentic",
            tonal_target="I",
        )
        assert phrase.index == 0
        assert phrase.bars == 2
        assert phrase.cadence == "authentic"

    def test_soprano_properties(self) -> None:
        from shared.types import ExpandedVoices
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1), FloatingNote(2)],
            durations=[Fraction(1), Fraction(1)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(1)],
            durations=[Fraction(2)],
        )
        voices = ExpandedVoices(voices=[soprano, bass])
        phrase = ExpandedPhrase(0, 2, voices, None, "I")
        assert phrase.soprano_pitches == (FloatingNote(1), FloatingNote(2))
        assert phrase.soprano_durations == (Fraction(1), Fraction(1))

    def test_bass_properties(self) -> None:
        from shared.types import ExpandedVoices
        soprano = VoiceMaterial(
            voice_index=0,
            pitches=[FloatingNote(1)],
            durations=[Fraction(2)],
        )
        bass = VoiceMaterial(
            voice_index=1,
            pitches=[FloatingNote(1), FloatingNote(5)],
            durations=[Fraction(1), Fraction(1)],
        )
        voices = ExpandedVoices(voices=[soprano, bass])
        phrase = ExpandedPhrase(0, 2, voices, None, "I")
        assert phrase.bass_pitches == (FloatingNote(1), FloatingNote(5))
        assert phrase.bass_durations == (Fraction(1), Fraction(1))


class TestRealisedNote:
    """Test RealisedNote dataclass."""

    def test_construction(self) -> None:
        note = RealisedNote(
            offset=Fraction(1, 2),
            pitch=60,
            duration=Fraction(1, 4),
            voice="soprano",
        )
        assert note.offset == Fraction(1, 2)
        assert note.pitch == 60
        assert note.duration == Fraction(1, 4)
        assert note.voice == "soprano"


class TestRealisedVoice:
    """Test RealisedVoice dataclass."""

    def test_construction(self) -> None:
        notes = [
            RealisedNote(Fraction(0), 60, Fraction(1, 4), "soprano"),
            RealisedNote(Fraction(1, 4), 62, Fraction(1, 4), "soprano"),
        ]
        voice = RealisedVoice(voice_index=0, notes=notes)
        assert voice.voice_index == 0
        assert len(voice.notes) == 2

    def test_note_count(self) -> None:
        notes = [
            RealisedNote(Fraction(0), 60, Fraction(1), "soprano"),
            RealisedNote(Fraction(1), 62, Fraction(1), "soprano"),
            RealisedNote(Fraction(2), 64, Fraction(1), "soprano"),
        ]
        voice = RealisedVoice(voice_index=0, notes=notes)
        assert voice.note_count == 3

    def test_empty_notes(self) -> None:
        voice = RealisedVoice(voice_index=0, notes=[])
        assert voice.note_count == 0


class TestRealisedPhrase:
    """Test RealisedPhrase dataclass."""

    def test_construction(self) -> None:
        soprano_notes = [RealisedNote(Fraction(0), 72, Fraction(1), "soprano")]
        bass_notes = [RealisedNote(Fraction(0), 48, Fraction(1), "bass")]
        soprano = RealisedVoice(0, soprano_notes)
        bass = RealisedVoice(1, bass_notes)
        phrase = RealisedPhrase(index=0, voices=[soprano, bass])
        assert phrase.index == 0
        assert len(phrase.voices) == 2

    def test_soprano_property(self) -> None:
        soprano_notes = [
            RealisedNote(Fraction(0), 72, Fraction(1), "soprano"),
            RealisedNote(Fraction(1), 74, Fraction(1), "soprano"),
        ]
        bass_notes = [RealisedNote(Fraction(0), 48, Fraction(2), "bass")]
        soprano = RealisedVoice(0, soprano_notes)
        bass = RealisedVoice(1, bass_notes)
        phrase = RealisedPhrase(0, [soprano, bass])
        assert phrase.soprano == tuple(soprano_notes)

    def test_bass_property(self) -> None:
        soprano_notes = [RealisedNote(Fraction(0), 72, Fraction(2), "soprano")]
        bass_notes = [
            RealisedNote(Fraction(0), 48, Fraction(1), "bass"),
            RealisedNote(Fraction(1), 50, Fraction(1), "bass"),
        ]
        soprano = RealisedVoice(0, soprano_notes)
        bass = RealisedVoice(1, bass_notes)
        phrase = RealisedPhrase(0, [soprano, bass])
        assert phrase.bass == tuple(bass_notes)


class TestAnnotation:
    """Test Annotation dataclass."""

    def test_construction(self) -> None:
        ann = Annotation(
            offset=Fraction(4),
            text="Section A",
            level="section",
        )
        assert ann.offset == Fraction(4)
        assert ann.text == "Section A"
        assert ann.level == "section"


class TestPieceMetrics:
    """Test PieceMetrics dataclass."""

    def test_construction(self) -> None:
        metrics = PieceMetrics(
            total_bars=32,
            subject_bars=8,
            derived_bars=8,
            episode_bars=8,
            free_bars=8,
        )
        assert metrics.total_bars == 32
        assert metrics.subject_bars == 8

    def test_thematic_ratio(self) -> None:
        metrics = PieceMetrics(
            total_bars=100,
            subject_bars=20,
            derived_bars=30,
            episode_bars=30,
            free_bars=20,
        )
        # (20 + 30) / 100 = 0.5
        assert metrics.thematic_ratio == 0.5

    def test_thematic_ratio_zero_bars(self) -> None:
        metrics = PieceMetrics(0, 0, 0, 0, 0)
        assert metrics.thematic_ratio == 0.0

    def test_variety_ratio(self) -> None:
        metrics = PieceMetrics(
            total_bars=100,
            subject_bars=20,
            derived_bars=30,
            episode_bars=30,
            free_bars=20,
        )
        # (30 + 30 + 20) / 100 = 0.8
        assert metrics.variety_ratio == 0.8

    def test_variety_ratio_zero_bars(self) -> None:
        metrics = PieceMetrics(0, 0, 0, 0, 0)
        assert metrics.variety_ratio == 0.0

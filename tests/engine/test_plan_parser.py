"""Integration tests for engine.plan_parser.

Category B orchestrator tests: verify parsing orchestration and data flow.
Tests import only:
- engine.plan_parser (module under test)
- engine.types (output types)
- planner.subject (Subject type)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.plan_parser import (
    parse_fraction,
    parse_phrase,
    parse_episode,
    parse_section,
    parse_subject,
    parse_yaml,
)
from engine.engine_types import EpisodeAST, PhraseAST, PieceAST, SectionAST
from planner.subject import Subject


class TestParseFraction:
    """Test parse_fraction function."""

    def test_parse_fraction_string(self) -> None:
        """Parse fraction from string format."""
        assert parse_fraction("1/4") == Fraction(1, 4)
        assert parse_fraction("3/8") == Fraction(3, 8)
        assert parse_fraction("1/2") == Fraction(1, 2)

    def test_parse_fraction_integer(self) -> None:
        """Parse fraction from integer value."""
        assert parse_fraction(1) == Fraction(1)
        assert parse_fraction(2) == Fraction(2)

    def test_parse_fraction_already_fraction(self) -> None:
        """Parse handles string representation of int."""
        assert parse_fraction("1") == Fraction(1)


class TestParseSubject:
    """Test parse_subject function."""

    def test_parse_subject_basic(self) -> None:
        """Parse basic subject material."""
        material: dict = {
            "subject": {
                "degrees": [1, 2, 3, 4, 5],
                "durations": ["1/4", "1/4", "1/4", "1/8", "1/8"],
                "bars": 1,
            }
        }
        subj: Subject = parse_subject(material, "major", 2)
        assert subj.degrees == (1, 2, 3, 4, 5)
        assert subj.durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 8), Fraction(1, 8))
        assert subj.bars == 1

    def test_parse_subject_with_counter_subject(self) -> None:
        """Parse subject with explicit counter-subject."""
        material: dict = {
            "subject": {
                "degrees": [1, 2, 3],
                "durations": ["1/4", "1/4", "1/2"],
                "bars": 1,
            },
            "counter_subject": {
                "degrees": [5, 4, 3],
                "durations": ["1/2", "1/4", "1/4"],
            },
        }
        subj: Subject = parse_subject(material, "major", 2)
        assert subj._cs_degrees == (5, 4, 3)
        assert subj._cs_durations == (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4))

    def test_parse_subject_with_genre(self) -> None:
        """Parse subject with genre specification."""
        material: dict = {
            "subject": {
                "degrees": [1, 3, 5],
                "durations": ["1/4", "1/4", "1/2"],
                "bars": 1,
            }
        }
        subj: Subject = parse_subject(material, "minor", 2, genre="fantasia")
        assert subj._genre == "fantasia"


class TestParsePhrase:
    """Test parse_phrase function."""

    def test_parse_phrase_minimal(self) -> None:
        """Parse phrase with required fields only."""
        data: dict = {
            "index": 0,
            "bars": 4,
            "tonal_target": "I",
            "treatment": "statement",
        }
        phrase: PhraseAST = parse_phrase(data)
        assert phrase.index == 0
        assert phrase.bars == 4
        assert phrase.tonal_target == "I"
        assert phrase.treatment == "statement"
        assert phrase.cadence is None
        assert phrase.surprise is None
        assert phrase.is_climax is False

    def test_parse_phrase_with_all_optional_fields(self) -> None:
        """Parse phrase with all optional fields."""
        data: dict = {
            "index": 1,
            "bars": 2,
            "tonal_target": "V",
            "treatment": "sequence",
            "cadence": "half",
            "surprise": "deceptive_cadence",
            "is_climax": True,
            "articulation": "legato",
            "rhythm": "dotted",
            "device": "stretto",
            "gesture": "question",
            "energy": "high",
        }
        phrase: PhraseAST = parse_phrase(data)
        assert phrase.index == 1
        assert phrase.bars == 2
        assert phrase.tonal_target == "V"
        assert phrase.treatment == "sequence"
        assert phrase.cadence == "half"
        assert phrase.surprise == "deceptive_cadence"
        assert phrase.is_climax is True
        assert phrase.articulation == "legato"
        assert phrase.rhythm == "dotted"
        assert phrase.device == "stretto"
        assert phrase.gesture == "question"
        assert phrase.energy == "high"

    def test_parse_phrase_with_voice_assignments(self) -> None:
        """Parse phrase with explicit voice assignments."""
        data: dict = {
            "index": 0,
            "bars": 4,
            "tonal_target": "I",
            "treatment": "counterpoint",
            "voices": {
                "soprano": "subject",
                "bass": "cs_1",
            },
        }
        phrase: PhraseAST = parse_phrase(data)
        assert phrase.voice_assignments == ("subject", "cs_1")

    def test_parse_phrase_voice_order(self) -> None:
        """Voice assignments follow soprano, alto, tenor, bass order."""
        data: dict = {
            "index": 0,
            "bars": 4,
            "tonal_target": "I",
            "treatment": "counterpoint",
            "voices": {
                "soprano": "subject",
                "alto": "cs_1",
                "tenor": "cs_2",
                "bass": "cs_3",
            },
        }
        phrase: PhraseAST = parse_phrase(data)
        assert phrase.voice_assignments == ("subject", "cs_1", "cs_2", "cs_3")


class TestParseEpisode:
    """Test parse_episode function."""

    def test_parse_episode_minimal(self) -> None:
        """Parse episode with required fields."""
        data: dict = {
            "type": "statement",
            "bars": 4,
            "phrases": [
                {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement"},
            ],
        }
        episode: EpisodeAST = parse_episode(data)
        assert episode.type == "statement"
        assert episode.bars == 4
        assert episode.texture == "polyphonic"
        assert episode.is_transition is False
        assert len(episode.phrases) == 1

    def test_parse_episode_with_texture(self) -> None:
        """Parse episode with explicit texture."""
        data: dict = {
            "type": "development",
            "bars": 8,
            "texture": "figured_bass",
            "phrases": [
                {"index": 0, "bars": 4, "tonal_target": "V", "treatment": "sequence"},
                {"index": 1, "bars": 4, "tonal_target": "I", "treatment": "statement"},
            ],
        }
        episode: EpisodeAST = parse_episode(data)
        assert episode.texture == "figured_bass"
        assert len(episode.phrases) == 2

    def test_parse_episode_transition(self) -> None:
        """Parse transition episode."""
        data: dict = {
            "type": "transition",
            "bars": 2,
            "is_transition": True,
            "phrases": [
                {"index": 0, "bars": 2, "tonal_target": "V", "treatment": "sequence"},
            ],
        }
        episode: EpisodeAST = parse_episode(data)
        assert episode.is_transition is True


class TestParseSection:
    """Test parse_section function."""

    def test_parse_section_basic(self) -> None:
        """Parse section with basic structure."""
        data: dict = {
            "label": "A",
            "tonal_path": ["I", "V"],
            "final_cadence": "authentic",
            "episodes": [
                {
                    "type": "statement",
                    "bars": 4,
                    "phrases": [
                        {"index": 0, "bars": 2, "tonal_target": "I", "treatment": "statement"},
                        {"index": 1, "bars": 2, "tonal_target": "V", "treatment": "sequence"},
                    ],
                },
            ],
        }
        section: SectionAST = parse_section(data)
        assert section.label == "A"
        assert section.tonal_path == ("I", "V")
        assert section.final_cadence == "authentic"
        assert len(section.episodes) == 1
        assert len(section.episodes[0].phrases) == 2


class TestParseYaml:
    """Test parse_yaml function."""

    def test_parse_yaml_minimal_valid(self) -> None:
        """Parse minimal valid YAML plan."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4, 5]
    durations: ["1/4", "1/4", "1/4", "1/8", "1/8"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.key == "C"
        assert piece.mode == "major"
        assert piece.metre == "4/4"
        assert piece.tempo == "allegro"
        assert piece.voices == 2
        assert piece.arc == "imitative"
        assert len(piece.sections) == 1

    def test_parse_yaml_with_upbeat(self) -> None:
        """Parse YAML with upbeat specification."""
        yaml_str: str = """
frame:
  key: G
  mode: major
  metre: "3/4"
  tempo: andante
  voices: 2
  upbeat: "1/4"
material:
  subject:
    degrees: [5, 1, 2]
    durations: ["1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.upbeat == Fraction(1, 4)

    def test_parse_yaml_with_form(self) -> None:
        """Parse YAML with form specification."""
        yaml_str: str = """
frame:
  key: D
  mode: minor
  metre: "4/4"
  tempo: adagio
  voices: 2
  form: binary
material:
  subject:
    degrees: [1, 3, 5, 3]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [i]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: i
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.form == "binary"

    def test_parse_yaml_with_brief(self) -> None:
        """Parse YAML with brief section for genre and virtuosic."""
        yaml_str: str = """
brief:
  genre: fantasia
  virtuosic: true
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.virtuosic is True

    def test_parse_yaml_subject_is_subject_instance(self) -> None:
        """Parsed subject is a Subject instance with correct data."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 3, 5, 3]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert isinstance(piece.subject, Subject)
        assert piece.subject.degrees == (1, 3, 5, 3)
        assert piece.subject.bars == 1

    def test_parse_yaml_four_voices(self) -> None:
        """Parse YAML for 4-voice piece."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 4
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: fugue_4voice
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.voices == 4

    def test_parse_yaml_multiple_sections(self) -> None:
        """Parse YAML with multiple sections."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I, V]
      final_cadence: half
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 4
              tonal_target: I
              treatment: statement
    - label: B
      tonal_path: [V, I]
      final_cadence: authentic
      episodes:
        - type: sequential
          bars: 4
          phrases:
            - index: 1
              bars: 2
              tonal_target: V
              treatment: sequence
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert len(piece.sections) == 2
        assert piece.sections[0].label == "A"
        assert piece.sections[1].label == "B"


class TestParseYamlEdgeCases:
    """Test edge cases and error handling in parse_yaml."""

    def test_parse_yaml_zero_upbeat(self) -> None:
        """Parse YAML with zero upbeat (common case)."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
  upbeat: 0
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.upbeat == Fraction(0)

    def test_parse_yaml_minor_mode(self) -> None:
        """Parse YAML in minor mode with correct tonal targets."""
        yaml_str: str = """
frame:
  key: A
  mode: minor
  metre: "4/4"
  tempo: andante
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [i, III]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: i
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        assert piece.mode == "minor"
        assert piece.sections[0].tonal_path == ("i", "III")


class TestDataFlowIntegrity:
    """Test that parsed data maintains integrity through types."""

    def test_phrase_index_preserved(self) -> None:
        """Phrase indices are correctly preserved through parsing."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I, V]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
            - index: 1
              bars: 2
              tonal_target: V
              treatment: sequence
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        phrases = piece.sections[0].episodes[0].phrases
        assert phrases[0].index == 0
        assert phrases[1].index == 1

    def test_tonal_targets_preserved(self) -> None:
        """Tonal targets are correctly preserved through parsing."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4]
    durations: ["1/4", "1/4", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I, V, vi, IV]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 8
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
            - index: 1
              bars: 2
              tonal_target: V
              treatment: sequence
            - index: 2
              bars: 2
              tonal_target: vi
              treatment: sequence
            - index: 3
              bars: 2
              tonal_target: IV
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        phrases = piece.sections[0].episodes[0].phrases
        assert phrases[0].tonal_target == "I"
        assert phrases[1].tonal_target == "V"
        assert phrases[2].tonal_target == "vi"
        assert phrases[3].tonal_target == "IV"

    def test_durations_are_fractions(self) -> None:
        """Subject durations are parsed as Fractions, not strings."""
        yaml_str: str = """
frame:
  key: C
  mode: major
  metre: "4/4"
  tempo: allegro
  voices: 2
material:
  subject:
    degrees: [1, 2, 3, 4, 5]
    durations: ["1/4", "1/8", "1/8", "1/4", "1/4"]
    bars: 1
structure:
  arc: imitative
  sections:
    - label: A
      tonal_path: [I]
      final_cadence: authentic
      episodes:
        - type: statement
          bars: 4
          phrases:
            - index: 0
              bars: 2
              tonal_target: I
              treatment: statement
              cadence: authentic
"""
        piece: PieceAST = parse_yaml(yaml_str)
        for dur in piece.subject.durations:
            assert isinstance(dur, Fraction)
        assert sum(piece.subject.durations) == Fraction(1)

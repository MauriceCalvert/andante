"""100% coverage tests for engine.validate.

Tests import only:
- engine.validate (module under test)
- stdlib
"""
from pathlib import Path

import pytest
from engine.validate import (
    ARCS,
    CADENCES,
    TREATMENTS,
    VALID_FORMS,
    VALID_KEYS,
    VALID_MODES,
    VALID_SECTION_CADENCES,
    VALID_TEMPOS,
    VALID_TONAL_TARGETS,
    ValidationError,
    _err,
    validate_episode,
    validate_file,
    validate_frame,
    validate_phrase,
    validate_section,
    validate_structure,
    validate_subject,
    validate_yaml,
)

# Get a valid arc name for testing (avoids dynamic __import__)
TEST_ARC: str = next(iter(ARCS))


class TestValidationError:
    """Test ValidationError and _err helper."""

    def test_err_creates_validation_error(self) -> None:
        err = _err("context", "message")
        assert isinstance(err, ValidationError)
        assert "context: message" in str(err)


class TestValidateFrame:
    """Test validate_frame function."""

    def test_valid_frame(self) -> None:
        frame = {
            "key": "C",
            "mode": "major",
            "metre": "4/4",
            "tempo": "allegro",
            "voices": 2,
        }
        validate_frame(frame)  # Should not raise

    def test_valid_frame_with_optional_fields(self) -> None:
        frame = {
            "key": "Bb",
            "mode": "minor",
            "metre": "3/4",
            "tempo": "adagio",
            "voices": 4,
            "form": "binary",
            "upbeat": "1/4",
        }
        validate_frame(frame)

    def test_valid_frame_upbeat_zero(self) -> None:
        frame = {
            "key": "C",
            "mode": "major",
            "metre": "4/4",
            "tempo": "allegro",
            "voices": 2,
            "upbeat": 0,
        }
        validate_frame(frame)

    def test_missing_key_raises(self) -> None:
        frame = {"mode": "major", "metre": "4/4", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_key_raises(self) -> None:
        frame = {"key": "X", "mode": "major", "metre": "4/4", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_missing_mode_raises(self) -> None:
        frame = {"key": "C", "metre": "4/4", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_mode_raises(self) -> None:
        frame = {"key": "C", "mode": "dorian", "metre": "4/4", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_missing_metre_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_metre_no_slash_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "44", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_metre_non_numeric_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "a/b", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_metre_denominator_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/3", "tempo": "allegro", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_missing_tempo_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_tempo_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "tempo": "fast", "voices": 2}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_missing_voices_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "tempo": "allegro"}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_voices_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "tempo": "allegro", "voices": 5}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_form_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "tempo": "allegro", "voices": 2, "form": "sonata"}
        with pytest.raises(AssertionError):
            validate_frame(frame)

    def test_invalid_upbeat_raises(self) -> None:
        frame = {"key": "C", "mode": "major", "metre": "4/4", "tempo": "allegro", "voices": 2, "upbeat": 1}
        with pytest.raises(AssertionError):
            validate_frame(frame)


class TestValidateSubject:
    """Test validate_subject function."""

    def test_valid_subject(self) -> None:
        subject = {
            "degrees": [1, 2, 3, 4],
            "durations": ["1/4", "1/4", "1/4", "1/4"],
            "bars": 1,
        }
        validate_subject(subject, "4/4")

    def test_valid_subject_integer_duration(self) -> None:
        subject = {
            "degrees": [1, 2],
            "durations": [1, 1],
            "bars": 2,
        }
        validate_subject(subject, "4/4")

    def test_missing_degrees_raises(self) -> None:
        subject = {"durations": ["1/4"], "bars": 1}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_missing_durations_raises(self) -> None:
        subject = {"degrees": [1, 2], "bars": 1}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_missing_bars_raises(self) -> None:
        subject = {"degrees": [1, 2], "durations": ["1/4", "1/4"]}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_length_mismatch_raises(self) -> None:
        subject = {"degrees": [1, 2, 3], "durations": ["1/4", "1/4"], "bars": 1}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_too_few_notes_raises(self) -> None:
        subject = {"degrees": [1], "durations": ["1"], "bars": 1}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_bars_zero_raises(self) -> None:
        subject = {"degrees": [1, 2], "durations": ["1/4", "1/4"], "bars": 0}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")

    def test_invalid_degree_raises(self) -> None:
        subject = {"degrees": [1, 8], "durations": ["1/4", "1/4"], "bars": 1}
        with pytest.raises(AssertionError):
            validate_subject(subject, "2/4")

    def test_duration_mismatch_raises(self) -> None:
        subject = {"degrees": [1, 2], "durations": ["1/4", "1/4"], "bars": 2}
        with pytest.raises(AssertionError):
            validate_subject(subject, "4/4")


class TestValidatePhrase:
    """Test validate_phrase function."""

    def test_valid_phrase(self) -> None:
        phrase = {
            "index": 0,
            "bars": 4,
            "tonal_target": "I",
            "treatment": "statement",
        }
        validate_phrase(phrase, 0, "A", 0)

    def test_valid_phrase_with_optional_fields(self) -> None:
        treatment = next(iter(TREATMENTS))
        cadence = next(iter(CADENCES))
        phrase = {
            "index": 1,
            "bars": 2,
            "tonal_target": "V",
            "treatment": treatment,
            "cadence": cadence,
            "rhythm": "straight",
            "gesture": "statement_open",
            "device": "stretto",
            "energy": "moderate",
            "surprise": "deceptive_cadence",
        }
        validate_phrase(phrase, 1, "A", 0)

    def test_missing_index_raises(self) -> None:
        phrase = {"bars": 4, "tonal_target": "I", "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_index_mismatch_raises(self) -> None:
        phrase = {"index": 1, "bars": 4, "tonal_target": "I", "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_missing_bars_raises(self) -> None:
        phrase = {"index": 0, "tonal_target": "I", "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_bars_zero_raises(self) -> None:
        phrase = {"index": 0, "bars": 0, "tonal_target": "I", "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_missing_tonal_target_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_tonal_target_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "VIII", "treatment": "statement"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_missing_treatment_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_treatment_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "invalid_treatment"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_cadence_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "cadence": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_rhythm_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "rhythm": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_gesture_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "gesture": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_device_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "device": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_energy_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "energy": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)

    def test_invalid_surprise_raises(self) -> None:
        phrase = {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement", "surprise": "invalid"}
        with pytest.raises(AssertionError):
            validate_phrase(phrase, 0, "A", 0)


class TestValidateEpisode:
    """Test validate_episode function."""

    def test_valid_episode(self) -> None:
        episode = {
            "type": "statement",
            "bars": 4,
            "phrases": [
                {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement"},
            ],
        }
        result = validate_episode(episode, 0, "A", 0, ["I"])
        assert result == 1

    def test_missing_type_raises(self) -> None:
        episode = {"bars": 4, "phrases": []}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_invalid_type_raises(self) -> None:
        episode = {"type": "invalid_type", "bars": 4, "phrases": []}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_missing_bars_raises(self) -> None:
        episode = {"type": "statement", "phrases": []}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_bars_zero_raises(self) -> None:
        episode = {"type": "statement", "bars": 0, "phrases": []}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_missing_phrases_raises(self) -> None:
        episode = {"type": "statement", "bars": 4}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_empty_phrases_raises(self) -> None:
        episode = {"type": "statement", "bars": 4, "phrases": []}
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])

    def test_tonal_target_not_in_path_raises(self) -> None:
        episode = {
            "type": "statement",
            "bars": 4,
            "phrases": [
                {"index": 0, "bars": 4, "tonal_target": "V", "treatment": "statement"},
            ],
        }
        with pytest.raises(AssertionError):
            validate_episode(episode, 0, "A", 0, ["I"])


class TestValidateSection:
    """Test validate_section function."""

    def test_valid_section(self) -> None:
        section = {
            "label": "A",
            "tonal_path": ["I"],
            "final_cadence": "authentic",
            "episodes": [
                {
                    "type": "statement",
                    "bars": 4,
                    "phrases": [
                        {"index": 0, "bars": 4, "tonal_target": "I", "treatment": "statement"},
                    ],
                },
            ],
        }
        result = validate_section(section, 0, 0)
        assert result == 1

    def test_missing_label_raises(self) -> None:
        section = {"tonal_path": ["I"], "final_cadence": "authentic", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_missing_tonal_path_raises(self) -> None:
        section = {"label": "A", "final_cadence": "authentic", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_empty_tonal_path_raises(self) -> None:
        section = {"label": "A", "tonal_path": [], "final_cadence": "authentic", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_invalid_tonal_path_target_raises(self) -> None:
        section = {"label": "A", "tonal_path": ["VIII"], "final_cadence": "authentic", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_missing_final_cadence_raises(self) -> None:
        section = {"label": "A", "tonal_path": ["I"], "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_invalid_final_cadence_raises(self) -> None:
        section = {"label": "A", "tonal_path": ["I"], "final_cadence": "invalid", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_missing_episodes_raises(self) -> None:
        section = {"label": "A", "tonal_path": ["I"], "final_cadence": "authentic"}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)

    def test_empty_episodes_raises(self) -> None:
        section = {"label": "A", "tonal_path": ["I"], "final_cadence": "authentic", "episodes": []}
        with pytest.raises(AssertionError):
            validate_section(section, 0, 0)


class TestValidateStructure:
    """Test validate_structure function."""

    def test_valid_structure(self) -> None:
        structure = {
            "arc": TEST_ARC,
            "sections": [
                {
                    "label": "A",
                    "tonal_path": ["I"],
                    "final_cadence": "authentic",
                    "episodes": [
                        {
                            "type": "statement",
                            "bars": 4,
                            "phrases": [
                                {"index": 0, "bars": 2, "tonal_target": "I", "treatment": "statement", "cadence": "authentic"},
                            ],
                        },
                    ],
                },
            ],
        }
        validate_structure(structure)

    def test_missing_arc_raises(self) -> None:
        structure = {"sections": []}
        with pytest.raises(AssertionError):
            validate_structure(structure)

    def test_invalid_arc_raises(self) -> None:
        structure = {"arc": "invalid_arc", "sections": []}
        with pytest.raises(AssertionError):
            validate_structure(structure)

    def test_missing_sections_raises(self) -> None:
        structure = {"arc": TEST_ARC}
        with pytest.raises(AssertionError):
            validate_structure(structure)

    def test_empty_sections_raises(self) -> None:
        structure = {"arc": TEST_ARC, "sections": []}
        with pytest.raises(AssertionError):
            validate_structure(structure)

    def test_final_phrase_no_authentic_cadence_raises(self) -> None:
        structure = {
            "arc": TEST_ARC,
            "sections": [
                {
                    "label": "A",
                    "tonal_path": ["I"],
                    "final_cadence": "authentic",
                    "episodes": [
                        {
                            "type": "statement",
                            "bars": 4,
                            "phrases": [
                                {"index": 0, "bars": 2, "tonal_target": "I", "treatment": "statement"},
                            ],
                        },
                    ],
                },
            ],
        }
        with pytest.raises(AssertionError):
            validate_structure(structure)

    def test_final_phrase_too_short_raises(self) -> None:
        structure = {
            "arc": TEST_ARC,
            "sections": [
                {
                    "label": "A",
                    "tonal_path": ["I"],
                    "final_cadence": "authentic",
                    "episodes": [
                        {
                            "type": "statement",
                            "bars": 4,
                            "phrases": [
                                {"index": 0, "bars": 1, "tonal_target": "I", "treatment": "statement", "cadence": "authentic"},
                            ],
                        },
                    ],
                },
            ],
        }
        with pytest.raises(AssertionError):
            validate_structure(structure)


class TestValidateYaml:
    """Test validate_yaml function."""

    def test_valid_yaml(self) -> None:
        data = {
            "frame": {
                "key": "C",
                "mode": "major",
                "metre": "4/4",
                "tempo": "allegro",
                "voices": 2,
            },
            "material": {
                "subject": {
                    "degrees": [1, 2, 3, 4],
                    "durations": ["1/4", "1/4", "1/4", "1/4"],
                    "bars": 1,
                },
            },
            "structure": {
                "arc": TEST_ARC,
                "sections": [
                    {
                        "label": "A",
                        "tonal_path": ["I"],
                        "final_cadence": "authentic",
                        "episodes": [
                            {
                                "type": "statement",
                                "bars": 4,
                                "phrases": [
                                    {"index": 0, "bars": 2, "tonal_target": "I", "treatment": "statement", "cadence": "authentic"},
                                ],
                            },
                        ],
                    },
                ],
            },
        }
        validate_yaml(data)

    def test_missing_frame_raises(self) -> None:
        data = {"material": {}, "structure": {}}
        with pytest.raises(AssertionError):
            validate_yaml(data)

    def test_missing_material_raises(self) -> None:
        data = {"frame": {}, "structure": {}}
        with pytest.raises(AssertionError):
            validate_yaml(data)

    def test_missing_structure_raises(self) -> None:
        data = {"frame": {}, "material": {}}
        with pytest.raises(AssertionError):
            validate_yaml(data)


class TestValidateFile:
    """Test validate_file function."""

    def test_validate_file(self, tmp_path) -> None:
        yaml_content = f"""
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
  arc: {TEST_ARC}
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
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text(yaml_content)
        validate_file(yaml_file)

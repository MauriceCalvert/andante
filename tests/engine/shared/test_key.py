"""100% coverage tests for shared.key.

Tests import only:
- shared (shared types)
- stdlib
"""
import pytest
from shared.pitch import FloatingNote
from shared.key import Key
from shared.constants import (
    DOMINANT_TARGETS,
    FLAT_KEYS_MAJOR,
    FLAT_KEYS_MINOR,
    HARMONIC_MINOR_SCALE,
    MAJOR_SCALE,
    MELODIC_MINOR_SCALE,
    MINOR_SCALE,
    MODULATION_TARGETS,
    NATURAL_MINOR_SCALE,
    NOTE_NAME_MAP,
    NOTE_NAMES_FLAT,
    NOTE_NAMES_SHARP,
)


class TestConstants:
    """Test module-level constants."""

    def test_major_scale_intervals(self) -> None:
        assert MAJOR_SCALE == (0, 2, 4, 5, 7, 9, 11)

    def test_natural_minor_scale_intervals(self) -> None:
        assert NATURAL_MINOR_SCALE == (0, 2, 3, 5, 7, 8, 10)

    def test_harmonic_minor_scale_intervals(self) -> None:
        assert HARMONIC_MINOR_SCALE == (0, 2, 3, 5, 7, 8, 11)

    def test_melodic_minor_scale_intervals(self) -> None:
        assert MELODIC_MINOR_SCALE == (0, 2, 3, 5, 7, 9, 11)

    def test_minor_scale_alias(self) -> None:
        assert MINOR_SCALE == NATURAL_MINOR_SCALE

    def test_dominant_targets(self) -> None:
        assert DOMINANT_TARGETS == frozenset({"V", "v", "vii", "VII"})

    def test_note_names_sharp_length(self) -> None:
        assert len(NOTE_NAMES_SHARP) == 12

    def test_note_names_flat_length(self) -> None:
        assert len(NOTE_NAMES_FLAT) == 12

    def test_flat_keys_major(self) -> None:
        assert "F" in FLAT_KEYS_MAJOR
        assert "Bb" in FLAT_KEYS_MAJOR
        assert "G" not in FLAT_KEYS_MAJOR

    def test_flat_keys_minor(self) -> None:
        assert "D" in FLAT_KEYS_MINOR
        assert "G" in FLAT_KEYS_MINOR

    def test_note_name_map_c(self) -> None:
        assert NOTE_NAME_MAP["C"] == 0

    def test_note_name_map_enharmonics(self) -> None:
        assert NOTE_NAME_MAP["C#"] == NOTE_NAME_MAP["Db"]
        assert NOTE_NAME_MAP["F#"] == NOTE_NAME_MAP["Gb"]

    def test_modulation_targets_major_keys(self) -> None:
        assert "I" in MODULATION_TARGETS["major"]
        assert "V" in MODULATION_TARGETS["major"]
        assert "vi" in MODULATION_TARGETS["major"]

    def test_modulation_targets_minor_keys(self) -> None:
        assert "i" in MODULATION_TARGETS["minor"]
        assert "III" in MODULATION_TARGETS["minor"]
        assert "V" in MODULATION_TARGETS["minor"]


class TestKeyConstruction:
    """Test Key dataclass construction and validation."""

    def test_valid_major_key(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.tonic == "C"
        assert key.mode == "major"

    def test_valid_minor_key(self) -> None:
        key = Key(tonic="A", mode="minor")
        assert key.tonic == "A"
        assert key.mode == "minor"

    def test_all_valid_tonics(self) -> None:
        for tonic in NOTE_NAME_MAP:
            key = Key(tonic=tonic, mode="major")
            assert key.tonic == tonic

    def test_invalid_tonic_raises(self) -> None:
        with pytest.raises(AssertionError, match="Invalid tonic"):
            Key(tonic="X", mode="major")

    def test_invalid_mode_raises(self) -> None:
        with pytest.raises(AssertionError, match="Invalid mode"):
            Key(tonic="C", mode="dorian")

    def test_key_is_frozen(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(Exception):
            key.tonic = "D"


class TestKeyProperties:
    """Test Key property methods."""

    def test_tonic_pc_c(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.tonic_pc == 0

    def test_tonic_pc_g(self) -> None:
        key = Key(tonic="G", mode="major")
        assert key.tonic_pc == 7

    def test_tonic_pc_f_sharp(self) -> None:
        key = Key(tonic="F#", mode="major")
        assert key.tonic_pc == 6

    def test_tonic_pc_bb(self) -> None:
        key = Key(tonic="Bb", mode="minor")
        assert key.tonic_pc == 10

    def test_scale_major(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.scale == MAJOR_SCALE

    def test_scale_minor(self) -> None:
        key = Key(tonic="A", mode="minor")
        assert key.scale == NATURAL_MINOR_SCALE


class TestGetScaleForContext:
    """Test get_scale_for_context method."""

    def test_major_returns_major_scale(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.get_scale_for_context("V") == MAJOR_SCALE
        assert key.get_scale_for_context("I") == MAJOR_SCALE
        assert key.get_scale_for_context(None) == MAJOR_SCALE

    def test_minor_returns_natural_minor(self) -> None:
        key = Key(tonic="A", mode="minor")
        assert key.get_scale_for_context("V") == NATURAL_MINOR_SCALE
        assert key.get_scale_for_context("i") == NATURAL_MINOR_SCALE
        assert key.get_scale_for_context(None) == NATURAL_MINOR_SCALE


class TestUsesFlats:
    """Test uses_flats method."""

    def test_f_major_uses_flats(self) -> None:
        key = Key(tonic="F", mode="major")
        assert key.uses_flats() is True

    def test_bb_major_uses_flats(self) -> None:
        key = Key(tonic="Bb", mode="major")
        assert key.uses_flats() is True

    def test_g_major_uses_sharps(self) -> None:
        key = Key(tonic="G", mode="major")
        assert key.uses_flats() is False

    def test_d_major_uses_sharps(self) -> None:
        key = Key(tonic="D", mode="major")
        assert key.uses_flats() is False

    def test_c_major_uses_sharps(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.uses_flats() is False

    def test_d_minor_uses_flats(self) -> None:
        key = Key(tonic="D", mode="minor")
        assert key.uses_flats() is True

    def test_e_minor_uses_sharps(self) -> None:
        key = Key(tonic="E", mode="minor")
        assert key.uses_flats() is False


class TestDiatonicStep:
    """Test diatonic_step method."""

    def test_step_up_from_c(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.diatonic_step(60, 1) == 62  # C -> D

    def test_step_down_from_d(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.diatonic_step(62, -1) == 60  # D -> C

    def test_step_across_octave(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.diatonic_step(71, 1) == 72  # B -> C

    def test_multiple_steps_up(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.diatonic_step(60, 7) == 72  # C4 -> C5

    def test_multiple_steps_down(self) -> None:
        key = Key(tonic="C", mode="major")
        assert key.diatonic_step(72, -7) == 60  # C5 -> C4

    def test_step_in_g_major(self) -> None:
        key = Key(tonic="G", mode="major")
        assert key.diatonic_step(55, 2) == 59  # G -> B

    def test_step_from_non_scale_tone(self) -> None:
        key = Key(tonic="C", mode="major")
        result = key.diatonic_step(61, 1)  # C# (not in scale)
        assert result in [62, 64]  # Should snap to nearest scale tone


class TestModulateTo:
    """Test modulate_to method."""

    def test_major_to_dominant(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("V")
        assert new_key.tonic == "G"
        assert new_key.mode == "major"

    def test_major_to_relative_minor(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("vi")
        assert new_key.tonic == "A"
        assert new_key.mode == "minor"

    def test_major_to_subdominant(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("IV")
        assert new_key.tonic == "F"
        assert new_key.mode == "major"

    def test_major_to_supertonic(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("ii")
        assert new_key.tonic == "D"
        assert new_key.mode == "minor"

    def test_major_to_mediant(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("iii")
        assert new_key.tonic == "E"
        assert new_key.mode == "minor"

    def test_major_to_tonic(self) -> None:
        key = Key(tonic="C", mode="major")
        new_key = key.modulate_to("I")
        assert new_key.tonic == "C"
        assert new_key.mode == "major"

    def test_minor_to_relative_major(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key = key.modulate_to("III")
        assert new_key.tonic == "C"
        assert new_key.mode == "major"

    def test_minor_to_dominant_major(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key = key.modulate_to("V")
        assert new_key.tonic == "E"
        assert new_key.mode == "major"

    def test_minor_to_dominant_minor(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key = key.modulate_to("v")
        assert new_key.tonic == "E"
        assert new_key.mode == "minor"

    def test_minor_to_subdominant(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key = key.modulate_to("iv")
        assert new_key.tonic == "D"
        assert new_key.mode == "minor"

    def test_minor_to_submediant(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key = key.modulate_to("VI")
        assert new_key.tonic == "F"
        assert new_key.mode == "major"

    def test_invalid_modulation_target_raises(self) -> None:
        key = Key(tonic="C", mode="major")
        with pytest.raises(ValueError, match="Unknown modulation target"):
            key.modulate_to("VII")

    def test_modulation_preserves_flat_spelling(self) -> None:
        key = Key(tonic="F", mode="major")  # Flat key
        new_key = key.modulate_to("V")
        assert new_key.tonic == "C"

    def test_modulation_from_bb_major(self) -> None:
        key = Key(tonic="Bb", mode="major")
        new_key = key.modulate_to("V")
        assert new_key.tonic == "F"

    def test_minor_lowercase_aliases(self) -> None:
        key = Key(tonic="A", mode="minor")
        new_key_upper = key.modulate_to("III")
        new_key_lower = key.modulate_to("iii")
        assert new_key_upper.tonic == new_key_lower.tonic


class TestFloatingToMidi:
    """Test floating_to_midi method."""

    def test_degree_1_near_middle_c(self) -> None:
        key = Key(tonic="C", mode="major")
        midi = key.floating_to_midi(FloatingNote(1), 60, 60)
        assert midi == 60  # C4

    def test_degree_5_near_middle_c(self) -> None:
        key = Key(tonic="C", mode="major")
        midi = key.floating_to_midi(FloatingNote(5), 60, 60)
        assert abs(midi - 60) <= 12

    def test_all_degrees_produce_valid_midi(self) -> None:
        key = Key(tonic="G", mode="major")
        for deg in range(1, 8):
            midi = key.floating_to_midi(FloatingNote(deg), 60, 60)
            assert 0 <= midi <= 127

    def test_respects_prev_midi(self) -> None:
        key = Key(tonic="C", mode="major")
        midi_low = key.floating_to_midi(FloatingNote(1), 48, 48)
        midi_high = key.floating_to_midi(FloatingNote(1), 72, 72)
        assert midi_low < midi_high

    def test_median_bias(self) -> None:
        key = Key(tonic="C", mode="major")
        midi = key.floating_to_midi(FloatingNote(1), 60, 72)
        assert abs(midi - 66) <= 12

    def test_g_major_degree_1(self) -> None:
        key = Key(tonic="G", mode="major")
        midi = key.floating_to_midi(FloatingNote(1), 55, 55)
        assert midi % 12 == 7  # G

    def test_minor_key_degree_3(self) -> None:
        key = Key(tonic="A", mode="minor")
        midi = key.floating_to_midi(FloatingNote(3), 60, 60)
        assert midi % 12 == 0  # C (minor 3rd from A)

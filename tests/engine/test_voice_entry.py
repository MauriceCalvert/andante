"""100% coverage tests for engine.voice_entry.

Tests import only:
- engine.voice_entry (module under test)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.voice_entry import (
    VoiceTreatmentSpec,
    PhraseVoiceEntry,
    ArcVoiceEntries,
)


class TestVoiceTreatmentSpecConstruction:
    """Test VoiceTreatmentSpec dataclass construction."""

    def test_valid_construction(self) -> None:
        spec = VoiceTreatmentSpec(
            treatment="statement",
            source="subject",
            interval=0,
        )
        assert spec.treatment == "statement"
        assert spec.source == "subject"
        assert spec.interval == 0
        assert spec.delay == Fraction(0)

    def test_with_delay(self) -> None:
        spec = VoiceTreatmentSpec(
            treatment="imitation",
            source="subject",
            interval=4,
            delay=Fraction(1, 2),
        )
        assert spec.delay == Fraction(1, 2)
        assert spec.interval == 4

    def test_none_source(self) -> None:
        spec = VoiceTreatmentSpec(treatment="rest", source=None, interval=0)
        assert spec.source is None

    def test_frozen(self) -> None:
        spec = VoiceTreatmentSpec(treatment="statement", source="subject", interval=0)
        with pytest.raises(Exception):
            spec.treatment = "sequence"


class TestVoiceTreatmentSpecRest:
    """Test VoiceTreatmentSpec.rest factory."""

    def test_rest_creation(self) -> None:
        spec = VoiceTreatmentSpec.rest()
        assert spec.treatment == "rest"
        assert spec.source is None
        assert spec.interval == 0
        assert spec.delay == Fraction(0)

    def test_is_rest_true(self) -> None:
        spec = VoiceTreatmentSpec.rest()
        assert spec.is_rest is True

    def test_is_rest_false(self) -> None:
        spec = VoiceTreatmentSpec(treatment="statement", source="subject", interval=0)
        assert spec.is_rest is False


class TestVoiceTreatmentSpecFromDict:
    """Test VoiceTreatmentSpec.from_dict parsing."""

    def test_full_dict(self) -> None:
        d = {
            "treatment": "imitation",
            "source": "counter_subject",
            "interval": -3,
            "delay": "1/4",
        }
        spec = VoiceTreatmentSpec.from_dict(d)
        assert spec.treatment == "imitation"
        assert spec.source == "counter_subject"
        assert spec.interval == -3
        assert spec.delay == Fraction(1, 4)

    def test_minimal_dict(self) -> None:
        d = {}
        spec = VoiceTreatmentSpec.from_dict(d)
        assert spec.treatment == "statement"
        assert spec.source is None
        assert spec.interval == 0
        assert spec.delay == Fraction(0)

    def test_partial_dict(self) -> None:
        d = {"treatment": "sequence", "source": "subject"}
        spec = VoiceTreatmentSpec.from_dict(d)
        assert spec.treatment == "sequence"
        assert spec.source == "subject"
        assert spec.interval == 0


class TestVoiceTreatmentSpecIsChordal:
    """Test VoiceTreatmentSpec.is_chordal property."""

    def test_is_chordal_true(self) -> None:
        spec = VoiceTreatmentSpec(treatment="chordal", source=None, interval=0)
        assert spec.is_chordal is True

    def test_is_chordal_false(self) -> None:
        spec = VoiceTreatmentSpec(treatment="statement", source="subject", interval=0)
        assert spec.is_chordal is False

    def test_rest_not_chordal(self) -> None:
        spec = VoiceTreatmentSpec.rest()
        assert spec.is_chordal is False


class TestPhraseVoiceEntryConstruction:
    """Test PhraseVoiceEntry dataclass construction."""

    def test_valid_construction(self) -> None:
        specs = (
            VoiceTreatmentSpec(treatment="statement", source="subject", interval=0),
            VoiceTreatmentSpec(treatment="rest", source=None, interval=0),
        )
        entry = PhraseVoiceEntry(phrase_index=0, texture="polyphonic", voice_specs=specs)
        assert entry.phrase_index == 0
        assert entry.texture == "polyphonic"
        assert entry.voice_count == 2

    def test_four_voices(self) -> None:
        specs = tuple(VoiceTreatmentSpec.rest() for _ in range(4))
        entry = PhraseVoiceEntry(phrase_index=3, texture="homophonic", voice_specs=specs)
        assert entry.voice_count == 4

    def test_less_than_two_voices_raises(self) -> None:
        specs = (VoiceTreatmentSpec.rest(),)
        with pytest.raises(AssertionError, match="at least 2 voices"):
            PhraseVoiceEntry(phrase_index=0, texture="polyphonic", voice_specs=specs)


class TestPhraseVoiceEntrySpecForVoice:
    """Test PhraseVoiceEntry.spec_for_voice method."""

    def test_get_first_voice(self) -> None:
        spec0 = VoiceTreatmentSpec(treatment="statement", source="subject", interval=0)
        spec1 = VoiceTreatmentSpec.rest()
        entry = PhraseVoiceEntry(0, "polyphonic", (spec0, spec1))
        assert entry.spec_for_voice(0) == spec0

    def test_get_second_voice(self) -> None:
        spec0 = VoiceTreatmentSpec(treatment="statement", source="subject", interval=0)
        spec1 = VoiceTreatmentSpec(treatment="imitation", source="subject", interval=4)
        entry = PhraseVoiceEntry(0, "polyphonic", (spec0, spec1))
        assert entry.spec_for_voice(1) == spec1

    def test_invalid_index_negative(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        entry = PhraseVoiceEntry(0, "polyphonic", specs)
        with pytest.raises(AssertionError, match="Invalid voice index"):
            entry.spec_for_voice(-1)

    def test_invalid_index_too_high(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        entry = PhraseVoiceEntry(0, "polyphonic", specs)
        with pytest.raises(AssertionError, match="Invalid voice index"):
            entry.spec_for_voice(2)


class TestPhraseVoiceEntryFromDict:
    """Test PhraseVoiceEntry.from_dict parsing."""

    def test_full_dict(self) -> None:
        d = {
            "phrase": 2,
            "texture": "homophonic",
            "voices": {
                "soprano": {"treatment": "statement", "source": "subject"},
                "bass": {"treatment": "imitation", "source": "subject", "interval": -7},
            },
        }
        voice_names = ("soprano", "bass")
        entry = PhraseVoiceEntry.from_dict(d, voice_names)
        assert entry.phrase_index == 2
        assert entry.texture == "homophonic"
        assert entry.voice_specs[0].treatment == "statement"
        assert entry.voice_specs[1].interval == -7

    def test_missing_voice_gets_rest(self) -> None:
        d = {
            "phrase": 0,
            "voices": {
                "soprano": {"treatment": "statement", "source": "subject"},
            },
        }
        voice_names = ("soprano", "alto", "bass")
        entry = PhraseVoiceEntry.from_dict(d, voice_names)
        assert entry.voice_specs[0].treatment == "statement"
        assert entry.voice_specs[1].is_rest is True
        assert entry.voice_specs[2].is_rest is True

    def test_default_texture(self) -> None:
        d = {"phrase": 0, "voices": {"soprano": {}, "bass": {}}}
        voice_names = ("soprano", "bass")
        entry = PhraseVoiceEntry.from_dict(d, voice_names)
        assert entry.texture == "polyphonic"

    def test_empty_voices_all_rest(self) -> None:
        d = {"phrase": 1}
        voice_names = ("soprano", "bass")
        entry = PhraseVoiceEntry.from_dict(d, voice_names)
        assert entry.voice_specs[0].is_rest is True
        assert entry.voice_specs[1].is_rest is True


class TestArcVoiceEntriesConstruction:
    """Test ArcVoiceEntries dataclass construction."""

    def test_valid_construction(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        phrase_entry = PhraseVoiceEntry(0, "polyphonic", specs)
        arc = ArcVoiceEntries(entries=(phrase_entry,), voice_count=2)
        assert arc.voice_count == 2
        assert len(arc.entries) == 1

    def test_empty_entries(self) -> None:
        arc = ArcVoiceEntries(entries=(), voice_count=4)
        assert arc.voice_count == 4
        assert len(arc.entries) == 0


class TestArcVoiceEntriesEntryForPhrase:
    """Test ArcVoiceEntries.entry_for_phrase method."""

    def test_find_existing_phrase(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        entry0 = PhraseVoiceEntry(0, "polyphonic", specs)
        entry2 = PhraseVoiceEntry(2, "homophonic", specs)
        arc = ArcVoiceEntries(entries=(entry0, entry2), voice_count=2)
        assert arc.entry_for_phrase(0) == entry0
        assert arc.entry_for_phrase(2) == entry2

    def test_phrase_not_found(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        entry0 = PhraseVoiceEntry(0, "polyphonic", specs)
        arc = ArcVoiceEntries(entries=(entry0,), voice_count=2)
        assert arc.entry_for_phrase(1) is None
        assert arc.entry_for_phrase(5) is None

    def test_empty_entries_returns_none(self) -> None:
        arc = ArcVoiceEntries.empty(2)
        assert arc.entry_for_phrase(0) is None


class TestArcVoiceEntriesHasExplicitEntries:
    """Test ArcVoiceEntries.has_explicit_entries method."""

    def test_with_entries(self) -> None:
        specs = (VoiceTreatmentSpec.rest(), VoiceTreatmentSpec.rest())
        entry = PhraseVoiceEntry(0, "polyphonic", specs)
        arc = ArcVoiceEntries(entries=(entry,), voice_count=2)
        assert arc.has_explicit_entries() is True

    def test_empty(self) -> None:
        arc = ArcVoiceEntries.empty(2)
        assert arc.has_explicit_entries() is False


class TestArcVoiceEntriesEmpty:
    """Test ArcVoiceEntries.empty factory."""

    def test_creates_empty_entries(self) -> None:
        arc = ArcVoiceEntries.empty(3)
        assert arc.voice_count == 3
        assert arc.entries == ()
        assert arc.has_explicit_entries() is False


class TestArcVoiceEntriesFromList:
    """Test ArcVoiceEntries.from_list parsing."""

    def test_single_entry(self) -> None:
        entries_list = [
            {
                "phrase": 0,
                "texture": "polyphonic",
                "voices": {
                    "soprano": {"treatment": "statement", "source": "subject"},
                    "bass": {"treatment": "rest"},
                },
            }
        ]
        voice_names = ("soprano", "bass")
        arc = ArcVoiceEntries.from_list(entries_list, 2, voice_names)
        assert arc.voice_count == 2
        assert len(arc.entries) == 1
        assert arc.entries[0].phrase_index == 0

    def test_multiple_entries(self) -> None:
        entries_list = [
            {"phrase": 0, "voices": {"soprano": {}, "bass": {}}},
            {"phrase": 1, "voices": {"soprano": {}, "bass": {}}},
            {"phrase": 2, "voices": {"soprano": {}, "bass": {}}},
        ]
        voice_names = ("soprano", "bass")
        arc = ArcVoiceEntries.from_list(entries_list, 2, voice_names)
        assert len(arc.entries) == 3
        assert arc.entries[0].phrase_index == 0
        assert arc.entries[1].phrase_index == 1
        assert arc.entries[2].phrase_index == 2

    def test_empty_list(self) -> None:
        arc = ArcVoiceEntries.from_list([], 2, ("soprano", "bass"))
        assert arc.entries == ()
        assert arc.has_explicit_entries() is False

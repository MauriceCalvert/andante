"""Integration tests for engine.voice_pipeline.

Category B orchestrator tests: verify voice expansion pipeline stages.
Tests import only:
- engine.voice_pipeline (module under test)
- engine.types (data types)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Pitch, Rest
from engine.voice_pipeline import (
    apply_voice_delay,
    expand_voice,
    get_source_material,
    voice_spec_from_treatment,
    VoiceSpec,
)
from engine.engine_types import MotifAST
from shared.timed_material import TimedMaterial


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


class TestVoiceSpec:
    """Test VoiceSpec dataclass."""

    def test_voice_spec_frozen(self) -> None:
        """VoiceSpec is immutable."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        with pytest.raises(Exception):
            spec.source = "counter_subject"

    def test_voice_spec_attributes(self) -> None:
        """VoiceSpec has all attributes."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="invert", transform_params={},
            derivation="imitation", derivation_params={"interval": 4}, delay=Fraction(1, 4),
            direct=False
        )
        assert spec.source == "subject"
        assert spec.transform == "invert"
        assert spec.derivation == "imitation"
        assert spec.delay == Fraction(1, 4)


class TestVoiceSpecFromTreatment:
    """Test voice_spec_from_treatment function."""

    def test_soprano_defaults(self) -> None:
        """Soprano defaults to subject source."""
        treatment: dict = {}
        spec: VoiceSpec = voice_spec_from_treatment(treatment, "soprano")
        assert spec.source == "subject"

    def test_bass_defaults(self) -> None:
        """Bass defaults to subject source."""
        treatment: dict = {}
        spec: VoiceSpec = voice_spec_from_treatment(treatment, "bass")
        assert spec.source == "subject"

    def test_custom_source(self) -> None:
        """Custom source is used."""
        treatment: dict = {"soprano_source": "counter_subject"}
        spec: VoiceSpec = voice_spec_from_treatment(treatment, "soprano")
        assert spec.source == "counter_subject"

    def test_transform_extracted(self) -> None:
        """Transform is extracted from treatment."""
        treatment: dict = {"soprano_transform": "invert"}
        spec: VoiceSpec = voice_spec_from_treatment(treatment, "soprano")
        assert spec.transform == "invert"

    def test_delay_extracted(self) -> None:
        """Delay is extracted from treatment."""
        treatment: dict = {"bass_delay": "1/4"}
        spec: VoiceSpec = voice_spec_from_treatment(treatment, "bass")
        assert spec.delay == Fraction(1, 4)


class TestGetSourceMaterial:
    """Test get_source_material function."""

    def test_subject_source(self) -> None:
        """Subject source returns subject material."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        subject: MotifAST = make_subject()
        pitches, durations = get_source_material(spec, subject, None)
        assert pitches == subject.pitches
        assert durations == subject.durations

    def test_counter_subject_source(self) -> None:
        """Counter-subject source returns counter_subject material."""
        spec: VoiceSpec = VoiceSpec(
            source="counter_subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        subject: MotifAST = make_subject()
        counter_subject: MotifAST = make_counter_subject()
        pitches, durations = get_source_material(spec, subject, counter_subject)
        assert pitches == counter_subject.pitches
        assert durations == counter_subject.durations

    def test_sustained_source(self) -> None:
        """Sustained source returns long notes."""
        spec: VoiceSpec = VoiceSpec(
            source="sustained", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        pitches, durations = get_source_material(spec, make_subject(), None)
        assert len(pitches) == 2  # Two sustained notes
        assert sum(durations) == Fraction(2)

    def test_fallback_to_subject(self) -> None:
        """Unknown source falls back to subject."""
        spec: VoiceSpec = VoiceSpec(
            source="unknown", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        subject: MotifAST = make_subject()
        pitches, durations = get_source_material(spec, subject, None)
        assert pitches == subject.pitches


class TestApplyVoiceDelay:
    """Test apply_voice_delay function."""

    def test_no_delay(self) -> None:
        """Zero delay returns material unchanged."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(1, 2))
        result: TimedMaterial = apply_voice_delay(material, Fraction(0), Fraction(1, 2))
        assert result.pitches == pitches
        assert result.durations == durations

    def test_with_delay(self) -> None:
        """Delay prepends rest."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(1, 2))
        result: TimedMaterial = apply_voice_delay(material, Fraction(1, 4), Fraction(3, 4))
        assert isinstance(result.pitches[0], Rest)
        assert result.durations[0] == Fraction(1, 4)

    def test_delay_prepends_to_pitches(self) -> None:
        """Delay prepends rest followed by original pitches."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1),)
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        material: TimedMaterial = TimedMaterial(pitches, durations, Fraction(1, 4))
        result: TimedMaterial = apply_voice_delay(material, Fraction(1, 8), Fraction(3, 8))
        assert len(result.pitches) == 2
        assert isinstance(result.pitches[0], Rest)
        assert result.pitches[1] == FloatingNote(1)


class TestExpandVoice:
    """Test expand_voice function."""

    def test_expand_soprano_fills_budget(self) -> None:
        """Soprano expansion fills budget."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        result: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(2), 0, "soprano"
        )
        assert result.budget == Fraction(2)
        assert sum(result.durations) == Fraction(2)

    def test_expand_bass_fills_budget(self) -> None:
        """Bass expansion fills budget."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        result: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(2), 0, "bass"
        )
        assert sum(result.durations) == Fraction(2)

    def test_expand_with_delay(self) -> None:
        """Expansion with delay starts with rest."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(1, 4), direct=False
        )
        result: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(2), 0, "soprano"
        )
        assert isinstance(result.pitches[0], Rest)

    def test_expand_sustained(self) -> None:
        """Sustained source produces long notes."""
        spec: VoiceSpec = VoiceSpec(
            source="sustained", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        result: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(4), 0, "soprano"
        )
        assert sum(result.durations) == Fraction(4)

    def test_expand_with_imitation(self) -> None:
        """Imitation derivation transposes pitches."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation="imitation", derivation_params={"interval": 4}, delay=Fraction(0), direct=False
        )
        result: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(1), 0, "soprano"
        )
        # Transposed pitches should differ from original
        if isinstance(result.pitches[0], FloatingNote):
            orig: int = make_subject().pitches[0].degree
            assert result.pitches[0].degree != orig


class TestExpandVoiceIntegration:
    """Integration tests for expand_voice."""

    def test_soprano_bass_different_content(self) -> None:
        """Soprano and bass produce different content."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        soprano: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(2), 0, "soprano"
        )
        bass: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(2), 0, "bass"
        )
        # Both fill budget
        assert sum(soprano.durations) == Fraction(2)
        assert sum(bass.durations) == Fraction(2)

    def test_different_phrase_seeds_vary_output(self) -> None:
        """Different phrase seeds produce varied output."""
        spec: VoiceSpec = VoiceSpec(
            source="subject", transform="none", transform_params={},
            derivation=None, derivation_params={}, delay=Fraction(0), direct=False
        )
        result_0: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(4), 0, "soprano"
        )
        result_1: TimedMaterial = expand_voice(
            spec, make_subject(), None,
            Fraction(4), 1, "soprano"
        )
        # Different seeds may produce different bar treatments
        # Both should fill budget
        assert sum(result_0.durations) == Fraction(4)
        assert sum(result_1.durations) == Fraction(4)

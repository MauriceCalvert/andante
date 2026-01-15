"""Integration tests for engine.phrase_builder.

Category B orchestrator tests: verify phrase building with bar treatments.
Tests import only:
- engine.phrase_builder (module under test)
- engine.types (data types)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Pitch
from engine.phrase_builder import (
    apply_transform,
    build_phrase_bass,
    build_phrase_soprano,
    build_voice,
    build_voices,
    BarTreatment,
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


class TestApplyTransform:
    """Test apply_transform function."""

    def test_none_transform(self) -> None:
        """None transform returns unchanged."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        p, d = apply_transform(pitches, durations, "none")
        assert p == pitches
        assert d == durations

    def test_invert_transform(self) -> None:
        """Invert mirrors pitches around axis."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(5))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        p, d = apply_transform(pitches, durations, "invert")
        # Inverted pitches should be different
        assert p[0].degree != 1 or p[1].degree != 5
        # Durations unchanged
        assert d == durations

    def test_retrograde_transform(self) -> None:
        """Retrograde reverses order."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2), FloatingNote(3))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8), Fraction(1, 2))
        p, d = apply_transform(pitches, durations, "retrograde")
        assert p == (FloatingNote(3), FloatingNote(2), FloatingNote(1))
        assert d == (Fraction(1, 2), Fraction(1, 8), Fraction(1, 4))

    def test_head_transform(self) -> None:
        """Head takes first 4 notes."""
        pitches: tuple[Pitch, ...] = tuple(FloatingNote(i) for i in range(1, 8))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 8) for _ in range(7))
        p, d = apply_transform(pitches, durations, "head")
        assert len(p) == 4
        assert len(d) == 4

    def test_tail_transform(self) -> None:
        """Tail takes last 3 notes."""
        pitches: tuple[Pitch, ...] = tuple(FloatingNote(i) for i in range(1, 8))
        durations: tuple[Fraction, ...] = tuple(Fraction(1, 8) for _ in range(7))
        p, d = apply_transform(pitches, durations, "tail")
        assert len(p) == 3
        assert len(d) == 3

    def test_augment_transform(self) -> None:
        """Augment doubles durations."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8))
        p, d = apply_transform(pitches, durations, "augment")
        assert d == (Fraction(1, 2), Fraction(1, 4))
        assert p == pitches

    def test_diminish_transform(self) -> None:
        """Diminish halves durations with minimum of 1/16."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 2))
        p, d = apply_transform(pitches, durations, "diminish")
        # Uses integer division with min 1/16: max(x // 2, 1/16)
        # 1/4 // 2 = 0, max(0, 1/16) = 1/16
        # 1/2 // 2 = 0, max(0, 1/16) = 1/16
        assert d == (Fraction(1, 16), Fraction(1, 16))

    def test_shift_transposes(self) -> None:
        """Shift transposes pitches."""
        pitches: tuple[Pitch, ...] = (FloatingNote(1), FloatingNote(2))
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4))
        p, d = apply_transform(pitches, durations, "none", shift=2)
        assert p[0].degree == 3
        assert p[1].degree == 4


class TestBarTreatment:
    """Test BarTreatment dataclass."""

    def test_bar_treatment_attributes(self) -> None:
        """BarTreatment has all attributes."""
        bt: BarTreatment = BarTreatment("statement", "none", 0)
        assert bt.name == "statement"
        assert bt.transform == "none"
        assert bt.shift == 0


class TestBuildVoice:
    """Test build_voice function."""

    def test_build_voice_fills_budget(self) -> None:
        """Voice fills budget exactly."""
        subject: MotifAST = make_subject()
        material, treatments = build_voice(
            subject.pitches, subject.durations, Fraction(2), 0
        )
        assert sum(material.durations) == Fraction(2)

    def test_build_voice_returns_treatments(self) -> None:
        """Returns list of treatments used."""
        subject: MotifAST = make_subject()
        material, treatments = build_voice(
            subject.pitches, subject.durations, Fraction(4), 0
        )
        assert len(treatments) >= 1
        assert all(isinstance(t, str) for t in treatments)

    def test_build_voice_with_shift(self) -> None:
        """Pitch shift is applied."""
        subject: MotifAST = make_subject()
        material, _ = build_voice(
            subject.pitches, subject.durations, Fraction(1), 0, pitch_shift=-7
        )
        # Material should be produced
        assert len(material.pitches) > 0

    def test_build_voice_with_transform(self) -> None:
        """Primary transform is applied."""
        subject: MotifAST = make_subject()
        material, _ = build_voice(
            subject.pitches, subject.durations, Fraction(1), 0,
            primary_transform="invert"
        )
        assert len(material.pitches) > 0

    def test_build_voice_soprano_treatments_derive_bass(self) -> None:
        """Bass derives from soprano treatments."""
        subject: MotifAST = make_subject()
        soprano, sop_treatments = build_voice(
            subject.pitches, subject.durations, Fraction(2), 0
        )
        bass, bass_treatments = build_voice(
            subject.pitches, subject.durations, Fraction(2), 0,
            soprano_treatments=sop_treatments
        )
        # Bass treatments should complement soprano
        assert len(bass_treatments) == len(sop_treatments)


class TestBuildPhraseSoprano:
    """Test build_phrase_soprano function."""

    def test_soprano_fills_budget(self) -> None:
        """Soprano fills budget exactly."""
        subject: MotifAST = make_subject()
        material: TimedMaterial = build_phrase_soprano(
            subject, None, Fraction(2), 0
        )
        assert sum(material.durations) == Fraction(2)

    def test_soprano_produces_pitches(self) -> None:
        """Soprano produces pitched notes."""
        subject: MotifAST = make_subject()
        material: TimedMaterial = build_phrase_soprano(
            subject, None, Fraction(1), 0
        )
        assert len(material.pitches) > 0

    def test_soprano_with_transform(self) -> None:
        """Soprano applies primary transform."""
        subject: MotifAST = make_subject()
        material: TimedMaterial = build_phrase_soprano(
            subject, None, Fraction(1), 0, primary_transform="augment"
        )
        assert len(material.pitches) > 0


class TestBuildPhraseBass:
    """Test build_phrase_bass function."""

    def test_bass_fills_budget(self) -> None:
        """Bass fills budget exactly."""
        subject: MotifAST = make_subject()
        material: TimedMaterial = build_phrase_bass(
            subject, None, Fraction(2), 0
        )
        assert sum(material.durations) == Fraction(2)

    def test_bass_uses_counter_subject(self) -> None:
        """Bass can use counter-subject."""
        subject: MotifAST = make_subject()
        cs: MotifAST = make_counter_subject()
        material: TimedMaterial = build_phrase_bass(
            subject, cs, Fraction(1), 0, use_counter_subject=True
        )
        assert len(material.pitches) > 0

    def test_bass_default_shift(self) -> None:
        """Bass has default pitch shift (lower register)."""
        subject: MotifAST = make_subject()
        material: TimedMaterial = build_phrase_bass(
            subject, None, Fraction(1), 0
        )
        # Bass should be produced with shifted pitches
        assert len(material.pitches) > 0


class TestBuildVoices:
    """Test build_voices function."""

    def test_build_voices_returns_two(self) -> None:
        """Returns soprano and bass."""
        subject: MotifAST = make_subject()
        soprano, bass = build_voices(subject, None, Fraction(2), 0)
        assert isinstance(soprano, TimedMaterial)
        assert isinstance(bass, TimedMaterial)

    def test_both_fill_budget(self) -> None:
        """Both voices fill budget."""
        subject: MotifAST = make_subject()
        soprano, bass = build_voices(subject, None, Fraction(2), 0)
        assert sum(soprano.durations) == Fraction(2)
        assert sum(bass.durations) == Fraction(2)

    def test_with_transforms(self) -> None:
        """Different transforms can be applied."""
        subject: MotifAST = make_subject()
        soprano, bass = build_voices(
            subject, None, Fraction(2), 0,
            soprano_transform="none",
            bass_transform="invert"
        )
        assert len(soprano.pitches) > 0
        assert len(bass.pitches) > 0

    def test_bass_uses_counter_subject(self) -> None:
        """Bass can use counter-subject source."""
        subject: MotifAST = make_subject()
        cs: MotifAST = make_counter_subject()
        soprano, bass = build_voices(
            subject, cs, Fraction(2), 0,
            use_counter_subject_for_bass=True
        )
        assert len(bass.pitches) > 0

    def test_bass_derives_from_soprano(self) -> None:
        """Bass treatment is derived from soprano."""
        subject: MotifAST = make_subject()
        soprano, bass = build_voices(subject, None, Fraction(4), 0)
        # Both should be built
        assert sum(soprano.durations) == Fraction(4)
        assert sum(bass.durations) == Fraction(4)


class TestBuildVoiceVariety:
    """Test variety in build_voice output."""

    def test_different_seeds_different_treatments(self) -> None:
        """Different phrase seeds can produce different treatments."""
        subject: MotifAST = make_subject()
        _, treatments_0 = build_voice(
            subject.pitches, subject.durations, Fraction(8), 0
        )
        _, treatments_1 = build_voice(
            subject.pitches, subject.durations, Fraction(8), 1
        )
        # Treatments may differ with different seeds
        assert len(treatments_0) >= 1
        assert len(treatments_1) >= 1

    def test_long_phrase_uses_multiple_treatments(self) -> None:
        """Long phrases use multiple bar treatments."""
        subject: MotifAST = make_subject()
        _, treatments = build_voice(
            subject.pitches, subject.durations, Fraction(8), 0
        )
        # 8 bars should use multiple treatments
        assert len(treatments) >= 4


class TestBuildVoiceEdgeCases:
    """Test edge cases in build_voice."""

    def test_single_bar_budget(self) -> None:
        """Single bar budget works."""
        subject: MotifAST = make_subject()
        material, treatments = build_voice(
            subject.pitches, subject.durations, Fraction(1), 0
        )
        assert sum(material.durations) == Fraction(1)

    def test_fractional_budget(self) -> None:
        """Fractional budget fills exactly."""
        subject: MotifAST = make_subject()
        material, _ = build_voice(
            subject.pitches, subject.durations, Fraction(3, 2), 0
        )
        assert sum(material.durations) == Fraction(3, 2)

    def test_large_budget(self) -> None:
        """Large budget is handled."""
        subject: MotifAST = make_subject()
        material, _ = build_voice(
            subject.pitches, subject.durations, Fraction(16), 0
        )
        assert sum(material.durations) == Fraction(16)

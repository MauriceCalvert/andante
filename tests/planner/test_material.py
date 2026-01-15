"""Tests for planner.material.

Category B tests: Material generation and motif transforms.
Tests import only:
- planner.material (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.material import (
    MOTIFS,
    _apply_duration_transform,
    _apply_motif_transform,
    acquire_material,
    bar_duration,
    compute_derived_motifs,
    generate_motif,
)
from planner.plannertypes import DerivedMotif, Frame, Material, Motif


def make_frame(metre: str = "4/4", mode: str = "major") -> Frame:
    """Create Frame for testing."""
    return Frame(
        key="C",
        mode=mode,
        metre=metre,
        tempo="allegro",
        voices=2,
        upbeat=Fraction(0),
        form="through_composed",
    )


class TestBarDuration:
    """Test bar_duration function."""

    def test_4_4(self) -> None:
        """4/4 metre has 1 whole note duration."""
        result: Fraction = bar_duration("4/4")
        assert result == Fraction(1)

    def test_3_4(self) -> None:
        """3/4 metre has 3/4 duration."""
        result: Fraction = bar_duration("3/4")
        assert result == Fraction(3, 4)

    def test_2_4(self) -> None:
        """2/4 metre has 1/2 duration."""
        result: Fraction = bar_duration("2/4")
        assert result == Fraction(1, 2)

    def test_6_8(self) -> None:
        """6/8 metre has 3/4 duration."""
        result: Fraction = bar_duration("6/8")
        assert result == Fraction(6, 8)


class TestMotifTemplates:
    """Test MOTIFS constant."""

    def test_4_4_motif_exists(self) -> None:
        """4/4 metre has motif template."""
        assert "4/4" in MOTIFS

    def test_3_4_motif_exists(self) -> None:
        """3/4 metre has motif template."""
        assert "3/4" in MOTIFS

    def test_motif_degrees_in_range(self) -> None:
        """All motif degrees are 1-7."""
        for metre, (degrees, _) in MOTIFS.items():
            assert all(1 <= d <= 7 for d in degrees), f"Invalid degrees in {metre}"

    def test_motif_durations_sum_to_bar(self) -> None:
        """Motif durations sum to bar length."""
        for metre, (degrees, durations) in MOTIFS.items():
            expected: Fraction = bar_duration(metre)
            actual: Fraction = sum(durations, Fraction(0))
            assert actual == expected, f"{metre}: {actual} != {expected}"


class TestGenerateMotif:
    """Test generate_motif function."""

    def test_returns_motif(self) -> None:
        """generate_motif returns Motif object."""
        frame: Frame = make_frame("4/4")
        result: Motif = generate_motif(frame)
        assert isinstance(result, Motif)

    def test_motif_from_4_4(self) -> None:
        """4/4 metre generates correct motif."""
        frame: Frame = make_frame("4/4")
        result: Motif = generate_motif(frame)
        assert result.bars == 1
        assert len(result.degrees) == len(result.durations)

    def test_motif_from_3_4(self) -> None:
        """3/4 metre generates correct motif."""
        frame: Frame = make_frame("3/4")
        result: Motif = generate_motif(frame)
        assert result.bars == 1
        assert sum(result.durations, Fraction(0)) == Fraction(3, 4)

    def test_unknown_metre_raises(self) -> None:
        """Unknown metre raises assertion error."""
        frame: Frame = make_frame("5/4")
        with pytest.raises(AssertionError, match="No motif template"):
            generate_motif(frame)


class TestApplyMotifTransform:
    """Test _apply_motif_transform function."""

    def test_invert(self) -> None:
        """Invert transform: degree -> 8 - degree (wrapped)."""
        degrees: tuple[int, ...] = (1, 3, 5)
        result: tuple[int, ...] = _apply_motif_transform(degrees, "invert")
        # 1 -> 8-1=7, 3 -> 8-3=5, 5 -> 8-5=3
        assert result == (7, 5, 3)

    def test_retrograde(self) -> None:
        """Retrograde transform reverses degrees."""
        degrees: tuple[int, ...] = (1, 3, 5, 7)
        result: tuple[int, ...] = _apply_motif_transform(degrees, "retrograde")
        assert result == (7, 5, 3, 1)

    def test_unknown_transform_unchanged(self) -> None:
        """Unknown transform leaves degrees unchanged."""
        degrees: tuple[int, ...] = (1, 2, 3)
        result: tuple[int, ...] = _apply_motif_transform(degrees, "unknown")
        assert result == degrees


class TestApplyDurationTransform:
    """Test _apply_duration_transform function."""

    def test_augment_doubles(self) -> None:
        """Augment doubles all durations."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8))
        result: tuple[Fraction, ...] = _apply_duration_transform(durations, "augment")
        assert result == (Fraction(1, 2), Fraction(1, 4))

    def test_diminish_halves(self) -> None:
        """Diminish halves durations (minimum 1/16)."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8))
        result: tuple[Fraction, ...] = _apply_duration_transform(durations, "diminish")
        assert result == (Fraction(1, 8), Fraction(1, 16))

    def test_diminish_minimum(self) -> None:
        """Diminish doesn't go below 1/16."""
        durations: tuple[Fraction, ...] = (Fraction(1, 16),)
        result: tuple[Fraction, ...] = _apply_duration_transform(durations, "diminish")
        assert result == (Fraction(1, 16),)

    def test_retrograde_reverses(self) -> None:
        """Retrograde reverses durations."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 8), Fraction(1, 2))
        result: tuple[Fraction, ...] = _apply_duration_transform(durations, "retrograde")
        assert result == (Fraction(1, 2), Fraction(1, 8), Fraction(1, 4))

    def test_unknown_transform_unchanged(self) -> None:
        """Unknown transform leaves durations unchanged."""
        durations: tuple[Fraction, ...] = (Fraction(1, 4),)
        result: tuple[Fraction, ...] = _apply_duration_transform(durations, "unknown")
        assert result == durations


class TestComputeDerivedMotifs:
    """Test compute_derived_motifs function."""

    def test_returns_tuple(self) -> None:
        """compute_derived_motifs returns tuple of DerivedMotif."""
        subject: Motif = Motif(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, None)
        assert isinstance(result, tuple)
        assert all(isinstance(dm, DerivedMotif) for dm in result)

    def test_creates_head_inverted(self) -> None:
        """Creates head_inverted derived motif."""
        subject: Motif = Motif(
            degrees=(1, 3, 5, 7, 5, 3, 1),
            durations=(Fraction(1, 8),) * 7,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, None)
        names: list[str] = [dm.name for dm in result]
        assert "head_inverted" in names

    def test_creates_tail_augmented(self) -> None:
        """Creates tail_augmented derived motif."""
        subject: Motif = Motif(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, None)
        names: list[str] = [dm.name for dm in result]
        assert "tail_augmented" in names

    def test_creates_head_retrograde(self) -> None:
        """Creates head_retrograde derived motif."""
        subject: Motif = Motif(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, None)
        names: list[str] = [dm.name for dm in result]
        assert "head_retrograde" in names

    def test_includes_counter_head_when_cs_provided(self) -> None:
        """Includes counter_head when counter-subject provided."""
        subject: Motif = Motif(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        cs: Motif = Motif(
            degrees=(5, 4, 3, 2, 1),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, cs)
        names: list[str] = [dm.name for dm in result]
        assert "counter_head" in names

    def test_source_is_subject(self) -> None:
        """Subject-derived motifs have source='subject'."""
        subject: Motif = Motif(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 8),) * 5,
            bars=1,
        )
        result: tuple[DerivedMotif, ...] = compute_derived_motifs(subject, None)
        for dm in result:
            assert dm.source == "subject"


class TestAcquireMaterial:
    """Test acquire_material function."""

    def test_returns_material(self) -> None:
        """acquire_material returns Material object."""
        frame: Frame = make_frame()
        result: Material = acquire_material(frame)
        assert isinstance(result, Material)

    def test_has_subject(self) -> None:
        """Material has subject motif."""
        frame: Frame = make_frame()
        result: Material = acquire_material(frame)
        assert result.subject is not None
        assert isinstance(result.subject, Motif)

    def test_has_counter_subject(self) -> None:
        """Material has counter-subject generated by solver."""
        frame: Frame = make_frame()
        result: Material = acquire_material(frame)
        assert result.counter_subject is not None

    def test_has_derived_motifs(self) -> None:
        """Material has derived motifs."""
        frame: Frame = make_frame()
        result: Material = acquire_material(frame)
        assert len(result.derived_motifs) > 0

    def test_uses_user_motif_when_provided(self) -> None:
        """User-provided motif is used as subject."""
        frame: Frame = make_frame()
        user_motif: Motif = Motif(
            degrees=(1, 1, 5, 5, 6, 6, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 8),
                       Fraction(1, 8), Fraction(1, 8), Fraction(1, 8) * 0 + Fraction(1, 16) * 2),
            bars=1,
        )
        # Need to fix duration sum for test
        user_motif = Motif(
            degrees=(1, 1, 5, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
        )
        result: Material = acquire_material(frame, user_motif)
        assert result.subject.degrees == user_motif.degrees

    def test_counter_subject_different_rhythm(self) -> None:
        """Counter-subject has different rhythm from subject."""
        frame: Frame = make_frame()
        result: Material = acquire_material(frame)
        # Rhythms should differ (solver minimizes parallel attacks)
        assert result.subject.durations != result.counter_subject.durations


class TestIntegration:
    """Integration tests for material module."""

    def test_full_workflow_4_4(self) -> None:
        """Complete material acquisition for 4/4 metre."""
        frame: Frame = make_frame("4/4")
        material: Material = acquire_material(frame, genre="invention")
        # Verify all components
        assert material.subject is not None
        assert material.counter_subject is not None
        assert len(material.derived_motifs) >= 3

    def test_subject_valid_degrees(self) -> None:
        """Subject has valid scale degrees."""
        frame: Frame = make_frame()
        material: Material = acquire_material(frame)
        assert all(1 <= d <= 7 for d in material.subject.degrees)
        assert all(1 <= d <= 7 for d in material.counter_subject.degrees)

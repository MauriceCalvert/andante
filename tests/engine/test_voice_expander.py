"""Integration tests for engine.voice_expander.

Category B orchestrator tests: verify voice expansion orchestration.
Tests import only:
- engine.voice_expander (module under test)
- engine.key (for Key type)
- planner.subject (for Subject type)
- shared types
- stdlib
"""
from fractions import Fraction

import pytest
from shared.pitch import FloatingNote, Pitch
from shared.timed_material import TimedMaterial
from engine.key import Key
from engine.voice_expander import (
    expand_n_voices,
    expand_voices,
)
from planner.subject import Subject


class TestExpandNVoices:
    """Test expand_n_voices function."""

    def test_expand_two_voices_with_assignments(self) -> None:
        """Expand 2 voices with explicit assignments."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        assignments: tuple[str, ...] = ("subject", "cs_1")
        budget: Fraction = Fraction(1)
        result: list[TimedMaterial] = expand_n_voices(subj, assignments, budget, 2)
        assert len(result) == 2
        assert all(isinstance(m, TimedMaterial) for m in result)
        for mat in result:
            assert mat.budget == budget

    def test_expand_four_voices_with_assignments(self) -> None:
        """Expand 4 voices with explicit assignments."""
        subj: Subject = Subject(
            degrees=(1, 3, 5, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
            voice_count=4,
        )
        assignments: tuple[str, ...] = ("subject", "cs_1", "cs_2", "cs_3")
        budget: Fraction = Fraction(1)
        result: list[TimedMaterial] = expand_n_voices(subj, assignments, budget, 4)
        assert len(result) == 4

    def test_expand_voices_extends_to_budget(self) -> None:
        """Voice materials are extended to fill budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
            bars=1,
            mode="major",
        )
        assignments: tuple[str, ...] = ("subject", "cs_1")
        budget: Fraction = Fraction(2)  # Longer than subject
        result: list[TimedMaterial] = expand_n_voices(subj, assignments, budget, 2)
        for mat in result:
            assert mat.budget == budget

    def test_expand_voices_trims_to_budget(self) -> None:
        """Voice materials are trimmed when shorter than budget needed."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5, 6, 7, 1),
            durations=tuple(Fraction(1, 4) for _ in range(8)),
            bars=2,
            mode="major",
        )
        assignments: tuple[str, ...] = ("subject",)
        budget: Fraction = Fraction(1)  # Shorter than subject
        result: list[TimedMaterial] = expand_n_voices(subj, assignments, budget, 1)
        assert result[0].budget == budget


class TestExpandVoices:
    """Test expand_voices function."""

    def test_expand_voices_statement_treatment(self) -> None:
        """Statement treatment produces two voice materials."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=42,
        )
        assert len(result) == 2
        sop, bass = result
        assert isinstance(sop, TimedMaterial)
        assert isinstance(bass, TimedMaterial)
        assert sop.budget == Fraction(1)
        assert bass.budget == Fraction(1)

    def test_expand_voices_sequence_treatment(self) -> None:
        """Sequence treatment produces two voice materials."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="sequence",
            subj=subj,
            tonal_target="V",
            budget=Fraction(2),
            seed=0,
        )
        assert len(result) == 2

    def test_expand_voices_counterpoint_treatment(self) -> None:
        """Counterpoint treatment uses subject and counter-subject."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="counterpoint",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
        )
        assert len(result) == 2
        # Counterpoint uses subject and CS directly
        sop, bass = result
        assert sop.budget == Fraction(1)
        assert bass.budget == Fraction(1)

    def test_expand_voices_with_key(self) -> None:
        """Key parameter is used for figured bass texture."""
        subj: Subject = Subject(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
            mode="major",
        )
        key: Key = Key(tonic="C", mode="major")
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
            key=key,
        )
        assert len(result) == 2

    def test_expand_voices_figured_bass_texture(self) -> None:
        """Figured bass texture generates soprano from figures."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
            mode="major",
        )
        key: Key = Key(tonic="C", mode="major")
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
            texture="figured_bass",
            key=key,
        )
        assert len(result) == 2
        sop, bass = result
        assert sop.budget == Fraction(1)

    def test_expand_voices_with_voice_assignments(self) -> None:
        """Explicit voice assignments override treatment pipeline."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        assignments: tuple[str, ...] = ("subject", "cs_1")
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",  # Ignored with voice_assignments
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
            voice_assignments=assignments,
            voice_count=2,
        )
        assert len(result) == 2

    def test_expand_voices_opening_phrase(self) -> None:
        """Opening phrase may have special bass treatment."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
            is_opening=True,
        )
        assert len(result) == 2

    def test_expand_voices_cadential_phrase(self) -> None:
        """Cadential phrase may have special bass treatment."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
            is_cadential=True,
        )
        assert len(result) == 2

    def test_expand_voices_minor_mode(self) -> None:
        """Minor mode subject expands correctly."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4, 5),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="minor",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="i",
            budget=Fraction(1),
            seed=0,
        )
        assert len(result) == 2


class TestExpandVoicesDifferentBudgets:
    """Test expand_voices with different budget values."""

    def test_expand_voices_one_bar(self) -> None:
        """Expand voices for one bar budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
        )
        for mat in result:
            assert mat.budget == Fraction(1)

    def test_expand_voices_two_bars(self) -> None:
        """Expand voices for two bar budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(2),
            seed=0,
        )
        for mat in result:
            assert mat.budget == Fraction(2)

    def test_expand_voices_four_bars(self) -> None:
        """Expand voices for four bar budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="sequence",
            subj=subj,
            tonal_target="V",
            budget=Fraction(4),
            seed=0,
        )
        for mat in result:
            assert mat.budget == Fraction(4)

    def test_expand_voices_triple_metre(self) -> None:
        """Expand voices for triple metre budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        # Triple metre bar duration
        budget: Fraction = Fraction(3, 4)
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=budget,
            seed=0,
            bar_dur=Fraction(3, 4),
        )
        for mat in result:
            assert mat.budget == budget


class TestExpandVoicesSeeding:
    """Test that seed parameter affects output deterministically."""

    def test_same_seed_same_output(self) -> None:
        """Same seed produces identical output."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result1: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=42,
        )
        result2: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=42,
        )
        assert result1[0].pitches == result2[0].pitches
        assert result1[0].durations == result2[0].durations


class TestExpandVoicesOutputTypes:
    """Test that output types are correct."""

    def test_output_pitches_are_pitch_type(self) -> None:
        """All output pitches are Pitch instances."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
        )
        for mat in result:
            for pitch in mat.pitches:
                assert isinstance(pitch, Pitch)

    def test_output_durations_are_fractions(self) -> None:
        """All output durations are Fraction instances."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(1),
            seed=0,
        )
        for mat in result:
            for dur in mat.durations:
                assert isinstance(dur, Fraction)

    def test_output_budgets_match_input(self) -> None:
        """Output budgets match input budget."""
        subj: Subject = Subject(
            degrees=(1, 2, 3, 4),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        budget: Fraction = Fraction(3, 2)
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=budget,
            seed=0,
        )
        for mat in result:
            assert mat.budget == budget

    def test_pitch_duration_counts_match(self) -> None:
        """Pitch and duration lists have equal length."""
        subj: Subject = Subject(
            degrees=(1, 3, 5, 3, 1),
            durations=(Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4), Fraction(1, 4)),
            bars=1,
            mode="major",
        )
        result: tuple[TimedMaterial, ...] = expand_voices(
            treatment_name="statement",
            subj=subj,
            tonal_target="I",
            budget=Fraction(2),
            seed=0,
        )
        for mat in result:
            assert len(mat.pitches) == len(mat.durations)

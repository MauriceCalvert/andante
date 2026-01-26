"""Tests for planner layer modules.

Category A tests: Pure functions, specification-based.

Specification source: architecture.md - The Seven Layers
Layer 1: Rhetorical - Genre → Trajectory + rhythm + tempo
Layer 2: Tonal - Affect → Tonal plan + density + modality
Layer 3: Schematic - Tonal plan → Schema chain
Layer 4: Metric - Schema chain → Bar assignments + phrase anchors
Layer 5: Textural - Genre + bar assignments → Treatment assignments
Layer 6: Rhythmic - Anchors + treatments + density → Active slots + durations
Layer 7: Melodic - Active slots + anchors → Pitches
"""
from fractions import Fraction
from typing import Any

import pytest

from builder.config_loader import load_configs
from builder.types import (
    AffectConfig, Anchor, FormConfig, GenreConfig, KeyConfig,
    MotiveWeights, SchemaChain, SchemaConfig, Solution, TreatmentAssignment,
)
from planner.melodic import layer_7_melodic
from planner.metric import layer_4_metric
from planner.metric.distribution import distribute_arrivals
from planner.rhetorical import layer_1_rhetorical
from planner.schematic import layer_3_schematic, _check_connection
from planner.textural import layer_5_textural
from planner.tonal import layer_2_tonal


class TestLayer1Rhetorical:
    """Tests for Layer 1: Rhetorical."""

    @pytest.fixture
    def genre_config(self) -> GenreConfig:
        config = load_configs("invention", "c_major", "default")
        return config["genre"]

    def test_returns_trajectory(self, genre_config: GenreConfig) -> None:
        trajectory, _, _ = layer_1_rhetorical(genre_config)
        assert isinstance(trajectory, list)
        assert len(trajectory) > 0

    def test_invention_trajectory(self, genre_config: GenreConfig) -> None:
        trajectory, _, _ = layer_1_rhetorical(genre_config)
        assert "exordium" in trajectory
        assert "narratio" in trajectory
        assert "confirmatio" in trajectory
        assert "peroratio" in trajectory

    def test_returns_rhythm_vocab(self, genre_config: GenreConfig) -> None:
        _, rhythm_vocab, _ = layer_1_rhetorical(genre_config)
        assert isinstance(rhythm_vocab, dict)
        assert "rhythmic_unit" in rhythm_vocab

    def test_invention_primary_value(self, genre_config: GenreConfig) -> None:
        _, rhythm_vocab, _ = layer_1_rhetorical(genre_config)
        assert rhythm_vocab["rhythmic_unit"] == "1/16"

    def test_returns_tempo(self, genre_config: GenreConfig) -> None:
        _, _, tempo = layer_1_rhetorical(genre_config)
        assert isinstance(tempo, int)
        assert 60 <= tempo <= 120


class TestLayer2Tonal:
    """Tests for Layer 2: Tonal."""

    @pytest.fixture
    def affect_config(self) -> AffectConfig:
        config = load_configs("invention", "c_major", "default")
        return config["affect"]

    def test_returns_tonal_plan(self, affect_config: AffectConfig) -> None:
        tonal_plan, _, _ = layer_2_tonal(affect_config)
        assert isinstance(tonal_plan, dict)

    def test_default_narratio_path(self, affect_config: AffectConfig) -> None:
        tonal_plan, _, _ = layer_2_tonal(affect_config)
        assert "narratio" in tonal_plan
        assert tonal_plan["narratio"] == ("V", "vi", "IV")

    def test_returns_density(self, affect_config: AffectConfig) -> None:
        _, density, _ = layer_2_tonal(affect_config)
        assert density in ("high", "medium", "low")

    def test_default_high_density(self, affect_config: AffectConfig) -> None:
        _, density, _ = layer_2_tonal(affect_config)
        assert density == "high"

    def test_returns_modality(self, affect_config: AffectConfig) -> None:
        _, _, modality = layer_2_tonal(affect_config)
        assert modality in ("diatonic", "chromatic")


class TestLayer3Schematic:
    """Tests for Layer 3: Schematic."""

    @pytest.fixture
    def full_config(self) -> dict[str, Any]:
        return load_configs("invention", "c_major", "default")

    def test_returns_schema_chain(self, full_config: dict[str, Any]) -> None:
        tonal_plan = dict(full_config["affect"].tonal_path)
        chain = layer_3_schematic(
            tonal_plan,
            full_config["genre"],
            full_config["form"],
            full_config["schemas"],
        )
        assert isinstance(chain, SchemaChain)

    def test_chain_has_schemas(self, full_config: dict[str, Any]) -> None:
        tonal_plan = dict(full_config["affect"].tonal_path)
        chain = layer_3_schematic(
            tonal_plan,
            full_config["genre"],
            full_config["form"],
            full_config["schemas"],
        )
        assert len(chain.schemas) > 0

    def test_chain_has_key_areas(self, full_config: dict[str, Any]) -> None:
        tonal_plan = dict(full_config["affect"].tonal_path)
        chain = layer_3_schematic(
            tonal_plan,
            full_config["genre"],
            full_config["form"],
            full_config["schemas"],
        )
        assert len(chain.key_areas) == len(chain.schemas)


class TestCheckConnection:
    """Tests for _check_connection function."""

    @pytest.fixture
    def schemas(self) -> dict[str, SchemaConfig]:
        config = load_configs("invention", "c_major", "default")
        return config["schemas"]

    def test_identity_connection(self, schemas: dict[str, SchemaConfig]) -> None:
        drm = schemas["do_re_mi"]
        prinner = schemas["prinner"]
        result = _check_connection(drm, drm)
        assert result is True

    def test_step_connection(self) -> None:
        schema_a = SchemaConfig(
            name="a", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=1, exit_soprano=1, exit_bass=1,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        schema_b = SchemaConfig(
            name="b", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=2, exit_soprano=1, exit_bass=2,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        assert _check_connection(schema_a, schema_b) is True

    def test_dominant_connection(self) -> None:
        schema_dom = SchemaConfig(
            name="dom", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=1, exit_soprano=1, exit_bass=5,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        schema_tonic = SchemaConfig(
            name="tonic", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=1, exit_soprano=1, exit_bass=1,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        assert _check_connection(schema_dom, schema_tonic) is True

    def test_no_connection(self) -> None:
        schema_a = SchemaConfig(
            name="a", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=1, exit_soprano=1, exit_bass=1,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        schema_b = SchemaConfig(
            name="b", soprano_degrees=(1,), bass_degrees=(1,),
            entry_soprano=1, entry_bass=4, exit_soprano=1, exit_bass=4,
            bars_min=1, bars_max=1, position="test", cadential_state="open",
        )
        assert _check_connection(schema_a, schema_b) is False


class TestLayer4Metric:
    """Tests for Layer 4: Metric."""

    @pytest.fixture
    def full_config(self) -> dict[str, Any]:
        return load_configs("invention", "c_major", "default")

    def test_returns_bar_assignments(self, full_config: dict[str, Any]) -> None:
        chain = SchemaChain(("do_re_mi",), ("I",), frozenset())
        bar_assignments, _, _ = layer_4_metric(
            chain,
            full_config["genre"],
            full_config["form"],
            full_config["key"],
            "default",
        )
        assert isinstance(bar_assignments, dict)

    def test_returns_arrivals(self, full_config: dict[str, Any]) -> None:
        chain = SchemaChain(("do_re_mi",), ("I",), frozenset())
        _, arrivals, _ = layer_4_metric(
            chain,
            full_config["genre"],
            full_config["form"],
            full_config["key"],
            "default",
        )
        assert isinstance(arrivals, list)
        assert all(isinstance(a, Anchor) for a in arrivals)

    def test_returns_total_bars(self, full_config: dict[str, Any]) -> None:
        chain = SchemaChain(("do_re_mi",), ("I",), frozenset())
        _, _, total_bars = layer_4_metric(
            chain,
            full_config["genre"],
            full_config["form"],
            full_config["key"],
            "default",
        )
        assert total_bars == 20


class TestDistributeArrivals:
    """Tests for distribute_arrivals function."""

    def test_three_stages_two_bars_4_4(self) -> None:
        arrivals = distribute_arrivals(3, 1, 2, "4/4")
        assert len(arrivals) == 3
        assert arrivals[0] == "1.1"
        assert arrivals[1] == "1.3"
        assert arrivals[2] == "2.1"

    def test_four_stages_two_bars(self) -> None:
        arrivals = distribute_arrivals(4, 1, 2, "4/4")
        assert len(arrivals) == 4
        assert "1.1" in arrivals
        assert "2.3" in arrivals

    def test_three_quarter_time(self) -> None:
        arrivals = distribute_arrivals(3, 1, 3, "3/4")
        assert len(arrivals) == 3


class TestLayer5Textural:
    """Tests for Layer 5: Textural."""

    @pytest.fixture
    def full_config(self) -> dict[str, Any]:
        return load_configs("invention", "c_major", "default")

    @pytest.fixture
    def bar_assignments(self, full_config: dict[str, Any]) -> dict[str, tuple[int, int]]:
        """Build bar assignments from genre sections."""
        assignments: dict[str, tuple[int, int]] = {}
        for section in full_config["genre"].sections:
            name = section["name"]
            bars = section["bars"]
            assignments[name] = (bars[0], bars[1])
        return assignments

    def test_returns_treatment_list(
        self, full_config: dict[str, Any], bar_assignments: dict[str, tuple[int, int]]
    ) -> None:
        texture = layer_5_textural(full_config["genre"], bar_assignments)
        assert isinstance(texture, list)
        assert all(isinstance(t, TreatmentAssignment) for t in texture)

    def test_invention_has_subject_and_answer(
        self, full_config: dict[str, Any], bar_assignments: dict[str, tuple[int, int]]
    ) -> None:
        texture = layer_5_textural(full_config["genre"], bar_assignments)
        treatments = [t.treatment for t in texture]
        assert "subject" in treatments
        assert "answer" in treatments

    def test_voice_assignments(
        self, full_config: dict[str, Any], bar_assignments: dict[str, tuple[int, int]]
    ) -> None:
        texture = layer_5_textural(full_config["genre"], bar_assignments)
        voice_assignments = [t.subject_voice for t in texture]
        assert 0 in voice_assignments or 1 in voice_assignments

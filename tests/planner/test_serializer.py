"""Tests for planner.serializer.

Category A tests: Plan serialization to YAML.
Tests import only:
- planner.serializer (module under test)
- planner.types (shared types)
- stdlib
"""
from fractions import Fraction

import pytest
import yaml

from planner.serializer import (
    InlineList,
    _serialize_material,
    _serialize_motif,
    fraction_representer,
    inline_list_representer,
    plan_to_dict,
    serialize_plan,
)
from planner.plannertypes import (
    Brief,
    DerivedMotif,
    Episode,
    Frame,
    Material,
    Motif,
    Phrase,
    Plan,
    Section,
    Structure,
)


def make_minimal_plan() -> Plan:
    """Create minimal valid Plan for testing."""
    brief: Brief = Brief(affect="maestoso", genre="fugue", forces="keyboard", bars=16)
    frame: Frame = Frame(
        key="C", mode="major", metre="4/4", tempo="allegro",
        voices=2, upbeat=Fraction(0), form="through_composed"
    )
    subject: Motif = Motif(
        degrees=(1, 2, 3, 4),
        durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        bars=1
    )
    material: Material = Material(subject=subject)
    phrase: Phrase = Phrase(
        index=0, bars=4, tonal_target="I", cadence="authentic",
        treatment="statement", surprise=None, is_climax=False, energy="moderate"
    )
    episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
    section: Section = Section(
        label="A", tonal_path=("I",), final_cadence="authentic", episodes=(episode,)
    )
    structure: Structure = Structure(sections=(section,), arc="arch")
    return Plan(brief=brief, frame=frame, material=material, structure=structure, actual_bars=4)


class TestFractionRepresenter:
    """Test fraction_representer function."""

    def test_zero_as_int(self) -> None:
        """Zero fraction represented as integer 0."""
        dumper: yaml.Dumper = yaml.Dumper("")
        node = fraction_representer(dumper, Fraction(0))
        assert node.value == "0"

    def test_nonzero_as_string(self) -> None:
        """Non-zero fraction represented as string."""
        dumper: yaml.Dumper = yaml.Dumper("")
        node = fraction_representer(dumper, Fraction(1, 4))
        assert node.value == "1/4"

    def test_whole_number_as_string(self) -> None:
        """Whole number fraction (like 2/1) as string."""
        dumper: yaml.Dumper = yaml.Dumper("")
        node = fraction_representer(dumper, Fraction(2))
        assert node.value == "2"


class TestInlineList:
    """Test InlineList class and representer."""

    def test_is_list_subclass(self) -> None:
        """InlineList is a list subclass."""
        il: InlineList = InlineList([1, 2, 3])
        assert isinstance(il, list)
        assert il == [1, 2, 3]

    def test_yaml_flow_style(self) -> None:
        """InlineList renders in YAML flow style."""
        il: InlineList = InlineList([1, 2, 3])
        # Register representer for this test
        yaml.add_representer(InlineList, inline_list_representer)
        result: str = yaml.dump({"test": il})
        # Flow style uses brackets: [1, 2, 3]
        assert "[1, 2, 3]" in result


class TestSerializeMotif:
    """Test _serialize_motif function."""

    def test_returns_dict(self) -> None:
        """_serialize_motif returns dictionary."""
        motif: Motif = Motif(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1
        )
        result: dict = _serialize_motif(motif)
        assert isinstance(result, dict)

    def test_has_required_keys(self) -> None:
        """Result has degrees, durations, bars keys."""
        motif: Motif = Motif(degrees=(1, 2), durations=(Fraction(1, 2),) * 2, bars=1)
        result: dict = _serialize_motif(motif)
        assert "degrees" in result
        assert "durations" in result
        assert "bars" in result

    def test_degrees_as_inline_list(self) -> None:
        """Degrees are wrapped as InlineList."""
        motif: Motif = Motif(degrees=(1, 5, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        result: dict = _serialize_motif(motif)
        assert isinstance(result["degrees"], InlineList)
        assert list(result["degrees"]) == [1, 5, 3]

    def test_durations_as_strings(self) -> None:
        """Durations converted to strings."""
        motif: Motif = Motif(degrees=(1, 2), durations=(Fraction(1, 4), Fraction(1, 8)), bars=1)
        result: dict = _serialize_motif(motif)
        assert "1/4" in result["durations"]
        assert "1/8" in result["durations"]


class TestSerializeMaterial:
    """Test _serialize_material function."""

    def test_subject_only(self) -> None:
        """Material with only subject."""
        subject: Motif = Motif(degrees=(1, 2, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        material: Material = Material(subject=subject)
        result: dict = _serialize_material(material)
        assert "subject" in result
        assert "counter_subject" not in result

    def test_with_counter_subject(self) -> None:
        """Material with counter_subject included."""
        subject: Motif = Motif(degrees=(1, 2, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        cs: Motif = Motif(degrees=(5, 4, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        material: Material = Material(subject=subject, counter_subject=cs)
        result: dict = _serialize_material(material)
        assert "subject" in result
        assert "counter_subject" in result

class TestPlanToDict:
    """Test plan_to_dict function."""

    def test_has_all_top_level_keys(self) -> None:
        """Converted plan has brief, frame, material, structure, actual_bars."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        assert "brief" in result
        assert "frame" in result
        assert "material" in result
        assert "structure" in result
        assert "actual_bars" in result

    def test_brief_fields(self) -> None:
        """Brief section has expected fields."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        brief: dict = result["brief"]
        assert brief["affect"] == "maestoso"
        assert brief["genre"] == "fugue"
        assert brief["forces"] == "keyboard"
        assert brief["bars"] == 16

    def test_frame_fields(self) -> None:
        """Frame section has expected fields."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        frame: dict = result["frame"]
        assert frame["key"] == "C"
        assert frame["mode"] == "major"
        assert frame["metre"] == "4/4"
        assert frame["tempo"] == "allegro"
        assert frame["voices"] == 2

    def test_structure_has_sections(self) -> None:
        """Structure has sections list."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        structure: dict = result["structure"]
        assert "sections" in structure
        assert "arc" in structure
        assert len(structure["sections"]) == 1

    def test_section_has_episodes(self) -> None:
        """Each section has episodes with phrases."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        section: dict = result["structure"]["sections"][0]
        assert "episodes" in section
        assert "label" in section
        assert "tonal_path" in section
        assert "final_cadence" in section

    def test_phrase_fields(self) -> None:
        """Phrase has all expected fields."""
        plan: Plan = make_minimal_plan()
        result: dict = plan_to_dict(plan)
        phrase: dict = result["structure"]["sections"][0]["episodes"][0]["phrases"][0]
        assert "index" in phrase
        assert "bars" in phrase
        assert "tonal_target" in phrase
        assert "cadence" in phrase
        assert "treatment" in phrase
        assert "surprise" in phrase
        assert "is_climax" in phrase
        assert "energy" in phrase


class TestSerializePlan:
    """Test serialize_plan function."""

    def test_returns_string(self) -> None:
        """serialize_plan returns YAML string."""
        plan: Plan = make_minimal_plan()
        result: str = serialize_plan(plan)
        assert isinstance(result, str)

    def test_valid_yaml(self) -> None:
        """Output is valid YAML that can be parsed."""
        plan: Plan = make_minimal_plan()
        result: str = serialize_plan(plan)
        parsed: dict = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_roundtrip_brief(self) -> None:
        """Brief data survives roundtrip."""
        plan: Plan = make_minimal_plan()
        result: str = serialize_plan(plan)
        parsed: dict = yaml.safe_load(result)
        assert parsed["brief"]["affect"] == plan.brief.affect
        assert parsed["brief"]["genre"] == plan.brief.genre

    def test_roundtrip_frame(self) -> None:
        """Frame data survives roundtrip."""
        plan: Plan = make_minimal_plan()
        result: str = serialize_plan(plan)
        parsed: dict = yaml.safe_load(result)
        assert parsed["frame"]["key"] == plan.frame.key
        assert parsed["frame"]["mode"] == plan.frame.mode

    def test_upbeat_serialized_correctly(self) -> None:
        """Upbeat Fraction serialized as expected."""
        brief: Brief = Brief(affect="grazioso", genre="fugue", forces="keyboard", bars=16)
        frame: Frame = Frame(
            key="G", mode="major", metre="3/4", tempo="andante",
            voices=2, upbeat=Fraction(1, 4), form="binary"
        )
        subject: Motif = Motif(
            degrees=(5, 4, 3),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
            bars=1
        )
        material: Material = Material(subject=subject)
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="I", cadence="authentic",
                                treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        section: Section = Section(label="A", tonal_path=("I",), final_cadence="authentic", episodes=(episode,))
        structure: Structure = Structure(sections=(section,), arc="arch")
        plan: Plan = Plan(brief=brief, frame=frame, material=material, structure=structure, actual_bars=4)
        result: str = serialize_plan(plan)
        parsed: dict = yaml.safe_load(result)
        # Upbeat should be string "1/4" or parseable as such
        assert str(parsed["frame"]["upbeat"]) == "1/4"

    def test_motif_durations_as_strings(self) -> None:
        """Motif durations serialized as fraction strings."""
        plan: Plan = make_minimal_plan()
        result: str = serialize_plan(plan)
        parsed: dict = yaml.safe_load(result)
        durations: list = parsed["material"]["subject"]["durations"]
        # Should be strings like "1/4"
        assert all(isinstance(d, str) for d in durations)
        assert "1/4" in durations

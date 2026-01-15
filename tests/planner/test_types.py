"""Tests for planner.types.

Category A tests: Pure dataclass types with no external dependencies.
Tests import only:
- planner.types (module under test)
- stdlib
"""
from fractions import Fraction

import pytest

from planner.plannertypes import (
    Brief,
    DerivedMotif,
    Episode,
    EpisodeSpec,
    Frame,
    MacroForm,
    MacroSection,
    Material,
    Motif,
    Phrase,
    Plan,
    Section,
    SectionPlan,
    Structure,
    TensionCurve,
    TensionPoint,
)


class TestBrief:
    """Test Brief dataclass."""

    def test_creation_minimal(self) -> None:
        """Brief created with required fields uses defaults."""
        brief: Brief = Brief(affect="maestoso", genre="fugue", forces="keyboard", bars=32)
        assert brief.affect == "maestoso"
        assert brief.genre == "fugue"
        assert brief.forces == "keyboard"
        assert brief.bars == 32
        assert brief.virtuosic is False

    def test_creation_with_virtuosic(self) -> None:
        """Brief created with virtuosic flag."""
        brief: Brief = Brief(affect="furioso", genre="fantasia", forces="keyboard", bars=64, virtuosic=True)
        assert brief.virtuosic is True

    def test_frozen(self) -> None:
        """Brief is immutable."""
        brief: Brief = Brief(affect="dolore", genre="fugue", forces="keyboard", bars=24)
        with pytest.raises(AttributeError):
            brief.bars = 48  # type: ignore


class TestFrame:
    """Test Frame dataclass."""

    def test_creation(self) -> None:
        """Frame created with all fields."""
        frame: Frame = Frame(
            key="C",
            mode="major",
            metre="4/4",
            tempo="allegro",
            voices=4,
            upbeat=Fraction(0),
            form="through_composed",
        )
        assert frame.key == "C"
        assert frame.mode == "major"
        assert frame.metre == "4/4"
        assert frame.tempo == "allegro"
        assert frame.voices == 4
        assert frame.upbeat == Fraction(0)
        assert frame.form == "through_composed"

    def test_upbeat_fraction(self) -> None:
        """Frame with non-zero upbeat as Fraction."""
        frame: Frame = Frame(
            key="D",
            mode="minor",
            metre="3/4",
            tempo="andante",
            voices=2,
            upbeat=Fraction(1, 4),
            form="binary",
        )
        assert frame.upbeat == Fraction(1, 4)


class TestMotif:
    """Test Motif dataclass."""

    def test_creation(self) -> None:
        """Motif created with degrees, durations, bars."""
        motif: Motif = Motif(
            degrees=(1, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
            bars=1,
        )
        assert motif.degrees == (1, 3, 5)
        assert motif.durations == (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
        assert motif.bars == 1

    def test_frozen(self) -> None:
        """Motif is immutable."""
        motif: Motif = Motif(degrees=(1, 2), durations=(Fraction(1, 2), Fraction(1, 2)), bars=1)
        with pytest.raises(AttributeError):
            motif.bars = 2  # type: ignore


class TestDerivedMotif:
    """Test DerivedMotif dataclass."""

    def test_creation(self) -> None:
        """DerivedMotif with all fields."""
        dm: DerivedMotif = DerivedMotif(
            name="head_inverted",
            degrees=(1, 7, 5, 3),
            durations=(Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
            source="subject",
            transforms=("head", "invert"),
        )
        assert dm.name == "head_inverted"
        assert dm.degrees == (1, 7, 5, 3)
        assert dm.source == "subject"
        assert dm.transforms == ("head", "invert")


class TestMaterial:
    """Test Material dataclass."""

    def test_minimal_creation(self) -> None:
        """Material with only subject."""
        subject: Motif = Motif(degrees=(1, 2, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        material: Material = Material(subject=subject)
        assert material.subject == subject
        assert material.counter_subject is None
        assert material.derived_motifs == ()

    def test_full_creation(self) -> None:
        """Material with subject, counter_subject, and derived motifs."""
        subject: Motif = Motif(degrees=(1, 2, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        cs: Motif = Motif(degrees=(5, 4, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        dm: DerivedMotif = DerivedMotif(
            name="head",
            degrees=(1, 2),
            durations=(Fraction(1, 4), Fraction(1, 4)),
            source="subject",
            transforms=("head",),
        )
        material: Material = Material(subject=subject, counter_subject=cs, derived_motifs=(dm,))
        assert material.counter_subject == cs
        assert len(material.derived_motifs) == 1


class TestPhrase:
    """Test Phrase dataclass."""

    def test_creation_minimal(self) -> None:
        """Phrase with required fields."""
        phrase: Phrase = Phrase(
            index=0,
            bars=4,
            tonal_target="I",
            cadence=None,
            treatment="statement",
            surprise=None,
        )
        assert phrase.index == 0
        assert phrase.bars == 4
        assert phrase.tonal_target == "I"
        assert phrase.is_climax is False
        assert phrase.energy is None

    def test_creation_full(self) -> None:
        """Phrase with all fields."""
        phrase: Phrase = Phrase(
            index=3,
            bars=8,
            tonal_target="V",
            cadence="authentic",
            treatment="sequence",
            surprise="evaded_cadence",
            is_climax=True,
            energy="peak",
        )
        assert phrase.cadence == "authentic"
        assert phrase.is_climax is True
        assert phrase.energy == "peak"


class TestEpisode:
    """Test Episode dataclass."""

    def test_creation(self) -> None:
        """Episode with phrases."""
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="I", cadence=None, treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        assert episode.type == "exposition"
        assert episode.bars == 4
        assert episode.texture == "polyphonic"
        assert len(episode.phrases) == 1
        assert episode.is_transition is False

    def test_transition_episode(self) -> None:
        """Episode marked as transition."""
        phrase: Phrase = Phrase(index=0, bars=2, tonal_target="V", cadence=None, treatment="sequence", surprise=None)
        episode: Episode = Episode(type="linking", bars=2, texture="polyphonic", phrases=(phrase,), is_transition=True)
        assert episode.is_transition is True


class TestSection:
    """Test Section dataclass."""

    def test_creation(self) -> None:
        """Section with episodes."""
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="I", cadence="authentic", treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        section: Section = Section(
            label="A",
            tonal_path=("I",),
            final_cadence="authentic",
            episodes=(episode,),
        )
        assert section.label == "A"
        assert section.tonal_path == ("I",)
        assert section.final_cadence == "authentic"
        assert len(section.episodes) == 1


class TestStructure:
    """Test Structure dataclass."""

    def test_creation(self) -> None:
        """Structure with sections."""
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="I", cadence="authentic", treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        section: Section = Section(label="A", tonal_path=("I",), final_cadence="authentic", episodes=(episode,))
        structure: Structure = Structure(sections=(section,), arc="arch")
        assert structure.arc == "arch"
        assert len(structure.sections) == 1


class TestMacroSection:
    """Test MacroSection dataclass."""

    def test_creation(self) -> None:
        """MacroSection with all fields."""
        ms: MacroSection = MacroSection(
            label="introduction",
            character="dramatic",
            bars=16,
            texture="polyphonic",
            key_area="I",
            energy_arc="rising",
        )
        assert ms.label == "introduction"
        assert ms.character == "dramatic"
        assert ms.bars == 16
        assert ms.texture == "polyphonic"
        assert ms.key_area == "I"
        assert ms.energy_arc == "rising"


class TestMacroForm:
    """Test MacroForm dataclass."""

    def test_creation(self) -> None:
        """MacroForm with sections."""
        sec1: MacroSection = MacroSection(
            label="A", character="expressive", bars=16, texture="polyphonic", key_area="I", energy_arc="rising"
        )
        sec2: MacroSection = MacroSection(
            label="B", character="climax", bars=8, texture="homophonic", key_area="V", energy_arc="peak"
        )
        macro: MacroForm = MacroForm(sections=(sec1, sec2), climax_section="B", total_bars=24)
        assert macro.climax_section == "B"
        assert macro.total_bars == 24
        assert len(macro.sections) == 2


class TestEpisodeSpec:
    """Test EpisodeSpec dataclass."""

    def test_creation_minimal(self) -> None:
        """EpisodeSpec with defaults."""
        spec: EpisodeSpec = EpisodeSpec(type="statement", bars=4)
        assert spec.type == "statement"
        assert spec.bars == 4
        assert spec.is_transition is False

    def test_creation_transition(self) -> None:
        """EpisodeSpec as transition."""
        spec: EpisodeSpec = EpisodeSpec(type="linking", bars=2, is_transition=True)
        assert spec.is_transition is True


class TestSectionPlan:
    """Test SectionPlan dataclass."""

    def test_creation(self) -> None:
        """SectionPlan with episodes."""
        ep1: EpisodeSpec = EpisodeSpec(type="statement", bars=4)
        ep2: EpisodeSpec = EpisodeSpec(type="continuation", bars=4)
        plan: SectionPlan = SectionPlan(
            label="A",
            character="expressive",
            texture="polyphonic",
            key_area="I",
            episodes=(ep1, ep2),
            total_bars=8,
        )
        assert plan.label == "A"
        assert plan.total_bars == 8
        assert len(plan.episodes) == 2


class TestTensionPoint:
    """Test TensionPoint dataclass."""

    def test_creation(self) -> None:
        """TensionPoint with position and level."""
        tp: TensionPoint = TensionPoint(position=0.5, level=0.8)
        assert tp.position == 0.5
        assert tp.level == 0.8


class TestTensionCurve:
    """Test TensionCurve dataclass."""

    def test_creation(self) -> None:
        """TensionCurve with points and climax info."""
        p1: TensionPoint = TensionPoint(position=0.0, level=0.2)
        p2: TensionPoint = TensionPoint(position=0.5, level=0.9)
        p3: TensionPoint = TensionPoint(position=1.0, level=0.3)
        curve: TensionCurve = TensionCurve(points=(p1, p2, p3), climax_position=0.5, climax_level=0.9)
        assert curve.climax_position == 0.5
        assert curve.climax_level == 0.9
        assert len(curve.points) == 3


class TestPlan:
    """Test Plan dataclass."""

    def test_creation_minimal(self) -> None:
        """Plan with required fields."""
        brief: Brief = Brief(affect="maestoso", genre="fugue", forces="keyboard", bars=32)
        frame: Frame = Frame(
            key="C", mode="major", metre="4/4", tempo="allegro", voices=4, upbeat=Fraction(0), form="through_composed"
        )
        subject: Motif = Motif(degrees=(1, 2, 3, 4), durations=(Fraction(1, 4),) * 4, bars=1)
        material: Material = Material(subject=subject)
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="I", cadence="authentic", treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        section: Section = Section(label="A", tonal_path=("I",), final_cadence="authentic", episodes=(episode,))
        structure: Structure = Structure(sections=(section,), arc="arch")
        plan: Plan = Plan(brief=brief, frame=frame, material=material, structure=structure, actual_bars=4)
        assert plan.actual_bars == 4
        assert plan.macro_form is None
        assert plan.tension_curve is None

    def test_creation_full(self) -> None:
        """Plan with macro_form and tension_curve."""
        brief: Brief = Brief(affect="furioso", genre="fantasia", forces="keyboard", bars=64)
        frame: Frame = Frame(
            key="D", mode="minor", metre="4/4", tempo="presto", voices=2, upbeat=Fraction(0), form="through_composed"
        )
        subject: Motif = Motif(degrees=(1, 2, 3), durations=(Fraction(1, 4),) * 3, bars=1)
        material: Material = Material(subject=subject)
        phrase: Phrase = Phrase(index=0, bars=4, tonal_target="i", cadence="authentic", treatment="statement", surprise=None)
        episode: Episode = Episode(type="exposition", bars=4, texture="polyphonic", phrases=(phrase,))
        section: Section = Section(label="A", tonal_path=("i",), final_cadence="authentic", episodes=(episode,))
        structure: Structure = Structure(sections=(section,), arc="dramatic")
        macro_sec: MacroSection = MacroSection(label="A", character="turbulent", bars=64, texture="polyphonic", key_area="i", energy_arc="rising")
        macro: MacroForm = MacroForm(sections=(macro_sec,), climax_section="A", total_bars=64)
        p1: TensionPoint = TensionPoint(position=0.0, level=0.3)
        p2: TensionPoint = TensionPoint(position=1.0, level=0.7)
        curve: TensionCurve = TensionCurve(points=(p1, p2), climax_position=1.0, climax_level=0.7)
        plan: Plan = Plan(
            brief=brief,
            frame=frame,
            material=material,
            structure=structure,
            actual_bars=4,
            macro_form=macro,
            tension_curve=curve,
        )
        assert plan.macro_form is not None
        assert plan.tension_curve is not None

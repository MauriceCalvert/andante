"""Composition plan types per phase5_design.md.

Contract between planner (produces) and voice writer (consumes).
Every compositional decision lives in these structures.  The writer
makes zero compositional choices.
"""
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from shared.key import Key
from shared.voice_types import Range, Role


class WritingMode(Enum):
    """How to fill a single gap between consecutive anchors."""
    FIGURATION = "figuration"
    CADENTIAL = "cadential"
    PILLAR = "pillar"
    STAGGERED = "staggered"
    WALKING = "walking"
    ARPEGGIATED = "arpeggiated"


@dataclass(frozen=True)
class PlanAnchor:
    """Schema arrival constraint at specific bar.beat position.
    
    Degrees are 1-7. Direction hints (up/down/same/None) indicate how to
    approach this anchor from the previous one. MIDI resolution is deferred
    to fill time when the previous pitch is known.
    """
    bar_beat: str
    upper_degree: int
    lower_degree: int
    local_key: Key
    schema: str
    stage: int
    upper_direction: str | None = None
    lower_direction: str | None = None
    section: str = ""


@dataclass(frozen=True)
class GapPlan:
    """All decisions for one figuration gap (anchor[i] to anchor[i+1])."""
    bar_num: int
    writing_mode: WritingMode
    interval: str
    ascending: bool
    gap_duration: Fraction
    density: str
    character: str
    harmonic_tension: str
    bar_function: str
    near_cadence: bool
    use_hemiola: bool
    overdotted: bool
    start_beat: int
    next_anchor_strength: str
    required_note_count: int | None
    compound_allowed: bool


@dataclass(frozen=True)
class SectionPlan:
    """Contiguous span of gaps sharing one strategy and one role."""
    start_gap_index: int
    end_gap_index: int
    schema_name: str | None
    sequencing: str
    figure_profile: str | None
    role: Role
    follows: str | None
    follow_interval: int | None
    follow_delay: Fraction | None
    shared_actuator_with: str | None
    gaps: tuple[GapPlan, ...]


@dataclass(frozen=True)
class AnacrusisPlan:
    """Anacrusis (upbeat) specification."""
    target_degree: int
    duration: Fraction
    note_count: int
    ascending: bool


@dataclass(frozen=True)
class VoicePlan:
    """Complete plan for one voice."""
    voice_id: str
    actuator_range: Range
    tessitura_median: int  # MIDI pitch for first-note placement
    composition_order: int
    midi_track: int         # MIDI track/channel number (e.g. 0=soprano, 3=bass)
    seed: int
    metre: str
    rhythmic_unit: Fraction
    sections: tuple[SectionPlan, ...]
    anacrusis: AnacrusisPlan | None
    bass_pattern: str | None = None


@dataclass(frozen=True)
class CompositionPlan:
    """Top-level plan handed to the builder."""
    home_key: Key
    tempo: int
    upbeat: Fraction
    voice_plans: tuple[VoicePlan, ...]
    anchors: tuple[PlanAnchor, ...]


# ── validate_plan ────────────────────────────────────────────────────────────

def validate_plan(plan: CompositionPlan) -> None:
    """Assert structural invariants on a CompositionPlan.

    Called every time the planner builds a plan.  Catches structural
    bugs that faults.py cannot see (faults.py checks notes, not plans).
    """
    voice_ids: list[str] = [vp.voice_id for vp in plan.voice_plans]
    _check_unique_voice_ids(voice_ids=voice_ids)
    _check_composition_order(voice_plans=plan.voice_plans)
    _check_follows_references(voice_plans=plan.voice_plans, voice_ids=voice_ids)
    _check_follows_order(voice_plans=plan.voice_plans)
    _check_role_fields(voice_plans=plan.voice_plans)
    _check_gap_contiguity(voice_plans=plan.voice_plans, anchor_count=len(plan.anchors))
    _check_gap_counts(voice_plans=plan.voice_plans)
    _check_shared_actuator_reciprocal(voice_plans=plan.voice_plans)


def _check_unique_voice_ids(voice_ids: list[str]) -> None:
    seen: set[str] = set()
    for vid in voice_ids:
        assert vid not in seen, f"Duplicate voice_id: '{vid}'"
        seen.add(vid)


def _check_composition_order(voice_plans: tuple[VoicePlan, ...]) -> None:
    orders: list[int] = sorted(vp.composition_order for vp in voice_plans)
    expected: list[int] = list(range(len(voice_plans)))
    assert orders == expected, (
        f"composition_order must be 0..{len(voice_plans) - 1}, "
        f"got {orders}"
    )


def _check_follows_references(
    voice_plans: tuple[VoicePlan, ...],
    voice_ids: list[str],
) -> None:
    id_set: set[str] = set(voice_ids)
    for vp in voice_plans:
        for sp in vp.sections:
            if sp.follows is not None:
                assert sp.follows in id_set, (
                    f"Voice '{vp.voice_id}' section follows "
                    f"unknown voice '{sp.follows}'"
                )
                assert sp.follows != vp.voice_id, (
                    f"Voice '{vp.voice_id}' cannot follow itself"
                )


def _check_follows_order(voice_plans: tuple[VoicePlan, ...]) -> None:
    """Verify no circular imitation within overlapping sections."""
    follows_graph: dict[str, set[str]] = {}
    for vp in voice_plans:
        for sp in vp.sections:
            if sp.follows is not None:
                follows_graph.setdefault(vp.voice_id, set()).add(sp.follows)
    for vid, targets in follows_graph.items():
        for target in targets:
            assert vid not in follows_graph.get(target, set()), (
                f"Circular imitation: '{vid}' follows '{target}' and "
                f"'{target}' follows '{vid}'"
            )


def _check_role_fields(voice_plans: tuple[VoicePlan, ...]) -> None:
    for vp in voice_plans:
        for i, sp in enumerate(vp.sections):
            label: str = f"Voice '{vp.voice_id}' section {i}"
            if sp.role == Role.IMITATIVE:
                assert sp.follows is not None, (
                    f"{label}: IMITATIVE requires follows"
                )
                assert sp.follow_interval is not None, (
                    f"{label}: IMITATIVE requires follow_interval"
                )
                assert sp.follow_delay is not None, (
                    f"{label}: IMITATIVE requires follow_delay"
                )
            else:
                assert sp.follows is None, (
                    f"{label}: {sp.role.name} must not have follows"
                )
                assert sp.follow_interval is None, (
                    f"{label}: {sp.role.name} must not have follow_interval"
                )
                assert sp.follow_delay is None, (
                    f"{label}: {sp.role.name} must not have follow_delay"
                )


def _check_gap_contiguity(
    voice_plans: tuple[VoicePlan, ...],
    anchor_count: int,
) -> None:
    total_gaps: int = max(anchor_count - 1, 0)
    for vp in voice_plans:
        if not vp.sections:
            continue
        assert vp.sections[0].start_gap_index == 0, (
            f"Voice '{vp.voice_id}': first section must start at gap 0, "
            f"starts at {vp.sections[0].start_gap_index}"
        )
        assert vp.sections[-1].end_gap_index == total_gaps, (
            f"Voice '{vp.voice_id}': last section must end at gap {total_gaps}, "
            f"ends at {vp.sections[-1].end_gap_index}"
        )
        for i in range(1, len(vp.sections)):
            prev_end: int = vp.sections[i - 1].end_gap_index
            curr_start: int = vp.sections[i].start_gap_index
            assert curr_start == prev_end, (
                f"Voice '{vp.voice_id}': gap between sections {i - 1} and {i}: "
                f"prev ends at {prev_end}, next starts at {curr_start}"
            )


def _check_gap_counts(voice_plans: tuple[VoicePlan, ...]) -> None:
    for vp in voice_plans:
        for i, sp in enumerate(vp.sections):
            expected: int = sp.end_gap_index - sp.start_gap_index
            assert len(sp.gaps) == expected, (
                f"Voice '{vp.voice_id}' section {i}: "
                f"has {len(sp.gaps)} gaps but span is {expected} "
                f"({sp.start_gap_index}..{sp.end_gap_index})"
            )


def _check_shared_actuator_reciprocal(
    voice_plans: tuple[VoicePlan, ...],
) -> None:
    for vp in voice_plans:
        for i, sp in enumerate(vp.sections):
            if sp.shared_actuator_with is None:
                continue
            partner_id: str = sp.shared_actuator_with
            found_reciprocal: bool = False
            for other_vp in voice_plans:
                if other_vp.voice_id != partner_id:
                    continue
                for other_sp in other_vp.sections:
                    overlaps: bool = (
                        other_sp.start_gap_index < sp.end_gap_index
                        and other_sp.end_gap_index > sp.start_gap_index
                    )
                    if overlaps and other_sp.shared_actuator_with == vp.voice_id:
                        found_reciprocal = True
                        break
                break
            assert found_reciprocal, (
                f"Voice '{vp.voice_id}' section {i} has "
                f"shared_actuator_with='{partner_id}' but no reciprocal "
                f"found on '{partner_id}'"
            )

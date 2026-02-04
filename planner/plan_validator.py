"""Plan validator: structural and semantic checks.

Two validators:
- validate(): For legacy Plan with Episode/Phrase hierarchy
- validate_schema_plan(): For SchemaPlan with schema-based structure
"""
import warnings
from fractions import Fraction
from typing import TYPE_CHECKING

from planner.koch_rules import validate_koch
from planner.material import bar_duration
from planner.plannertypes import Plan
from planner.schema_loader import get_schema
from shared.constants import SCHEMA_TREATMENTS, SCHEMA_TEXTURES, CADENCE_TYPES

if TYPE_CHECKING:
    from planner.planner import SchemaPlan


def validate(plan: Plan) -> tuple[bool, list[str]]:
    """Validate plan. Returns (valid, errors)."""
    errors: list[str] = []
    if not plan.structure.sections:
        errors.append("Structure must have at least one section")
    seen_labels: set[str] = set()
    for section in plan.structure.sections:
        if section.label in seen_labels:
            errors.append(f"Duplicate section label: {section.label}")
        seen_labels.add(section.label)
        if not section.episodes:
            errors.append(f"Section {section.label} must have at least one episode")
        if not section.tonal_path:
            errors.append(f"Section {section.label} must have non-empty tonal_path")
        phrase_count: int = sum(len(ep.phrases) for ep in section.episodes)
        if phrase_count != len(section.tonal_path):
            errors.append(f"Section {section.label}: phrase count must equal tonal_path length")
    last_section = plan.structure.sections[-1] if plan.structure.sections else None
    if last_section and last_section.final_cadence != "authentic":
        errors.append("Last section must have authentic final_cadence")
    motif = plan.material.subject
    # Validate pitch/degree count matches durations (supports both pitches and degrees)
    pitch_count: int = len(motif.pitches) if motif.pitches else (len(motif.degrees) if motif.degrees else 0)
    if pitch_count != len(motif.durations):
        errors.append("Motif pitches/degrees and durations must have same length")
    bar_dur: Fraction = bar_duration(metre=plan.frame.metre)
    expected_dur: Fraction = bar_dur * motif.bars
    actual_dur: Fraction = sum(motif.durations, Fraction(0))
    if actual_dur != expected_dur:
        errors.append(f"Motif duration {actual_dur} != expected {expected_dur}")
    indices: list[int] = []
    for section in plan.structure.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                indices.append(phrase.index)
    expected_indices: list[int] = list(range(len(indices)))
    if indices != expected_indices:
        errors.append(f"Phrase indices must be sequential from 0: got {indices}")

    # Koch's mechanical rules for phrase sequences and structure
    koch_valid, koch_violations = validate_koch(plan=plan)
    for v in koch_violations:
        if v.severity == "blocker":
            errors.append(f"[{v.rule_id}] {v.message}")
        # Warnings are logged but don't fail validation

    return (len(errors) == 0, errors)


# =============================================================================
# Schema-First Plan Validation (planner_design.md)
# =============================================================================


def validate_schema_plan(plan: "SchemaPlan") -> tuple[bool, list[str]]:
    """Validate schema-based plan. Returns (valid, errors).

    Checks:
    1. Schema chain lands on all cadence points
    2. Final cadence is authentic to I
    3. Treatment vocabulary is valid
    4. Texture vocabulary is valid
    5. Cadence types are valid
    """
    errors: list[str] = []

    # Check structure has sections
    if not plan.structure.sections:
        errors.append("Structure must have at least one section")

    # Check schema chain is not empty
    if not plan.schema_chain:
        errors.append("Schema chain cannot be empty")

    # Check cadence plan is not empty
    if not plan.cadence_plan:
        errors.append("Cadence plan cannot be empty")

    # Validate treatment vocabulary
    for slot in plan.schema_chain:
        if slot.treatment not in SCHEMA_TREATMENTS:
            errors.append(
                f"Invalid treatment '{slot.treatment}' in schema slot. "
                f"Valid treatments: {SCHEMA_TREATMENTS}"
            )

    # Validate texture vocabulary
    for slot in plan.schema_chain:
        if slot.texture not in SCHEMA_TEXTURES:
            errors.append(
                f"Invalid texture '{slot.texture}' in schema slot. "
                f"Valid textures: {SCHEMA_TEXTURES}"
            )

    # Validate cadence types
    for cp in plan.cadence_plan:
        if cp.type not in CADENCE_TYPES:
            errors.append(
                f"Invalid cadence type '{cp.type}' at bar {cp.bar}. "
                f"Valid types: {CADENCE_TYPES}"
            )

    # Check schema chain lands on cadence points
    cadence_bars_from_plan = set(cp.bar for cp in plan.cadence_plan)
    cadence_bars_from_chain: set[int] = set()
    cumulative_bars = 0
    for slot in plan.schema_chain:
        cumulative_bars += slot.bars
        if slot.cadence is not None:
            cadence_bars_from_chain.add(cumulative_bars)

    # Every cadence in plan should have a corresponding schema ending
    missing_cadences = cadence_bars_from_plan - cadence_bars_from_chain
    if missing_cadences:
        errors.append(
            f"Schema chain doesn't land on cadence points: bars {sorted(missing_cadences)}"
        )

    # Check final cadence is authentic to I
    if plan.cadence_plan:
        final_cadence = plan.cadence_plan[-1]
        if final_cadence.type != "authentic":
            errors.append(
                f"Final cadence must be authentic, got '{final_cadence.type}'"
            )
        if final_cadence.target != "I":
            errors.append(
                f"Final cadence must target I, got '{final_cadence.target}'"
            )

    # Check actual_bars matches schema chain
    expected_bars = sum(slot.bars for slot in plan.schema_chain)
    if plan.actual_bars != expected_bars:
        errors.append(
            f"actual_bars ({plan.actual_bars}) doesn't match schema chain sum ({expected_bars})"
        )

    # Validate material (similar to legacy validator)
    motif = plan.material.subject
    pitch_count: int = len(motif.pitches) if motif.pitches else (len(motif.degrees) if motif.degrees else 0)
    if pitch_count != len(motif.durations):
        errors.append("Motif pitches/degrees and durations must have same length")

    # Warn if final schema lacks cadence_approach
    if plan.schema_chain:
        final_slot = plan.schema_chain[-1]
        final_schema = get_schema(name=final_slot.schema)
        if not final_schema.cadence_approach:
            warnings.warn(
                f"Final schema '{final_slot.schema}' lacks cadence_approach: true. "
                f"Piece may end abruptly without proper settling.",
                UserWarning,
                stacklevel=2,
            )

    return (len(errors) == 0, errors)

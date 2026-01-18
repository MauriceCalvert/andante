"""Material handler — orchestrates material generation.

Category B: Validates inputs, delegates to domain functions.
This is a thin orchestrator that coordinates adapters and domain.

SIZE: 145 lines — Handler must coordinate YAML loading, context extraction,
and two separate processing paths (MIDI vs degree subjects). The bar treatment
logic is inherently complex with YAML-driven transforms.
"""
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.adapters.tree_reader import extract_bar_context, extract_subject
from builder.adapters.tree_writer import build_notes_tree
from builder.domain.material_ops import (
    apply_pitch_shift,
    convert_degrees_to_diatonic,
    convert_midi_to_diatonic,
    fit_to_duration,
)
from builder.domain.transform_ops import Transform, validate_transform_spec
from builder.handlers.bass_handler import generate_bass_for_bar
from builder.handlers.core import register
from builder.tree import Node
from builder.types import BarContext, BarTreatment, Notes, Subject
from shared.constants import DIATONIC_DEFAULTS
from shared.errors import MissingContextError

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"

# Bar treatment cycle for variety
BAR_TREATMENT_CYCLE: tuple[str, ...] = (
    "statement", "continuation", "development", "sequence_down",
    "response", "inversion_seq", "fragmentation", "retrograde",
)


def _load_bar_treatments() -> dict[str, BarTreatment]:
    """Load bar treatments from YAML."""
    path: Path = DATA_DIR / "bar_treatments.yaml"
    with open(path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    return {
        t["name"]: BarTreatment(t["name"], t["transform"], t["shift"])
        for t in data["treatments"]
    }


def _load_transform_specs() -> dict[str, dict[str, Any]]:
    """Load transform specs from YAML."""
    path: Path = Path(__file__).parent.parent / "data" / "transforms.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


BAR_TREATMENTS: dict[str, BarTreatment] = _load_bar_treatments()
TRANSFORM_SPECS: dict[str, dict[str, Any]] = _load_transform_specs()


@register("notes", "*")
def handle_notes(node: Node) -> Node:
    """Populate notes from subject with bar treatment cycling.

    Category B orchestrator: validates, extracts context, calls domain.
    """
    context: BarContext = extract_bar_context(node)

    if context.role == "bass":
        return generate_bass_for_bar(node)

    subject: Subject | None = extract_subject(node.root)
    if subject is None:
        raise MissingContextError("No subject in material")

    bar_duration: Fraction = context.frame.metre.bar_duration

    if subject.uses_pitches:
        final: Notes = _process_midi_subject(subject, context, bar_duration)
    else:
        final = _process_degree_subject(subject, context, bar_duration)

    return build_notes_tree(final, node.parent)


def _process_midi_subject(
    subject: Subject,
    context: BarContext,
    bar_duration: Fraction,
) -> Notes:
    """Process MIDI pitch subject — fit and convert to diatonic."""
    fitted: Notes = fit_to_duration(subject.notes, bar_duration)
    source_key: str = subject.source_key or "C"
    min_diatonic: int = DIATONIC_DEFAULTS.get(context.role, 28)

    return convert_midi_to_diatonic(
        fitted,
        source_key,
        context.frame.key,
        context.frame.mode,
        min_diatonic,
    )


def _process_degree_subject(
    subject: Subject,
    context: BarContext,
    bar_duration: Fraction,
) -> Notes:
    """Process degree subject — apply treatment, fit, convert."""
    treatment_name: str = _get_treatment_name(context)
    treatment: BarTreatment = BAR_TREATMENTS.get(
        treatment_name, BAR_TREATMENTS["statement"]
    )

    notes: Notes = _apply_bar_treatment(subject.notes, treatment, context.phrase_treatment)
    fitted: Notes = fit_to_duration(notes, bar_duration)
    base_octave: int = DIATONIC_DEFAULTS.get(context.role, 28) // 7

    return convert_degrees_to_diatonic(fitted, base_octave)


def _get_treatment_name(context: BarContext) -> str:
    """Determine treatment name based on bar position."""
    if context.bar_index == 0:
        return context.phrase_treatment
    return BAR_TREATMENT_CYCLE[context.bar_index % len(BAR_TREATMENT_CYCLE)]


def _apply_bar_treatment(notes: Notes, treatment: BarTreatment, phrase_treatment: str) -> Notes:
    """Apply bar treatment transform and shift."""
    result: Notes = notes

    if treatment.transform != "none" and treatment.transform in TRANSFORM_SPECS:
        spec: dict[str, Any] = TRANSFORM_SPECS[treatment.transform] or {}
        transform: Transform = Transform(treatment.transform, spec)
        result = transform.apply(result, pivot=4)

    if treatment.shift != 0:
        result = apply_pitch_shift(result, treatment.shift)

    if phrase_treatment in ("augmentation", "diminution"):
        spec = TRANSFORM_SPECS.get(phrase_treatment, {}) or {}
        transform = Transform(phrase_treatment, spec)
        result = transform.apply(result)

    return result

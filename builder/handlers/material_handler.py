"""Material handler — orchestrates material generation.
Category B: Validates inputs, delegates to domain functions.
This is a thin orchestrator that coordinates adapters and domain.
Subjects must be diatonic (scale degrees). All transforms operate in diatonic space.
"""
from fractions import Fraction
from typing import Any
from builder.adapters.config_loader import (
    BAR_CONTINUATION_CYCLE,
    BAR_TREATMENTS,
    TRANSFORM_SPECS,
    TREATMENT_TO_TRANSFORM,
)
from builder.adapters.tree_reader import extract_bar_context
from builder.adapters.tree_writer import build_notes_tree
from builder.domain.material_ops import (
    apply_pitch_shift,
    convert_degrees_to_diatonic,
    parse_treatment,
)
from builder.domain.transform_ops import Transform
from builder.handlers.bass_handler import generate_bass_for_bar
from builder.handlers.core import register
from builder.tree import Node
from builder.types import BarContext, Notes, ParsedTreatment, Subject
from shared.constants import DIATONIC_DEFAULTS

def _derive_bar_treatment(
    phrase_treatment: str, bar_index: int, phrase_index: int = 0
) -> tuple[str, int]:
    """Derive bar treatment from phrase treatment, bar position, and phrase index.
    For "statement" treatment: no transform, just play through subject (offset handles position).
    For other treatments: bar 0 uses the treatment, subsequent bars use continuation cycle.
    Args:
        phrase_treatment: Treatment from plan (e.g., "inversion[circulatio]")
        bar_index: Position within phrase (0, 1, 2...)
        phrase_index: Global phrase index (0, 1, 2...)
    Returns:
        (transform_name, shift_amount) for the bar
    """
    parsed: ParsedTreatment = parse_treatment(phrase_treatment)
    base_transform: str = TREATMENT_TO_TRANSFORM.get(parsed.base, "statement")
    # Statement: play through subject without transforms (offset handles bar position)
    if base_transform == "statement":
        return ("statement", 0)
    # Other treatments: bar 0 uses the treatment, subsequent bars vary
    if bar_index == 0:
        return (base_transform, 0)
    offset: int = phrase_index + bar_index - 1
    transform, shift = BAR_CONTINUATION_CYCLE[offset % len(BAR_CONTINUATION_CYCLE)]
    return (transform, shift)

@register("notes", "*")
def handle_notes(node: Node) -> Node:
    """Populate notes from phrase melody (soprano) or generate bass.
    Soprano melody is pre-computed at phrase level. Bar handler extracts its slice.
    Bass is generated per-bar based on harmony.
    """
    context: BarContext = extract_bar_context(node)
    if context.role == "bass":
        return generate_bass_for_bar(node)
    # Extract slice from phrase melody
    bar_duration: Fraction = context.frame.metre.bar_duration
    final: Notes = _extract_melody_slice(node, context.bar_index, bar_duration)
    return build_notes_tree(final, node.parent)

def _extract_melody_slice(node: Node, bar_index: int, bar_duration: Fraction) -> Notes:
    """Extract bar's portion of phrase melody.

    Works with both legacy phrase-based structure (parent.key == "phrases")
    and schema-based structure (parent.key == "schemas").
    """
    phrase: Node | None = node.find_ancestor(
        lambda n: n.parent is not None and n.parent.key in ("phrases", "schemas")
    )
    assert phrase is not None, "No phrase/schema ancestor found"
    assert "melody" in phrase, "Phrase missing melody (computed at phrase level)"
    melody_node: Node = phrase["melody"]
    pitches: tuple[int, ...] = tuple(c.value for c in melody_node["pitches"].children)
    durations: tuple[Fraction, ...] = tuple(
        Fraction(c.value) for c in melody_node["durations"].children
    )
    melody: Notes = Notes(pitches, durations)
    from builder.handlers.phrase_handler import extract_bar_melody
    return extract_bar_melody(melody, bar_index, bar_duration)

def _process_degree_subject(
    subject: Subject,
    context: BarContext,
    bar_duration: Fraction,
) -> Notes:
    """Process degree subject — apply treatment, fit, convert, harmonize.
    Bar_index determines offset into subject: bar 0 starts at 0, bar 1 at bar_duration, etc.
    This allows subjects spanning multiple bars to play through continuously.
    """
    transform_name, shift = _derive_bar_treatment(
        context.phrase_treatment, context.bar_index, context.phrase_index
    )
    pivot: int = _compute_pivot(subject.notes.pitches)
    notes: Notes = _apply_transform(subject.notes, transform_name, shift, pivot)
    # Offset into subject based on bar position within phrase
    offset: Fraction = bar_duration * context.bar_index
    fitted: Notes = fit_to_duration(notes, bar_duration, offset)
    if context.harmony is not None and context.bar_index < len(context.harmony):
        chord: str = context.harmony[context.bar_index]
        fitted = harmonize_melody(
            fitted, chord, context.frame.key, context.frame.mode
        )
    base_octave: int = DIATONIC_DEFAULTS.get(context.role, 28) // 7
    return convert_degrees_to_diatonic(fitted, base_octave)

def _compute_pivot(pitches: tuple[int, ...]) -> int:
    """Compute pivot point for inversion from pitch range median."""
    if not pitches:
        return 4
    return (min(pitches) + max(pitches)) // 2

def _apply_transform(notes: Notes, transform_name: str, shift: int, pivot: int = 4) -> Notes:
    """Apply a transform and pitch shift to notes.
    Args:
        notes: Input notes
        transform_name: Name of transform from transforms.yaml
        shift: Pitch shift to apply after transform
        pivot: Pivot point for inversion transforms
    Returns:
        Transformed notes
    """
    result: Notes = notes
    if transform_name != "statement" and transform_name in TRANSFORM_SPECS:
        spec: dict[str, Any] = TRANSFORM_SPECS[transform_name] or {}
        transform: Transform = Transform(transform_name, spec)
        result = transform.apply(result, pivot=pivot, n=shift)
        if shift != 0 and transform_name not in ("transposition",):
            result = apply_pitch_shift(result, shift)
    elif shift != 0:
        result = apply_pitch_shift(result, shift)
    return result

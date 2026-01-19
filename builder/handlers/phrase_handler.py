"""Phrase-level melody computation.
Computes full melodic content for a phrase by applying treatment to subject.
Bar handlers then extract their slice from this pre-computed melody.
"""
from fractions import Fraction
from builder.adapters.config_loader import TRANSFORM_SPECS, TREATMENT_TO_TRANSFORM
from builder.adapters.tree_reader import extract_subject
from builder.domain.material_ops import convert_degrees_to_diatonic, parse_treatment
from builder.domain.transform_ops import Transform
from builder.tree import Node
from builder.types import Notes, Subject
from shared.constants import DIATONIC_DEFAULTS

def compute_phrase_melody(phrase: Node, root: Node, bar_duration: Fraction) -> tuple[Notes, int]:
    """Compute full melody for phrase and return (melody_notes, bar_count).
    For statement: places subject as-is.
    For other treatments: applies transform to subject.
    Bar count is derived from melody duration.
    """
    subject: Subject | None = extract_subject(root)
    assert subject is not None, "No subject in material"
    assert not subject.uses_pitches, "Subject must use degrees"
    treatment: str = phrase["treatment"].value if "treatment" in phrase else "statement"
    parsed = parse_treatment(treatment)
    transform_name: str = TREATMENT_TO_TRANSFORM.get(parsed.base, "statement")
    # Apply transform to whole subject
    notes: Notes = _apply_transform(subject.notes, transform_name)
    # Convert to diatonic
    base_octave: int = DIATONIC_DEFAULTS.get("soprano", 28) // 7
    melody: Notes = convert_degrees_to_diatonic(notes, base_octave)
    # Bar count from melody duration
    total_duration: Fraction = sum(melody.durations, Fraction(0))
    bar_count: int = max(1, int((total_duration + bar_duration - Fraction(1, 32)) // bar_duration))
    return melody, bar_count

def _apply_transform(notes: Notes, transform_name: str) -> Notes:
    """Apply transform to notes (no shift for phrase-level)."""
    if transform_name == "statement" or transform_name not in TRANSFORM_SPECS:
        return notes
    spec = TRANSFORM_SPECS[transform_name] or {}
    pivot: int = (min(notes.pitches) + max(notes.pitches)) // 2
    transform = Transform(transform_name, spec)
    return transform.apply(notes, pivot=pivot, n=0)

def extract_bar_melody(melody: Notes, bar_index: int, bar_duration: Fraction) -> Notes:
    """Extract notes for a specific bar from phrase melody."""
    offset: Fraction = bar_duration * bar_index
    return _slice_notes(melody, offset, bar_duration)

def _slice_notes(notes: Notes, offset: Fraction, duration: Fraction) -> Notes:
    """Extract notes that START within [offset, offset+duration).

    Notes keep their full duration even if they extend past the window.
    Notes that started before the window are excluded (already emitted).
    """
    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    current: Fraction = Fraction(0)
    window_end: Fraction = offset + duration
    for p, d in zip(notes.pitches, notes.durations):
        note_start: Fraction = current
        current += d
        # Skip notes that start before window
        if note_start < offset:
            continue
        # Stop if we've passed the window
        if note_start >= window_end:
            break
        # Note starts within window - include with full duration
        result_pitches.append(p)
        result_durations.append(d)
    return Notes(tuple(result_pitches), tuple(result_durations))

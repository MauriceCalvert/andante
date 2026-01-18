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
    """Extract notes from offset for duration."""
    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    current: Fraction = Fraction(0)
    remaining: Fraction = duration
    for i, (p, d) in enumerate(zip(notes.pitches, notes.durations)):
        note_end: Fraction = current + d
        # Skip notes before offset
        if note_end <= offset:
            current = note_end
            continue
        # Note overlaps with our window
        note_start_in_window: Fraction = max(current, offset)
        note_end_in_window: Fraction = min(note_end, offset + duration)
        use_dur: Fraction = note_end_in_window - note_start_in_window
        if use_dur > 0 and remaining > 0:
            result_pitches.append(p)
            result_durations.append(min(use_dur, remaining))
            remaining -= use_dur
        current = note_end
        if remaining <= 0:
            break
    # If we ran out of notes, cycle from beginning
    if remaining > 0 and notes.pitches:
        idx = 0
        while remaining > 0:
            p = notes.pitches[idx % len(notes.pitches)]
            d = notes.durations[idx % len(notes.durations)]
            use_dur = min(d, remaining)
            result_pitches.append(p)
            result_durations.append(use_dur)
            remaining -= use_dur
            idx += 1
    return Notes(tuple(result_pitches), tuple(result_durations))

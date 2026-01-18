"""Material handlers - populate notes from planner material."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from builder.handlers.bass import generate_bass_for_bar
from builder.handlers.core import register
from builder.transform import Notes, Transform, notes_from_node, notes_to_dicts
from builder.tree import Node, yaml_to_tree
from shared.constants import DIATONIC_DEFAULTS, MAJOR_SCALE, NATURAL_MINOR_SCALE, NOTE_NAME_MAP

DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"


@dataclass(frozen=True)
class BarTreatment:
    """Treatment for a single bar."""
    name: str
    transform: str
    shift: int


def _load_bar_treatments() -> dict[str, BarTreatment]:
    """Load bar treatments from YAML as lookup dict."""
    with open(DATA_DIR / "bar_treatments.yaml", encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    return {
        t["name"]: BarTreatment(t["name"], t["transform"], t["shift"])
        for t in data["treatments"]
    }


BAR_TREATMENTS: dict[str, BarTreatment] = _load_bar_treatments()
BAR_TREATMENT_CYCLE: tuple[str, ...] = (
    "statement", "continuation", "development", "sequence_down",
    "response", "inversion_seq", "fragmentation", "retrograde",
)


@register('notes', '*')
def handle_notes(node: Node) -> Node:
    """Populate notes from subject with bar treatment cycling."""
    voice: Node = node.parent
    voices: Node = voice.parent
    bar: Node = voices.parent
    role: str = voice['role'].value
    if role == 'bass':
        return generate_bass_for_bar(node)
    bar_idx: int = bar['bar_index'].value
    bar_duration: Fraction = _get_bar_duration(node)
    phrase: Node | None = bar.find_ancestor(lambda n: n.parent is not None and n.parent.key == 'phrases')
    phrase_treatment: str = phrase['treatment'].value if phrase and 'treatment' in phrase else 'statement'
    subject: Notes | None = _get_subject(node.root)
    assert subject is not None, "No subject in material"

    # Check if subject uses MIDI pitches (from .note file) or degrees
    uses_pitches: bool = _subject_uses_pitches(node.root)

    if uses_pitches:
        # MIDI pitches: skip degree-based treatments, just fit to bar and convert
        bar_notes: Notes = _fit_to_bar(subject, bar_duration)
        source_key: str = _get_source_key(node.root)
        target_key: str = node.root['frame']['key'].value
        target_mode: str = node.root['frame']['mode'].value
        final: Notes = _midi_to_diatonic(bar_notes, source_key, target_key, target_mode, role)
    else:
        # Degrees: apply bar treatments and legacy conversion
        treatment_name: str = phrase_treatment if bar_idx == 0 else BAR_TREATMENT_CYCLE[bar_idx % len(BAR_TREATMENT_CYCLE)]
        treatment: BarTreatment = BAR_TREATMENTS.get(treatment_name, BAR_TREATMENTS["statement"])
        notes: Notes = _apply_bar_treatment(subject, treatment, phrase_treatment)
        bar_notes = _fit_to_bar(notes, bar_duration)
        final = _to_diatonic(bar_notes, role)

    notes_data: list[dict[str, Any]] = notes_to_dicts(final)
    return yaml_to_tree(notes_data, key='notes', parent=voice)


def _apply_bar_treatment(subject: Notes, treatment: BarTreatment, phrase_transform: str) -> Notes:
    """Apply bar treatment transform and shift, then phrase transform."""
    # Bar-level transform (from bar_treatments.yaml)
    bar_transform: Transform = Transform(treatment.transform) if treatment.transform != "none" else None
    notes: Notes = bar_transform.apply(subject, pivot=4) if bar_transform else subject

    # Apply shift
    shifted_pitches: tuple[int, ...] = tuple(p + treatment.shift for p in notes.pitches)
    notes = Notes(shifted_pitches, notes.durations)

    # Phrase-level transform (augmentation, diminution)
    phrase_transforms: dict[str, str] = {"augmentation": "augmentation", "diminution": "diminution"}
    phrase_tf_name: str | None = phrase_transforms.get(phrase_transform)
    if phrase_tf_name:
        phrase_tf: Transform = Transform(phrase_tf_name)
        notes = phrase_tf.apply(notes)

    return notes


def _fit_to_bar(notes: Notes, bar_duration: Fraction) -> Notes:
    """Fit notes to bar duration by cycling or truncating."""
    total: Fraction = sum(notes.durations, Fraction(0))

    # If notes fit exactly or are shorter, cycle to fill
    result_pitches: list[int] = []
    result_durations: list[Fraction] = []
    remaining: Fraction = bar_duration
    idx: int = 0

    while remaining > 0:
        p: int = notes.pitches[idx % len(notes.pitches)]
        d: Fraction = notes.durations[idx % len(notes.durations)]

        use_dur: Fraction = min(d, remaining)
        result_pitches.append(p)
        result_durations.append(use_dur)
        remaining -= use_dur
        idx += 1
        assert idx < 1000, "Infinite loop in _fit_to_bar"

    return Notes(tuple(result_pitches), tuple(result_durations))


def _to_diatonic(notes: Notes, role: str) -> Notes:
    """Convert degrees to diatonic pitches for role."""
    base: int = DIATONIC_DEFAULTS.get(role, 28)
    base_octave: int = base // 7

    diatonic: tuple[int, ...] = tuple(
        base_octave * 7 + ((d - 1) % 7)
        for d in notes.pitches
    )
    return Notes(diatonic, notes.durations)


def _get_bar_duration(node: Node) -> Fraction:
    """Get bar duration from frame metre."""
    metre: str = node.root['frame']['metre'].value
    parts: list[str] = metre.split('/')
    return Fraction(int(parts[0]), int(parts[1]))


def _get_subject(root: Node) -> Notes | None:
    """Get subject from material."""
    if 'material' not in root or 'subject' not in root['material']:
        return None
    return notes_from_node(root['material']['subject'])


def _subject_uses_pitches(root: Node) -> bool:
    """Check if subject uses MIDI pitches (vs degrees)."""
    if 'material' not in root or 'subject' not in root['material']:
        return False
    return 'pitches' in root['material']['subject']


def _get_source_key(root: Node) -> str:
    """Get source key from material subject."""
    if 'material' in root and 'subject' in root['material']:
        subj: Node = root['material']['subject']
        if 'source_key' in subj:
            return subj['source_key'].value
    return "C"  # Default


def _midi_to_diatonic(notes: Notes, source_key: str, target_key: str, target_mode: str, role: str) -> Notes:
    """Convert MIDI pitches to diatonic, transposing from source to target key.

    Preserves melodic contour by maintaining intervals during conversion.
    Ensures no notes fall below C4 (diatonic 28) after transposition.

    Args:
        notes: Notes with MIDI pitches
        source_key: Original key of the pitches (e.g., "G")
        target_key: Target key to transpose to (e.g., "C")
        target_mode: Target mode ("major" or "minor")
        role: Voice role for octave placement

    Returns:
        Notes with diatonic pitch values
    """
    # Get tonic MIDI values (pitch class 0-11)
    source_tonic: int = NOTE_NAME_MAP[source_key]
    target_tonic: int = NOTE_NAME_MAP[target_key]
    transpose: int = target_tonic - source_tonic

    # Get scale for pitch class to degree mapping
    scale: tuple[int, ...] = MAJOR_SCALE if target_mode == "major" else NATURAL_MINOR_SCALE

    # Build pitch class to scale degree lookup (0-indexed)
    pc_to_degree: dict[int, int] = {}
    for deg_idx, semitones in enumerate(scale):
        pc_to_degree[semitones] = deg_idx

    # First pass: convert to diatonic preserving original octaves
    diatonic_pitches: list[int] = []
    for midi in notes.pitches:
        # Transpose to target key
        transposed: int = midi + transpose

        # Get octave and pitch class
        octave: int = transposed // 12 - 1  # MIDI 60 = C4, octave 4
        pc: int = (transposed - target_tonic) % 12

        # Find scale degree
        if pc in pc_to_degree:
            degree: int = pc_to_degree[pc]
        else:
            # Chromatic note - find nearest scale degree
            for offset in [1, -1, 2, -2]:
                test_pc: int = (pc + offset) % 12
                if test_pc in pc_to_degree:
                    degree = pc_to_degree[test_pc]
                    break
            else:
                degree = 0  # Fallback to tonic

        # Calculate diatonic pitch preserving original octave
        diatonic: int = octave * 7 + degree
        diatonic_pitches.append(diatonic)

    # Second pass: shift up if any note is below C4 (diatonic 28)
    min_diatonic: int = min(diatonic_pitches)
    min_allowed: int = 28  # C4
    if min_diatonic < min_allowed:
        # Calculate octaves to shift up
        octaves_up: int = (min_allowed - min_diatonic + 6) // 7  # Round up
        diatonic_pitches = [p + octaves_up * 7 for p in diatonic_pitches]

    return Notes(tuple(diatonic_pitches), notes.durations)

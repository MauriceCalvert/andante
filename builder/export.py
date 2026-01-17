"""Export tree to MIDI."""
from fractions import Fraction

from builder.tree import Node
from shared.midi_writer import SimpleNote, write_midi_notes

C_MAJOR_OFFSETS: list[int] = [0, 2, 4, 5, 7, 9, 11]

VOICE_TRACKS: dict[str, int] = {
    'soprano': 0,
    'alto': 1,
    'tenor': 2,
    'bass': 3,
}


def diatonic_to_midi(diatonic: int, key_offset: int = 0) -> int:
    """Convert diatonic pitch to MIDI.

    Diatonic pitch = octave * 7 + degree_index (0-6)
    - diatonic 28 = octave 4, degree 0 = C4 = MIDI 60
    - diatonic 32 = octave 4, degree 4 = G4 = MIDI 67

    Args:
        diatonic: Diatonic pitch number
        key_offset: Semitones to transpose (0 for C major)

    Returns:
        MIDI pitch number (0-127)
    """
    octave: int = diatonic // 7
    degree_idx: int = diatonic % 7
    midi_base: int = (octave + 1) * 12
    return midi_base + C_MAJOR_OFFSETS[degree_idx] + key_offset


def collect_notes(tree: Node) -> list[tuple[str, int, Fraction, Fraction]]:
    """Walk tree and collect all notes.

    Returns:
        List of (role, diatonic, duration, offset) tuples
    """
    notes: list[tuple[str, int, Fraction, Fraction]] = []
    _collect_notes_recursive(tree, Fraction(0), notes)
    return notes


def _collect_notes_recursive(
    node: Node,
    bar_offset: Fraction,
    notes: list[tuple[str, int, Fraction, Fraction]],
    current_role: str | None = None
) -> Fraction:
    """Recursively collect notes from tree.

    Returns the offset after processing this node's subtree.
    """
    if node.key == 'bars':
        offset: Fraction = bar_offset
        bar_node: Node
        for bar_node in node.children:
            offset = _collect_notes_recursive(bar_node, offset, notes, current_role)
        return offset

    if isinstance(node.key, int) and 'voices' in node:
        bar_duration: Fraction = Fraction(0)
        voice_node: Node
        for voice_node in node['voices'].children:
            _collect_notes_recursive(voice_node, bar_offset, notes, current_role)
            if 'notes' in voice_node:
                note_node: Node
                for note_node in voice_node['notes'].children:
                    dur_str: str = note_node['duration'].value
                    dur: Fraction = Fraction(dur_str) if isinstance(dur_str, str) else Fraction(dur_str)
                    bar_duration = max(bar_duration, dur)
        return bar_offset + bar_duration

    if isinstance(node.key, int) and 'role' in node:
        role: str = node['role'].value
        if 'notes' in node:
            offset = bar_offset
            note_node: Node
            for note_node in node['notes'].children:
                diatonic: int = note_node['diatonic'].value
                dur_str: str = note_node['duration'].value
                dur: Fraction = Fraction(dur_str) if isinstance(dur_str, str) else Fraction(dur_str)
                notes.append((role, diatonic, dur, offset))
                offset += dur
        return bar_offset

    child: Node
    for child in node.children:
        bar_offset = _collect_notes_recursive(child, bar_offset, notes, current_role)

    return bar_offset


def export_midi(
    tree: Node,
    output_path: str,
    key_offset: int = 0,
    tempo: int = 80,
    time_signature: tuple[int, int] = (4, 4),
) -> bool:
    """Export tree to MIDI file.

    Args:
        tree: Elaborated tree with notes at leaves
        output_path: Output file path
        key_offset: Semitones to transpose (0 for C major)
        tempo: BPM
        time_signature: Tuple of (numerator, denominator)

    Returns:
        True if successful
    """
    collected: list[tuple[str, int, Fraction, Fraction]] = collect_notes(tree)

    simple_notes: list[SimpleNote] = []
    role: str
    diatonic: int
    duration: Fraction
    offset: Fraction
    for role, diatonic, duration, offset in collected:
        midi_pitch: int = diatonic_to_midi(diatonic, key_offset)
        assert role in VOICE_TRACKS, f"Unknown voice role: '{role}'. Valid: {sorted(VOICE_TRACKS.keys())}"
        track: int = VOICE_TRACKS[role]
        simple_notes.append(SimpleNote(
            pitch=midi_pitch,
            offset=float(offset),
            duration=float(duration),
            velocity=80,
            track=track,
        ))

    return write_midi_notes(
        output_path,
        simple_notes,
        tempo=tempo,
        time_signature=time_signature,
    )

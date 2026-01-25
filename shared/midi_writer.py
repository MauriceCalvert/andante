"""Standalone MIDI writer for andante.

No dependencies on datalayer - works with simple pitch/duration lists or Note dataclasses.
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

try:
    import mido
    from mido import MidiFile, MidiTrack, Message, MetaMessage
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False


@dataclass
class SimpleNote:
    """Minimal note representation."""
    pitch: int          # MIDI pitch (0-127)
    offset: float       # Start time in whole notes
    duration: float     # Duration in whole notes
    velocity: int = 80  # MIDI velocity (0-127)
    track: int = 0      # Track number


def midi_to_name(midi: int) -> str:
    """Convert MIDI number to note name (e.g., 67 -> 'G4')."""
    names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = midi // 12 - 1
    return f"{names[midi % 12]}{octave}"


def name_to_midi(name: str) -> int:
    """Convert note name to MIDI number (e.g., 'G4' -> 67)."""
    name_map = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}

    # Parse note name
    note = name[0].upper()
    rest = name[1:]

    # Handle accidentals
    semitone_offset = 0
    if rest.startswith('#') or rest.startswith('s'):
        semitone_offset = 1
        rest = rest[1:]
    elif rest.startswith('b'):
        semitone_offset = -1
        rest = rest[1:]

    # Parse octave
    octave = int(rest) if rest else 4

    return (octave + 1) * 12 + name_map[note] + semitone_offset


def write_midi(
    path: str,
    pitches: Sequence[int],
    durations: Sequence[float],
    *,
    tempo: int = 80,
    velocity: int = 80,
    time_signature: tuple[int, int] = (4, 4),
    tonic: Optional[str] = None,
    mode: str = "major"
) -> bool:
    """Write a single-track MIDI file from pitch and duration lists.

    Args:
        path: Output file path (.mid or .midi)
        pitches: List of MIDI pitch values (0-127)
        durations: List of durations in whole notes (1.0 = whole note)
        tempo: BPM (default 80)
        velocity: Note velocity 0-127 (default 80)
        time_signature: Tuple of (numerator, denominator)
        tonic: Tonic pitch for key signature (e.g., 'G', 'D', 'Bb')
        mode: 'major' or 'minor'

    Returns:
        True if successful, False if mido not available
    """
    if not MIDO_AVAILABLE:
        print(f"Warning: mido not installed, cannot write {path}")
        return False

    if len(pitches) != len(durations):
        raise ValueError(f"pitches ({len(pitches)}) and durations ({len(durations)}) must have same length")

    midi_file = MidiFile(type=1)
    ticks_per_beat = midi_file.ticks_per_beat  # Default 480
    print(f"PPQN {ticks_per_beat}")
    ticks_per_whole = ticks_per_beat * 4

    # Meta track
    meta_track = MidiTrack()
    midi_file.tracks.append(meta_track)
    meta_track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))
    meta_track.append(MetaMessage(
        'time_signature',
        numerator=time_signature[0],
        denominator=time_signature[1]
    ))
    if tonic:
        key_sig = tonic if mode == "major" else f"{tonic}m"
        try:
            meta_track.append(MetaMessage('key_signature', key=key_sig))
        except (ValueError, KeyError):
            pass  # Invalid key signature, skip
    meta_track.append(MetaMessage('end_of_track', time=0))

    # Note track
    note_track = MidiTrack()
    midi_file.tracks.append(note_track)
    note_track.append(MetaMessage('track_name', name='Motif', time=0))
    note_track.append(Message('program_change', channel=0, program=0, time=0))

    # L013: Ensure gap survives quantization - minimum 60 ticks (32nd note at 480 PPQN)
    MIN_GAP_TICKS = 60
    pending_gap = 0

    for pitch, dur in zip(pitches, durations):
        dur_ticks = max(1, int(dur * ticks_per_whole))
        gap_ticks = min(MIN_GAP_TICKS, dur_ticks // 2)  # Gap is min of 60 or half duration
        gate_ticks = dur_ticks - gap_ticks

        note_track.append(Message('note_on', note=pitch, velocity=velocity, time=pending_gap))
        note_track.append(Message('note_off', note=pitch, velocity=0, time=gate_ticks))
        pending_gap = gap_ticks

    note_track.append(MetaMessage('end_of_track', time=0))

    if not path.endswith(('.mid', '.midi')):
        path += '.midi'

    midi_file.save(path)
    return True


def write_midi_notes(
    path: str,
    notes: Sequence[SimpleNote],
    *,
    tempo: int = 100,
    time_signature: tuple[int, int] = (4, 4),
    tonic: Optional[str] = None,
    mode: str = "major"
) -> bool:
    """Write MIDI file from a list of SimpleNote objects.

    Supports multiple tracks if notes have different track numbers.
    Notes are sorted by offset and can overlap (polyphonic).

    Args:
        path: Output file path
        notes: List of SimpleNote objects
        tempo: BPM (default 80)
        time_signature: Tuple of (numerator, denominator)
        tonic: Tonic pitch for key signature
        mode: 'major' or 'minor'

    Returns:
        True if successful, False if mido not available
    """
    if not MIDO_AVAILABLE:
        print(f"Warning: mido not installed, cannot write {path}")
        return False

    if not notes:
        return False

    midi_file = MidiFile(type=1)
    ticks_per_beat = midi_file.ticks_per_beat
    ticks_per_whole = ticks_per_beat * 4

    # Meta track
    meta_track = MidiTrack()
    midi_file.tracks.append(meta_track)
    meta_track.append(MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo)))
    meta_track.append(MetaMessage(
        'time_signature',
        numerator=time_signature[0],
        denominator=time_signature[1]
    ))
    if tonic:
        key_sig = tonic if mode == "major" else f"{tonic}m"
        try:
            meta_track.append(MetaMessage('key_signature', key=key_sig))
        except (ValueError, KeyError):
            pass
    meta_track.append(MetaMessage('end_of_track', time=0))

    # Group notes by track
    track_nums = sorted(set(n.track for n in notes))
    track_names = ['Soprano', 'Alto', 'Tenor', 'Bass']

    for track_num in track_nums:
        track_notes = [n for n in notes if n.track == track_num]
        track_notes.sort(key=lambda n: n.offset)

        midi_track = MidiTrack()
        midi_file.tracks.append(midi_track)

        name = track_names[track_num] if track_num < len(track_names) else f'Track {track_num}'
        midi_track.append(MetaMessage('track_name', name=name, time=0))
        midi_track.append(Message('program_change', channel=track_num % 16, program=0, time=0))

        # L013: 75% gate time to avoid legato/slur rendering in MuseScore
        GATE_TIME = 0.95

        # Build events list (on/off with absolute times)
        events: List[tuple[int, str, int, int]] = []  # (tick, type, pitch, velocity)
        for note in track_notes:
            on_tick = int(note.offset * ticks_per_whole)
            gate_dur = note.duration * GATE_TIME
            off_tick = int((note.offset + gate_dur) * ticks_per_whole)
            events.append((on_tick, 'on', note.pitch, note.velocity))
            events.append((off_tick, 'off', note.pitch, 0))

        # Sort by time, then offs before ons at same time
        events.sort(key=lambda e: (e[0], 0 if e[1] == 'off' else 1))

        # Convert to delta times
        prev_tick = 0
        for tick, event_type, pitch, vel in events:
            delta = tick - prev_tick
            if event_type == 'on':
                midi_track.append(Message('note_on', note=pitch, velocity=vel, time=delta))
            else:
                midi_track.append(Message('note_off', note=pitch, velocity=0, time=delta))
            prev_tick = tick

        midi_track.append(MetaMessage('end_of_track', time=0))

    if not path.endswith(('.mid', '.midi')):
        path += '.midi'

    midi_file.save(path)
    return True


def write_note_file(
    path: str,
    pitches: Sequence[int],
    durations: Sequence[float],
    *,
    score: Optional[float] = None,
    header: Optional[str] = None
) -> None:
    """Write a human-readable .note file (for realised output with absolute pitches).

    Args:
        path: Output file path
        pitches: List of MIDI pitches
        durations: List of durations in whole notes
        score: Optional score to include in header
        header: Optional additional header text
    """
    with open(path, 'w') as f:
        if score is not None:
            f.write(f"# Score: {score:.3f}\n")
        f.write(f"# Pitches: {' '.join(midi_to_name(p) for p in pitches)}\n")
        f.write(f"# Durations: {' '.join(f'{d:g}' for d in durations)}\n")
        if header:
            f.write(f"# {header}\n")
        f.write("\n")

        offset = 0.0
        for pitch, dur in zip(pitches, durations):
            f.write(f"{midi_to_name(pitch):>4}  offset={offset:g}  dur={dur:g}\n")
            offset += dur


def write_motif_file(
    path: str,
    degrees: Sequence[int],
    durations: Sequence[float],
    *,
    score: Optional[float] = None,
    bars: Optional[float] = None,
    name: Optional[str] = None,
    source: Optional[str] = None,
    transforms: Optional[Sequence[str]] = None,
) -> None:
    """Write a .motif file with scale degrees (mode-agnostic).

    Args:
        path: Output file path (will add .motif extension if missing)
        degrees: List of scale degrees (1-7)
        durations: List of durations in whole notes
        score: Optional memorability score
        bars: Optional bar count
        name: Optional motif name
        source: Optional source motif name (for derived motifs)
        transforms: Optional list of transforms applied (for derived motifs)
    """
    if not path.endswith('.motif'):
        path = path.rsplit('.', 1)[0] + '.motif' if '.' in path else path + '.motif'

    total_dur = sum(durations)
    if bars is None:
        bars = total_dur

    with open(path, 'w') as f:
        f.write("# Motif File (mode-agnostic scale degrees)\n")
        if name:
            f.write(f"# Name: {name}\n")
        if score is not None:
            f.write(f"# Score: {score:.3f}\n")
        f.write(f"# Bars: {bars:g}\n")
        f.write(f"# Notes: {len(degrees)}\n")
        if source:
            f.write(f"# Source: {source}\n")
        if transforms:
            f.write(f"# Transforms: {', '.join(transforms)}\n")
        f.write(f"# Degrees: {' '.join(str(d) for d in degrees)}\n")
        f.write(f"# Durations: {' '.join(f'{d:g}' for d in durations)}\n")
        f.write("\n")

        # Body: offset, degree, duration per line
        f.write("# offset,degree,duration\n")
        offset = 0.0
        for deg, dur in zip(degrees, durations):
            f.write(f"{offset:g},{deg},{dur:g}\n")
            offset += dur


def read_motif_file(path: str) -> tuple[list[int], list[float], dict]:
    """Read a .motif file.

    Returns:
        Tuple of (degrees, durations, metadata dict)
    """
    degrees: list[int] = []
    durations: list[float] = []
    metadata: dict = {}

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('# Name:'):
                metadata['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('# Score:'):
                metadata['score'] = float(line.split(':', 1)[1].strip())
            elif line.startswith('# Bars:'):
                metadata['bars'] = float(line.split(':', 1)[1].strip())
            elif line.startswith('# Notes:'):
                metadata['notes'] = int(line.split(':', 1)[1].strip())
            elif line.startswith('# Source:'):
                metadata['source'] = line.split(':', 1)[1].strip()
            elif line.startswith('# Transforms:'):
                metadata['transforms'] = [t.strip() for t in line.split(':', 1)[1].split(',')]
            elif line.startswith('# Degrees:'):
                metadata['degrees_header'] = [int(d) for d in line.split(':', 1)[1].split()]
            elif line.startswith('# Durations:'):
                metadata['durations_header'] = [float(d) for d in line.split(':', 1)[1].split()]
            elif line.startswith('#'):
                continue  # Skip other comments
            elif ',' in line:
                parts = line.split(',')
                if len(parts) >= 3:
                    # offset, degree, duration
                    degrees.append(int(parts[1]))
                    durations.append(float(parts[2]))

    return degrees, durations, metadata

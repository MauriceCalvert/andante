"""Extract melody from _memorable*.note files and write as MIDI.
Strategy: For each piece, extract notes above a pitch threshold to get melody only.
"""
import sys
from pathlib import Path
from typing import List, Dict
sys.path.insert(0, 'D:/projects/Barok/barok')
from source.datalayer.note import Note
from source.utility.midiwriter import MidiWriter
# Piece-specific extraction rules
# (track, min_pitch, tempo, skyline, start_offset, end_offset)
# skyline=True takes highest note per beat
# start/end offset limits the extraction range
PIECE_CONFIG: Dict[str, tuple] = {
    # Brandenburg: complex ensemble - take highest note
    "Brandenburg Concerto": (None, 62, 100, True, 0, 99),
    # Pachelbel: Track 1 bars 3-4 only (the famous descending melody)
    "Canon and Gigue": (1, 0, 60, False, 2.0, 4.0),
    # Dido: Track 1, skyline for vocal line
    "Dido and Aeneas": (1, 65, 50, True, 0, 99),
    # Little Fugue: Track 6, single voice - no skyline needed
    "Fugue in G_BWV578": (6, 0, 80, False, 0, 99),
    # Spring: Track 1, single voice
    "La primavera (Spring)": (1, 0, 100, False, 0, 99),
    # Hallelujah: Track 14, single voice
    "Messiah_HWV56": (14, 0, 100, False, 0, 99),
    # Tambourin: Track 1, skyline for treble
    "Pieces de clavecin": (1, 64, 120, True, 0, 99),
    # Toccata: Track 1, single voice
    "Toccata and Fugue": (1, 0, 40, False, 0, 99),
}

def get_config(filename: str) -> tuple:
    """Get extraction config for a piece."""
    for key, config in PIECE_CONFIG.items():
        if key in filename:
            return config
    return (1, 0, 80, False, 0, 99)  # Default

def parse_note_file(path: Path) -> List[Dict]:
    """Parse a .note file into a list of note dicts."""
    notes: List[Dict] = []
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines[1:]:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split(',')
        if len(parts) < 8:
            continue
        try:
            offset = float(parts[0])
            midi = int(parts[1])
            duration = float(parts[2])
            track = int(parts[3])
            notes.append({
                'offset': offset,
                'midi': midi,
                'duration': duration,
                'track': track,
            })
        except (ValueError, IndexError):
            continue
    return notes

def extract_melody(
    notes: List[Dict],
    track: int,
    min_pitch: int,
    skyline,
    start_offset: float,
    end_offset: float
) -> List[Dict]:
    """Extract melody notes by track, pitch, and offset range."""
    # Filter by track and pitch
    if track is None:
        filtered = [n for n in notes if n['midi'] >= min_pitch]
    else:
        filtered = [n for n in notes if n['track'] == track and n['midi'] >= min_pitch]
    # Filter by offset range
    filtered = [n for n in filtered if start_offset <= n['offset'] < end_offset]
    filtered.sort(key=lambda x: x['offset'])
    # Handle different skyline modes
    if skyline == "long":
        # Keep only notes with duration >= 0.1 (skip ornaments/trills)
        return [n for n in filtered if n['duration'] >= 0.1]
    if not skyline:
        return filtered
    # Skyline: keep only the highest note at each time point
    result: List[Dict] = []
    i = 0
    while i < len(filtered):
        current_offset = filtered[i]['offset']
        group: List[Dict] = [filtered[i]]
        j = i + 1
        while j < len(filtered) and abs(filtered[j]['offset'] - current_offset) < 0.05:
            group.append(filtered[j])
            j += 1
        highest = max(group, key=lambda n: n['midi'])
        result.append(highest)
        i = j
    return result

def notes_to_midi_and_note(melody_notes: List[Dict], output_path: Path, tempo: int) -> None:
    """Write melody notes to MIDI and .note files."""
    # Normalize offsets to start from 0
    if melody_notes:
        min_offset = min(n['offset'] for n in melody_notes)
        for n in melody_notes:
            n['offset'] -= min_offset
    note_objects: List[Note] = []
    for n in melody_notes:
        note = Note(
            midiNote=n['midi'],
            Offset=n['offset'],
            Duration=n['duration'],
            bar=1 + int(n['offset']),
            beat=1.0 + (n['offset'] % 1) * 4
        )
        note_objects.append(note)
    note_objects.sort(key=lambda x: x.Offset)
    writer = MidiWriter(tempo=tempo)
    writer.write_midi(file_name=str(output_path), notes=note_objects)
    # Also write .note file
    note_path = str(output_path).replace('.midi', '.note')
    writer.write_notes(file_name=note_path, notes=note_objects)

def analyze_melody(melody_notes: List[Dict], name: str) -> Dict:
    """Analyze a melody and return scoring-relevant features."""
    if len(melody_notes) < 2:
        return {}
    # Compute intervals
    pitches = [n['midi'] for n in melody_notes]
    durations = [n['duration'] for n in melody_notes]
    intervals = [pitches[i+1] - pitches[i] for i in range(len(pitches)-1)]
    # Features
    abs_intervals = [abs(i) for i in intervals]
    steps = sum(1 for i in abs_intervals if i <= 2)
    leaps = sum(1 for i in abs_intervals if i > 2)
    repeats = sum(1 for i in intervals if i == 0)
    step_ratio = steps / len(intervals) if intervals else 0
    leap_ratio = leaps / len(intervals) if intervals else 0
    repeat_ratio = repeats / len(intervals) if intervals else 0
    # Duration variety
    unique_durs = len(set(round(d, 3) for d in durations))
    dur_variety = unique_durs / len(durations) if durations else 0
    # Isorhythmic check (all same duration)
    is_isorhythmic = unique_durs == 1
    # Range
    pitch_range = max(pitches) - min(pitches)
    # Opening interval
    opening_interval = abs(intervals[0]) if intervals else 0
    # Contour direction changes
    directions = [1 if i > 0 else (-1 if i < 0 else 0) for i in intervals]
    direction_changes = sum(1 for i in range(len(directions)-1)
                           if directions[i] != 0 and directions[i+1] != 0
                           and directions[i] != directions[i+1])
    return {
        'name': name,
        'notes': len(pitches),
        'step_ratio': step_ratio,
        'leap_ratio': leap_ratio,
        'repeat_ratio': repeat_ratio,
        'dur_variety': dur_variety,
        'is_isorhythmic': is_isorhythmic,
        'pitch_range': pitch_range,
        'opening_interval': opening_interval,
        'direction_changes': direction_changes,
        'max_leap': max(abs_intervals) if abs_intervals else 0,
    }

def main() -> None:
    """Extract melodies from all _memorable*.note files."""
    motifs_dir = Path("D:/projects/Barok/barok/source/imperfect/motifs")
    note_files = sorted(motifs_dir.glob('_memorable*.note'))
    print(f"Found {len(note_files)} memorable note files\n")
    analyses: List[Dict] = []
    for note_file in note_files:
        print(f"Processing: {note_file.name}")
        notes = parse_note_file(path=note_file)
        if not notes:
            print("  No notes found, skipping\n")
            continue
        # Get config for this piece
        track, min_pitch, tempo, skyline, start_off, end_off = get_config(filename=note_file.name)
        melody_notes = extract_melody(notes=notes, track=track, min_pitch=min_pitch, skyline=skyline, start_offset=start_off, end_offset=end_off)
        # Show extraction info
        track_str = "all" if track is None else str(track)
        sky_str = str(skyline) if skyline else "all"
        print(f"  Config: track={track_str}, min_pitch={min_pitch}, tempo={tempo}, {sky_str}, range={start_off}-{end_off}")
        print(f"  Extracted: {len(melody_notes)} notes")
        if not melody_notes:
            print("  No melody notes extracted, skipping\n")
            continue
        # Output filename
        output_name = note_file.stem + "_melody"
        output_path = note_file.parent / (output_name + ".midi")
        notes_to_midi_and_note(melody_notes=melody_notes, output_path=output_path, tempo=tempo)
        print(f"  Written: {output_path.name}")
        # Analyze melody
        short_name = note_file.stem.replace('_memorable_', '')[:30]
        analysis = analyze_melody(melody_notes=melody_notes, name=short_name)
        if analysis:
            analyses.append(analysis)
        # Print melody summary
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        pitches = [n['midi'] for n in melody_notes[:12]]
        names = [f"{note_names[p % 12]}{p // 12 - 1}" for p in pitches]
        print(f"  Melody: {' '.join(names)}")
        # Show rhythm pattern
        durs = [n['duration'] for n in melody_notes[:12]]
        print(f"  Rhythm: {' '.join(f'{d:.3f}' for d in durs)}")
        print()
    # Print analysis summary
    print("\n" + "="*80)
    print("MELODY ANALYSIS SUMMARY")
    print("="*80)
    print(f"{'Name':<32} {'N':>3} {'Step':>5} {'Leap':>5} {'Rep':>5} {'Iso':>4} {'Range':>5} {'Open':>4} {'Dir':>4}")
    print("-"*80)
    for a in analyses:
        iso = "Y" if a['is_isorhythmic'] else "N"
        print(f"{a['name']:<32} {a['notes']:>3} {a['step_ratio']:>5.2f} {a['leap_ratio']:>5.2f} "
              f"{a['repeat_ratio']:>5.2f} {iso:>4} {a['pitch_range']:>5} {a['opening_interval']:>4} {a['direction_changes']:>4}")

if __name__ == "__main__":
    main()

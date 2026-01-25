"""Convert .note CSV file to .subject YAML format."""
import sys
from fractions import Fraction
from pathlib import Path

from shared.constants import VALID_DURATIONS_SORTED
from shared.key import Key


def quantize_duration(duration: Fraction) -> Fraction:
    """Quantize duration to nearest valid note value."""
    best: Fraction = VALID_DURATIONS_SORTED[0]
    best_diff: Fraction = abs(duration - best)
    for valid in VALID_DURATIONS_SORTED:
        diff = abs(duration - valid)
        if diff < best_diff:
            best = valid
            best_diff = diff
    return best


def convert_note_to_subject(
    note_path: Path,
    tonic: str = "C",
    mode: str = "major",
    track: int | None = None,
) -> None:
    """Convert .note CSV file to .subject YAML file.

    Args:
        note_path: Path to input .note file
        tonic: Tonic pitch (default C)
        mode: Mode (major/minor, default major)
        track: Track number to extract (default: lowest track number)
    """
    # Read notes from CSV
    notes: list[dict] = []
    with open(note_path, encoding="utf-8-sig") as f:
        # Skip comment lines, find header
        header_line: str | None = None
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            header_line = stripped
            break
        assert header_line is not None, "No header line found"
        # Build case-insensitive field map
        fields = [field.strip() for field in header_line.split(",")]
        field_map: dict[str, int] = {field.lower(): i for i, field in enumerate(fields)}
        # Required fields
        idx_offset = field_map.get("offset")
        idx_midi = field_map.get("midinote") or field_map.get("midi")
        idx_duration = field_map.get("duration")
        idx_track = field_map.get("track")
        assert idx_offset is not None, f"Missing 'offset' column. Found: {fields}"
        assert idx_midi is not None, f"Missing 'midiNote' or 'midi' column. Found: {fields}"
        assert idx_duration is not None, f"Missing 'duration' column. Found: {fields}"
        # Read data lines
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            values = stripped.split(",")
            note_track = int(values[idx_track]) if idx_track is not None else 0
            raw_dur = Fraction(values[idx_duration]).limit_denominator(64)
            notes.append({
                "offset": float(values[idx_offset]),
                "midi": int(values[idx_midi]),
                "duration": quantize_duration(raw_dur),
                "track": note_track,
            })

    assert notes, "No notes found in file"

    # Filter by track
    tracks_present = sorted(set(n["track"] for n in notes))
    if track is None:
        track = tracks_present[0]
    notes = [n for n in notes if n["track"] == track]
    notes.sort(key=lambda n: n["offset"])

    assert notes, f"No notes found for track {track}"

    # Convert MIDI to degrees
    key_obj = Key(tonic, mode)
    base_midi = notes[0]["midi"]
    base_octave = base_midi // 12

    degrees: list[int] = []
    durations: list[str] = []

    for n in notes:
        midi = n["midi"]
        octave = midi // 12
        degree = key_obj.midi_to_degree(midi)
        # Adjust for octave relative to base
        octave_offset = octave - base_octave
        adjusted_degree = degree + (octave_offset * 7)
        degrees.append(adjusted_degree)
        durations.append(str(n["duration"]))

    # Write YAML
    output_path = note_path.with_suffix(".subject")
    lines = [
        f"# Subject extracted from {note_path.name}",
        f"source_tonic: {tonic}",
        f"mode: {mode}",
        f"degrees: {degrees}",
        f"durations: [{', '.join(durations)}]",
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(degrees)} notes to {output_path}")


def main() -> None:
    """Convert .note to .subject format."""
    if len(sys.argv) < 2:
        print("Usage: python note_to_subject.py <note_file> [tonic] [mode] [track]")
        print("  tonic: C, D, E, F, G, A, B (default: C)")
        print("  mode: major, minor (default: major)")
        print("  track: track number to extract (default: first track)")
        sys.exit(1)

    note_path = Path(sys.argv[1])
    assert note_path.exists(), f"File not found: {note_path}"

    tonic = sys.argv[2] if len(sys.argv) > 2 else "C"
    mode = sys.argv[3] if len(sys.argv) > 3 else "major"
    track = int(sys.argv[4]) if len(sys.argv) > 4 else None

    convert_note_to_subject(note_path, tonic, mode, track)


if __name__ == "__main__":
    main()

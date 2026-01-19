"""Convert .note CSV file to MIDI format."""
import csv
import sys
from pathlib import Path

from mido import Message, MidiFile, MidiTrack, MetaMessage


def convert_note_to_midi(note_path: Path) -> None:
    """Convert .note CSV file to MIDI file."""
    # Read notes from CSV, skipping comment lines
    notes: list[dict] = []
    with open(note_path, encoding="utf-8") as f:
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
        # Required fields (case-insensitive lookup)
        idx_offset = field_map.get("offset")
        idx_midi = field_map.get("midinote")
        idx_duration = field_map.get("duration")
        idx_track = field_map.get("track")
        assert idx_offset is not None, f"Missing 'offset' column. Found: {fields}"
        assert idx_midi is not None, f"Missing 'midiNote' column. Found: {fields}"
        assert idx_duration is not None, f"Missing 'duration' column. Found: {fields}"
        assert idx_track is not None, f"Missing 'track' column. Found: {fields}"
        # Read data lines
        for line in f:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                continue
            values = stripped.split(",")
            notes.append({
                "offset": float(values[idx_offset]),
                "midi_num": int(values[idx_midi]),
                "duration": float(values[idx_duration]),
                "track": int(values[idx_track]),
            })

    if not notes:
        print("No notes found in file")
        return

    # Find unique tracks
    tracks_used = sorted(set(n["track"] for n in notes))
    track_map = {t: i for i, t in enumerate(tracks_used)}

    # Create MIDI file
    mid = MidiFile(ticks_per_beat=480)

    # Create tracks
    for _ in tracks_used:
        track = MidiTrack()
        mid.tracks.append(track)

    # Convert notes to MIDI events per track
    for track_num in tracks_used:
        track_notes = [n for n in notes if n["track"] == track_num]
        track = mid.tracks[track_map[track_num]]

        # Add tempo (120 BPM)
        if track_map[track_num] == 0:
            track.append(MetaMessage("set_tempo", tempo=500000, time=0))

        # Create events (note_on and note_off)
        events: list[tuple[int, str, int, int]] = []
        for n in track_notes:
            start_tick = int(n["offset"] * 480)
            end_tick = int((n["offset"] + n["duration"]) * 480)
            events.append((start_tick, "note_on", n["midi_num"], 64))
            events.append((end_tick, "note_off", n["midi_num"], 0))

        # Sort by time
        events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))

        # Convert to delta times
        prev_tick = 0
        for tick, msg_type, note, vel in events:
            delta = tick - prev_tick
            if msg_type == "note_on":
                track.append(Message("note_on", note=note, velocity=vel, time=delta))
            else:
                track.append(Message("note_off", note=note, velocity=0, time=delta))
            prev_tick = tick

    # Write MIDI file
    output_path = note_path.with_suffix(".midi")
    mid.save(str(output_path))
    print(f"Wrote {len(notes)} notes to {output_path}")


def main() -> None:
    """Convert .note to MIDI format."""
    if len(sys.argv) < 2:
        print("Usage: python note_to_midi.py <note_file>")
        sys.exit(1)

    note_path = Path(sys.argv[1])
    if not note_path.exists():
        print(f"File not found: {note_path}")
        sys.exit(1)

    convert_note_to_midi(note_path)


if __name__ == "__main__":
    main()

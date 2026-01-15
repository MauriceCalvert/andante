"""Convert .note CSV file to MIDI format."""
import csv
import sys
from pathlib import Path

from mido import Message, MidiFile, MidiTrack, MetaMessage


def convert_note_to_midi(note_path: Path) -> None:
    """Convert .note CSV file to MIDI file."""
    # Read notes from CSV
    notes: list[dict] = []
    with open(note_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            notes.append({
                "offset": float(row["Offset"]),
                "midi_num": int(row["midiNote"]),
                "duration": float(row["Duration"]),
                "track": int(row["track"]),
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

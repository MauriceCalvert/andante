"""Convert MIDI file to .note CSV format."""
import sys
from fractions import Fraction
from pathlib import Path

from io import BytesIO

from mido import MidiFile

from shared.constants import VALID_DURATIONS_SORTED
from shared.pitch import midi_to_name as midi_to_note_name


# MIDI meta-event: FF 59 02 sf mode  (key signature)
KEY_SIG_META_TYPE = 0x59
KEY_SIG_LENGTH = 0x02


def _sanitise_midi_bytes(data: bytearray) -> bytearray:
    """Fix corrupt key-signature mode bytes in raw MIDI data."""
    i = 0
    while i < len(data) - 4:
        if (data[i] == 0xFF
                and data[i + 1] == KEY_SIG_META_TYPE
                and data[i + 2] == KEY_SIG_LENGTH):
            mode_byte = data[i + 4]
            if mode_byte not in (0, 1):
                data[i + 4] = 0  # default to major
        i += 1
    return data


def quantize_duration(duration: float) -> Fraction:
    """Quantize duration (in beats) to nearest valid note value."""
    dur_frac = Fraction(duration).limit_denominator(64)
    best: Fraction = VALID_DURATIONS_SORTED[0]
    best_diff: float = abs(float(dur_frac) - float(best))
    for valid in VALID_DURATIONS_SORTED:
        diff = abs(float(dur_frac) - float(valid))
        if diff < best_diff:
            best = valid
            best_diff = diff
    return best


def convert_midi_to_note(midi_path: Path) -> None:
    """Convert MIDI file to .note CSV file."""
    raw: bytearray = bytearray(midi_path.read_bytes())
    raw = _sanitise_midi_bytes(data=raw)
    mid = MidiFile(file=BytesIO(raw))
    ticks_per_beat = mid.ticks_per_beat

    # Collect all note events per track
    notes: list[dict] = []

    for track_idx, track in enumerate(mid.tracks):
        abs_time = 0
        active_notes: dict[int, tuple[int, int]] = {}  # midi_num -> (start_tick, velocity)

        for msg in track:
            abs_time += msg.time
            if msg.type == "note_on" and msg.velocity > 0:
                active_notes[msg.note] = (abs_time, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active_notes:
                    start_tick, velocity = active_notes.pop(msg.note)
                    duration_ticks = abs_time - start_tick
                    notes.append({
                        "start_tick": start_tick,
                        "midi_num": msg.note,
                        "duration_ticks": duration_ticks,
                        "track": track_idx,
                    })

    # Sort by start time, then by pitch (descending for same time)
    notes.sort(key=lambda n: (n["start_tick"], -n["midi_num"]))

    # Convert ticks to bars (assuming 4/4 time: 4 beats per bar)
    beats_per_bar = 4
    output_lines = ["offset,midinote,duration,track,length,bar,beat,notename,lyric"]

    for n in notes:
        offset_beats = n["start_tick"] / ticks_per_beat
        offset_bars = offset_beats / beats_per_bar
        raw_duration_beats = n["duration_ticks"] / ticks_per_beat
        raw_duration_bars = raw_duration_beats / beats_per_bar
        duration = quantize_duration(duration=raw_duration_bars)
        midi_num = n["midi_num"]
        track = n["track"]
        note_name = midi_to_note_name(midi=midi_num)

        # Calculate bar and beat (bar 1-indexed)
        bar = int(offset_beats // beats_per_bar) + 1
        beat = (offset_beats % beats_per_bar) + 1

        output_lines.append(
            f"{offset_bars},{midi_num},{duration},{track},,{bar},{beat},{note_name},"
        )

    # Write output
    output_path = midi_path.with_suffix(".note")
    output_path.write_text("\n".join(output_lines), encoding="utf-8")
    print(f"Wrote {len(notes)} notes to {output_path}")


def main() -> None:
    """Convert MIDI to .note format."""
    if len(sys.argv) < 2:
        print("Usage: python midi_to_note.py <midi_file_or_directory>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Path not found: {path}")
        sys.exit(1)

    if path.is_dir():
        midi_files = list(path.glob("*.mid")) + list(path.glob("*.midi"))
        if not midi_files:
            print(f"No MIDI files found in {path}")
            sys.exit(1)
        for midi_path in sorted(midi_files):
            convert_midi_to_note(midi_path=midi_path)
    else:
        convert_midi_to_note(midi_path=path)


if __name__ == "__main__":
    main()

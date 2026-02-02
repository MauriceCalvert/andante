"""Debug script to examine bar 10 key context."""
from pathlib import Path
import yaml

from builder.faults import find_faults, print_faults
from builder.types import Composition
from planner.planner import generate_to_files
from shared.tracer import get_tracer, reset_tracer, set_trace_level


def main() -> None:
    reset_tracer()
    set_trace_level(3)
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    result = generate_to_files("gavotte", "default", output_dir, "debug_run", "g_major")
    for vid, vnotes in result.voices.items():
        print(f"\n{vid}: {len(vnotes)} notes")
    print(f"\n=== Notes around bar 10 ===\n")
    bar_duration = 1.0  # 4/4 = 1 whole note per bar
    bar_10_start = 9 * bar_duration
    bar_11_end = 11 * bar_duration
    for vid, vnotes in result.voices.items():
        print(f"{vid.upper()}:")
        for note in vnotes:
            if bar_10_start - bar_duration <= float(note.offset) <= bar_11_end:
                pc = note.pitch % 12
                bar = int(float(note.offset) / bar_duration) + 1
                beat = (float(note.offset) % bar_duration) / 0.25 + 1
                print(f"  {bar}.{beat:.1f}: MIDI {note.pitch} (pc={pc})")
    print("\n=== Faults ===\n")
    faults = find_faults(list(result.voices.values()), result.metre)
    for f in faults:
        if "10" in f.bar_beat:
            print(f"[{f.bar_beat}] {f.category}: {f.message}")
    get_tracer().write_to_file(output_dir / "debug_trace.txt")
    print(f"\nFull trace written to {output_dir / 'debug_trace.txt'}")


if __name__ == "__main__":
    main()

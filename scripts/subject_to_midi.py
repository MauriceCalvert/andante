"""Convert .subject YAML file to MIDI format."""
import sys
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import yaml

from shared.midi_writer import write_midi

MAJOR_INTERVALS = (0, 2, 4, 5, 7, 9, 11)
MINOR_INTERVALS = (0, 2, 3, 5, 7, 8, 10)
TONIC_TO_MIDI = {
    'C': 60, 'C#': 61, 'Db': 61, 'D': 62, 'D#': 63, 'Eb': 63,
    'E': 64, 'F': 65, 'F#': 66, 'Gb': 66, 'G': 67, 'G#': 68,
    'Ab': 68, 'A': 69, 'A#': 70, 'Bb': 70, 'B': 71,
}


def degrees_to_midi(
    degrees: Sequence[int],
    tonic: str = 'G',
    mode: str = 'major',
    start_octave: int = 4,
) -> list[int]:
    """Convert degrees to MIDI, choosing octave to minimise leaps."""
    intervals = MAJOR_INTERVALS if mode == 'major' else MINOR_INTERVALS
    base = TONIC_TO_MIDI[tonic]
    pitches: list[int] = []
    prev: int = base + (start_octave - 4) * 12
    for deg in degrees:
        assert 1 <= deg <= 7, f"Degree must be 1-7, got {deg}"
        interval = intervals[deg - 1]
        candidate = (prev // 12) * 12 + (base % 12) + interval
        options = [candidate - 12, candidate, candidate + 12]
        best = min(options, key=lambda p: abs(p - prev))
        pitches.append(best)
        prev = best
    return pitches


def parse_duration(d: str | float | int) -> float:
    """Parse duration string (e.g., '1/8') to float."""
    if isinstance(d, (int, float)):
        return float(d)
    return float(Fraction(d))


def convert_subject_to_midi(
    subject_path: Path,
    tonic: str = 'G',
    mode: str = 'major',
    octave: int = 4,
) -> None:
    """Convert .subject file to MIDI."""
    with open(subject_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert 'durations' in data, "Subject file must have 'durations' field"
    durations: list[float] = [parse_duration(d) for d in data['durations']]
    if 'pitches' in data:
        pitches: list[int] = data['pitches']
    elif 'degrees' in data:
        degrees: list[int] = data['degrees']
        pitches = degrees_to_midi(degrees, tonic, mode, octave)
    else:
        raise ValueError("Subject file must have 'pitches' or 'degrees' field")
    assert len(pitches) == len(durations), "pitches/degrees and durations must match"
    output_path = subject_path.with_suffix('.midi')
    write_midi(
        str(output_path),
        pitches,
        durations,
        tempo=90,
        tonic=tonic,
        mode=mode,
    )
    print(f"Wrote {len(pitches)} notes to {output_path}")


def main() -> None:
    """Convert .subject to MIDI."""
    if len(sys.argv) < 2:
        print("Usage: python subject_to_midi.py <subject_file> [key] [mode] [octave]")
        print("  key: C, D, Eb, F#, G, etc. (default: G)")
        print("  mode: major, minor (default: major)")
        print("  octave: 3, 4, 5 (default: 4)")
        sys.exit(1)
    subject_path = Path(sys.argv[1])
    if not subject_path.exists():
        print(f"File not found: {subject_path}")
        sys.exit(1)
    key = sys.argv[2] if len(sys.argv) > 2 else 'G'
    mode = sys.argv[3] if len(sys.argv) > 3 else 'major'
    octave = int(sys.argv[4]) if len(sys.argv) > 4 else 4
    convert_subject_to_midi(subject_path, key, mode, octave)


if __name__ == "__main__":
    main()

"""Convert .subject YAML file to MIDI format."""
import argparse
import sys
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import yaml

from shared.constants import MAJOR_SCALE, NATURAL_MINOR_SCALE, TONIC_TO_MIDI
from shared.midi_writer import write_midi


def degrees_to_midi(
    degrees: Sequence[int],
    tonic: str,
    mode: str,
    start_octave: int = 4,
) -> list[int]:
    """Convert degrees to MIDI, choosing octave to minimise leaps."""
    assert tonic in TONIC_TO_MIDI, f"Unknown tonic: {tonic}"
    assert mode in ('major', 'minor'), f"Mode must be 'major' or 'minor', got {mode}"
    intervals = MAJOR_SCALE if mode == 'major' else NATURAL_MINOR_SCALE
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
    tonic: str,
    mode: str,
    tempo: int,
    octave: int = 4,
) -> None:
    """Convert .subject file to MIDI."""
    with open(subject_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    assert 'durations' in data, "Subject file must have 'durations' field"
    durations: list[float] = [parse_duration(d=d) for d in data['durations']]
    if 'pitches' in data:
        pitches: list[int] = data['pitches']
    elif 'degrees' in data:
        degrees: list[int] = data['degrees']
        pitches = degrees_to_midi(degrees=degrees, tonic=tonic, mode=mode, start_octave=octave)
    else:
        raise ValueError("Subject file must have 'pitches' or 'degrees' field")
    assert len(pitches) == len(durations), "pitches/degrees and durations must match"
    output_path = subject_path.with_suffix('.midi')
    write_midi(
        path=str(output_path),
        pitches=pitches,
        durations=durations,
        tempo=tempo,
        tonic=tonic,
        mode=mode,
    )
    print(f"Wrote {len(pitches)} notes to {output_path}")


def main() -> None:
    """Convert .subject to MIDI."""
    parser = argparse.ArgumentParser(description='Convert .subject YAML to MIDI')
    parser.add_argument('subject_file', type=Path, help='Path to .subject file')
    parser.add_argument('--tonic', '-k', type=str, help='Tonic (C, D, Eb, F#, G, etc.)')
    parser.add_argument('--mode', '-m', type=str, choices=['major', 'minor'], help='Mode')
    parser.add_argument('--tempo', '-t', type=int, help='Tempo in BPM')
    parser.add_argument('--octave', '-o', type=int, default=4, help='Starting octave (default: 4)')
    args = parser.parse_args()
    if not args.subject_file.exists():
        print(f"File not found: {args.subject_file}")
        sys.exit(1)
    with open(args.subject_file, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    tonic = args.tonic or data.get('tonic')
    mode = args.mode or data.get('mode')
    tempo = args.tempo or data.get('tempo')
    assert tonic is not None, "tonic must be specified in YAML or via --tonic"
    assert mode is not None, "mode must be specified in YAML or via --mode"
    assert tempo is not None, "tempo must be specified in YAML or via --tempo"
    convert_subject_to_midi(subject_path=args.subject_file, tonic=tonic, mode=mode, tempo=tempo, octave=args.octave)


if __name__ == "__main__":
    main()

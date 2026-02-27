"""Episode kernel demo -- soprano-only sequential patterns from subject material.

Generates MIDI files demonstrating kernel extraction and sequential
transposition for each subject in the motifs library.

Usage:
    python -m scripts.episode_kernel_demo [--subject NAME] [-o OUTPUT_DIR]
"""
from __future__ import annotations

import argparse
import logging
import sys
from fractions import Fraction
from pathlib import Path

from motifs.fragen import Kernel, Note, extract_kernels, sequence_kernel
from motifs.head_generator import degrees_to_midi
from motifs.subject_loader import SubjectTriple, list_triples, load_triple
from shared.midi_writer import SimpleNote, write_midi_notes

logging.basicConfig(level=logging.WARNING)
_log: logging.Logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT_DIR: str = "output"
_DEFAULT_START_DEGREE: int = 7    # one octave above tonic
_DEFAULT_ITERATIONS: int = 5
_SILENCE_BEATS: Fraction = Fraction(1, 4)  # 1 crotchet silence between sections
_DEFAULT_TEMPO: int = 100
_DEFAULT_VELOCITY: int = 80


def _contour_label(degrees: tuple[int, ...]) -> str:
    """Classify kernel contour as ascending/descending/mixed."""
    if len(degrees) < 2:
        return "static"
    ups: int = sum(1 for i in range(len(degrees) - 1) if degrees[i + 1] > degrees[i])
    downs: int = sum(1 for i in range(len(degrees) - 1) if degrees[i + 1] < degrees[i])
    if ups > 0 and downs == 0:
        return "ascending"
    if downs > 0 and ups == 0:
        return "descending"
    return "mixed"


def _generate_subject_midi(
    triple: SubjectTriple,
    subject_name: str,
    output_dir: Path,
) -> None:
    """Generate kernel demo MIDI for one subject."""
    name: str = subject_name
    tonic_midi: int = triple.tonic_midi
    mode: str = triple.subject.mode
    metre: tuple[int, int] = triple.metre

    kernels: list[Kernel] = extract_kernels(fugue=triple)
    if not kernels:
        print(f"  No kernels extracted for {name}")
        return

    # Print summary table header
    print(f"\n  {'Name':<30} {'Source':<12} {'Notes':>5} {'Duration':>10} {'Contour':<12}")
    print(f"  {'-'*30} {'-'*12} {'-'*5} {'-'*10} {'-'*12}")

    all_midi_notes: list[SimpleNote] = []
    cursor: Fraction = Fraction(0)

    for kernel in kernels:
        # Print summary row
        dur_str: str = str(kernel.total_duration)
        print(
            f"  {kernel.name:<30} {kernel.source:<12} "
            f"{len(kernel.degrees):>5} {dur_str:>10} "
            f"{_contour_label(degrees=kernel.degrees):<12}"
        )

        # Generate descending and ascending sequences
        for step, direction in ((-1, "desc"), (1, "asc")):
            notes: list[Note] = sequence_kernel(
                kernel=kernel,
                start_degree=_DEFAULT_START_DEGREE,
                step=step,
                iterations=_DEFAULT_ITERATIONS,
                voice=0,
            )
            for note in notes:
                midi_pitches: tuple[int, ...] = degrees_to_midi(
                    degrees=(note.degree,),
                    tonic_midi=tonic_midi,
                    mode=mode,
                )
                midi_pitch: int = midi_pitches[0]
                # Clamp to valid MIDI range
                if midi_pitch < 0 or midi_pitch > 127:
                    continue
                all_midi_notes.append(SimpleNote(
                    pitch=midi_pitch,
                    offset=float(cursor + note.offset),
                    duration=float(note.duration),
                    velocity=_DEFAULT_VELOCITY,
                    track=0,
                ))

            # Advance cursor past this sequence + silence gap
            seq_duration: Fraction = _DEFAULT_ITERATIONS * kernel.total_duration
            cursor += seq_duration + _SILENCE_BEATS

    if not all_midi_notes:
        print(f"  No valid MIDI notes generated for {name}")
        return

    # Find subject file stem for output naming
    out_path: Path = output_dir / f"episode_kernels_{name}.mid"
    success: bool = write_midi_notes(
        path=str(out_path),
        notes=all_midi_notes,
        tempo=_DEFAULT_TEMPO,
        time_signature=metre,
        tonic=triple.tonic,
        mode=mode,
    )
    if success:
        print(f"\n  -> {out_path}  ({len(kernels)} kernels, {len(all_midi_notes)} notes)")
    else:
        print(f"\n  -> FAILED to write {out_path} (mido not available?)")


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Episode kernel demo: soprano-only sequential patterns",
    )
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help="Subject name to process (default: all subjects in library)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=_DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {_DEFAULT_OUTPUT_DIR})",
    )
    args: argparse.Namespace = parser.parse_args()

    output_dir: Path = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.subject is not None:
        subjects: list[str] = [args.subject]
    else:
        subjects = sorted(list_triples())

    assert len(subjects) > 0, "No subjects found in library"

    for subject_name in subjects:
        print(f"\n{'='*70}")
        print(f"Subject: {subject_name}")
        print(f"{'='*70}")
        triple: SubjectTriple = load_triple(name=subject_name)
        _generate_subject_midi(triple=triple, subject_name=subject_name, output_dir=output_dir)

    print(f"\nDone. {len(subjects)} subject(s) processed.")


if __name__ == "__main__":
    main()

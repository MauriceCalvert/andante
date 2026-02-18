"""Archetype sampler: generates one fugue triple per archetype and writes MIDI files.

Calls the generation chain directly (kopfmotiv → fortspinnung → kadenz →
validate → analyse_answer) for each of the six archetypes using their natural
affect/mode/metre, then writes individual MIDI + .fugue files and a combined
sampler MIDI that plays all six back-to-back.

Run from the andante directory as:
    python -m scripts.archetype_sampler
"""
import random
from fractions import Fraction
from pathlib import Path

from motifs.answer_generator import generate_answer
from motifs.archetype_types import load_archetype
from motifs.countersubject_generator import generate_countersubject
from motifs.fortspinnung import generate_fortspinnung
from motifs.head_generator import degrees_to_midi
from motifs.kadenz import generate_kadenz
from motifs.kopfmotiv import generate_kopfmotiv
from motifs.melodic_validator import validate_melody
from motifs.subject_generator import (
    FugueTriple,
    GeneratedSubject,
    write_fugue_demo_midi,
    write_fugue_file,
)
from shared.midi_writer import SimpleNote, write_midi_notes


# ---------------------------------------------------------------------------
# Archetype configuration table
# (name, affect, mode, metre, tonic_name, direction)
# ---------------------------------------------------------------------------

_TONIC_MIDI: dict[str, int] = {
    "C": 60, "D": 62, "E": 64, "F": 65, "G": 67, "A": 69, "B": 71,
}

# Each entry: (archetype_name, affect, mode, metre, tonic_name, direction)
_CONFIGS: tuple[tuple[str, str, str, tuple[int, int], str, str], ...] = (
    ("scalar",    "Majestaet",        "major", (4, 4), "C", "ascending"),
    ("triadic",   "Zaertlichkeit",    "major", (4, 4), "G", "ascending"),
    ("chromatic", "Klage",            "minor", (4, 4), "C", "descending"),
    ("rhythmic",  "Entschlossenheit", "major", (4, 4), "D", "ascending"),
    ("compound",  "Majestaet",        "minor", (4, 4), "G", "descending"),
    ("dance",     "Freudigkeit",      "major", (3, 4), "F", "ascending"),
)

_MAX_ATTEMPTS: int = 200
_SEED: int = 42
_TEMPO: int = 80
_MIN_KADENZ: Fraction = Fraction(1, 2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _bar_duration_float(metre: tuple[int, int]) -> float:
    """Bar duration in whole-note units as float."""
    return metre[0] / metre[1]


def _collect_demo_notes(
    triple: FugueTriple,
    start_offset: float,
) -> tuple[list[SimpleNote], float]:
    """Collect SimpleNote objects for a triple's demo sequence.

    Replicates write_fugue_demo_midi's 6-section layout:
      1. Subject alone
      2. Answer alone
      3. CS alone
      4. Subject + CS (polyphonic, CS one octave lower)
      5. Answer + CS (polyphonic, CS one octave lower)
      6. CS + Subject again (polyphonic, CS one octave lower)

    Returns collected notes and the end offset (exclusive of trailing silence).
    """
    bar_dur: float = _bar_duration_float(triple.metre)
    notes: list[SimpleNote] = []
    offset: float = start_offset

    def add_melody(
        pitches: tuple[int, ...],
        durations: tuple[float, ...],
        track: int,
        start: float,
    ) -> float:
        """Add notes; return offset after last note."""
        pos: float = start
        for pitch, dur in zip(pitches, durations):
            notes.append(
                SimpleNote(pitch=pitch, offset=pos, duration=dur, velocity=80, track=track)
            )
            pos += dur
        return pos

    subj_pitches: tuple[int, ...] = triple.subject.midi_pitches
    subj_dur: tuple[float, ...] = triple.subject.durations
    ans_pitches: tuple[int, ...] = triple.answer.midi_pitches
    ans_dur: tuple[float, ...] = triple.answer.durations
    cs_pitches: tuple[int, ...] = triple.countersubject.midi_pitches
    cs_dur: tuple[float, ...] = triple.countersubject.durations
    cs_pitches_low: tuple[int, ...] = tuple(p - 12 for p in cs_pitches)

    # 1. Subject alone
    offset = add_melody(subj_pitches, subj_dur, 0, offset)
    offset += bar_dur

    # 2. Answer alone
    offset = add_melody(ans_pitches, ans_dur, 0, offset)
    offset += bar_dur

    # 3. CS alone
    offset = add_melody(cs_pitches, cs_dur, 0, offset)
    offset += bar_dur

    # 4. Subject + CS polyphonic
    subj_end: float = add_melody(subj_pitches, subj_dur, 0, offset)
    add_melody(cs_pitches_low, cs_dur, 1, offset)
    offset = subj_end + bar_dur

    # 5. Answer + CS polyphonic
    ans_end: float = add_melody(ans_pitches, ans_dur, 0, offset)
    add_melody(cs_pitches_low, cs_dur, 1, offset)
    offset = ans_end + bar_dur

    # 6. CS + Subject polyphonic (mirror of section 4)
    subj_end2: float = add_melody(subj_pitches, subj_dur, 0, offset)
    cs_end2: float = add_melody(cs_pitches_low, cs_dur, 1, offset)
    end_offset: float = max(subj_end2, cs_end2)

    return notes, end_offset


# ---------------------------------------------------------------------------
# Per-archetype generation
# ---------------------------------------------------------------------------

def _generate_triple(
    name: str,
    affect: str,
    mode: str,
    metre: tuple[int, int],
    tonic_name: str,
    direction: str,
) -> FugueTriple | None:
    """Generate a fugue triple for the given archetype configuration.

    Uses a private Random(42) per archetype for independence.
    Tries target bar counts [2, 1, 3, 4] to accommodate gestures of various sizes.
    Returns None (with a printed warning) if all _MAX_ATTEMPTS fail.
    """
    from motifs.answer_analyser import analyse_answer

    tonic_midi: int = _TONIC_MIDI[tonic_name]
    archetype = load_archetype(name)
    rng: random.Random = random.Random(_SEED)

    bar_dur: Fraction = Fraction(metre[0], metre[1])

    for _attempt in range(_MAX_ATTEMPTS):
        for target_bars in [2, 1, 3, 4]:
            total_beats_frac: Fraction = Fraction(target_bars) * bar_dur
            total_beats: float = float(total_beats_frac)

            # Step 1: Kopfmotiv
            head = generate_kopfmotiv(
                archetype, direction, total_beats, mode, metre, affect, rng
            )
            if head is None:
                continue

            # Step 2: Fortspinnung
            cont_budget: Fraction = total_beats_frac - head.beats_used - _MIN_KADENZ
            if cont_budget <= Fraction(0):
                continue
            body = generate_fortspinnung(head, archetype, cont_budget, mode, metre, affect, rng)
            if body is None:
                continue

            # Step 3: Kadenz
            result = generate_kadenz(body, archetype, metre, affect, rng)
            if result is None:
                continue

            # Step 4: Melodic validation
            validation = validate_melody(result.degrees, result.durations, mode)
            if not validation.valid:
                continue

            # Step 5: Answer feasibility
            answer_analysis = analyse_answer(result.degrees, result.durations, metre, mode)
            if not answer_analysis.feasible:
                continue

            # Build chromatic offsets from head's chromatic_inflections if present
            chromatic_offsets: tuple[int, ...] | None = None
            if head.chromatic_inflections is not None:
                direction_offset: int = -1 if head.direction == "descending" else 1
                offsets_list: list[int] = [0] * len(result.degrees)
                for idx in head.chromatic_inflections:
                    if idx < len(offsets_list):
                        offsets_list[idx] = direction_offset
                chromatic_offsets = tuple(offsets_list)

            # Assemble GeneratedSubject
            float_durations: tuple[float, ...] = tuple(float(d) for d in result.durations)
            midi_pitches: tuple[int, ...] = degrees_to_midi(
                result.degrees, tonic_midi, mode, chromatic_offsets
            )

            head_length: int = len(head.degrees)
            head_intervals: list[int] = [
                result.degrees[i + 1] - result.degrees[i]
                for i in range(head_length - 1)
            ]
            max_leap: int = max((abs(iv) for iv in head_intervals), default=0)

            subject = GeneratedSubject(
                scale_indices=result.degrees,
                durations=float_durations,
                midi_pitches=midi_pitches,
                bars=result.n_bars,
                score=0.0,
                seed=_SEED,
                mode=mode,
                head_name=name,
                leap_size=max_leap,
                leap_direction=direction,
                tail_direction="descending" if direction == "ascending" else "ascending",
                affect=affect,
                figurae_score=0.0,
                archetype=name,
                direction=direction,
            )

            answer = generate_answer(subject=subject, tonic_midi=tonic_midi)

            try:
                cs = generate_countersubject(
                    subject=subject,
                    metre=metre,
                    tonic_midi=tonic_midi,
                    answer_degrees=answer.scale_indices,
                )
            except Exception:
                continue
            if cs is None:
                continue

            return FugueTriple(
                subject=subject,
                answer=answer,
                countersubject=cs,
                metre=metre,
                tonic_midi=tonic_midi,
                seed=_SEED,
            )

    print(f"WARNING: [{name}] failed after {_MAX_ATTEMPTS} attempts — skipping.")
    return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate one fugue triple per archetype; write individual and combined MIDI."""
    samples_dir: Path = Path("samples")
    samples_dir.mkdir(exist_ok=True)

    triples: list[tuple[str, FugueTriple]] = []

    for name, affect, mode, metre, tonic_name, direction in _CONFIGS:
        triple = _generate_triple(name, affect, mode, metre, tonic_name, direction)
        if triple is None:
            continue

        # Console output
        print(
            f"[{name}] {affect} {mode} {metre[0]}/{metre[1]} {tonic_name} — "
            f"degrees: {triple.subject.scale_indices} — "
            f"{triple.subject.bars} bars — "
            f"direction: {direction}"
        )

        # Individual MIDI + .fugue
        base: Path = samples_dir / f"{name}_{affect}_{mode}"
        write_fugue_demo_midi(triple=triple, path=base.with_suffix(".midi"), tempo=_TEMPO)
        write_fugue_file(triple=triple, path=base.with_suffix(".fugue"))

        triples.append((name, triple))

    # Combined sampler MIDI: all demo sequences back-to-back with 2-bar silence
    all_notes: list[SimpleNote] = []
    accumulated: float = 0.0

    for _name, triple in triples:
        demo_notes, end_offset = _collect_demo_notes(triple, start_offset=accumulated)
        all_notes.extend(demo_notes)
        # 2 bars of silence after each archetype
        accumulated = end_offset + 2.0 * _bar_duration_float(triple.metre)

    sampler_path: Path = samples_dir / "archetype_sampler.midi"
    write_midi_notes(
        path=str(sampler_path),
        notes=all_notes,
        tempo=_TEMPO,
        time_signature=(4, 4),
    )

    n_individual: int = len(triples)
    print(f"Wrote {n_individual} individual MIDIs + archetype_sampler.midi to samples/")


if __name__ == "__main__":
    main()

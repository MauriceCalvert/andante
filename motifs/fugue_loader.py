"""Fugue file loader.

Loads .fugue YAML files containing pre-composed subject, answer, and countersubject.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

import yaml

from motifs.head_generator import degrees_to_midi


LIBRARY_DIR = Path(__file__).parent / "library"


@dataclass(frozen=True)
class LoadedSubject:
    """Subject loaded from .fugue file."""
    degrees: Tuple[int, ...]
    durations: Tuple[float, ...]
    mode: str
    bars: int
    head_name: str
    leap_size: int
    leap_direction: str


@dataclass(frozen=True)
class LoadedAnswer:
    """Answer loaded from .fugue file."""
    degrees: Tuple[int, ...]
    durations: Tuple[float, ...]
    answer_type: str
    mutation_points: Tuple[int, ...]


@dataclass(frozen=True)
class LoadedCountersubject:
    """Countersubject loaded from .fugue file."""
    degrees: Tuple[int, ...]
    durations: Tuple[float, ...]
    vertical_intervals: Tuple[int, ...]


@dataclass(frozen=True)
class LoadedFugue:
    """Complete fugue triple loaded from file."""
    subject: LoadedSubject
    answer: LoadedAnswer
    countersubject: LoadedCountersubject
    metre: Tuple[int, int]
    tonic: str
    tonic_midi: int
    seed: int

    def subject_midi(self, tonic_midi: int | None = None) -> Tuple[int, ...]:
        """Get subject as MIDI pitches."""
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        return degrees_to_midi(
            degrees=self.subject.degrees,
            tonic_midi=midi,
            mode=self.subject.mode,
        )

    def answer_midi(self, tonic_midi: int | None = None) -> Tuple[int, ...]:
        """Get answer as MIDI pitches (in dominant key)."""
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        dominant_midi = midi + 7
        return degrees_to_midi(
            degrees=self.answer.degrees,
            tonic_midi=dominant_midi,
            mode=self.subject.mode,
        )

    def countersubject_midi(self, tonic_midi: int | None = None) -> Tuple[int, ...]:
        """Get countersubject as MIDI pitches."""
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        return degrees_to_midi(
            degrees=self.countersubject.degrees,
            tonic_midi=midi,
            mode=self.subject.mode,
        )


def load_fugue(name: str) -> LoadedFugue:
    """Load a fugue triple from the library by name."""
    if name.endswith(".fugue"):
        name = name[:-6]
    path = LIBRARY_DIR / f"{name}.fugue"
    assert path.exists(), f"Fugue file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    subj_data = data["subject"]
    ans_data = data["answer"]
    cs_data = data["countersubject"]
    meta = data["metadata"]
    subject = LoadedSubject(
        degrees=tuple(subj_data["degrees"]),
        durations=tuple(subj_data["durations"]),
        mode=subj_data["mode"],
        bars=subj_data["bars"],
        head_name=subj_data["head_name"],
        leap_size=subj_data["leap_size"],
        leap_direction=subj_data["leap_direction"],
    )
    answer = LoadedAnswer(
        degrees=tuple(ans_data["degrees"]),
        durations=tuple(ans_data["durations"]),
        answer_type=ans_data["type"],
        mutation_points=tuple(ans_data["mutation_points"]),
    )
    countersubject = LoadedCountersubject(
        degrees=tuple(cs_data["degrees"]),
        durations=tuple(cs_data["durations"]),
        vertical_intervals=tuple(cs_data["vertical_intervals"]),
    )
    return LoadedFugue(
        subject=subject,
        answer=answer,
        countersubject=countersubject,
        metre=tuple(meta["metre"]),
        tonic=meta["tonic"],
        tonic_midi=meta["tonic_midi"],
        seed=meta["seed"],
    )


def list_fugues() -> list[str]:
    """List available fugue names in the library."""
    return [p.stem for p in LIBRARY_DIR.glob("*.fugue")]

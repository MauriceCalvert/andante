"""Fugue file loader.

Loads .fugue YAML files containing pre-composed subject, answer, and countersubject.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from motifs.head_generator import degrees_to_midi

LIBRARY_DIR = Path(__file__).parent / "library"

@dataclass(frozen=True)
class LoadedSubject:
    """Subject loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    mode: str
    bars: int
    head_name: str
    leap_size: int
    leap_direction: str

@dataclass(frozen=True)
class LoadedAnswer:
    """Answer loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    answer_type: str
    mutation_points: tuple[int, ...]

@dataclass(frozen=True)
class LoadedCountersubject:
    """Countersubject loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    vertical_intervals: tuple[int, ...]

@dataclass(frozen=True)
class LoadedStretto:
    """One viable stretto offset from .fugue file."""
    offset_slots: int
    quality: float

@dataclass(frozen=True)
class LoadedFugue:
    """Complete fugue triple loaded from file."""
    subject: LoadedSubject
    answer: LoadedAnswer
    countersubject: LoadedCountersubject
    metre: tuple[int, int]
    tonic: str
    tonic_midi: int
    seed: int
    stretto: tuple[LoadedStretto, ...]

    def subject_midi(self, tonic_midi: int | None = None, mode: str | None = None) -> tuple[int, ...]:
        """Get subject as MIDI pitches.

        Args:
            tonic_midi: MIDI pitch of tonic (default: self.tonic_midi)
            mode: "major" or "minor" (default: self.subject.mode)
        """
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        effective_mode = mode if mode is not None else self.subject.mode
        return degrees_to_midi(
            degrees=self.subject.degrees,
            tonic_midi=midi,
            mode=effective_mode,
        )

    def answer_midi(self, tonic_midi: int | None = None) -> tuple[int, ...]:
        """Get answer as MIDI pitches (in dominant key)."""
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        dominant_midi = midi + 7
        return degrees_to_midi(
            degrees=self.answer.degrees,
            tonic_midi=dominant_midi,
            mode=self.subject.mode,
        )

    def countersubject_midi(self, tonic_midi: int | None = None, mode: str | None = None) -> tuple[int, ...]:
        """Get countersubject as MIDI pitches.

        Args:
            tonic_midi: MIDI pitch of tonic (default: self.tonic_midi)
            mode: "major" or "minor" (default: self.subject.mode)
        """
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        effective_mode = mode if mode is not None else self.subject.mode
        return degrees_to_midi(
            degrees=self.countersubject.degrees,
            tonic_midi=midi,
            mode=effective_mode,
        )

def _parse_fugue_data(data: dict) -> LoadedFugue:
    """Parse fugue YAML data dict into a LoadedFugue."""
    subj_data: dict = data["subject"]
    ans_data: dict = data["answer"]
    cs_data: dict = data["countersubject"]
    meta: dict = data["metadata"]
    subject: LoadedSubject = LoadedSubject(
        degrees=tuple(subj_data["degrees"]),
        durations=tuple(subj_data["durations"]),
        mode=subj_data["mode"],
        bars=subj_data["bars"],
        head_name=subj_data["head_name"],
        leap_size=subj_data["leap_size"],
        leap_direction=subj_data["leap_direction"],
    )
    answer: LoadedAnswer = LoadedAnswer(
        degrees=tuple(ans_data["degrees"]),
        durations=tuple(ans_data["durations"]),
        answer_type=ans_data["type"],
        mutation_points=tuple(ans_data["mutation_points"]),
    )
    countersubject: LoadedCountersubject = LoadedCountersubject(
        degrees=tuple(cs_data["degrees"]),
        durations=tuple(cs_data["durations"]),
        vertical_intervals=tuple(cs_data["vertical_intervals"]),
    )
    stretto_entries: list[LoadedStretto] = []
    for s in data.get("stretto", []):
        stretto_entries.append(LoadedStretto(
            offset_slots=s["offset_slots"],
            quality=s["quality"],
        ))
    return LoadedFugue(
        subject=subject,
        answer=answer,
        countersubject=countersubject,
        metre=tuple(meta["metre"]),
        tonic=meta["tonic"],
        tonic_midi=meta["tonic_midi"],
        seed=meta["seed"],
        stretto=tuple(stretto_entries),
    )

def load_fugue(name: str) -> LoadedFugue:
    """Load a fugue triple from the library by name."""
    if name.endswith(".fugue"):
        name = name[:-6]
    path: Path = LIBRARY_DIR / f"{name}.fugue"
    assert path.exists(), f"Fugue file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    return _parse_fugue_data(data=data)

def load_fugue_path(path: Path) -> LoadedFugue:
    """Load a fugue triple from an explicit file path."""
    assert path.exists(), f"Fugue file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    return _parse_fugue_data(data=data)

def list_fugues() -> list[str]:
    """List available fugue names in the library."""
    return [p.stem for p in LIBRARY_DIR.glob("*.fugue")]

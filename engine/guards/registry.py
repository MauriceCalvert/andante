"""Guard registry: load and apply guards from lessons.yaml."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Callable

import yaml

from engine.voice_checks import (
    check_parallel_fifths,
    check_parallel_octaves,
    check_bar_duplication,
    check_parallel_rhythm,
    check_sequence_duplication,
    check_endless_trill,
    check_metrical_stress,
    Violation,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def format_offset(offset: Fraction, bar_duration: Fraction, metre: str) -> str:
    """Convert beat offset to bar:beat format (1-indexed bars).

    For 4/4 metre with bar_duration=4, offset 33/8 becomes "5:1.125" (bar 5, beat 1.125).
    """
    bar_num: int = int(offset // bar_duration) + 1
    beat_in_bar: Fraction = offset % bar_duration
    beat_float: float = float(beat_in_bar) + 1  # 1-indexed beat
    if beat_float == int(beat_float):
        return f"{bar_num}:{int(beat_float)}"
    return f"{bar_num}:{beat_float:.3g}"

CHECK_FUNCTIONS: dict[str, Callable] = {
    "parallel_fifths": check_parallel_fifths,
    "parallel_octaves": check_parallel_octaves,
    "bar_duplication": check_bar_duplication,
    "parallel_rhythm": check_parallel_rhythm,
    "sequence_duplication": check_sequence_duplication,
    "endless_trill": check_endless_trill,
    "metrical_stress": check_metrical_stress,
}


@dataclass(frozen=True)
class Guard:
    """A validation guard with metadata."""
    id: str
    name: str
    severity: str
    scope: str
    description: str
    check: Callable


@dataclass(frozen=True)
class Diagnostic:
    """Result of a guard check."""
    guard_id: str
    severity: str
    message: str
    location: str
    offset: Fraction | None = None


def load_lessons() -> dict:
    """Load lessons.yaml."""
    with open(DATA_DIR / "lessons.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_guards() -> dict[str, Guard]:
    """Create guard instances from lessons.yaml."""
    lessons: dict = load_lessons()
    guards: dict[str, Guard] = {}
    for name, lesson in lessons.items():
        guard_id: str = lesson["id"]
        assert name in CHECK_FUNCTIONS, f"No check function for lesson: {name}"
        check_fn: Callable = CHECK_FUNCTIONS[name]
        guard: Guard = Guard(
            id=guard_id,
            name=name,
            severity=lesson["severity"],
            scope=lesson["scope"],
            description=lesson["description"],
            check=check_fn,
        )
        guards[guard_id] = guard
    return guards


def run_guards(
    guards: dict[str, Guard],
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    location: str,
    bar_duration: Fraction,
    metre: str,
) -> list[Diagnostic]:
    """Run phrase-scoped guards and collect diagnostics."""
    diagnostics: list[Diagnostic] = []
    for guard in guards.values():
        if guard.scope != "phrase":
            continue
        violations: list[Violation] = guard.check(soprano, bass)
        for v in violations:
            offset_str: str = format_offset(v.offset, bar_duration, metre)
            diag: Diagnostic = Diagnostic(
                guard_id=guard.id,
                severity=guard.severity,
                message=f"{guard.description} at bar:beat {offset_str}",
                location=location,
                offset=v.offset,
            )
            diagnostics.append(diag)
    return diagnostics


def run_piece_guards(
    guards: dict[str, Guard],
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
    bar_duration: Fraction,
) -> list[Diagnostic]:
    """Run piece-scoped guards and collect diagnostics."""
    diagnostics: list[Diagnostic] = []
    for guard in guards.values():
        if guard.scope != "piece":
            continue
        if guard.name == "bar_duplication":
            for voice_name, notes in [("soprano", soprano), ("bass", bass)]:
                violations: list[Violation] = guard.check(notes, bar_duration)
                for v in violations:
                    diag: Diagnostic = Diagnostic(
                        guard_id=guard.id,
                        severity=guard.severity,
                        message=f"{guard.description} in {voice_name} at bar {int(v.offset / bar_duration)}",
                        location="piece",
                    )
                    diagnostics.append(diag)
        elif guard.name == "parallel_rhythm":
            violations: list[Violation] = guard.check(soprano, bass, bar_duration)
            for v in violations:
                diag: Diagnostic = Diagnostic(
                    guard_id=guard.id,
                    severity=guard.severity,
                    message=f"{guard.description} at bar {int(v.offset / bar_duration)}",
                    location="piece",
                )
                diagnostics.append(diag)
        elif guard.name == "sequence_duplication":
            for voice_name, notes in [("soprano", soprano), ("bass", bass)]:
                violations: list[Violation] = guard.check(notes)
                for v in violations:
                    bar_num: int = int(v.offset / bar_duration) + 1
                    diag: Diagnostic = Diagnostic(
                        guard_id=guard.id,
                        severity=guard.severity,
                        message=f"{guard.description} in {voice_name} at bar {bar_num}",
                        location="piece",
                    )
                    diagnostics.append(diag)
        elif guard.name == "endless_trill":
            for voice_name, notes in [("soprano", soprano), ("bass", bass)]:
                violations: list[Violation] = guard.check(notes)
                for v in violations:
                    bar_num: int = int(v.offset / bar_duration) + 1
                    diag: Diagnostic = Diagnostic(
                        guard_id=guard.id,
                        severity=guard.severity,
                        message=f"{guard.description} in {voice_name} at bar {bar_num}",
                        location="piece",
                    )
                    diagnostics.append(diag)
        elif guard.name == "metrical_stress":
            violations: list[Violation] = guard.check(soprano, bass, bar_duration)
            for v in violations:
                bar_num: int = int(v.offset / bar_duration) + 1
                diag: Diagnostic = Diagnostic(
                    guard_id=guard.id,
                    severity=guard.severity,
                    message=f"{guard.description} at bar {bar_num}",
                    location="piece",
                )
                diagnostics.append(diag)
    return diagnostics

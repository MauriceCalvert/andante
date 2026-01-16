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
    detect_direct_perfect,
    validate_dissonance,
    check_leap_compensation,
    check_consecutive_leaps,
    check_tritone_outline,
    check_forbidden_intervals,
    validate_leading_tone_resolution,
    validate_cadence_bass_motion,
    validate_cadence_preparation,
    Violation,
    MelodicPenalty,
)

DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Module-level bar_duration set by run_guards before calling checks
# This allows time-signature-aware checks without changing all signatures
_current_bar_duration: Fraction = Fraction(1)
_current_tonic_pc: int = 0  # Tonic pitch class (0-11), set by run_guards


def _get_bar_duration() -> Fraction:
    """Get current bar duration for checks that need it."""
    return _current_bar_duration


def _get_tonic_pc() -> int:
    """Get current tonic pitch class for key-aware checks."""
    return _current_tonic_pc


# === Wrapper functions to adapt check signatures ===

def _check_direct_fifth(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for direct fifth detection."""
    return [v for v in detect_direct_perfect(soprano, bass) if v.type == "direct_fifth"]


def _check_direct_octave(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for direct octave detection."""
    return [v for v in detect_direct_perfect(soprano, bass) if v.type == "direct_octave"]


def _check_voice_overlap(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for voice overlap - converts VoiceViolation to Violation."""
    from engine.voice_checks import detect_voice_overlap
    voice_violations = detect_voice_overlap([soprano, bass])
    return [
        Violation(
            type="voice_overlap",
            offset=v.offset,
            soprano_pitch=v.upper_pitch,
            bass_pitch=v.lower_pitch,
        )
        for v in voice_violations
    ]


def _check_dissonance_unprepared(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for unprepared dissonance."""
    return [v for v in validate_dissonance(soprano, bass, _get_bar_duration())
            if v.type == "dissonance_unprepared"]


def _check_dissonance_unresolved(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for unresolved dissonance."""
    return [v for v in validate_dissonance(soprano, bass, _get_bar_duration())
            if v.type == "dissonance_unresolved"]


def _check_dissonance_resolved_up(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for dissonance resolved upward.

    Filters out leading tones which MAY resolve upward per Fux II.3.
    The original check incorrectly uses interval=11, but leading tone
    is determined by soprano pitch class matching (tonic_pc + 11) % 12.
    """
    leading_tone_pc: int = (_get_tonic_pc() + 11) % 12
    violations: list[Violation] = []
    for v in validate_dissonance(soprano, bass, _get_bar_duration()):
        if v.type != "dissonance_resolved_up":
            continue
        # Skip if soprano is actually the leading tone (allowed to resolve up)
        if v.soprano_pitch % 12 == leading_tone_pc:
            continue
        violations.append(v)
    return violations


def _check_dissonance_by_leap(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for dissonance approached by leap."""
    return [v for v in validate_dissonance(soprano, bass, _get_bar_duration())
            if v.type == "dissonance_by_leap"]


def _penalty_to_violation(p: MelodicPenalty, v_type: str) -> Violation:
    """Convert MelodicPenalty to Violation."""
    return Violation(type=v_type, offset=p.offset, soprano_pitch=p.pitch, bass_pitch=0)


def _check_leap_not_compensated(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for uncompensated leaps."""
    penalties = check_leap_compensation(soprano)
    return [_penalty_to_violation(p, "leap_not_compensated") for p in penalties]


def _check_consecutive_leaps(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for consecutive leaps same direction."""
    penalties = check_consecutive_leaps(soprano)
    return [_penalty_to_violation(p, "consecutive_leaps_same_direction") for p in penalties]


def _check_tritone_outline(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for tritone outline."""
    penalties = check_tritone_outline(soprano)
    return [_penalty_to_violation(p, "tritone_outline") for p in penalties]


def _check_leap_augmented(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for augmented leap."""
    penalties = [p for p in check_forbidden_intervals(soprano) if p.type == "leap_augmented"]
    return [_penalty_to_violation(p, "leap_augmented") for p in penalties]


def _check_leap_seventh(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for seventh leap."""
    penalties = [p for p in check_forbidden_intervals(soprano) if p.type == "leap_seventh"]
    return [_penalty_to_violation(p, "leap_seventh") for p in penalties]


def _check_leap_beyond_octave(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for leap beyond octave."""
    penalties = [p for p in check_forbidden_intervals(soprano) if p.type == "leap_beyond_octave"]
    return [_penalty_to_violation(p, "leap_beyond_octave") for p in penalties]


def _check_leading_tone_unresolved(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for unresolved leading tone."""
    return [v for v in validate_leading_tone_resolution(soprano, _get_tonic_pc())
            if v.type == "leading_tone_unresolved"]


def _check_leading_tone_resolved_down(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for leading tone resolved down."""
    return [v for v in validate_leading_tone_resolution(soprano, _get_tonic_pc())
            if v.type == "leading_tone_resolved_down"]


def _check_cadence_bass_motion(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for cadence bass motion (no-op without cadence type)."""
    # This check requires cadence_type which isn't available at guard level
    # Return empty - actual check happens elsewhere with context
    return []


def _check_cadence_preparation_weak(
    soprano: list[tuple[Fraction, int]],
    bass: list[tuple[Fraction, int]],
) -> list[Violation]:
    """Wrapper for weak cadence preparation."""
    return validate_cadence_preparation(soprano, _get_bar_duration())


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
    # Original checks
    "parallel_fifths": check_parallel_fifths,
    "parallel_octaves": check_parallel_octaves,
    "bar_duplication": check_bar_duplication,
    "parallel_rhythm": check_parallel_rhythm,
    "sequence_duplication": check_sequence_duplication,
    "endless_trill": check_endless_trill,
    "metrical_stress": check_metrical_stress,
    # Phase 1: Voice-leading hard constraints
    "direct_fifth": _check_direct_fifth,
    "direct_octave": _check_direct_octave,
    "voice_overlap": _check_voice_overlap,
    "dissonance_unprepared": _check_dissonance_unprepared,
    "dissonance_unresolved": _check_dissonance_unresolved,
    "dissonance_resolved_up": _check_dissonance_resolved_up,
    "dissonance_by_leap": _check_dissonance_by_leap,
    # Phase 2: Melodic constraints
    "leap_not_compensated": _check_leap_not_compensated,
    "consecutive_leaps_same_direction": _check_consecutive_leaps,
    "tritone_outline": _check_tritone_outline,
    "leap_augmented": _check_leap_augmented,
    "leap_seventh": _check_leap_seventh,
    "leap_beyond_octave": _check_leap_beyond_octave,
    # Phase 5: Cadence validation
    "leading_tone_unresolved": _check_leading_tone_unresolved,
    "leading_tone_resolved_down": _check_leading_tone_resolved_down,
    "cadence_bass_motion": _check_cadence_bass_motion,
    "cadence_preparation_weak": _check_cadence_preparation_weak,
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
    tonic_pc: int = 0,
) -> list[Diagnostic]:
    """Run phrase-scoped guards and collect diagnostics."""
    global _current_bar_duration, _current_tonic_pc
    assert 0 <= tonic_pc <= 11, f"Invalid tonic_pc: {tonic_pc}, must be 0-11"
    _current_bar_duration = bar_duration
    _current_tonic_pc = tonic_pc
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
    global _current_bar_duration
    _current_bar_duration = bar_duration
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

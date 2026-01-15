"""Cadenza generation - quasi-improvisatory virtuosic passages.

Cadenzas differ from regular passages:
- Mixed figurations (not repetitive)
- Unmeasured feel via varied durations
- Solo voice with bass pedal
- Dramatic arc: ascent → climax → descent → resolution

Deterministic: planner selects pattern, executor applies it.
"""
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree
from shared.timed_material import TimedMaterial

_PATTERNS: dict[str, dict] | None = None


def _load_patterns() -> dict[str, dict]:
    """Load cadenza patterns from YAML (cached)."""
    global _PATTERNS
    if _PATTERNS is None:
        path: Path = Path(__file__).parent.parent / "data" / "cadenza_patterns.yaml"
        with open(path) as f:
            _PATTERNS = yaml.safe_load(f)
    return _PATTERNS


def _scalar_segment(start: int, direction: int, count: int) -> list[int]:
    """Generate scalar degrees from start."""
    return [start + direction * i for i in range(count)]


def _arpeggio_segment(root: int, direction: int, count: int) -> list[int]:
    """Generate arpeggio degrees from root."""
    steps: list[int] = [0, 2, 4, 7, 9, 11, 14]
    result: list[int] = []
    for i in range(count):
        step: int = steps[i % len(steps)]
        deg: int = root + direction * step
        result.append(deg)
    return result


def _apply_multipliers(
    base_dur: Fraction,
    multipliers: list[int],
    count: int,
) -> list[Fraction]:
    """Apply duration multipliers cyclically to reach count notes."""
    result: list[Fraction] = []
    for i in range(count):
        mult: int = multipliers[i % len(multipliers)]
        result.append(base_dur * mult)
    return result


def generate_cadenza(
    budget: Fraction,
    root: int,
    pattern: str = "flourish_a",
) -> TimedMaterial:
    """Generate cadenza with mixed figurations and varied rhythm.

    Structure:
    - 25% ascent (scalar)
    - 15% intensification (broken thirds)
    - 30% climax (arpeggios at peak)
    - 20% descent (scalar)
    - 10% resolution (slow notes to root)

    Uses only standard durations (1/16, 1/8, 1/4) - no 32nd notes.

    Args:
        budget: Duration budget in whole notes (must be >= 2)
        root: Root degree (1-7)
        pattern: Pattern name from cadenza_patterns.yaml
    """
    assert budget >= 2, f"Cadenza requires budget >= 2, got {budget}"
    patterns: dict[str, dict] = _load_patterns()
    pat: dict = patterns.get(pattern, patterns["flourish_a"])
    base_dur: Fraction = Fraction(1, 16)
    degrees: list[int] = []
    durations: list[Fraction] = []
    phase_budgets: list[Fraction] = [
        budget * Fraction(25, 100),
        budget * Fraction(15, 100),
        budget * Fraction(30, 100),
        budget * Fraction(20, 100),
        budget * Fraction(10, 100),
    ]
    ascent_count: int = max(4, int(phase_budgets[0] / base_dur))
    ascent_degs: list[int] = _scalar_segment(root, 1, ascent_count)
    degrees.extend(ascent_degs)
    durations.extend(_apply_multipliers(base_dur, pat["ascent"], ascent_count))
    peak: int = root + 7
    broken_count: int = max(4, int(phase_budgets[1] / base_dur))
    broken_degs: list[int] = []
    for i in range(broken_count):
        deg: int = peak + (i % 4) - 1 + (i // 4) * 2
        broken_degs.append(deg)
    degrees.extend(broken_degs)
    durations.extend(_apply_multipliers(base_dur, pat["broken"], broken_count))
    climax_count: int = max(6, int(phase_budgets[2] / base_dur))
    climax_degs: list[int] = _arpeggio_segment(peak, 1, climax_count // 2)
    climax_degs.extend(_arpeggio_segment(peak + 7, -1, climax_count - climax_count // 2))
    degrees.extend(climax_degs)
    durations.extend(_apply_multipliers(base_dur, pat["climax"], climax_count))
    descent_count: int = max(4, int(phase_budgets[3] / base_dur))
    descent_degs: list[int] = _scalar_segment(peak, -1, descent_count)
    degrees.extend(descent_degs)
    durations.extend(_apply_multipliers(base_dur, pat["descent"], descent_count))
    resolve_degs: list[int] = [root + 4, root + 2, root]
    degrees.extend(resolve_degs)
    durations.extend(_apply_multipliers(base_dur, pat["resolution"], 3))
    actual: Fraction = sum(durations, Fraction(0))
    if actual < budget:
        durations[-1] += budget - actual
    elif actual > budget:
        excess: Fraction = actual - budget
        i: int = len(durations) - 1
        while excess > 0 and i >= 0:
            reduce: Fraction = min(durations[i] - Fraction(1, 16), excess)
            if reduce > 0:
                durations[i] -= reduce
                excess -= reduce
            i -= 1
    pitches: tuple[Pitch, ...] = tuple(FloatingNote(wrap_degree(d)) for d in degrees)
    return TimedMaterial(pitches, tuple(durations), budget)


def generate_cadenza_bass(budget: Fraction, root: int) -> TimedMaterial:
    """Generate bass pedal for cadenza - repeated root suitable for harpsichord.

    Re-articulates pedal every half note for keyboard decay, with brief
    movement to 4th degree before final resolution.
    """
    pulse: Fraction = Fraction(1, 2)
    pitches: list[Pitch] = []
    durations: list[Fraction] = []
    main_duration: Fraction = budget * Fraction(3, 4)
    remaining: Fraction = main_duration
    while remaining > Fraction(0):
        use_dur: Fraction = min(pulse, remaining)
        pitches.append(FloatingNote(root))
        durations.append(use_dur)
        remaining -= use_dur
    tail: Fraction = budget - main_duration
    pitches.append(FloatingNote(wrap_degree(root + 3)))
    durations.append(tail / 2)
    pitches.append(FloatingNote(root))
    durations.append(tail / 2)
    return TimedMaterial(tuple(pitches), tuple(durations), budget)

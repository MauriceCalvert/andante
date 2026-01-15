"""Harmonic schema application - partimento-style bass patterns."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, wrap_degree
from shared.timed_material import TimedMaterial

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "schemas.yaml", encoding="utf-8") as _f:
    SCHEMAS: dict = yaml.safe_load(_f)


@dataclass(frozen=True)
class Schema:
    """Parsed schema definition."""
    name: str
    bass_degrees: tuple[int, ...]
    soprano_degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bars: int
    cadence_approach: bool


def load_schema(name: str) -> Schema:
    """Load schema by name."""
    assert name in SCHEMAS, f"Unknown schema: {name}"
    data: dict = SCHEMAS[name]
    durs: list[Fraction] = [Fraction(d) for d in data["durations"]]
    return Schema(
        name=name,
        bass_degrees=tuple(data["bass_degrees"]),
        soprano_degrees=tuple(data["soprano_degrees"]),
        durations=tuple(durs),
        bars=data["bars"],
        cadence_approach=data.get("cadence_approach", False),
    )


def apply_schema(
    schema_name: str,
    budget: Fraction,
    start_degree: int = 1,
) -> tuple[TimedMaterial, TimedMaterial]:
    """Generate soprano and bass from schema, filling to budget.

    Args:
        schema_name: Name of schema from schemas.yaml
        budget: Time budget to fill
        start_degree: Degree offset to apply (for transposition)

    Returns:
        Tuple of (soprano, bass) TimedMaterial
    """
    schema: Schema = load_schema(schema_name)
    offset: int = start_degree - 1
    sop_pitches: list[Pitch] = []
    bass_pitches: list[Pitch] = []
    sop_durs: list[Fraction] = []
    bass_durs: list[Fraction] = []
    remaining: Fraction = budget
    idx: int = 0
    schema_len: int = len(schema.bass_degrees)
    while remaining > Fraction(0):
        i: int = idx % schema_len
        cycle: int = idx // schema_len
        dur: Fraction = schema.durations[i]
        use_dur: Fraction = min(dur, remaining)
        # Add cycle offset to transpose each repetition (ascending sequence)
        bass_deg: int = wrap_degree(schema.bass_degrees[i] + offset + cycle)
        sop_deg: int = wrap_degree(schema.soprano_degrees[i] + offset + cycle)
        bass_pitches.append(FloatingNote(bass_deg))
        sop_pitches.append(FloatingNote(sop_deg))
        bass_durs.append(use_dur)
        sop_durs.append(use_dur)
        remaining -= use_dur
        idx += 1
    soprano: TimedMaterial = TimedMaterial(
        tuple(sop_pitches), tuple(sop_durs), budget
    )
    bass: TimedMaterial = TimedMaterial(
        tuple(bass_pitches), tuple(bass_durs), budget
    )
    return soprano, bass


def get_schema_names() -> list[str]:
    """Return list of available schema names."""
    return list(SCHEMAS.keys())


def schema_for_context(
    episode_type: str | None,
    tonal_target: str,
    is_cadence_approach: bool,
) -> str | None:
    """Select appropriate schema for musical context.

    Returns schema name or None if no schema is appropriate.
    """
    if is_cadence_approach:
        return "prinner"
    if episode_type == "turbulent":
        return "fonte"
    if episode_type == "intensification":
        return "monte"
    if tonal_target in ("V", "v"):
        return "rule_of_octave_asc"
    if tonal_target in ("IV", "iv"):
        return "romanesca"
    return None

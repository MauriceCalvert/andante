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
class ChromaticDegree:
    """Scale degree with optional chromatic alteration.

    Supports notation like:
    - 7 = diatonic 7th
    - "b7" or -7 = lowered 7th
    - "#7" or +7 = raised 7th
    """
    degree: int  # 1-7
    alter: int = 0  # -1=flat, 0=natural, +1=sharp

    def to_floating_note(self) -> FloatingNote:
        """Convert to FloatingNote with alteration."""
        return FloatingNote(self.degree, alter=self.alter)


@dataclass(frozen=True)
class SchemaEvent:
    """A single event in a schema with metric position.

    baroque_plan.md item 6.1: Schema events with explicit metric positions.
    """
    metric: str  # "strong" or "weak"
    melody_degree: ChromaticDegree | None  # None for unspecified
    bass_degree: ChromaticDegree
    figured_bass: str = "5/3"  # Default root position


@dataclass(frozen=True)
class Schema:
    """Parsed schema definition."""
    name: str
    bass_degrees: tuple[int, ...]
    soprano_degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]
    bars: int
    cadence_approach: bool
    # New fields for enhanced schemas
    bass_alterations: tuple[int, ...] | None = None  # Chromatic alterations for bass
    soprano_alterations: tuple[int, ...] | None = None  # Chromatic alterations for soprano
    events: tuple[SchemaEvent, ...] | None = None  # Explicit events with metric positions
    function: str | None = None  # 'opening', 'riposte', 'sequence', 'thematic', 'framing'


def parse_chromatic_degree(value: int | str | dict) -> ChromaticDegree:
    """Parse a degree notation that may include chromatic alterations.

    Supports multiple formats:
    - int: plain degree (e.g., 7)
    - str: "b7" (lowered), "#7" (raised)
    - dict: {"degree": 7, "alter": -1}

    Args:
        value: Degree notation in any supported format

    Returns:
        ChromaticDegree with degree and alteration
    """
    if isinstance(value, int):
        return ChromaticDegree(degree=value, alter=0)

    if isinstance(value, str):
        if value.startswith("b") or value.startswith("-"):
            deg = int(value[1:])
            return ChromaticDegree(degree=deg, alter=-1)
        if value.startswith("#") or value.startswith("+"):
            deg = int(value[1:])
            return ChromaticDegree(degree=deg, alter=+1)
        # Plain string number
        return ChromaticDegree(degree=int(value), alter=0)

    if isinstance(value, dict):
        deg = value["degree"]
        alter = value.get("alter", 0)
        return ChromaticDegree(degree=deg, alter=alter)

    raise ValueError(f"Cannot parse chromatic degree: {value}")


def load_schema(name: str) -> Schema:
    """Load schema by name, parsing chromatic alterations if present."""
    assert name in SCHEMAS, f"Unknown schema: {name}"
    data: dict = SCHEMAS[name]
    durs: list[Fraction] = [Fraction(d) for d in data["durations"]]

    # Parse bass degrees (may include chromatic alterations)
    raw_bass = data["bass_degrees"]
    bass_degrees: list[int] = []
    bass_alters: list[int] = []
    for deg in raw_bass:
        parsed = parse_chromatic_degree(deg)
        bass_degrees.append(parsed.degree)
        bass_alters.append(parsed.alter)

    # Parse soprano degrees (may include chromatic alterations)
    raw_soprano = data["soprano_degrees"]
    soprano_degrees: list[int] = []
    soprano_alters: list[int] = []
    for deg in raw_soprano:
        parsed = parse_chromatic_degree(deg)
        soprano_degrees.append(parsed.degree)
        soprano_alters.append(parsed.alter)

    # Check if any alterations are non-zero
    has_bass_alters = any(a != 0 for a in bass_alters)
    has_soprano_alters = any(a != 0 for a in soprano_alters)

    # Determine function based on schema attributes
    function: str | None = None
    if data.get("opening"):
        function = "opening"
    elif data.get("cadence_approach"):
        function = "riposte"
    elif data.get("sequential"):
        function = "sequence"
    elif data.get("pedal"):
        function = "framing" if data.get("framing") else "prolongation"
    elif data.get("repeatable"):
        function = "thematic"

    return Schema(
        name=name,
        bass_degrees=tuple(bass_degrees),
        soprano_degrees=tuple(soprano_degrees),
        durations=tuple(durs),
        bars=data["bars"],
        cadence_approach=data.get("cadence_approach", False),
        bass_alterations=tuple(bass_alters) if has_bass_alters else None,
        soprano_alterations=tuple(soprano_alters) if has_soprano_alters else None,
        events=None,  # Could be populated from explicit event data
        function=function,
    )


def apply_schema(
    schema_name: str,
    budget: Fraction,
    start_degree: int = 1,
) -> tuple[TimedMaterial, TimedMaterial]:
    """Generate soprano and bass from schema, filling to budget.

    Now supports chromatic alterations in schema degrees.

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

        # Get chromatic alterations if present
        bass_alter: int = 0
        sop_alter: int = 0
        if schema.bass_alterations is not None:
            bass_alter = schema.bass_alterations[i]
        if schema.soprano_alterations is not None:
            sop_alter = schema.soprano_alterations[i]

        bass_pitches.append(FloatingNote(bass_deg, alter=bass_alter))
        sop_pitches.append(FloatingNote(sop_deg, alter=sop_alter))
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
    tempo: str | None = None,
    is_opening: bool = False,
    is_post_cadence: bool = False,
) -> str | None:
    """Select appropriate schema for musical context.

    Enhanced with baroque_plan.md requirements:
    - DO_RE_MI for opening
    - FENAROLI for dominant key
    - SOL_FA_MI for slow tempo
    - MEYER as fallback
    - QUIESCENZA for post-cadence framing

    Returns schema name or None if no schema is appropriate.
    """
    # Priority 1: Post-cadence framing
    if is_post_cadence:
        return "quiescenza"

    # Priority 2: Opening schemas
    if is_opening:
        return "do_re_mi"

    # Priority 3: Cadence approach
    if is_cadence_approach:
        return "prinner"

    # Priority 4: Episode-type specific
    if episode_type == "turbulent":
        return "fonte"
    if episode_type == "intensification":
        return "monte"

    # Priority 5: Tonal target specific
    if tonal_target in ("V", "v"):
        # Check for slow tempo -> sol_fa_mi
        if tempo in ("adagio", "largo", "lento"):
            return "sol_fa_mi"
        return "fenaroli"  # Dominant key schema
    if tonal_target in ("IV", "iv"):
        return "romanesca"

    # Priority 6: Tempo-based
    if tempo in ("adagio", "largo", "lento"):
        return "sol_fa_mi"

    # Fallback
    return "meyer"


# =============================================================================
# Phase 3: Rule of the Octave Enhancement (baroque_plan.md item 3.1)
# =============================================================================

# Rule of the Octave harmonizations by direction and scale degree
RULE_OF_OCTAVE_ASCENDING: dict[int, str] = {
    1: "5/3",      # Tonic - root position
    2: "6/3",      # Supertonic - first inversion
    3: "6/3",      # Mediant - first inversion
    4: "6/5/3",    # Subdominant - with added 6th
    5: "5/3",      # Dominant - root position
    6: "6/3",      # Submediant - first inversion
    7: "6/5/3",    # Leading tone - first inversion with 5th
    # 8: Same as 1
}

RULE_OF_OCTAVE_DESCENDING: dict[int, str] = {
    1: "5/3",      # Tonic - root position (high octave)
    7: "6/3",      # Leading tone - first inversion
    6: "#6/4/3",   # Submediant - with raised 6th (special dissonance)
    5: "5/3",      # Dominant - root position
    4: "6/4/2",    # Subdominant - second inversion (special dissonance)
    3: "6/3",      # Mediant - first inversion
    2: "6/4/3",    # Supertonic - with 4th
    # Return to 1: Same as high 1
}


def get_rule_of_octave_figure(degree: int, direction: str) -> str:
    """Get figured bass for a scale degree in Rule of the Octave.

    Args:
        degree: Scale degree (1-7)
        direction: "ascending" or "descending"

    Returns:
        Figured bass string (e.g., "5/3", "6/4/2")
    """
    if direction == "ascending":
        return RULE_OF_OCTAVE_ASCENDING.get(degree, "5/3")
    else:
        return RULE_OF_OCTAVE_DESCENDING.get(degree, "5/3")


def apply_rule_of_octave(
    bass_degrees: tuple[int, ...],
    budget: Fraction,
) -> tuple[TimedMaterial, list[str]]:
    """Apply Rule of the Octave harmonization to a bass line.

    Automatically detects direction for each transition and applies
    appropriate harmonization including special dissonances.

    Args:
        bass_degrees: Sequence of bass scale degrees
        budget: Time budget to fill

    Returns:
        Tuple of (bass TimedMaterial, list of figured bass symbols)
    """
    if not bass_degrees:
        return TimedMaterial((), (), budget), []

    # Calculate duration per note
    dur_per_note: Fraction = budget / len(bass_degrees)

    pitches: list[Pitch] = []
    durations: list[Fraction] = []
    figures: list[str] = []

    for i, degree in enumerate(bass_degrees):
        # Determine direction from previous degree
        if i == 0:
            direction = "ascending"  # Default for first note
        else:
            prev_degree = bass_degrees[i - 1]
            # Handle wraparound (e.g., 7 to 1 is ascending)
            if degree > prev_degree or (degree == 1 and prev_degree == 7):
                direction = "ascending"
            else:
                direction = "descending"

        figure = get_rule_of_octave_figure(degree, direction)
        pitches.append(FloatingNote(degree))
        durations.append(dur_per_note)
        figures.append(figure)

    bass = TimedMaterial(tuple(pitches), tuple(durations), budget)
    return bass, figures


# =============================================================================
# Phase 3: Bass Motion Pattern Detection (baroque_plan.md item 3.2)
# =============================================================================

@dataclass(frozen=True)
class BassPattern:
    """Detected bass motion pattern."""
    name: str
    intervals: tuple[int, ...]  # Intervals between consecutive bass notes
    harmonization: tuple[str, ...]  # Figured bass for each note


# Common baroque bass patterns with their harmonizations
BASS_PATTERNS: dict[str, BassPattern] = {
    "circle_fifths": BassPattern(
        name="circle_fifths",
        intervals=(4, -5),  # Up 4th, down 5th (in scale degrees)
        harmonization=("5/3", "5/3"),
    ),
    "up3_down1": BassPattern(
        name="up3_down1",
        intervals=(2, -1),  # Up 3rd, down step
        harmonization=("5/3", "6/3"),
    ),
    "down3_up1": BassPattern(
        name="down3_up1",
        intervals=(-2, 1),  # Down 3rd, up step
        harmonization=("5/3", "6/3"),
    ),
    "descending_stepwise": BassPattern(
        name="descending_stepwise",
        intervals=(-1,),  # Down step
        harmonization=("6/3",),  # Fauxbourdon-style
    ),
    "ascending_stepwise": BassPattern(
        name="ascending_stepwise",
        intervals=(1,),  # Up step
        harmonization=("6/3",),
    ),
    "falling_thirds": BassPattern(
        name="falling_thirds",
        intervals=(-2, -2),  # Two falling thirds
        harmonization=("5/3", "5/3", "6/3"),
    ),
    "romanesca": BassPattern(
        name="romanesca",
        intervals=(-1, -2, 2),  # 1-7-6-3 pattern
        harmonization=("5/3", "6/3", "6/3", "6/3"),
    ),
}


def detect_bass_pattern(
    bass_degrees: tuple[int, ...],
) -> list[tuple[int, BassPattern]]:
    """Detect sequential patterns in a bass line.

    Args:
        bass_degrees: Sequence of bass scale degrees

    Returns:
        List of (start_index, pattern) for each detected pattern
    """
    detected: list[tuple[int, BassPattern]] = []

    if len(bass_degrees) < 2:
        return detected

    # Calculate intervals between consecutive degrees
    intervals: list[int] = []
    for i in range(1, len(bass_degrees)):
        # Normalize to -3 to +3 range (scale degree difference)
        diff = bass_degrees[i] - bass_degrees[i - 1]
        # Handle octave wraparound
        while diff > 3:
            diff -= 7
        while diff < -3:
            diff += 7
        intervals.append(diff)

    # Search for pattern matches
    for pattern_name, pattern in BASS_PATTERNS.items():
        pattern_len = len(pattern.intervals)
        for i in range(len(intervals) - pattern_len + 1):
            window = tuple(intervals[i:i + pattern_len])
            if window == pattern.intervals:
                detected.append((i, pattern))

    return detected


def harmonise_bass_pattern(
    bass_degrees: tuple[int, ...],
) -> list[str]:
    """Generate figured bass for a bass line using pattern detection.

    Applies pattern-specific harmonization where patterns are detected,
    falls back to Rule of the Octave otherwise.

    Args:
        bass_degrees: Sequence of bass scale degrees

    Returns:
        List of figured bass symbols for each degree
    """
    if not bass_degrees:
        return []

    # Initialize with default harmonization
    figures: list[str] = ["5/3"] * len(bass_degrees)

    # Detect patterns
    patterns = detect_bass_pattern(bass_degrees)

    # Apply pattern harmonizations
    for start_idx, pattern in patterns:
        for j, fig in enumerate(pattern.harmonization):
            if start_idx + j < len(figures):
                figures[start_idx + j] = fig

    # Fill remaining with Rule of the Octave
    for i in range(len(bass_degrees)):
        if figures[i] == "5/3" and i > 0:
            prev = bass_degrees[i - 1]
            curr = bass_degrees[i]
            direction = "ascending" if curr > prev else "descending"
            figures[i] = get_rule_of_octave_figure(curr, direction)

    return figures

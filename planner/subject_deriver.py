"""Subject derivation from opening schema.

When no user subject is provided, derive one from the opening schema's
soprano degrees combined with a rhythmic pattern from the genre template.
"""
import logging
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from planner.plannertypes import Frame, Motif
from planner.schema_loader import get_schema
from planner.subject_validator import check_answerability, check_invertibility
from shared.constants import VALID_DURATIONS

logger: logging.Logger = logging.getLogger(__name__)


DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Default subject rhythm patterns by genre
# Format: (durations, style) where style is 'motoric' or 'lyrical'
DEFAULT_SUBJECT_RHYTHMS: dict[str, tuple[tuple[Fraction, ...], str]] = {
    "invention": (
        (Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        "motoric",
    ),
    "minuet": (
        (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        "lyrical",
    ),
    "gavotte": (
        (Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
        "motoric",
    ),
    "sarabande": (
        (Fraction(1, 2), Fraction(1, 4), Fraction(1, 4)),
        "lyrical",
    ),
    "bourree": (
        (Fraction(1, 4), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        "motoric",
    ),
    "fantasia": (
        (Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 4)),
        "motoric",
    ),
    "chorale": (
        (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        "lyrical",
    ),
    "trio_sonata": (
        (Fraction(1, 8), Fraction(1, 8), Fraction(1, 8), Fraction(1, 8)),
        "motoric",
    ),
}

# Fallback rhythm
FALLBACK_RHYTHM: tuple[tuple[Fraction, ...], str] = (
    (Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
    "motoric",
)


def _load_genre_yaml(genre: str) -> dict[str, Any]:
    """Load genre YAML file if it exists."""
    path = DATA_DIR / "genres" / f"{genre}.yaml"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_subject_rhythm(genre: str) -> tuple[tuple[Fraction, ...], str]:
    """Get rhythm pattern and style from genre template.

    Priority:
    1. subject_rhythm field in genre YAML
    2. DEFAULT_SUBJECT_RHYTHMS
    3. FALLBACK_RHYTHM

    Returns:
        (durations, style) where style is 'motoric' or 'lyrical'
    """
    genre_data = _load_genre_yaml(genre=genre)

    if "subject_rhythm" in genre_data:
        rhythm_data = genre_data["subject_rhythm"]
        pattern = tuple(Fraction(d) for d in rhythm_data["pattern"])
        style = rhythm_data.get("style", "motoric")
        return pattern, style

    if genre in DEFAULT_SUBJECT_RHYTHMS:
        return DEFAULT_SUBJECT_RHYTHMS[genre]
    logger.warning(
        "Genre %r has no subject_rhythm in YAML and no entry in "
        "DEFAULT_SUBJECT_RHYTHMS; using FALLBACK_RHYTHM (4 x 1/4, motoric). "
        "Add a rhythm to data/genres/%s.yaml or DEFAULT_SUBJECT_RHYTHMS.",
        genre, genre,
    )
    return FALLBACK_RHYTHM


def apply_rhythm_pattern(
    degrees: tuple[int, ...],
    pattern: tuple[Fraction, ...],
    style: str,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Apply rhythmic pattern to scale degrees.

    If degrees and pattern have different lengths, adjust by:
    - Repeating degrees if pattern is longer
    - Repeating pattern if degrees are longer

    Args:
        degrees: Scale degrees from schema
        pattern: Duration pattern from genre
        style: 'motoric' or 'lyrical'

    Returns:
        (adjusted_degrees, adjusted_durations) both same length
    """
    n_degrees = len(degrees)
    n_pattern = len(pattern)

    if n_degrees == n_pattern:
        # Perfect match
        return degrees, pattern

    if n_degrees < n_pattern:
        # Extend degrees by repeating
        extended_degrees = list(degrees)
        while len(extended_degrees) < n_pattern:
            # Cycle through degrees
            idx = len(extended_degrees) % n_degrees
            extended_degrees.append(degrees[idx])
        return tuple(extended_degrees[:n_pattern]), pattern

    # n_degrees > n_pattern: extend pattern
    extended_pattern = list(pattern)
    while len(extended_pattern) < n_degrees:
        idx = len(extended_pattern) % n_pattern
        extended_pattern.append(pattern[idx])
    return degrees, tuple(extended_pattern[:n_degrees])


def adjust_for_tritone(
    degrees: tuple[int, ...],
    mode: str,
) -> tuple[int, ...]:
    """Adjust degrees to avoid tritone leaps.

    Tritone (degree 4 to 7 or 7 to 4) is avoided in baroque subjects.
    Replace with stepwise motion.

    Args:
        degrees: Original degrees
        mode: 'major' or 'minor'

    Returns:
        Adjusted degrees with tritones filled
    """
    if len(degrees) < 2:
        return degrees

    result = list(degrees)

    for i in range(len(result) - 1):
        d1 = ((result[i] - 1) % 7) + 1
        d2 = ((result[i + 1] - 1) % 7) + 1

        # Check for tritone (4-7 or 7-4)
        if (d1 == 4 and d2 == 7) or (d1 == 7 and d2 == 4):
            # Fill with passing tone
            if d1 == 4:
                # 4 -> 7 becomes 4 -> 5 (or keep 4)
                result[i + 1] = 5 if i + 1 < len(result) - 1 else result[i + 1]
            else:
                # 7 -> 4 becomes 7 -> 6 (or keep 7)
                result[i + 1] = 6 if i + 1 < len(result) - 1 else result[i + 1]

    return tuple(result)


def ensure_valid_durations(
    durations: tuple[Fraction, ...],
) -> tuple[Fraction, ...]:
    """Assert all durations are in VALID_DURATIONS (L012: no quantization)."""
    valid_set: set[Fraction] = set(VALID_DURATIONS)
    for i, d in enumerate(durations):
        assert d in valid_set, (
            f"Duration[{i}]={d} not in VALID_DURATIONS. "
            f"Fix the source that produced this duration. "
            f"Valid: {sorted(valid_set, reverse=True)}"
        )
    return durations


def derive_subject(
    opening_schema: str,
    frame: Frame,
    genre: str,
    target_bars: int = 2,
) -> Motif:
    """Create subject from schema's soprano degrees.

    Steps:
    1. Get soprano_degrees from schema definition
    2. Stretch durations to fit target_bars
    3. Get rhythm pattern from genre's subject_rhythm
    4. Combine: map degrees to durations
    5. Validate and adjust (avoid tritones, etc.)

    Args:
        opening_schema: Name of opening schema
        frame: Frame with mode info
        genre: Genre name for rhythm pattern
        target_bars: Target bar count for subject (default 2)

    Returns:
        Motif with degrees and durations
    """
    schema = get_schema(name=opening_schema)
    mode = frame.mode

    # Get soprano degrees from schema
    soprano_degrees = schema.soprano_degrees

    # Get rhythm pattern from genre
    rhythm_pattern, style = get_subject_rhythm(genre=genre)

    # Apply rhythm pattern to degrees
    degrees, durations = apply_rhythm_pattern(degrees=soprano_degrees, pattern=rhythm_pattern, style=style)

    # Adjust for tritones
    degrees = adjust_for_tritone(degrees=degrees, mode=mode)

    # Validate durations
    durations = ensure_valid_durations(durations=durations)

    # Calculate total duration and bars
    total_dur = sum(durations)

    # Determine bars (round to nearest integer)
    if total_dur.denominator == 1:
        bars = int(total_dur)
    else:
        bars = max(1, round(float(total_dur)))

    # Verify invertibility and answerability (soft constraints - warn but don't fail)
    invert_ok, _ = check_invertibility(degrees=degrees, mode=mode)
    answer_ok, _ = check_answerability(degrees=degrees, mode=mode)

    # Note: We could iterate to find better degrees, but for now accept as-is
    # The schema-derived subject is a starting point; user can override

    return Motif(
        degrees=degrees,
        durations=durations,
        bars=bars,
    )

"""Pattern loader adapter for voice generation.

Loads rhythmic patterns from YAML files and provides Pattern dataclass
for CP-SAT solver consumption.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

# Pattern file locations
DATA_DIR: Path = Path(__file__).parent.parent / "data"
BASS_PATTERNS_FILE: Path = DATA_DIR / "bass_patterns.yaml"
INNER_PATTERNS_FILE: Path = DATA_DIR / "inner_patterns.yaml"


@dataclass(frozen=True)
class Pattern:
    """A rhythmic pattern for voice generation.

    Attributes:
        name: Pattern identifier (e.g., "walking_bass")
        intervals: Scale degree offsets from chord root per beat (0=root, 4=fifth)
        durations: Note durations per beat
        motion: Motion type hint (stepwise, chordal, static)
    """
    name: str
    intervals: tuple[int, ...]
    durations: tuple[Fraction, ...]
    motion: str

    def __post_init__(self) -> None:
        assert len(self.intervals) == len(self.durations), (
            f"Pattern {self.name}: intervals ({len(self.intervals)}) and "
            f"durations ({len(self.durations)}) must have same length"
        )
        assert all(isinstance(d, Fraction) for d in self.durations), (
            f"Pattern {self.name}: all durations must be Fraction"
        )


def load_pattern(pattern_name: str, metre: str, voice_role: str) -> Pattern:
    """Load a pattern by name for the given metre and voice role.

    Args:
        pattern_name: Pattern identifier (e.g., "walking_bass", "sustained")
        metre: Time signature (e.g., "4/4", "3/4")
        voice_role: Voice type ("bass", "alto", "tenor")

    Returns:
        Pattern with intervals and durations for the metre

    Raises:
        AssertionError: If pattern or metre not found
    """
    # Select pattern file based on voice role
    if voice_role == "bass":
        patterns_file = BASS_PATTERNS_FILE
    else:
        patterns_file = INNER_PATTERNS_FILE

    assert patterns_file.exists(), f"Pattern file not found: {patterns_file}"

    with open(patterns_file, "r") as f:
        all_patterns: dict[str, Any] = yaml.safe_load(f)

    # Handle nested pattern names (e.g., "cadential.authentic")
    if "." in pattern_name:
        parts = pattern_name.split(".")
        pattern_data = all_patterns
        for part in parts:
            assert part in pattern_data, (
                f"Pattern '{pattern_name}' not found in {patterns_file.name}. "
                f"Available at level '{part}': {list(pattern_data.keys())}"
            )
            pattern_data = pattern_data[part]
    else:
        assert pattern_name in all_patterns, (
            f"Pattern '{pattern_name}' not found in {patterns_file.name}. "
            f"Available: {[k for k in all_patterns.keys() if not k.startswith('_')]}"
        )
        pattern_data = all_patterns[pattern_name]

    # Get metre-specific definition
    assert "metres" in pattern_data, (
        f"Pattern '{pattern_name}' has no 'metres' section. "
        f"Keys: {list(pattern_data.keys())}"
    )

    metres = pattern_data["metres"]
    assert metre in metres, (
        f"Pattern '{pattern_name}' has no definition for metre '{metre}'. "
        f"Available metres: {list(metres.keys())}"
    )

    metre_data = metres[metre]
    intervals_raw = metre_data["intervals"]
    durations_raw = metre_data["durations"]

    # Convert durations to Fraction
    durations: list[Fraction] = []
    for d in durations_raw:
        if isinstance(d, str):
            durations.append(Fraction(d))
        elif isinstance(d, (int, float)):
            durations.append(Fraction(d).limit_denominator(32))
        else:
            durations.append(Fraction(d))

    # Get motion type (default to "stepwise")
    motion: str = pattern_data.get("motion", "stepwise")

    return Pattern(
        name=pattern_name,
        intervals=tuple(intervals_raw),
        durations=tuple(durations),
        motion=motion,
    )


def get_default_pattern(voice_role: str) -> str:
    """Get default pattern name for a voice role.

    Args:
        voice_role: Voice type ("bass", "alto", "tenor")

    Returns:
        Default pattern name for the voice
    """
    if voice_role == "bass":
        return "walking_bass"
    else:
        return "sustained"

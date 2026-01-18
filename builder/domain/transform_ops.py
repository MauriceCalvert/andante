"""Transform operations for note sequences.

Category A: Pure functions, no validation, no I/O.
Assumes all inputs are valid — validation happens in orchestrators.

SIZE: 128 lines — Transform class is a cohesive state machine with
tightly-coupled pitch and duration operations. The apply/transform methods
form an indivisible unit. Splitting would scatter related transformation logic.

Functions:
    load_transform_specs — Load transform specs from dict (for adapter to call)

Classes:
    Transform — YAML-driven melodic transformation
"""
from fractions import Fraction
from typing import Any

from builder.music_math import augment_duration, diminish_duration
from builder.types import Notes
from shared.constants import VALID_DURATION_OPS, VALID_PITCH_OPS


class Transform:
    """YAML-driven melodic transformation.

    Transforms are loaded from YAML specs and applied to Notes.
    Each transform can modify pitches, durations, or both.
    """

    def __init__(self, name: str, spec: dict[str, Any]) -> None:
        """Initialize transform from spec dict.

        Args:
            name: Transform name for error messages
            spec: Dict with 'pitch', 'duration', 'slice' keys
        """
        self.name: str = name
        self.pitch_op: str | None = spec.get("pitch")
        self.duration_op: str | None = spec.get("duration")
        self.slice_n: int | None = spec.get("slice")
        self.transpose_n: int | None = None

        if self.pitch_op is not None and self.pitch_op.startswith("transpose"):
            self.transpose_n = int(_parse_arg(self.pitch_op))

    def apply(self, notes: Notes, **kwargs: Any) -> Notes:
        """Apply transform to notes.

        Required kwargs by operation:
        - negate: pivot (int) — the pitch to invert around
        - transpose: n (int) — semitones (overrides YAML default)

        Args:
            notes: Input notes
            **kwargs: Operation-specific parameters

        Returns:
            Transformed notes
        """
        pitches: tuple[int, ...] = notes.pitches
        durations: tuple[Fraction, ...] = notes.durations

        if self.slice_n is not None:
            if self.slice_n > 0:
                pitches = pitches[: self.slice_n]
                durations = durations[: self.slice_n]
            else:
                pitches = pitches[self.slice_n :]
                durations = durations[self.slice_n :]

        pitches = self._transform_pitch(pitches, **kwargs)
        durations = self._transform_duration(durations)
        return Notes(pitches, durations)

    def _transform_pitch(self, pitches: tuple[int, ...], **kwargs: Any) -> tuple[int, ...]:
        """Apply pitch operation."""
        if self.pitch_op is None:
            return pitches

        if self.pitch_op == "negate":
            pivot: int = kwargs["pivot"]
            return tuple(2 * pivot - p for p in pitches)

        if self.pitch_op == "reverse":
            return pitches[::-1]

        if self.pitch_op.startswith("transpose"):
            n: int = kwargs.get("n", self.transpose_n) or 0
            return tuple(p + n for p in pitches)

        return pitches

    def _transform_duration(self, durations: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
        """Apply duration operation."""
        if self.duration_op is None:
            return durations

        if self.duration_op == "reverse":
            return durations[::-1]

        if self.duration_op == "augment":
            return tuple(augment_duration(d) for d in durations)

        if self.duration_op == "diminish":
            return tuple(diminish_duration(d) for d in durations)

        return durations


def _parse_arg(op: str) -> Fraction:
    """Parse argument from operation string like 'transpose(3)'."""
    start: int = op.find("(")
    end: int = op.find(")")
    return Fraction(op[start + 1 : end])


def validate_transform_spec(name: str, spec: dict[str, Any]) -> None:
    """Validate transform spec. Raises ValueError if invalid."""
    pitch_op: str | None = spec.get("pitch")
    duration_op: str | None = spec.get("duration")

    if pitch_op is not None:
        op_name: str = pitch_op.split("(")[0]
        if op_name not in VALID_PITCH_OPS:
            raise ValueError(f"Transform '{name}': unknown pitch op '{pitch_op}'")

    if duration_op is not None and duration_op not in VALID_DURATION_OPS:
        raise ValueError(f"Transform '{name}': unknown duration op '{duration_op}'")

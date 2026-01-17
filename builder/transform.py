"""Transform system for note sequences."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, TextIO

import yaml

from builder.music_math import augment_duration, diminish_duration, validate_duration
from builder.tree import Node

TRANSFORMS_PATH: Path = Path(__file__).parent / "data" / "transforms.yaml"

# Valid operations - validated at construction time
VALID_PITCH_OPS: frozenset[str] = frozenset({'negate', 'reverse', 'transpose'})
VALID_DURATION_OPS: frozenset[str] = frozenset({'reverse', 'augment', 'diminish'})


@dataclass(frozen=True)
class Notes:
    """Immutable sequence of notes with pitches and durations."""
    pitches: tuple[int, ...]
    durations: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if len(self.pitches) != len(self.durations):
            raise ValueError(
                f"pitches ({len(self.pitches)}) and durations ({len(self.durations)}) "
                "must have same length"
            )


class Transform:
    """YAML-driven melodic transformation."""

    _cache: dict[str, dict[str, str]] = {}

    def __init__(self, name: str) -> None:
        self.name: str = name
        spec: dict[str, str] = self._load_spec(name)
        self.pitch_op: str | None = spec.get('pitch')
        self.duration_op: str | None = spec.get('duration')
        self.transpose_n: int | None = None
        self._validate_spec()

    def _validate_spec(self) -> None:
        """Validate operations at construction time. Fail fast on bad YAML."""
        if self.pitch_op is not None:
            op_name: str = self.pitch_op.split('(')[0]
            if op_name not in VALID_PITCH_OPS:
                raise ValueError(
                    f"Transform '{self.name}': unknown pitch op '{self.pitch_op}'. "
                    f"Valid: {sorted(VALID_PITCH_OPS)}"
                )
            if op_name == 'transpose':
                self.transpose_n = int(self._parse_arg(self.pitch_op))

        if self.duration_op is not None:
            if self.duration_op not in VALID_DURATION_OPS:
                raise ValueError(
                    f"Transform '{self.name}': unknown duration op '{self.duration_op}'. "
                    f"Valid: {sorted(VALID_DURATION_OPS)}"
                )

    @classmethod
    def _load_spec(cls, name: str) -> dict[str, str]:
        """Load transform spec from YAML, with caching."""
        if not cls._cache:
            f: TextIO
            with open(TRANSFORMS_PATH, encoding='utf-8') as f:
                cls._cache = yaml.safe_load(f)
        if name not in cls._cache:
            raise ValueError(f"Unknown transform: {name}")
        return cls._cache[name] or {}

    def apply(self, notes: Notes, **kwargs: Any) -> Notes:
        """Apply transform to notes.

        Required kwargs by operation:
        - negate: pivot (int) - the pitch to invert around
        - transpose: n (int) - semitones to transpose (overrides YAML default)
        """
        pitches: tuple[int, ...] = self._transform_pitch(notes.pitches, **kwargs)
        durations: tuple[Fraction, ...] = self._transform_duration(notes.durations)
        return Notes(pitches, durations)

    def _transform_pitch(self, pitches: tuple[int, ...], **kwargs: Any) -> tuple[int, ...]:
        """Apply pitch operation."""
        if self.pitch_op is None:
            return pitches

        if self.pitch_op == 'negate':
            if 'pivot' not in kwargs:
                raise ValueError(
                    f"Transform '{self.name}': 'negate' requires 'pivot' kwarg"
                )
            pivot: int = kwargs['pivot']
            if not isinstance(pivot, int):
                raise TypeError(
                    f"Transform '{self.name}': pivot must be int, got {type(pivot).__name__}"
                )
            return tuple(2 * pivot - p for p in pitches)

        if self.pitch_op == 'reverse':
            return pitches[::-1]

        if self.pitch_op.startswith('transpose'):
            n: int
            if 'n' in kwargs:
                n = kwargs['n']
                if not isinstance(n, int):
                    raise TypeError(
                        f"Transform '{self.name}': n must be int, got {type(n).__name__}"
                    )
            elif self.transpose_n is not None:
                n = self.transpose_n
            else:
                raise ValueError(
                    f"Transform '{self.name}': 'transpose' requires 'n' kwarg or YAML arg"
                )
            return tuple(p + n for p in pitches)

        raise ValueError(f"Unknown pitch op: {self.pitch_op}")

    def _transform_duration(self, durations: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
        """Apply duration operation."""
        if self.duration_op is None:
            return durations

        if self.duration_op == 'reverse':
            return durations[::-1]

        if self.duration_op == 'augment':
            return tuple(augment_duration(d) for d in durations)

        if self.duration_op == 'diminish':
            return tuple(diminish_duration(d) for d in durations)

        raise ValueError(f"Unknown duration op: {self.duration_op}")

    @staticmethod
    def _parse_arg(op: str) -> Fraction:
        """Parse argument from operation string like 'transpose(3)'."""
        start: int = op.find('(')
        end: int = op.find(')')
        if start == -1 or end == -1:
            raise ValueError(f"Cannot parse argument from: {op}")
        return Fraction(op[start + 1:end])


def notes_from_node(node: Node) -> Notes:
    """Extract Notes from a subject/motif node with degrees and durations."""
    pitches: tuple[int, ...] = tuple(c.value for c in node['degrees'].children)
    durations: tuple[Fraction, ...] = tuple(
        validate_duration(Fraction(c.value)) for c in node['durations'].children
    )
    return Notes(pitches, durations)


def notes_to_dicts(notes: Notes) -> list[dict[str, Any]]:
    """Convert Notes to list of note dicts for tree insertion."""
    return [
        {'diatonic': p, 'duration': str(d)}
        for p, d in zip(notes.pitches, notes.durations)
    ]

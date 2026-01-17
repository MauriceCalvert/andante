"""Transform system for note sequences."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, TextIO

import yaml

from builder.music_math import validate_duration
from builder.tree import Node

TRANSFORMS_PATH: Path = Path(__file__).parent / "data" / "transforms.yaml"


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
        """Apply transform to notes."""
        pitches: tuple[int, ...] = self._transform_pitch(notes.pitches, **kwargs)
        durations: tuple[Fraction, ...] = self._transform_duration(notes.durations, **kwargs)
        return Notes(pitches, durations)

    def _transform_pitch(self, pitches: tuple[int, ...], **kwargs: Any) -> tuple[int, ...]:
        """Apply pitch operation."""
        if not self.pitch_op:
            return pitches

        if self.pitch_op == 'negate':
            pivot: int = kwargs.get('pivot', pitches[0])
            return tuple(2 * pivot - p for p in pitches)

        if self.pitch_op == 'reverse':
            return pitches[::-1]

        if self.pitch_op.startswith('transpose'):
            n: int = int(kwargs.get('n', self._parse_arg(self.pitch_op)))
            return tuple(p + n for p in pitches)

        raise ValueError(f"Unknown pitch op: {self.pitch_op}")

    def _transform_duration(self, durations: tuple[Fraction, ...], **kwargs: Any) -> tuple[Fraction, ...]:
        """Apply duration operation."""
        if not self.duration_op:
            return durations

        if self.duration_op == 'reverse':
            return durations[::-1]

        if self.duration_op.startswith('multiply'):
            factor: Fraction = kwargs.get('factor', self._parse_arg(self.duration_op))
            return tuple(validate_duration(d * factor) for d in durations)

        raise ValueError(f"Unknown duration op: {self.duration_op}")

    @staticmethod
    def _parse_arg(op: str) -> Fraction:
        """Parse argument from operation string like 'multiply(2)' or 'transpose(3)'."""
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

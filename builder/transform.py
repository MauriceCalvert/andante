"""Transform system for note sequences."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, TextIO

import yaml

from builder.music_math import augment_duration, diminish_duration, validate_duration
from builder.tree import Node
from shared.constants import VALID_DURATION_OPS, VALID_PITCH_OPS

TRANSFORMS_PATH: Path = Path(__file__).parent / "data" / "transforms.yaml"


@dataclass(frozen=True)
class Notes:
    """Immutable sequence of notes with pitches and durations."""
    pitches: tuple[int, ...]
    durations: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        assert len(self.pitches) == len(self.durations), (
            f"pitches ({len(self.pitches)}) and durations ({len(self.durations)}) "
            "must have same length"
        )


class Transform:
    """YAML-driven melodic transformation."""

    _cache: dict[str, dict[str, Any]] = {}

    def __init__(self, name: str) -> None:
        self.name: str = name
        spec: dict[str, Any] = self._load_spec(name)
        self.pitch_op: str | None = spec.get('pitch')
        self.duration_op: str | None = spec.get('duration')
        self.slice_n: int | None = spec.get('slice')  # positive=head, negative=tail
        self.transpose_n: int | None = None
        self._validate_spec()

    def _validate_spec(self) -> None:
        """Validate operations at construction time. Fail fast on bad YAML."""
        if self.pitch_op is not None:
            op_name: str = self.pitch_op.split('(')[0]
            assert op_name in VALID_PITCH_OPS, (
                f"Transform '{self.name}': unknown pitch op '{self.pitch_op}'. "
                f"Valid: {sorted(VALID_PITCH_OPS)}"
            )
            if op_name == 'transpose':
                self.transpose_n = int(self._parse_arg(self.pitch_op))

        if self.duration_op is not None:
            assert self.duration_op in VALID_DURATION_OPS, (
                f"Transform '{self.name}': unknown duration op '{self.duration_op}'. "
                f"Valid: {sorted(VALID_DURATION_OPS)}"
            )

    @classmethod
    def _load_spec(cls, name: str) -> dict[str, str]:
        """Load transform spec from YAML, with caching."""
        if not cls._cache:
            f: TextIO
            with open(TRANSFORMS_PATH, encoding='utf-8') as f:
                loaded: Any = yaml.safe_load(f)
            assert loaded is not None, f"Empty YAML file: {TRANSFORMS_PATH}"
            assert isinstance(loaded, dict), f"Expected dict in {TRANSFORMS_PATH}, got {type(loaded).__name__}"
            cls._cache = loaded
        assert name in cls._cache, (
            f"Unknown transform: '{name}'. Available: {sorted(cls._cache.keys())}"
        )
        spec: Any = cls._cache[name]
        if spec is None:
            return {}
        assert isinstance(spec, dict), (
            f"Transform '{name}' spec must be dict, got {type(spec).__name__}"
        )
        return spec

    def apply(self, notes: Notes, **kwargs: Any) -> Notes:
        """Apply transform to notes.

        Required kwargs by operation:
        - negate: pivot (int) - the pitch to invert around
        - transpose: n (int) - semitones to transpose (overrides YAML default)
        """
        pitches: tuple[int, ...] = notes.pitches
        durations: tuple[Fraction, ...] = notes.durations

        # Apply slice first (head/tail)
        if self.slice_n is not None:
            if self.slice_n > 0:
                pitches = pitches[:self.slice_n]
                durations = durations[:self.slice_n]
            else:
                pitches = pitches[self.slice_n:]
                durations = durations[self.slice_n:]

        pitches = self._transform_pitch(pitches, **kwargs)
        durations = self._transform_duration(durations)
        return Notes(pitches, durations)

    def _transform_pitch(self, pitches: tuple[int, ...], **kwargs: Any) -> tuple[int, ...]:
        """Apply pitch operation."""
        if self.pitch_op is None:
            return pitches

        if self.pitch_op == 'negate':
            assert 'pivot' in kwargs, f"Transform '{self.name}': 'negate' requires 'pivot' kwarg"
            pivot: Any = kwargs['pivot']
            assert isinstance(pivot, int), (
                f"Transform '{self.name}': pivot must be int, got {type(pivot).__name__}"
            )
            return tuple(2 * pivot - p for p in pitches)

        if self.pitch_op == 'reverse':
            return pitches[::-1]

        if self.pitch_op.startswith('transpose'):
            n: int
            if 'n' in kwargs:
                n_val: Any = kwargs['n']
                assert isinstance(n_val, int), (
                    f"Transform '{self.name}': n must be int, got {type(n_val).__name__}"
                )
                n = n_val
            elif self.transpose_n is not None:
                n = self.transpose_n
            else:
                assert False, f"Transform '{self.name}': 'transpose' requires 'n' kwarg or YAML arg"
            return tuple(p + n for p in pitches)

        assert False, f"Unknown pitch op: {self.pitch_op}"

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

        assert False, f"Unknown duration op: {self.duration_op}"

    @staticmethod
    def _parse_arg(op: str) -> Fraction:
        """Parse argument from operation string like 'transpose(3)'."""
        start: int = op.find('(')
        end: int = op.find(')')
        assert start != -1 and end != -1, f"Cannot parse argument from: '{op}'. Expected format: 'op(arg)'"
        assert end > start + 1, f"Empty argument in: '{op}'"
        return Fraction(op[start + 1:end])


def notes_from_node(node: Node) -> Notes:
    """Extract Notes from a subject/motif node with pitches or degrees and durations.

    Supports both:
    - pitches: MIDI pitch values (preserves contour)
    - degrees: Scale degrees 1-7 (legacy format)
    """
    has_pitches: bool = 'pitches' in node
    has_degrees: bool = 'degrees' in node
    assert has_pitches or has_degrees, (
        f"Node missing 'pitches' or 'degrees' key at {node.path_string()}"
    )
    assert 'durations' in node, f"Node missing 'durations' key at {node.path_string()}"

    pitches: list[int] = []
    pitch_key: str = 'pitches' if has_pitches else 'degrees'
    for c in node[pitch_key].children:
        assert isinstance(c.value, int), (
            f"{pitch_key} value must be int, got {type(c.value).__name__} at {c.path_string()}"
        )
        pitches.append(c.value)

    durations: list[Fraction] = []
    for c in node['durations'].children:
        assert isinstance(c.value, (int, float, str)), (
            f"Duration must be numeric or string, got {type(c.value).__name__} at {c.path_string()}"
        )
        durations.append(validate_duration(Fraction(c.value)))

    return Notes(tuple(pitches), tuple(durations))


def notes_to_dicts(notes: Notes) -> list[dict[str, Any]]:
    """Convert Notes to list of note dicts for tree insertion."""
    return [
        {'diatonic': p, 'duration': str(d)}
        for p, d in zip(notes.pitches, notes.durations)
    ]

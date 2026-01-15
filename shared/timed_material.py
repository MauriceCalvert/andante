"""TimedMaterial - Budget-First Musical Material.

Core abstraction for duration-safe operations. Invariant: sum(durations) == budget.
All transformations return new TimedMaterial with same budget.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable

from shared.pitch import FloatingNote, Pitch, Rest, is_rest, wrap_degree
from shared.music_math import (
    VALID_DURATIONS,
    VALID_DURATIONS_SORTED,
    fill_slot,
)


@dataclass(frozen=True)
class TimedMaterial:
    """Musical material with explicit time budget.

    Invariant: sum(durations) == budget (always enforced)
    """
    pitches: tuple[Pitch, ...]
    durations: tuple[Fraction, ...]
    budget: Fraction

    def __post_init__(self) -> None:
        actual: Fraction = sum(self.durations)
        if actual != self.budget:
            raise ValueError(
                f"TimedMaterial invariant violated: "
                f"sum(durations)={actual} != budget={self.budget}"
            )
        if len(self.pitches) != len(self.durations):
            raise ValueError(
                f"Length mismatch: {len(self.pitches)} pitches "
                f"vs {len(self.durations)} durations"
            )
        for i, dur in enumerate(self.durations):
            if dur <= 0:
                raise ValueError(f"Non-positive duration at index {i}: {dur}")

    def __len__(self) -> int:
        return len(self.pitches)

    @classmethod
    def repeat_to_budget(
        cls,
        pitches: list[Pitch] | tuple[Pitch, ...],
        durations: list[Fraction] | tuple[Fraction, ...],
        budget: Fraction,
        shift: int = 0,
    ) -> TimedMaterial:
        """Repeat pattern cyclically to fill budget exactly.

        Args:
            shift: Degree shift to apply (for phrase variation).
        """
        if not pitches or not durations:
            raise ValueError("Cannot repeat empty material")
        pattern_dur: Fraction = sum(durations)
        assert pattern_dur > 0, "Pattern duration must be positive"
        result_pitch: list[Pitch] = []
        result_dur: list[Fraction] = []
        remaining: Fraction = budget
        idx: int = 0
        while remaining > 0:
            note_dur: Fraction = durations[idx % len(durations)]
            p: Pitch = pitches[idx % len(pitches)]
            if shift != 0 and not is_rest(p):
                assert isinstance(p, FloatingNote)
                p = FloatingNote(wrap_degree(p.degree + shift))
            if note_dur <= remaining:
                result_pitch.append(p)
                result_dur.append(note_dur)
                remaining -= note_dur
            else:
                result_pitch.append(p)
                result_dur.append(remaining)
                remaining = Fraction(0)
            idx += 1
        return cls(tuple(result_pitch), tuple(result_dur), budget)

    def shift(self, interval: int) -> TimedMaterial:
        """Shift all degrees by interval, wrapping to 1-7."""
        def shift_pitch(p: Pitch) -> Pitch:
            if is_rest(p):
                return p
            assert isinstance(p, FloatingNote)
            return FloatingNote(wrap_degree(p.degree + interval))
        return TimedMaterial(
            tuple(shift_pitch(p) for p in self.pitches),
            self.durations,
            self.budget,
        )

    def invert(self, axis: int = 4) -> TimedMaterial:
        """Invert around axis degree."""
        def invert_pitch(p: Pitch) -> Pitch:
            if is_rest(p):
                return p
            assert isinstance(p, FloatingNote)
            return FloatingNote(wrap_degree(2 * axis - p.degree))
        return TimedMaterial(
            tuple(invert_pitch(p) for p in self.pitches),
            self.durations,
            self.budget,
        )

    def retrograde(self) -> TimedMaterial:
        """Reverse the material."""
        return TimedMaterial(
            tuple(reversed(self.pitches)),
            tuple(reversed(self.durations)),
            self.budget,
        )

    def head(self, n: int) -> TimedMaterial:
        """Take first n notes as fragment."""
        assert 0 < n <= len(self.pitches), f"Invalid head size: {n}"
        pitches: tuple[Pitch, ...] = self.pitches[:n]
        durations: tuple[Fraction, ...] = self.durations[:n]
        budget: Fraction = sum(durations, Fraction(0))
        return TimedMaterial(pitches, durations, budget)

    def tail(self, n: int) -> TimedMaterial:
        """Take last n notes as fragment."""
        assert 0 < n <= len(self.pitches), f"Invalid tail size: {n}"
        pitches: tuple[Pitch, ...] = self.pitches[-n:]
        durations: tuple[Fraction, ...] = self.durations[-n:]
        budget: Fraction = sum(durations, Fraction(0))
        return TimedMaterial(pitches, durations, budget)

    def augment(self) -> TimedMaterial:
        """Double all durations (augmentation)."""
        new_durs: tuple[Fraction, ...] = tuple(d * 2 for d in self.durations)
        new_budget: Fraction = self.budget * 2
        return TimedMaterial(self.pitches, new_durs, new_budget)

    def diminish(self, min_dur: Fraction | None = None) -> TimedMaterial:
        """Halve all durations (diminution), with optional floor.

        Args:
            min_dur: Minimum duration for any note. If None, no floor applied.
        """
        if min_dur is None:
            new_durs: tuple[Fraction, ...] = tuple(d / 2 for d in self.durations)
        else:
            new_durs = tuple(max(d / 2, min_dur) for d in self.durations)
        new_budget: Fraction = sum(new_durs)
        return TimedMaterial(self.pitches, new_durs, new_budget)

    @classmethod
    def concatenate(cls, first: TimedMaterial, second: TimedMaterial) -> TimedMaterial:
        """Concatenate two TimedMaterial instances into one.

        The resulting budget is the sum of both budgets.
        """
        pitches: tuple[Pitch, ...] = first.pitches + second.pitches
        durations: tuple[Fraction, ...] = first.durations + second.durations
        budget: Fraction = first.budget + second.budget
        return cls(pitches, durations, budget)

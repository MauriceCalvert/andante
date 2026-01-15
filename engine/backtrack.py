"""Backtracking system for constraint satisfaction in realisation."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class Choice:
    """A choice point with alternatives."""
    location: str
    alternatives: list[int]
    current_idx: int = 0

    @property
    def current(self) -> int:
        return self.alternatives[self.current_idx]

    @property
    def exhausted(self) -> bool:
        return self.current_idx >= len(self.alternatives) - 1

    def next(self) -> int | None:
        if self.exhausted:
            return None
        self.current_idx += 1
        return self.current


@dataclass
class BacktrackState:
    """State for backtracking through choices."""
    choices: list[Choice] = field(default_factory=list)
    max_backtracks: int = 10
    backtrack_count: int = 0

    def add_choice(self, location: str, alternatives: list[int]) -> int:
        """Add a choice point, return the first alternative."""
        choice = Choice(location=location, alternatives=alternatives)
        self.choices.append(choice)
        return choice.current

    def backtrack(self) -> bool:
        """Try next alternative at most recent non-exhausted choice.

        Returns True if backtrack succeeded, False if all exhausted.
        """
        if self.backtrack_count >= self.max_backtracks:
            return False
        while self.choices:
            choice = self.choices[-1]
            next_alt = choice.next()
            if next_alt is not None:
                self.backtrack_count += 1
                return True
            self.choices.pop()
        return False

    def clear(self) -> None:
        self.choices = []
        self.backtrack_count = 0


def octave_alternatives(base_pitch: int, median: int) -> list[int]:
    """Generate octave alternatives for a pitch, ordered by distance from median."""
    alternatives: list[int] = []
    for octave_shift in [0, -12, 12, -24, 24]:
        candidate: int = base_pitch + octave_shift
        if 21 <= candidate <= 108:
            alternatives.append(candidate)
    alternatives.sort(key=lambda p: abs(p - median))
    return alternatives


def choose_octave(state: BacktrackState, location: str, base_pitch: int, median: int) -> int:
    """Choose octave with backtracking support."""
    alternatives = octave_alternatives(base_pitch, median)
    if not alternatives:
        return base_pitch
    return state.add_choice(location, alternatives)

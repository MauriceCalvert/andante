"""Voice pair types for constraint checking.

v6: No priority filtering - all pairs checked equally (L004).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class VoicePair:
    """A pair of voices to check for constraint violations."""
    upper_index: int
    lower_index: int


@dataclass(frozen=True)
class VoicePairSet:
    """All voice pairs for a given voice count."""
    pairs: tuple[VoicePair, ...]

    @staticmethod
    def compute(n: int) -> "VoicePairSet":
        """Generate all voice pairs for n voices.

        All pairs checked equally - no priority filtering.
        Returns n*(n-1)/2 pairs.
        """
        assert n >= 2, "Need at least 2 voices"
        pairs: list[VoicePair] = []
        for i in range(n):
            for j in range(i + 1, n):
                pairs.append(VoicePair(i, j))
        return VoicePairSet(pairs=tuple(pairs))

    @property
    def count(self) -> int:
        return len(self.pairs)

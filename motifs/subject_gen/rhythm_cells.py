"""Baroque rhythm cell definitions and transition table.

Cells are the atomic rhythmic units from which subject durations are built.
The transition table encodes which cell successions are idiomatic (Y),
acceptable with penalty (W), or forbidden (N).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Cell:
    """A named rhythmic cell with a fixed number of notes and tick pattern."""

    name: str
    ticks: tuple[int, ...]

    @property
    def notes(self) -> int:
        """Number of notes in this cell."""
        return len(self.ticks)


# ── Cell definitions at 1x scale ─────────────────────────────────────

LONGA: Cell = Cell(name="longa", ticks=(2,))
PYRRHIC: Cell = Cell(name="pyrrhic", ticks=(1, 1))
IAMB: Cell = Cell(name="iamb", ticks=(1, 2))
SPONDEE: Cell = Cell(name="spondee", ticks=(2, 2))
TROCHEE: Cell = Cell(name="trochee", ticks=(2, 1))
DOTTED: Cell = Cell(name="dotted", ticks=(3, 1))
SNAP: Cell = Cell(name="snap", ticks=(1, 3))
TRIBRACH: Cell = Cell(name="tribrach", ticks=(1, 1, 1))
DACTYL: Cell = Cell(name="dactyl", ticks=(2, 1, 1))
AMPHIBRACH: Cell = Cell(name="amphibrach", ticks=(1, 2, 1))
ANAPAEST: Cell = Cell(name="anapaest", ticks=(1, 1, 2))
TIRATA: Cell = Cell(name="tirata", ticks=(1, 1, 1, 1))

ALL_CELLS: tuple[Cell, ...] = (
    LONGA, PYRRHIC, IAMB, SPONDEE, TROCHEE, DOTTED, SNAP,
    TRIBRACH, DACTYL, AMPHIBRACH, ANAPAEST, TIRATA,
)

# ── Cells grouped by note count ──────────────────────────────────────

CELLS_BY_SIZE: dict[int, list[Cell]] = {}
for _cell in ALL_CELLS:
    CELLS_BY_SIZE.setdefault(_cell.notes, []).append(_cell)

# ── Transition table ─────────────────────────────────────────────────
# Y = 1.0 (good), W = 0.5 (acceptable with penalty), N = 0.0 (forbidden)
#
# Governing principles:
#   - Same cell repeated: N or W (monotony)
#   - Ending strong + starting strong: N (stodgy)
#   - Ending weak + starting strong: Y (natural resolution)
#   - Ending strong + starting weak: Y (good contrast)
#   - All-short cells (pyrrhic, tribrach, tirata) must not chain
#     into each other: use tirata instead
#   - Longa is a single held note; it chains well after motion
#     but consecutive longas are forbidden (monotony).

_Y: float = 1.0
_W: float = 0.5
_N: float = 0.0

_CELL_NAMES: tuple[str, ...] = (
    "longa", "pyrrhic", "iamb", "spondee", "trochee", "dotted", "snap",
    "tribrach", "dactyl", "amphibrach", "anapaest", "tirata",
)

# fmt: off
_TRANSITION_MATRIX: tuple[tuple[float, ...], ...] = (
    # long  pyrr  iamb spond troch dottd snap  tribr dctyl amphi anap  tir
    (_N, _Y, _Y, _W, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y),  # from longa
    (_Y, _N, _Y, _Y, _Y, _Y, _Y, _N, _Y, _Y, _Y, _N),  # from pyrrhic
    (_Y, _W, _W, _Y, _Y, _Y, _W, _W, _Y, _Y, _W, _Y),  # from iamb
    (_Y, _Y, _Y, _N, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y),  # from spondee
    (_Y, _Y, _Y, _Y, _W, _W, _Y, _Y, _N, _W, _Y, _Y),  # from trochee
    (_Y, _Y, _Y, _Y, _W, _N, _Y, _Y, _W, _Y, _Y, _Y),  # from dotted
    (_Y, _Y, _Y, _N, _W, _N, _W, _Y, _Y, _Y, _Y, _Y),  # from snap
    (_Y, _N, _Y, _Y, _Y, _Y, _Y, _N, _Y, _Y, _Y, _N),  # from tribrach
    (_Y, _Y, _Y, _Y, _W, _Y, _Y, _Y, _W, _Y, _Y, _Y),  # from dactyl
    (_Y, _Y, _Y, _Y, _W, _Y, _Y, _Y, _W, _W, _Y, _Y),  # from amphibrach
    (_Y, _Y, _Y, _Y, _W, _Y, _Y, _Y, _Y, _Y, _N, _W),  # from anapaest
    (_Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _Y, _N),  # from tirata
)
# fmt: on

TRANSITION: dict[tuple[str, str], float] = {
    (_CELL_NAMES[r], _CELL_NAMES[c]): _TRANSITION_MATRIX[r][c]
    for r in range(len(_CELL_NAMES))
    for c in range(len(_CELL_NAMES))
}

# ── Available uniform scaling factors ────────────────────────────────

SCALES: tuple[int, ...] = (1, 2, 4)

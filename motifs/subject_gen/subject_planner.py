"""Subject planner — structural design for fugue subjects.

A subject is not N independent notes. It is a head motif and a tail,
both drawing from a shared rhythmic and intervallic vocabulary.  The
planner chooses the vocabulary and specifies how head and tail deploy
it differently.

The existing duration and pitch generators become segment-level tools
executing the planner's specs.
"""
import logging
from dataclasses import dataclass
from itertools import combinations

from motifs.subject_gen.constants import (
    MAX_SUBJECT_NOTES,
    MIN_SUBJECT_NOTES,
)
from motifs.subject_gen.rhythm_cells import ALL_CELLS, Cell, SCALES

logger: logging.Logger = logging.getLogger(__name__)

# ── Contour types ────────────────────────────────────────────────────

CONTOURS: tuple[str, ...] = ("ascending", "descending", "arch", "dip")

# ── Motion types ─────────────────────────────────────────────────────

MOTION_ARPEGGIATED: str = "arpeggiated"
MOTION_STEPWISE: str = "stepwise"
MOTION_MIXED: str = "mixed"
ALL_MOTIONS: tuple[str, ...] = (MOTION_ARPEGGIATED, MOTION_STEPWISE, MOTION_MIXED)

# ── Signature intervals (diatonic steps) ─────────────────────────────

SIGNATURE_INTERVALS: tuple[int, ...] = (2, 3, 4)  # third, fourth, fifth

# ── Cell names that provide arpeggiated motion ───────────────────────

_ARPEGGIO_CELLS: frozenset[str] = frozenset({"spondee"})

# ── Head/tail note count ranges ──────────────────────────────────────

MIN_HEAD_NOTES: int = 4
MAX_HEAD_NOTES: int = 7
MIN_TAIL_NOTES: int = 3
MIN_NOTE_COUNT_DIFFERENCE: int = 2

# ── Contrasting contour pairs ────────────────────────────────────────
# For each head contour, which tail contours provide contrast.

_CONTOUR_CONTRAST: dict[str, tuple[str, ...]] = {
    "ascending": ("descending", "dip"),
    "descending": ("ascending", "arch"),
    "arch": ("dip", "descending"),
    "dip": ("arch", "ascending"),
}

# ── Density levels ───────────────────────────────────────────────────

DENSITY_SPARSE: str = "sparse"
DENSITY_MEDIUM: str = "medium"
DENSITY_DENSE: str = "dense"

# Sparse = scale 2 only; medium = mostly scale 2 with some scale 1;
# dense = must include scale 1 cells.
_DENSITY_SCALES: dict[str, tuple[int, ...]] = {
    DENSITY_SPARSE: (2,),
    DENSITY_MEDIUM: (1, 2),
    DENSITY_DENSE: (1, 2),
}

ALL_DENSITIES: tuple[str, ...] = (DENSITY_SPARSE, DENSITY_MEDIUM, DENSITY_DENSE)


# ── Data structures ──────────────────────────────────────────────────

@dataclass(frozen=True)
class SubjectVocabulary:
    """The shared DNA of a subject — what makes head and tail sound related."""

    cells: tuple[str, ...]
    signature_interval: int
    motion: str

    # density removed — now lives on SegmentSpec (SUB-2)


@dataclass(frozen=True)
class SegmentSpec:
    """Deployment of vocabulary for one segment (head or tail)."""

    n_notes: int
    contour: str
    must_have_signature: bool
    density: str

    @property
    def allowed_scales(self) -> tuple[int, ...]:
        """Which scale factors are available for this density."""
        return _DENSITY_SCALES[self.density]

    def __post_init__(self) -> None:
        assert self.contour in CONTOURS, (
            f"contour must be one of {CONTOURS}, got {self.contour!r}"
        )
        assert self.density in ALL_DENSITIES, (
            f"density must be one of {ALL_DENSITIES}, got {self.density!r}"
        )


@dataclass(frozen=True)
class SubjectPlan:
    """Complete structural plan for a subject."""

    vocabulary: SubjectVocabulary
    head: SegmentSpec
    tail: SegmentSpec

    @property
    def total_notes(self) -> int:
        """Total note count for this plan."""
        return self.head.n_notes + self.tail.n_notes


# ── Cell lookup ──────────────────────────────────────────────────────

_CELLS_BY_NAME: dict[str, Cell] = {c.name: c for c in ALL_CELLS}


def cells_from_names(names: tuple[str, ...]) -> tuple[Cell, ...]:
    """Resolve cell names to Cell objects."""
    return tuple(_CELLS_BY_NAME[n] for n in names)


# ── Plan generation ──────────────────────────────────────────────────

def _is_valid_vocabulary(
    cell_names: tuple[str, ...],
    motion: str,
) -> bool:
    """Check that a cell set is consistent with the motion type."""
    has_arpeggio: bool = bool(_ARPEGGIO_CELLS & set(cell_names))
    if motion == MOTION_ARPEGGIATED and not has_arpeggio:
        return False
    if motion == MOTION_STEPWISE and has_arpeggio:
        return False
    return True


def _valid_note_splits(
    total_notes: int,
) -> list[tuple[int, int]]:
    """Return valid (head_notes, tail_notes) splits."""
    splits: list[tuple[int, int]] = []
    for head_n in range(MIN_HEAD_NOTES, MAX_HEAD_NOTES + 1):
        tail_n: int = total_notes - head_n
        if tail_n >= MIN_TAIL_NOTES and abs(head_n - tail_n) >= MIN_NOTE_COUNT_DIFFERENCE:
            splits.append((head_n, tail_n))
    return splits


def generate_plans(
    total_notes_range: tuple[int, ...] | None = None,
) -> list[SubjectPlan]:
    """Generate all structurally valid subject plans.

    Each plan combines a vocabulary with contrasting head/tail deployment.
    Plans are not scored here — that happens downstream when rhythm and
    pitch are realised.
    """
    if total_notes_range is None:
        total_notes_range = tuple(
            range(MIN_SUBJECT_NOTES, MAX_SUBJECT_NOTES + 1)
        )

    plans: list[SubjectPlan] = []
    all_cell_names: list[str] = [c.name for c in ALL_CELLS]

    # Enumerate 2-cell and 3-cell vocabularies.
    cell_combos: list[tuple[str, ...]] = []
    for r in (2, 3):
        for combo in combinations(all_cell_names, r):
            cell_combos.append(combo)

    for cell_names in cell_combos:
        for motion in ALL_MOTIONS:
            if not _is_valid_vocabulary(cell_names=cell_names, motion=motion):
                continue
            for sig_interval in SIGNATURE_INTERVALS:
                vocab = SubjectVocabulary(
                    cells=cell_names,
                    signature_interval=sig_interval,
                    motion=motion,
                )
                for head_density in ALL_DENSITIES:
                    for tail_density in ALL_DENSITIES:
                        if head_density == tail_density:
                            continue  # SUB-2: force density contrast
                        for total_n in total_notes_range:
                            for head_n, tail_n in _valid_note_splits(total_n):
                                for head_contour in CONTOURS:
                                    for tail_contour in _CONTOUR_CONTRAST[head_contour]:
                                        head = SegmentSpec(
                                            n_notes=head_n,
                                            contour=head_contour,
                                            must_have_signature=True,
                                            density=head_density,
                                        )
                                        tail = SegmentSpec(
                                            n_notes=tail_n,
                                            contour=tail_contour,
                                            must_have_signature=False,
                                            density=tail_density,
                                        )
                                        plans.append(SubjectPlan(
                                            vocabulary=vocab,
                                            head=head,
                                            tail=tail,
                                        ))

    logger.info(
        "generate_plans: %d plans from %d vocabularies",
        len(plans), len(cell_combos),
    )
    return plans

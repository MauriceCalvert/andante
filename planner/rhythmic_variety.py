"""Rhythmic variety validators.

Hard constraints ensuring rhythmic planning does not produce
monotonous output. Per D010: guards detect, generators prevent.
"""
import logging
from fractions import Fraction
from builder.types import GapRhythm, RhythmicMotif, RhythmicProfile

logger = logging.getLogger(__name__)


def _durations_differ(
    a: tuple[Fraction, ...],
    b: tuple[Fraction, ...],
) -> bool:
    """Return True if two duration tuples differ in length or content."""
    if len(a) != len(b):
        return True
    return any(x != y for x, y in zip(a, b))


def validate_no_consecutive_identical(
    gap_rhythms: list[GapRhythm],
) -> None:
    """V-R001: No consecutive identical rhythm patterns."""
    for i in range(len(gap_rhythms) - 1):
        current: tuple[Fraction, ...] = gap_rhythms[i].durations
        next_gap: tuple[Fraction, ...] = gap_rhythms[i + 1].durations
        assert _durations_differ(a=current, b=next_gap), (
            f"V-R001 violation: identical rhythms at gaps {i} and {i + 1}: "
            f"{current}"
        )


def validate_motif_variation(
    phrase_motifs: list[tuple[int, RhythmicMotif]],
) -> None:
    """V-R002: Phrases after the second must develop the base motif."""
    if len(phrase_motifs) < 4:
        return
    base_motif: RhythmicMotif | None = None
    for phrase_idx, motif in phrase_motifs:
        if phrase_idx == 0:
            base_motif = motif
        elif phrase_idx >= 3 and base_motif is not None:
            assert motif.pattern != base_motif.pattern, (
                f"V-R002 violation: phrase {phrase_idx} uses literal base motif "
                f"'{base_motif.name}'"
            )


def validate_cadential_change(
    gap_rhythms: list[GapRhythm],
    cadence_gap_indices: set[int],
) -> None:
    """V-R003: Rhythm must change near cadences compared to 2 gaps prior."""
    for i in cadence_gap_indices:
        if i < 2 or i >= len(gap_rhythms):
            continue
        current: tuple[Fraction, ...] = gap_rhythms[i].durations
        prior: tuple[Fraction, ...] = gap_rhythms[i - 2].durations
        assert _durations_differ(a=current, b=prior), (
            f"V-R003 violation: no rhythmic change before cadence at gap {i}"
        )


def validate_density_arc(
    profile: RhythmicProfile,
    gap_rhythms: list[GapRhythm],
    section_start_gap: int,
) -> None:
    """V-R004: Density peak should be in the middle third for arc trajectories."""
    if profile.density_trajectory != "arc":
        return
    if len(gap_rhythms) < 4:
        return
    densities: list[float] = []
    for r in gap_rhythms:
        total_dur: Fraction = sum(r.durations)
        if total_dur > 0:
            densities.append(len(r.durations) / float(total_dur))
        else:
            densities.append(0.0)
    peak_idx: int = densities.index(max(densities))
    third: int = len(densities) // 3
    if third == 0:
        return
    assert third <= peak_idx <= 2 * third, (
        f"V-R004 violation: density arc peak at local gap {peak_idx} "
        f"(absolute gap {section_start_gap + peak_idx}), "
        f"expected in [{third}, {2 * third}]"
    )


def validate_phrase_continuity(
    gap_rhythms: list[GapRhythm],
    phrase_boundary_gaps: list[int],
) -> None:
    """V-R005: No rhythmic seam at phrase boundaries."""
    for boundary_gap in phrase_boundary_gaps:
        if boundary_gap <= 0 or boundary_gap >= len(gap_rhythms):
            continue
        final_dur: Fraction = gap_rhythms[boundary_gap - 1].durations[-1]
        initial_dur: Fraction = gap_rhythms[boundary_gap].durations[0]
        seam: bool = (
            final_dur >= Fraction(1, 4)
            and initial_dur >= Fraction(1, 4)
            and final_dur == initial_dur
        )
        assert not seam, (
            f"V-R005 violation: rhythmic seam at phrase boundary gap {boundary_gap}: "
            f"final={final_dur}, initial={initial_dur}"
        )


def validate_all(
    gap_rhythms: list[GapRhythm],
    phrase_motifs: list[tuple[int, RhythmicMotif]],
    profile: RhythmicProfile,
    cadence_gap_indices: set[int],
    phrase_boundary_gaps: list[int],
    section_start_gap: int,
) -> None:
    """Run all variety validators."""
    validate_no_consecutive_identical(gap_rhythms=gap_rhythms)
    validate_motif_variation(phrase_motifs=phrase_motifs)
    validate_cadential_change(
        gap_rhythms=gap_rhythms,
        cadence_gap_indices=cadence_gap_indices,
    )
    validate_density_arc(
        profile=profile,
        gap_rhythms=gap_rhythms,
        section_start_gap=section_start_gap,
    )
    validate_phrase_continuity(
        gap_rhythms=gap_rhythms,
        phrase_boundary_gaps=phrase_boundary_gaps,
    )

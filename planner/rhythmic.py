"""Layer 6: Hierarchical Rhythmic Planning.

Produces a RhythmPlan with three levels:
  1. Section profiles (affect + section function -> rhythmic character)
  2. Phrase motifs (selected and developed per phrase)
  3. Gap rhythms (derived from phrase motifs)

Input:  Anchors, AffectConfig, PassageAssignments, GenreConfig, TonalPlan
Output: RhythmPlan

Per A005: RNG lives here; downstream executor is deterministic.
"""
import logging
from fractions import Fraction
from typing import Sequence
from builder.types import (
    AffectConfig,
    Anchor,
    GapRhythm,
    GenreConfig,
    PassageAssignment,
    RhythmicMotif,
    RhythmicProfile,
    RhythmPlan,
    TonalPlan,
)
from planner.rhythmic_gap import derive_gap_rhythm
from planner.rhythmic_motif import (
    develop_motif,
    load_motif_vocabulary,
    select_motif,
)
from planner.rhythmic_profile import compute_section_profile

logger = logging.getLogger(__name__)


def _get_section_function(
    passage_assignments: Sequence[PassageAssignment] | None,
    bar_num: int,
) -> str:
    """Get section function for a bar from passage assignments."""
    if passage_assignments is None:
        return "subject"
    for pa in passage_assignments:
        if pa.start_bar <= bar_num < pa.end_bar:
            return pa.function
    return "subject"


def _has_cadence_near(
    anchors: Sequence[Anchor],
    start_idx: int,
    end_idx: int,
) -> bool:
    """Check if any anchor in range is near a cadence schema."""
    for i in range(start_idx, min(end_idx + 1, len(anchors))):
        if "cadenz" in anchors[i].schema.lower():
            return True
    return False


def _bar_from_anchor(anchor: Anchor) -> int:
    """Extract bar number from anchor bar_beat string."""
    return int(anchor.bar_beat.split(".")[0])


def _compute_gap_duration(
    source_bar_beat: str,
    target_bar_beat: str,
    metre: str,
) -> Fraction:
    """Compute duration between two bar.beat positions."""
    num_str, den_str = metre.split("/")
    den: int = int(den_str)
    num: int = int(num_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    s_parts: list[str] = source_bar_beat.split(".")
    s_bar: int = int(s_parts[0])
    s_beat: int = int(s_parts[1])
    t_parts: list[str] = target_bar_beat.split(".")
    t_bar: int = int(t_parts[0])
    t_beat: int = int(t_parts[1])
    source_offset: Fraction = (s_bar - 1) * bar_length + (s_beat - 1) * beat_unit
    target_offset: Fraction = (t_bar - 1) * bar_length + (t_beat - 1) * beat_unit
    return target_offset - source_offset


def _detect_phrase_boundaries(
    passage_assignments: Sequence[PassageAssignment] | None,
    total_gaps: int,
    anchors: Sequence[Anchor],
) -> list[int]:
    """Detect gap indices that start new phrases.

    Each passage assignment boundary defines a phrase boundary.
    Returns sorted list of gap indices where new phrases begin.
    """
    boundaries: list[int] = [0]
    if passage_assignments is None:
        return boundaries
    for pa in passage_assignments:
        for i in range(total_gaps):
            bar_num: int = _bar_from_anchor(anchor=anchors[i])
            if bar_num == pa.start_bar and i not in boundaries:
                boundaries.append(i)
    boundaries.sort()
    return boundaries


def _determine_phrase_position(
    phrase_idx_in_section: int,
    total_phrases_in_section: int,
    has_cadence: bool,
) -> str:
    """Determine phrase position: opening, interior, or cadential."""
    if phrase_idx_in_section == 0:
        return "opening"
    if has_cadence and phrase_idx_in_section == total_phrases_in_section - 1:
        return "cadential"
    return "interior"


def layer_6_rhythmic(
    anchors: Sequence[Anchor],
    affect_config: AffectConfig,
    passage_assignments: Sequence[PassageAssignment] | None,
    genre_config: GenreConfig,
    tonal_plan: TonalPlan,
    seed: int = 42,
) -> RhythmPlan:
    """Execute Layer 6: Generate hierarchical rhythm plan."""
    total_gaps: int = len(anchors) - 1
    if total_gaps <= 0:
        return RhythmPlan(
            section_profiles=(),
            phrase_motifs=(),
            gap_rhythms=(),
        )
    metre: str = genre_config.metre
    affect_name: str = affect_config.name
    tonal_density: str = tonal_plan.density
    vocabulary: list[RhythmicMotif] = load_motif_vocabulary(metre=metre)
    # Detect phrase boundaries from passage assignments
    phrase_boundaries: list[int] = _detect_phrase_boundaries(
        passage_assignments=passage_assignments,
        total_gaps=total_gaps,
        anchors=anchors,
    )
    # Build section profiles for each passage segment
    section_profiles: list[tuple[str, RhythmicProfile]] = []
    profile_by_gap: dict[int, RhythmicProfile] = {}
    if passage_assignments is not None:
        for pa in passage_assignments:
            has_cadence: bool = _has_cadence_near(
                anchors=anchors,
                start_idx=0,
                end_idx=len(anchors) - 1,
            )
            profile: RhythmicProfile = compute_section_profile(
                affect_name=affect_name,
                section_function=pa.function,
                section_start_bar=pa.start_bar,
                section_end_bar=pa.end_bar,
                metre=metre,
                tonal_density=tonal_density,
                has_cadence=has_cadence,
            )
            section_profiles.append((pa.function, profile))
            for gap_idx in range(total_gaps):
                bar_num: int = _bar_from_anchor(anchor=anchors[gap_idx])
                if pa.start_bar <= bar_num < pa.end_bar:
                    profile_by_gap[gap_idx] = profile
    else:
        # Single default profile for entire piece
        first_bar: int = _bar_from_anchor(anchor=anchors[0])
        last_bar: int = _bar_from_anchor(anchor=anchors[-1])
        profile = compute_section_profile(
            affect_name=affect_name,
            section_function="subject",
            section_start_bar=first_bar,
            section_end_bar=last_bar,
            metre=metre,
            tonal_density=tonal_density,
            has_cadence=True,
        )
        section_profiles.append(("subject", profile))
        for gap_idx in range(total_gaps):
            profile_by_gap[gap_idx] = profile
    # Default profile for any gaps not covered
    default_profile: RhythmicProfile = section_profiles[0][1] if section_profiles else compute_section_profile(
        affect_name=affect_name,
        section_function="subject",
        section_start_bar=1,
        section_end_bar=2,
        metre=metre,
        tonal_density=tonal_density,
        has_cadence=False,
    )
    # Select and develop motifs per phrase
    phrase_motifs: list[tuple[int, RhythmicMotif]] = []
    motif_by_gap: dict[int, RhythmicMotif] = {}
    previous_motif_name: str | None = None
    base_motif: RhythmicMotif | None = None
    for phrase_local_idx, phrase_start_gap in enumerate(phrase_boundaries):
        phrase_end_gap: int = (
            phrase_boundaries[phrase_local_idx + 1]
            if phrase_local_idx + 1 < len(phrase_boundaries)
            else total_gaps
        )
        gap_profile: RhythmicProfile = profile_by_gap.get(phrase_start_gap, default_profile)
        # Determine phrase position
        total_phrases: int = len(phrase_boundaries)
        has_cadence_in_section: bool = any(
            "cadenz" in anchors[g].schema.lower()
            for g in range(phrase_start_gap, min(phrase_end_gap + 1, len(anchors)))
        )
        phrase_position: str = _determine_phrase_position(
            phrase_idx_in_section=phrase_local_idx,
            total_phrases_in_section=total_phrases,
            has_cadence=has_cadence_in_section,
        )
        selected: RhythmicMotif = select_motif(
            vocabulary=vocabulary,
            phrase_position=phrase_position,
            profile=gap_profile,
            previous_motif_name=previous_motif_name,
            seed=seed + phrase_local_idx,
        )
        if phrase_local_idx == 0:
            base_motif = selected
        # Apply development for subsequent phrases
        if base_motif is not None and phrase_local_idx > 0:
            developed: RhythmicMotif = develop_motif(
                base=base_motif,
                phrase_idx=phrase_local_idx,
                development_plan=gap_profile.development_plan,
            )
        else:
            developed = selected
        phrase_motifs.append((phrase_local_idx, developed))
        previous_motif_name = developed.name
        # Assign motif to all gaps in this phrase
        for g in range(phrase_start_gap, phrase_end_gap):
            motif_by_gap[g] = developed
    # Derive gap rhythms
    gap_rhythms: list[GapRhythm] = []
    for gap_idx in range(total_gaps):
        gap_profile = profile_by_gap.get(gap_idx, default_profile)
        gap_motif: RhythmicMotif = motif_by_gap.get(gap_idx, vocabulary[0])
        gap_duration: Fraction = _compute_gap_duration(
            source_bar_beat=anchors[gap_idx].bar_beat,
            target_bar_beat=anchors[gap_idx + 1].bar_beat,
            metre=metre,
        )
        assert gap_duration > 0, (
            f"Non-positive gap duration at gap {gap_idx}: "
            f"{anchors[gap_idx].bar_beat} -> {anchors[gap_idx + 1].bar_beat}"
        )
        # Compute position within phrase
        phrase_start: int = 0
        phrase_end: int = total_gaps
        for bi, boundary in enumerate(phrase_boundaries):
            if boundary <= gap_idx:
                phrase_start = boundary
                phrase_end = (
                    phrase_boundaries[bi + 1]
                    if bi + 1 < len(phrase_boundaries)
                    else total_gaps
                )
        phrase_length: int = max(1, phrase_end - phrase_start)
        gap_position: float = (gap_idx - phrase_start) / phrase_length
        gap_fraction: float = 1.0 / phrase_length
        near_cadence: bool = (
            "cadenz" in anchors[gap_idx].schema.lower()
            or "cadenz" in anchors[gap_idx + 1].schema.lower()
        )
        is_downbeat: bool = anchors[gap_idx].bar_beat.endswith(".1")
        gap_rhythm: GapRhythm = derive_gap_rhythm(
            phrase_motif=gap_motif,
            profile=gap_profile,
            gap_position=gap_position,
            gap_fraction=gap_fraction,
            gap_duration=gap_duration,
            is_downbeat=is_downbeat,
            near_cadence=near_cadence,
        )
        gap_rhythms.append(gap_rhythm)
    logger.info(
        "Rhythmic plan: %d section profiles, %d phrase motifs, %d gap rhythms",
        len(section_profiles),
        len(phrase_motifs),
        len(gap_rhythms),
    )
    return RhythmPlan(
        section_profiles=tuple(section_profiles),
        phrase_motifs=tuple(phrase_motifs),
        gap_rhythms=tuple(gap_rhythms),
    )

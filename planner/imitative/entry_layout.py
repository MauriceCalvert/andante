"""Entry layout: converts SubjectPlan to PhrasePlans.

IMP-3. Maps the structural scaffold from SubjectPlan into PhrasePlans
that compose.py can consume. Groups consecutive BarAssignments into
entries/cadences, populates thematic_roles for imitative material.
"""
from __future__ import annotations
from fractions import Fraction

from builder.phrase_types import BeatPosition, PhrasePlan
from builder.types import GenreConfig
from planner.imitative.types import BarAssignment, SubjectPlan, VoiceAssignment
from planner.schema_loader import get_schema
from planner.thematic import BeatRole, ThematicRole
from shared.constants import MIN_SOPRANO_MIDI, VOICE_RANGES
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range


# Map SubjectPlan role strings to ThematicRole enum and material strings
_ROLE_MAP: dict[str, ThematicRole] = {
    "subject": ThematicRole.SUBJECT,
    "answer": ThematicRole.ANSWER,
    "cs": ThematicRole.CS,
    "free": ThematicRole.FREE,
    "cadence": ThematicRole.CADENCE,
    "episode": ThematicRole.EPISODE,
    "pedal": ThematicRole.PEDAL,
    "stretto": ThematicRole.STRETTO,
}

_MATERIAL_MAP: dict[str, str | None] = {
    "subject": "subject",
    "answer": "answer",
    "cs": "countersubject",
    "free": None,
    "cadence": None,
    "episode": "head",
    "pedal": None,
    "stretto": "subject",
}


def build_imitative_plans(
    subject_plan: SubjectPlan,
    genre_config: GenreConfig,
    home_key: Key,
) -> tuple[PhrasePlan, ...]:
    """Convert SubjectPlan to PhrasePlans for compose.py.

    Groups consecutive BarAssignments by entry (same function + voice roles),
    builds PhrasePlan for each group with thematic_roles populated.

    Args:
        subject_plan: Structural plan from plan_subject
        genre_config: Genre configuration
        home_key: Home key of the piece

    Returns:
        Tuple of PhrasePlans in bar order, ready for compose_phrases
    """
    bar_length: Fraction
    beat_unit: Fraction
    bar_length, beat_unit = parse_metre(metre=subject_plan.metre)
    beats_per_bar: int = int(bar_length / beat_unit)

    # Set up voice ranges (hardcoded for 2-voice invention)
    upper_range: Range = Range(low=MIN_SOPRANO_MIDI, high=VOICE_RANGES[0][1])
    lower_range: Range = Range(low=VOICE_RANGES[3][0], high=VOICE_RANGES[3][1])
    upper_median: int = (upper_range.low + upper_range.high) // 2
    lower_median: int = (lower_range.low + lower_range.high) // 2

    # Group consecutive BarAssignments by (function, voice role pattern)
    groups: list[dict] = _group_bar_assignments(bars=subject_plan.bars)

    # Build PhrasePlan for each group
    phrase_plans: list[PhrasePlan] = []
    for group in groups:
        function: str = group["function"]
        first_bar: int = group["first_bar"]
        bar_count: int = group["bar_count"]
        local_key: Key = group["local_key"]
        section_name: str = group["section_name"]
        bar_assignments: list[BarAssignment] = group["bar_assignments"]

        start_offset: Fraction = (first_bar - 1) * bar_length
        phrase_duration: Fraction = bar_count * bar_length

        if function == "cadence":
            # Cadential phrase: use cadenza_composta schema
            cadence_schema = get_schema(name="cadenza_composta")
            phrase_plans.append(PhrasePlan(
                schema_name="cadenza_composta",
                degrees_upper=cadence_schema.soprano_degrees,
                degrees_lower=cadence_schema.bass_degrees,
                degree_positions=_build_cadence_degree_positions(
                    bar_count=bar_count,
                    beats_per_bar=beats_per_bar,
                    soprano_degrees=cadence_schema.soprano_degrees,
                ),
                local_key=home_key,
                bar_span=bar_count,
                start_bar=first_bar,
                start_offset=start_offset,
                phrase_duration=phrase_duration,
                metre=subject_plan.metre,
                rhythm_profile=genre_config.rhythmic_unit or "default",
                is_cadential=True,
                cadence_type="authentic",
                prev_exit_upper=None,
                prev_exit_lower=None,
                section_name=section_name,
                upper_range=upper_range,
                lower_range=lower_range,
                upper_median=upper_median,
                lower_median=lower_median,
                bass_texture=genre_config.bass_treatment,
                thematic_roles=None,
            ))
        else:
            # Entry phrase: populate thematic_roles
            thematic_roles: tuple[BeatRole, ...] = _build_thematic_roles(
                bar_assignments=bar_assignments,
                beats_per_bar=beats_per_bar,
                beat_unit=beat_unit,
            )
            phrase_plans.append(PhrasePlan(
                schema_name="subject_entry",
                degrees_upper=(),
                degrees_lower=(),
                degree_positions=(),
                local_key=local_key,
                bar_span=bar_count,
                start_bar=first_bar,
                start_offset=start_offset,
                phrase_duration=phrase_duration,
                metre=subject_plan.metre,
                rhythm_profile=genre_config.rhythmic_unit or "default",
                is_cadential=False,
                cadence_type=None,
                prev_exit_upper=None,
                prev_exit_lower=None,
                section_name=section_name,
                upper_range=upper_range,
                lower_range=lower_range,
                upper_median=upper_median,
                lower_median=lower_median,
                bass_texture="contrapuntal",
                thematic_roles=thematic_roles,
            ))

    return tuple(phrase_plans)


def _group_bar_assignments(bars: tuple[BarAssignment, ...]) -> list[dict]:
    """Group consecutive BarAssignments by (function, voice role pattern).

    Returns list of group dicts with:
    - function: str
    - first_bar: int
    - bar_count: int
    - local_key: Key
    - section_name: str
    - bar_assignments: list[BarAssignment]
    """
    groups: list[dict] = []
    current_group: dict | None = None

    for bar_assignment in bars:
        function: str = bar_assignment.function
        # Extract voice role pattern (frozenset for comparison)
        voice_roles: frozenset[str] = frozenset(
            va.role for va in bar_assignment.voices.values()
        )

        if current_group is None:
            # Start first group
            current_group = {
                "function": function,
                "first_bar": bar_assignment.bar,
                "bar_count": 1,
                "local_key": bar_assignment.local_key,
                "section_name": bar_assignment.section,
                "voice_roles": voice_roles,
                "bar_assignments": [bar_assignment],
            }
        elif (function != current_group["function"] or
              voice_roles != current_group["voice_roles"]):
            # Pattern changed, close current group and start new one
            groups.append(current_group)
            current_group = {
                "function": function,
                "first_bar": bar_assignment.bar,
                "bar_count": 1,
                "local_key": bar_assignment.local_key,
                "section_name": bar_assignment.section,
                "voice_roles": voice_roles,
                "bar_assignments": [bar_assignment],
            }
        else:
            # Same pattern, extend current group
            current_group["bar_count"] += 1
            current_group["bar_assignments"].append(bar_assignment)

    # Close last group
    if current_group is not None:
        groups.append(current_group)

    return groups


def _build_cadence_degree_positions(
    bar_count: int,
    beats_per_bar: int,
    soprano_degrees: tuple[int, ...],
) -> tuple[BeatPosition, ...]:
    """Build degree_positions for cadence phrase.

    Distributes schema degrees evenly across available beats.
    """
    total_beats: int = bar_count * beats_per_bar
    degree_count: int = len(soprano_degrees)

    positions: list[BeatPosition] = []
    for i in range(degree_count):
        # Distribute degrees evenly across beats
        beat_idx: int = i * total_beats // degree_count
        bar_num: int = beat_idx // beats_per_bar + 1
        beat_in_bar: int = beat_idx % beats_per_bar + 1
        positions.append(BeatPosition(bar=bar_num, beat=beat_in_bar))

    return tuple(positions)


def _build_thematic_roles(
    bar_assignments: list[BarAssignment],
    beats_per_bar: int,
    beat_unit: Fraction,
) -> tuple[BeatRole, ...]:
    """Build BeatRole tuple for an entry group.

    Creates BeatRole for each bar × beat × voice.
    """
    roles: list[BeatRole] = []

    for bar_assignment in bar_assignments:
        bar_num: int = bar_assignment.bar

        for beat_idx in range(beats_per_bar):
            beat_offset: Fraction = Fraction(beat_idx) * beat_unit

            for voice_idx in (0, 1):
                voice_assignment: VoiceAssignment = bar_assignment.voices[voice_idx]

                # Map role string to ThematicRole
                role_str: str = voice_assignment.role
                assert role_str in _ROLE_MAP, (
                    f"Unknown role '{role_str}' in BarAssignment bar {bar_num}, "
                    f"voice {voice_idx}. Expected: {sorted(_ROLE_MAP.keys())}"
                )

                thematic_role: ThematicRole = _ROLE_MAP[role_str]
                material: str | None = _MATERIAL_MAP[role_str]

                # Override material for episode, pedal, and stretto roles (read from VoiceAssignment.fragment)
                if role_str == "episode":
                    material = voice_assignment.fragment  # "head" or "tail"
                elif role_str == "pedal":
                    material = voice_assignment.fragment  # degree as string, e.g. "5"
                elif role_str == "stretto":
                    material = voice_assignment.fragment  # delay as string, e.g. "2"

                roles.append(BeatRole(
                    bar=bar_num,
                    beat=beat_offset,
                    voice=voice_idx,
                    role=thematic_role,
                    material=material,
                    material_key=voice_assignment.material_key,
                    sequence_type="tonal",
                    pairing=voice_assignment.pairing,
                    texture=voice_assignment.texture,
                    fragment_iteration=voice_assignment.fragment_iteration,
                    anchor_pitch=None,
                ))

    return tuple(roles)

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
    "hold": ThematicRole.HOLD,
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
    "hold": None,
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

    # Stamp ALL BeatRoles from ALL BarAssignments first
    all_beat_roles: tuple[BeatRole, ...] = _build_thematic_roles(
        bar_assignments=list(subject_plan.bars),
        beats_per_bar=beats_per_bar,
        beat_unit=beat_unit,
        answer_offset_beats=0,
    )

    # Set render_offset on every ANSWER BeatRole so the renderer
    # shifts it backwards by answer_offset_beats.  The renderer
    # stamps the full answer once from (start_offset + render_offset)
    # and windows it, instead of the old approach that stamped
    # overlapping BeatRoles causing double-rendering.
    if subject_plan.answer_offset_beats > 0:
        answer_shift: Fraction = -Fraction(subject_plan.answer_offset_beats) * beat_unit
        patched: list[BeatRole] = []
        for role in all_beat_roles:
            if role.role == ThematicRole.ANSWER:
                patched.append(BeatRole(
                    bar=role.bar,
                    beat=role.beat,
                    voice=role.voice,
                    role=role.role,
                    material=role.material,
                    material_key=role.material_key,
                    sequence_type=role.sequence_type,
                    pairing=role.pairing,
                    texture=role.texture,
                    fragment_iteration=role.fragment_iteration,
                    anchor_pitch=role.anchor_pitch,
                    render_offset=answer_shift,
                ))
            else:
                patched.append(role)
        all_beat_roles = tuple(patched)

    # Group BeatRoles into phrase-level entries
    bar_to_section: dict[int, str] = {ba.bar: ba.section for ba in subject_plan.bars}
    groups: list[dict] = _group_beat_roles(
        beat_roles=all_beat_roles,
        bar_length=bar_length,
        bar_to_section=bar_to_section,
    )

    # Build PhrasePlan for each group
    phrase_plans: list[PhrasePlan] = []
    for group_idx, group in enumerate(groups):
        function: str = group["function"]
        first_bar: int = group["first_bar"]
        bar_count: int = group["bar_count"]
        local_key: Key = group["local_key"]
        section_name: str = group["section_name"]

        start_offset: Fraction = (first_bar - 1) * bar_length
        phrase_duration: Fraction = bar_count * bar_length

        # Extract BeatRoles for this group's bar range
        last_bar: int = first_bar + bar_count - 1
        group_beat_roles: tuple[BeatRole, ...] = tuple(
            r for r in all_beat_roles
            if first_bar <= r.bar <= last_bar
        )

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
            # Non-cadential phrase: use function-specific schema name
            thematic_roles: tuple[BeatRole, ...] = group_beat_roles
            # Map function to schema_name: keep "subject_entry" for actual entries,
            # use function name directly for episodes/holds/pedals/strettos
            schema_name: str = "subject_entry" if function == "entry" else function
            phrase_plans.append(PhrasePlan(
                schema_name=schema_name,
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


def _group_beat_roles(
    beat_roles: tuple[BeatRole, ...],
    bar_length: Fraction,
    bar_to_section: dict[int, str],
) -> list[dict]:
    """Group BeatRoles into phrase-level entries.

    An entry is a contiguous run of bars where each voice maintains the same role pattern.
    Detects role changes at bar boundaries (checks beat 0 of each bar).

    Returns list of group dicts similar to _group_bar_assignments.
    """
    if not beat_roles:
        return []

    # Extract bar-level role pattern (check beat 0 for each bar/voice)
    bars_data: dict[int, dict] = {}
    for role in beat_roles:
        if role.beat == Fraction(0):
            if role.bar not in bars_data:
                bars_data[role.bar] = {"roles": {}, "section": None, "local_key": None}
            bars_data[role.bar]["roles"][role.voice] = role.role
            bars_data[role.bar]["section"] = bar_to_section.get(role.bar, "unknown")
            if bars_data[role.bar]["local_key"] is None:
                bars_data[role.bar]["local_key"] = role.material_key

    sorted_bars: list[int] = sorted(bars_data.keys())

    # Determine function from role pattern
    def get_function(roles_dict: dict[int, ThematicRole]) -> str:
        if ThematicRole.CADENCE in roles_dict.values():
            return "cadence"
        if ThematicRole.HOLD in roles_dict.values():
            return "hold_exchange"
        if ThematicRole.PEDAL in roles_dict.values():
            return "pedal"
        if ThematicRole.STRETTO in roles_dict.values():
            return "stretto"
        if ThematicRole.EPISODE in roles_dict.values():
            return "episode"
        return "entry"

    # Group bars by (function, voice role pattern)
    groups: list[dict] = []
    current_group: dict | None = None

    # Build stretto material lookup: bar -> material string for STRETTO voice
    stretto_material: dict[int, str | None] = {}
    for role in beat_roles:
        if role.beat == Fraction(0) and role.role == ThematicRole.STRETTO:
            stretto_material[role.bar] = role.material

    for bar_num in sorted_bars:
        bar_data: dict = bars_data[bar_num]
        voice_roles: frozenset[ThematicRole] = frozenset(bar_data["roles"].values())
        function: str = get_function(bar_data["roles"])
        local_key: Key = bar_data["local_key"]
        section_name: str = bar_data["section"]
        bar_stretto_mat: str | None = stretto_material.get(bar_num)

        if current_group is None:
            # Start first group
            current_group = {
                "function": function,
                "first_bar": bar_num,
                "bar_count": 1,
                "local_key": local_key,
                "section_name": section_name,
                "voice_roles": voice_roles,
                "stretto_material": bar_stretto_mat,
                "bar_assignments": [],  # Not needed for BeatRole-based groups
            }
        elif (function != current_group["function"] or
              voice_roles != current_group["voice_roles"] or
              local_key != current_group["local_key"] or
              bar_stretto_mat != current_group["stretto_material"]):
            # Pattern, key, or stretto delay changed — close and start new
            groups.append(current_group)
            current_group = {
                "function": function,
                "first_bar": bar_num,
                "bar_count": 1,
                "local_key": local_key,
                "section_name": section_name,
                "voice_roles": voice_roles,
                "stretto_material": bar_stretto_mat,
                "bar_assignments": [],
            }
        else:
            # Same pattern, extend current group
            current_group["bar_count"] += 1

    # Close last group
    if current_group is not None:
        groups.append(current_group)

    return groups


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
    answer_offset_beats: int = 0,
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




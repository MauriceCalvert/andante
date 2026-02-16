"""Subject planner: builds a SubjectPlan from the genre entry_sequence.

IMP-2. Reads the declarative entry_sequence from the genre YAML thematic
section, walks entries top-to-bottom, and produces a BarAssignment for
every bar in the piece. No notes, no counterpoint — just the structural
scaffold that tells downstream modules what material goes where.

IMP-4. Auto-inserts episode bars at section boundaries. Episodes are not
declared in the YAML — the planner detects where sections change and
bridges them with sequential fragments of the subject head.
"""
from __future__ import annotations

from shared.constants import CADENCE_BARS
from shared.key import Key

from planner.imitative.types import BarAssignment, SubjectPlan, VoiceAssignment

# Roles that are not yet supported (IMP-5)
_UNSUPPORTED_ROLES: frozenset[str] = frozenset({
    "link",
})

# Episode length: fixed at 2 bars for IMP-4
_EPISODE_BARS: int = 2


def _extract_lead_voice_and_key(entry: dict | str, home_key: Key) -> tuple[int | None, Key | None]:
    """Extract which voice has subject/answer and what key it's in.

    Returns:
        (voice_idx, material_key) or (None, None) if entry is cadence or has no thematic material.
    """
    if entry == "cadence":
        return (None, None)

    assert isinstance(entry, dict), f"entry must be dict or 'cadence', got {type(entry).__name__}"

    # Check upper voice first (voice 0)
    upper = entry.get("upper")
    if isinstance(upper, list) and len(upper) >= 2:
        material_name = upper[0]
        if material_name in ("subject", "answer"):
            key_label = upper[1]
            material_key = home_key.modulate_to(key_label)
            return (0, material_key)

    # Check lower voice (voice 1)
    lower = entry.get("lower")
    if isinstance(lower, list) and len(lower) >= 2:
        material_name = lower[0]
        if material_name in ("subject", "answer"):
            key_label = lower[1]
            material_key = home_key.modulate_to(key_label)
            return (1, material_key)

    # No thematic material
    return (None, None)


def _semitone_distance(key1: Key, key2: Key) -> int:
    """Compute shortest semitone distance from key1 tonic to key2 tonic (mod 12)."""
    dist = (key2.tonic_pc - key1.tonic_pc) % 12
    if dist > 6:
        dist = dist - 12
    return dist


def plan_subject(
    thematic_config: dict,
    subject_bars: int,
    home_key: Key,
    metre: str,
    sections: tuple[dict, ...],
) -> SubjectPlan:
    """Build a SubjectPlan from the declarative entry_sequence.

    Args:
        thematic_config: Dict from genre YAML ``thematic:`` section.
        subject_bars: Number of bars each subject/answer entry occupies.
        home_key: Home key of the piece (e.g. Key("c", "major")).
        metre: Metre string like "4/4".
        sections: Genre sections from GenreConfig.sections.

    Returns:
        SubjectPlan with one BarAssignment per bar, fully validated.
    """
    entry_sequence: list = thematic_config["entry_sequence"]
    assert len(entry_sequence) > 0, "entry_sequence is empty"

    # Read answer_offset_beats (optional, defaults to 0 for bar-aligned entry)
    answer_offset_beats: int = thematic_config.get("answer_offset_beats", 0)

    # ── 1. Compute per-entry bar costs (no episodes yet) ────────────
    entry_costs: list[int] = []
    for entry in entry_sequence:
        if entry == "cadence":
            entry_costs.append(CADENCE_BARS)
            continue
        assert isinstance(entry, dict), (
            f"entry_sequence element must be dict or 'cadence', got {type(entry).__name__}: {entry}"
        )
        # Special entry types with explicit bar counts
        if entry.get("type") == "pedal":
            entry_costs.append(entry["bars"])
            continue
        if entry.get("type") == "hold_exchange":
            entry_costs.append(entry["bars"])
            continue
        if entry.get("type") == "stretto":
            entry_costs.append(subject_bars)
            continue
        # Guard against unsupported roles
        for slot_key in ("upper", "lower"):
            slot = entry.get(slot_key)
            if isinstance(slot, list) and len(slot) >= 1:
                assert slot[0] not in _UNSUPPORTED_ROLES, (
                    f"{slot[0]} entries not yet supported (IMP-5)"
                )
        entry_costs.append(subject_bars)

    # ── 2. Assign sections proportionally ───────────────────────────
    n_entries: int = len(entry_sequence)
    n_sections: int = len(sections)
    assert n_sections > 0, "sections list is empty"

    entry_section_names: list[str] = []
    for i in range(n_entries):
        section_idx: int = i * n_sections // n_entries
        entry_section_names.append(sections[section_idx]["name"])

    # ── 2b. Auto-insert episodes at section boundaries ──────────────
    # Build augmented entry list: original entries + auto-inserted episodes
    augmented_entries: list[dict | str] = []
    augmented_sections: list[str] = []
    augmented_costs: list[int] = []

    for i in range(n_entries):
        # Check if this is a section boundary (and neither side is cadence or pedal)
        prev_is_special = (
            entry_sequence[i - 1] == "cadence"
            or (isinstance(entry_sequence[i - 1], dict) and entry_sequence[i - 1].get("type") in ("pedal", "stretto", "hold_exchange"))
        ) if i > 0 else False
        curr_is_special = (
            entry_sequence[i] == "cadence"
            or (isinstance(entry_sequence[i], dict) and entry_sequence[i].get("type") in ("pedal", "stretto", "hold_exchange"))
        )

        is_boundary = (
            i > 0
            and entry_section_names[i] != entry_section_names[i - 1]
            and not prev_is_special
            and not curr_is_special
        )

        if is_boundary:
            # Insert episode between entry i-1 and entry i
            prev_voice_idx, prev_key = _extract_lead_voice_and_key(entry_sequence[i - 1], home_key)
            next_voice_idx, next_key = _extract_lead_voice_and_key(entry_sequence[i], home_key)

            assert prev_key is not None, (
                f"Cannot auto-insert episode: entry {i-1} has no thematic material"
            )
            assert next_key is not None, (
                f"Cannot auto-insert episode: entry {i} has no thematic material"
            )

            # Compute direction from key distance
            dist = _semitone_distance(prev_key, next_key)
            # Positive dist = target is higher → ascending episode (negative iterations)
            # Negative dist = target is lower → descending episode (positive iterations)
            ascending = dist > 0

            # Lead voice is opposite of preceding entry's lead voice
            assert prev_voice_idx is not None, f"Entry {i-1} has no lead voice"
            episode_lead_voice = 1 - prev_voice_idx
            episode_lead_voice_str = "upper" if episode_lead_voice == 0 else "lower"

            # Build episode entry
            episode_entry = {
                "_auto_episode": True,
                "source_key": prev_key,
                "lead_voice_str": episode_lead_voice_str,
                "ascending": ascending,
            }

            # Episode belongs to the outgoing section (entry i-1's section)
            augmented_entries.append(episode_entry)
            augmented_sections.append(entry_section_names[i - 1])
            augmented_costs.append(_EPISODE_BARS)

        # Add the original entry
        augmented_entries.append(entry_sequence[i])
        augmented_sections.append(entry_section_names[i])
        augmented_costs.append(entry_costs[i])

    # Total bars = original entries + auto-inserted episodes
    total_bars: int = sum(augmented_costs)

    # ── 3. Walk augmented entries and build BarAssignments ──────────
    bar_assignments: list[BarAssignment] = []
    bar_pointer: int = 1

    for entry_idx, entry in enumerate(augmented_entries):
        section_name: str = augmented_sections[entry_idx]
        cost: int = augmented_costs[entry_idx]

        if entry == "cadence":
            # Cadence bars: both voices get role="cadence"
            for offset in range(cost):
                bar_num: int = bar_pointer + offset
                voices: dict[int, VoiceAssignment] = {}
                for voice_idx in range(2):
                    voices[voice_idx] = VoiceAssignment(
                        role="cadence",
                        material_key=home_key,
                        texture="plain",
                        pairing="independent",
                        fragment=None,
                        fragment_iteration=0,
                    )
                bar_assignments.append(BarAssignment(
                    bar=bar_num,
                    section=section_name,
                    function="cadence",
                    local_key=home_key,
                    voices=voices,
                ))
            bar_pointer += cost
            continue

        # Auto-inserted episode
        if isinstance(entry, dict) and entry.get("_auto_episode"):
            source_key: Key = entry["source_key"]
            lead_voice_str: str = entry["lead_voice_str"]
            ascending: bool = entry["ascending"]

            # Map lead_voice string to voice index
            lead_voice_idx: int = 0 if lead_voice_str == "upper" else 1
            companion_voice_idx: int = 1 - lead_voice_idx

            # Stamp bars for this episode
            for bar_offset in range(_EPISODE_BARS):
                bar_num: int = bar_pointer + bar_offset
                voices: dict[int, VoiceAssignment] = {}

                # Fragment iteration: descending = positive (0,1,2), ascending = negative (0,-1,-2)
                if ascending:
                    iteration = -bar_offset if bar_offset > 0 else 0
                else:
                    iteration = bar_offset

                # Contrary motion: upper voice descends, lower voice ascends
                upper_iteration: int = iteration      # positive = descending
                lower_iteration: int = -iteration     # negated = ascending

                # Lead voice: episode fragment
                voices[lead_voice_idx] = VoiceAssignment(
                    role="episode",
                    material_key=source_key,
                    texture="plain",
                    pairing="independent",
                    fragment="head",
                    fragment_iteration=upper_iteration if lead_voice_idx == 0 else lower_iteration,
                )

                # Companion voice: episode tail fragment
                voices[companion_voice_idx] = VoiceAssignment(
                    role="episode",
                    material_key=source_key,
                    texture="plain",
                    pairing="independent",
                    fragment="tail",
                    fragment_iteration=upper_iteration if companion_voice_idx == 0 else lower_iteration,
                )

                bar_assignments.append(BarAssignment(
                    bar=bar_num,
                    section=section_name,
                    function="episode",
                    local_key=source_key,
                    voices=voices,
                ))

            bar_pointer += cost
            continue

        # Stretto entry
        if isinstance(entry, dict) and entry.get("type") == "stretto":
            stretto_key_label: str = entry["key"]
            stretto_delay: int = entry["delay"]
            stretto_key: Key = home_key.modulate_to(stretto_key_label)

            # Stamp bars for this stretto (uses subject_bars, same as normal entry)
            for offset in range(subject_bars):
                bar_num: int = bar_pointer + offset
                voices: dict[int, VoiceAssignment] = {}

                # Voice 0 (upper/leader): subject role at stretto_key
                voices[0] = VoiceAssignment(
                    role="subject",
                    material_key=stretto_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )

                # Voice 1 (lower/follower): stretto role with delay encoded in fragment
                voices[1] = VoiceAssignment(
                    role="stretto",
                    material_key=stretto_key,
                    texture="plain",
                    pairing="independent",
                    fragment=str(stretto_delay),
                    fragment_iteration=0,
                )

                bar_assignments.append(BarAssignment(
                    bar=bar_num,
                    section=section_name,
                    function="stretto",
                    local_key=stretto_key,
                    voices=voices,
                ))

            bar_pointer += subject_bars
            continue

        # Pedal entry
        if isinstance(entry, dict) and entry.get("type") == "pedal":
            pedal_degree: int = entry["degree"]
            pedal_bars: int = entry["bars"]

            # Stamp bars for this pedal
            for offset in range(pedal_bars):
                bar_num: int = bar_pointer + offset
                voices: dict[int, VoiceAssignment] = {}

                # Voice 1 (lower): pedal role, degree as fragment
                voices[1] = VoiceAssignment(
                    role="pedal",
                    material_key=home_key,
                    texture="plain",
                    pairing="independent",
                    fragment=str(pedal_degree),
                    fragment_iteration=0,
                )

                # Voice 0 (upper): free counterpoint
                voices[0] = VoiceAssignment(
                    role="free",
                    material_key=home_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )

                bar_assignments.append(BarAssignment(
                    bar=bar_num,
                    section=section_name,
                    function="pedal",
                    local_key=home_key,
                    voices=voices,
                ))

            bar_pointer += pedal_bars
            continue

        # Hold-exchange entry
        if isinstance(entry, dict) and entry.get("type") == "hold_exchange":
            he_key_label: str = entry["key"]
            he_bars: int = entry["bars"]
            assert he_bars >= 2, f"hold_exchange needs >= 2 bars, got {he_bars}"
            he_key: Key = home_key.modulate_to(he_key_label)

            for offset in range(he_bars):
                bar_num = bar_pointer + offset
                voices = {}

                # Alternate: even offsets = voice 0 holds, voice 1 runs
                #            odd offsets  = voice 0 runs, voice 1 holds
                if offset % 2 == 0:
                    hold_voice = 0
                    free_voice = 1
                else:
                    hold_voice = 1
                    free_voice = 0

                voices[hold_voice] = VoiceAssignment(
                    role="hold",
                    material_key=he_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )
                voices[free_voice] = VoiceAssignment(
                    role="free",
                    material_key=he_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )

                bar_assignments.append(BarAssignment(
                    bar=bar_num,
                    section=section_name,
                    function="hold_exchange",
                    local_key=he_key,
                    voices=voices,
                ))

            bar_pointer += he_bars
            continue

        # Dict entry with upper/lower voice slots
        assert "upper" in entry and "lower" in entry, (
            f"Entry must have 'upper' and 'lower' keys, got: {sorted(entry.keys())}"
        )

        # Parse voice slots
        voice_assignments: dict[int, VoiceAssignment] = {}
        bar_local_key: Key = home_key  # default; overridden by first active voice

        for slot_key, voice_idx in (("upper", 0), ("lower", 1)):
            slot = entry[slot_key]
            if slot == "none":
                voice_assignments[voice_idx] = VoiceAssignment(
                    role="free",
                    material_key=home_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )
                continue

            assert isinstance(slot, list) and len(slot) == 2, (
                f"Voice slot must be 'none' or [material, key_label], got: {slot}"
            )
            material_name: str = slot[0]
            key_label: str = slot[1]

            assert material_name in ("subject", "answer", "cs"), (
                f"Unknown material '{material_name}' — expected subject/answer/cs"
            )

            material_key: Key = home_key.modulate_to(key_label)
            voice_assignments[voice_idx] = VoiceAssignment(
                role=material_name,
                material_key=material_key,
                texture="plain",
                pairing="independent",
                fragment=None,
                fragment_iteration=0,
            )

            # First active voice sets bar-level local_key
            if bar_local_key == home_key or material_name == "subject":
                bar_local_key = material_key

        # Stamp bars for this entry
        for offset in range(cost):
            bar_num = bar_pointer + offset
            bar_assignments.append(BarAssignment(
                bar=bar_num,
                section=section_name,
                function="entry",
                local_key=bar_local_key,
                voices=voice_assignments,
            ))

        bar_pointer += cost

    # ── 4. Validate ─────────────────────────────────────────────────
    assert len(bar_assignments) == total_bars, (
        f"Expected {total_bars} BarAssignments, got {len(bar_assignments)}"
    )

    # Every bar from 1..total_bars present exactly once
    assigned_bars: list[int] = [ba.bar for ba in bar_assignments]
    expected_bars: list[int] = list(range(1, total_bars + 1))
    assert assigned_bars == expected_bars, (
        f"Bar coverage mismatch: expected {expected_bars}, got {assigned_bars}"
    )

    # Every bar has voice entries for indices 0 and 1
    for ba in bar_assignments:
        assert 0 in ba.voices and 1 in ba.voices, (
            f"Bar {ba.bar} missing voice entries: has {sorted(ba.voices.keys())}, need [0, 1]"
        )

    return SubjectPlan(
        bars=tuple(bar_assignments),
        total_bars=total_bars,
        home_key=home_key,
        metre=metre,
        answer_offset_beats=answer_offset_beats,
    )

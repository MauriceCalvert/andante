"""Thematic planner: assigns thematic roles to every beat × voice.

Layer 4b in the pipeline. Takes total bars and voice count, returns a
complete beat-level plan with material assignments for every voice at
every beat.

TD-1: Entry sequence declarative planner. Reads entry_sequence from
genre YAML and stamps bars top to bottom. No heuristics.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import TYPE_CHECKING

from shared.key import Key

if TYPE_CHECKING:
    from builder.types import SchemaChain, GenreConfig
    from shared.schema_types import Schema


class ThematicRole(Enum):
    """Classification of a beat's thematic function."""
    SUBJECT = "subject"
    ANSWER = "answer"
    CS = "countersubject"
    EPISODE = "episode"
    CADENCE = "cadence"
    STRETTO = "stretto"
    LINK = "link"
    PEDAL = "pedal"
    HOLD = "hold"
    FREE = "free"


@dataclass(frozen=True)
class BeatRole:
    """Thematic assignment for one beat in one voice.

    Complete specification of what material to render and how.
    """
    bar: int  # 1-based
    beat: Fraction  # offset within bar (0 = beat 1)
    voice: int  # 0 to voice_count-1
    role: ThematicRole
    material: str | None  # catalogue fragment name, or None for CADENCE/FREE
    material_key: Key  # local key for rendering
    sequence_type: str  # "tonal" or "real"
    pairing: str  # "independent", "parallel_10ths", etc.
    texture: str  # "plain", "bariolage_single", etc.
    fragment_iteration: int  # 0-based; for fragmentation envelope
    anchor_pitch: int | None  # MIDI pitch for bariolage/pedal anchor
    render_offset: Fraction = Fraction(0)  # shift start_offset at render time (negative = earlier)


def plan_thematic_roles(
    total_bars: int,
    metre: str,
    voice_count: int,
    home_key: Key,
    schema_chain: "SchemaChain | None" = None,
    schemas: "dict[str, Schema] | None" = None,
    genre_config: "GenreConfig | None" = None,
    thematic_config: "dict | None" = None,
    subject_bars: int | None = None,
) -> tuple[BeatRole, ...]:
    """Plan thematic roles for all beats × voices.

    TD-1: Reads entry_sequence from thematic_config and stamps bars with
    SUBJECT, ANSWER, CS based on the declarative sequence. All other
    beats remain FREE.

    Args:
        total_bars: Total number of bars in the piece
        metre: Metre string like "4/4", "3/4"
        voice_count: Number of voices (2 for invention)
        home_key: Home key of the piece
        schema_chain: SchemaChain with section boundaries and key areas
        schemas: Dict of Schema definitions by name
        genre_config: GenreConfig with section lead_voice and thematic config
        thematic_config: Dict with entry_sequence (from genre YAML thematic section)
        subject_bars: Number of bars each entry occupies (from fugue.subject.bars)

    Returns:
        Tuple of BeatRole covering every beat × voice
    """
    # Parse metre to get beats per bar
    metre_parts: list[str] = metre.split("/")
    assert len(metre_parts) == 2, f"Invalid metre '{metre}', expected 'N/N' format"
    beats_per_bar: int = int(metre_parts[0])
    beat_unit_denom: int = int(metre_parts[1])

    # Beat unit as Fraction (e.g., 1/4 for quarter note)
    beat_unit: Fraction = Fraction(4, beat_unit_denom)

    # Total beats in piece
    total_beats: int = total_bars * beats_per_bar

    # Build BeatRole for every beat × voice (all FREE initially)
    roles: list[BeatRole] = []

    for bar in range(1, total_bars + 1):
        for beat_idx in range(beats_per_bar):
            beat_offset: Fraction = Fraction(beat_idx) * beat_unit
            for voice in range(voice_count):
                role: BeatRole = BeatRole(
                    bar=bar,
                    beat=beat_offset,
                    voice=voice,
                    role=ThematicRole.FREE,
                    material=None,
                    material_key=home_key,
                    sequence_type="tonal",
                    pairing="independent",
                    texture="plain",
                    fragment_iteration=0,
                    anchor_pitch=None,
                )
                roles.append(role)

    # TD-1: Place entry_sequence if thematic config is present
    if thematic_config is not None and "entry_sequence" in thematic_config:
        assert subject_bars is not None, "subject_bars required when entry_sequence is present"

        # Trace entry sequence echo
        from shared.tracer import get_tracer
        tracer = get_tracer()
        entry_sequence_str = _format_entry_sequence_echo(
            entry_sequence=thematic_config["entry_sequence"],
            home_key=home_key,
        )
        tracer._line(f"L4b Entries: {entry_sequence_str}")

        roles = _place_entry_sequence(
            roles=roles,
            entry_sequence=thematic_config["entry_sequence"],
            subject_bars=subject_bars,
            beats_per_bar=beats_per_bar,
            beat_unit=beat_unit,
            voice_count=voice_count,
            home_key=home_key,
        )

    # Validate output length
    expected_count: int = total_beats * voice_count
    assert len(roles) == expected_count, (
        f"Thematic plan has {len(roles)} roles but expected {expected_count} "
        f"(total_beats={total_beats} × voice_count={voice_count})"
    )

    return tuple(roles)


_MATERIAL_CODE_MAP: dict[str, str] = {
    "subject": "S",
    "answer": "A",
    "cs": "cs",
    "stretto": "st",
}


def _format_entry_sequence_echo(
    entry_sequence: list,
    home_key: Key,
) -> str:
    """Format entry_sequence as compact one-line echo.

    Format: S.I|--- -> cs.I|A.V -> S.vi|cs.vi -> CAD

    Material codes:
    - S = subject
    - A = answer
    - cs = countersubject
    - st = stretto
    - --- = none
    - CAD = cadence
    """
    parts: list[str] = []

    for entry in entry_sequence:
        if entry == "cadence":
            parts.append("CAD")
            continue

        # Entry is dict with upper/lower
        assert isinstance(entry, dict), f"Entry must be dict or 'cadence', got {type(entry)}"

        upper_str: str = "---"
        lower_str: str = "---"

        if entry.get("upper") != "none" and isinstance(entry.get("upper"), list):
            material_name: str = entry["upper"][0]
            key_label: str = entry["upper"][1]
            # Map material name to compact code
            material_code: str = _MATERIAL_CODE_MAP.get(material_name, material_name)
            upper_str = f"{material_code}.{key_label}"

        if entry.get("lower") != "none" and isinstance(entry.get("lower"), list):
            material_name = entry["lower"][0]
            key_label = entry["lower"][1]
            material_code = {
                "subject": "S",
                "answer": "A",
                "cs": "cs",
                "stretto": "st",
            }.get(material_name, material_name)
            lower_str = f"{material_code}.{key_label}"

        parts.append(f"{upper_str}|{lower_str}")

    return " -> ".join(parts)


def _place_entry_sequence(
    roles: list[BeatRole],
    entry_sequence: list,
    subject_bars: int,
    beats_per_bar: int,
    beat_unit: Fraction,
    voice_count: int,
    home_key: Key,
) -> list[BeatRole]:
    """Place entries from declarative entry_sequence.

    Walks the entry_sequence top to bottom, stamping bars with appropriate
    ThematicRole based on material type. Handles "none" voice slots by
    leaving them FREE.

    Args:
        roles: List of BeatRole to modify (all FREE initially)
        entry_sequence: List of entry dicts from YAML
        subject_bars: Number of bars each entry occupies
        beats_per_bar: Beats per bar (from metre)
        beat_unit: Beat unit as Fraction (e.g., Fraction(1, 4))
        voice_count: Number of voices (2 for invention)
        home_key: Home key of the piece

    Returns:
        Modified roles list with entry assignments
    """
    bar_pointer: int = 1

    for entry in entry_sequence:
        # Check if entry is cadence marker
        if entry == "cadence":
            # Mark remaining bars as CADENCE role
            for bar in range(bar_pointer, len(roles) // (beats_per_bar * voice_count) + 1):
                for beat_idx in range(beats_per_bar):
                    beat_offset: Fraction = Fraction(beat_idx) * beat_unit
                    role_index_base: int = ((bar - 1) * beats_per_bar + beat_idx) * voice_count
                    for voice in range(voice_count):
                        role_idx: int = role_index_base + voice
                        if role_idx < len(roles):
                            roles[role_idx] = BeatRole(
                                bar=bar,
                                beat=beat_offset,
                                voice=voice,
                                role=ThematicRole.CADENCE,
                                material=None,
                                material_key=home_key,
                                sequence_type="tonal",
                                pairing="independent",
                                texture="plain",
                                fragment_iteration=0,
                                anchor_pitch=None,
                            )
            break

        # Entry is a dict with upper/lower voice slots
        assert isinstance(entry, dict), f"Entry must be dict or 'cadence', got {type(entry)}"
        assert "upper" in entry and "lower" in entry, f"Entry must have 'upper' and 'lower' keys: {entry}"

        # Process each voice slot
        for voice_slot, voice_idx in [("upper", 0), ("lower", 1)]:
            slot_value = entry[voice_slot]

            # Skip "none" slots
            if slot_value == "none":
                continue

            # Slot is [material, key_label]
            assert isinstance(slot_value, list) and len(slot_value) == 2, (
                f"Voice slot must be 'none' or [material, key_label], got {slot_value}"
            )

            material_name: str = slot_value[0]
            key_label: str = slot_value[1]

            # Skip stretto entries for TD-1
            if material_name == "stretto":
                continue

            # Map material name to ThematicRole
            role_mapping: dict[str, ThematicRole] = {
                "subject": ThematicRole.SUBJECT,
                "answer": ThematicRole.ANSWER,
                "cs": ThematicRole.CS,
            }
            assert material_name in role_mapping, (
                f"Unknown material '{material_name}', expected subject/answer/cs/stretto"
            )
            thematic_role: ThematicRole = role_mapping[material_name]

            # Resolve key from key_label
            material_key: Key = home_key.modulate_to(key_label)

            # Stamp this voice's beats for subject_bars bars
            for bar_offset in range(subject_bars):
                bar: int = bar_pointer + bar_offset
                if bar > len(roles) // (beats_per_bar * voice_count):
                    # Exceeded total bars, stop
                    break

                for beat_idx in range(beats_per_bar):
                    beat_offset: Fraction = Fraction(beat_idx) * beat_unit
                    role_index_base: int = ((bar - 1) * beats_per_bar + beat_idx) * voice_count
                    role_idx: int = role_index_base + voice_idx

                    if role_idx >= len(roles):
                        break

                    # Map material name to material string for renderer
                    material_str: str = {
                        "subject": "subject",
                        "answer": "answer",
                        "cs": "countersubject",
                    }[material_name]

                    roles[role_idx] = BeatRole(
                        bar=bar,
                        beat=beat_offset,
                        voice=voice_idx,
                        role=thematic_role,
                        material=material_str,
                        material_key=material_key,
                        sequence_type="tonal",
                        pairing="independent",
                        texture="plain",
                        fragment_iteration=0,
                        anchor_pitch=None,
                    )

        # Advance bar pointer by subject_bars
        bar_pointer += subject_bars

    return roles

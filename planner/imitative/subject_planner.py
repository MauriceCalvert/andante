"""Subject planner: builds a SubjectPlan from the genre entry_sequence.

IMP-2. Reads the declarative entry_sequence from the genre YAML thematic
section, walks entries top-to-bottom, and produces a BarAssignment for
every bar in the piece. No notes, no counterpoint — just the structural
scaffold that tells downstream modules what material goes where.

IMP-4. Auto-inserts episode bars at section boundaries. Episodes are not
declared in the YAML — the planner detects where sections change and
bridges them with sequential fragments of the subject head.

GEL-1. When thematic_config has 'vocabulary' instead of 'entry_sequence',
generate_entry_sequence() produces the sequence at runtime from vocabulary
+ brief. Downstream of raw_sequence is unchanged.
"""
from __future__ import annotations

import logging
import math

from builder.cadence_writer import load_cadence_templates
from shared.key import Key

from motifs.subject_loader import LoadedStretto
from planner.imitative.types import BarAssignment, SubjectPlan, VoiceAssignment

_log: logging.Logger = logging.getLogger(__name__)

# Roles that are not yet supported (IMP-5)
_UNSUPPORTED_ROLES: frozenset[str] = frozenset({
    "link",
})

# Episode length: fixed at 2 bars for IMP-4
_EPISODE_BARS: int = 2

# Slot-to-beat conversion (from stretto_constraints)
_SLOTS_PER_CROTCHET: int = 4
_SLOTS_PER_QUAVER: int = 2

# Scope -> default development entry count (GEL-1)
_SCOPE_DEV_COUNT: dict[str, int] = {"short": 2, "medium": 3, "extended": 5}


def _voice_0_leads(entry_idx: int, voice_lead: str) -> bool:
    """Return True if voice 0 (upper) should carry the subject in this development entry.

    entry_idx is 0-based counting of subject_cs entries emitted so far.
    """
    if voice_lead == "alternate":
        return entry_idx % 2 == 0
    if voice_lead == "soprano_heavy":
        return entry_idx % 3 != 2
    if voice_lead == "bass_heavy":
        return entry_idx % 3 == 2
    assert False, (
        f"Unknown voice_lead '{voice_lead}'. Use: alternate / soprano_heavy / bass_heavy"
    )


def generate_entry_sequence(
    vocabulary: dict,
    brief: dict,
    home_key: Key,
    stretto_offsets: tuple[LoadedStretto, ...],
) -> list[dict | str]:
    """Generate entry_sequence at runtime from vocabulary + brief (GEL-1).

    Produces a list in exactly the format that plan_subject expects:
    dicts with upper/lower keys, special type dicts, or the string "cadence".
    """
    sequence: list[dict | str] = []

    # ── a. Exposition ─────────────────────────────────────────────────
    exposition: list = vocabulary.get("exposition", [])
    assert len(exposition) > 0, (
        "vocabulary.exposition is empty; add at least one entry"
    )
    sequence.extend(exposition)

    # ── d. Scope mapping ──────────────────────────────────────────────
    scope: str = brief.get("scope", "medium")
    assert scope in _SCOPE_DEV_COUNT, (
        f"brief.scope must be 'short'/'medium'/'extended', got '{scope}'"
    )
    base_dev_count: int = _SCOPE_DEV_COUNT[scope]
    dev_count: int = brief.get("development_entries", base_dev_count)

    # Key journey from brief (selected by home key mode)
    if home_key.mode == "major":
        base_journey: list[str] = list(brief.get("key_journey_major", []))
    else:
        base_journey = list(brief.get("key_journey_minor", []))
    assert len(base_journey) > 0, (
        f"brief.key_journey_{home_key.mode} is empty; add at least one key label"
    )

    # Extend (extended scope) or truncate journey to match dev_count
    if scope == "extended":
        journey: list[str] = list(base_journey)
        while len(journey) < dev_count:
            journey.append(journey[-1])
        journey = journey[:dev_count]
    else:
        journey = base_journey[:dev_count]

    # ── b. Development ────────────────────────────────────────────────
    dev_templates: list[dict] = vocabulary.get("development_entries", [])
    assert len(dev_templates) > 0, (
        "vocabulary.development_entries is empty; add at least one template"
    )

    stretto_setting: str = brief.get("stretto", "single")
    assert stretto_setting in ("none", "single", "multiple"), (
        f"brief.stretto must be 'none'/'single'/'multiple', got '{stretto_setting}'"
    )
    voice_lead: str = brief.get("voice_lead", "alternate")

    hold_exchange_used: bool = False
    template_idx: int = 0
    subject_cs_count: int = 0  # tracks voice_lead alternation for subject_cs only

    for key_label in journey:
        emitted: bool = False
        for _ in range(len(dev_templates) * 2):
            tmpl: dict = dev_templates[template_idx % len(dev_templates)]
            tmpl_name: str = tmpl["template"]
            template_idx += 1

            if tmpl_name == "stretto" and stretto_setting == "none":
                continue
            if tmpl_name == "hold_exchange" and hold_exchange_used:
                continue

            if tmpl_name == "subject_cs":
                upper0: bool = _voice_0_leads(
                    entry_idx=subject_cs_count,
                    voice_lead=voice_lead,
                )
                cs_variant: int = (subject_cs_count + 1) % 2
                subject_cs_count += 1
                if upper0:
                    sequence.append({
                        "upper": ["subject", key_label],
                        "lower": ["cs", key_label],
                        "cs_variant": cs_variant,
                    })
                else:
                    sequence.append({
                        "upper": ["cs", key_label],
                        "lower": ["subject", key_label],
                        "cs_variant": cs_variant,
                    })
                emitted = True
                break

            if tmpl_name == "hold_exchange":
                he_bars: int = tmpl.get("bars", 2)
                sequence.append({"type": "hold_exchange", "key": key_label, "bars": he_bars})
                hold_exchange_used = True
                emitted = True
                break

            if tmpl_name == "stretto":
                sequence.append({"type": "stretto_section", "key": key_label})
                emitted = True
                break

            assert False, (
                f"Unknown development template '{tmpl_name}'. "
                f"Use: subject_cs / hold_exchange / stretto"
            )

        assert emitted, (
            f"All development templates were skipped for key '{key_label}'. "
            f"Check vocabulary.development_entries has a viable template "
            f"for brief.stretto='{stretto_setting}'"
        )

    # ── c. Peroration ─────────────────────────────────────────────────
    peroration_entries: list[dict] = vocabulary.get("peroration_entries", [])

    if stretto_setting in ("single", "multiple"):
        sequence.append({"type": "stretto_section", "key": "I"})
        if stretto_setting == "multiple" and len(stretto_offsets) >= 2:
            sequence.append({"type": "stretto_section", "key": "I"})

    if brief.get("pedal", False):
        pedal_tmpl: dict | None = next(
            (t for t in peroration_entries if t.get("template") == "pedal"),
            None,
        )
        if pedal_tmpl is not None:
            sequence.append({
                "type": "pedal",
                "degree": pedal_tmpl["degree"],
                "bars": pedal_tmpl["bars"],
            })

    sequence.append("cadence")

    _log.info(
        "GEL-1 generated entry_sequence (scope=%s, mode=%s, dev_count=%d): %s",
        scope,
        home_key.mode,
        dev_count,
        sequence,
    )
    return sequence


def _extract_lead_voice_and_key(entry: dict | str, home_key: Key) -> tuple[int | None, Key | None]:
    """Extract which voice has subject/answer and what key it's in.

    Returns:
        (voice_idx, material_key) or (None, None) if entry is cadence.
        For special types (hold_exchange, stretto, pedal), returns the
        entry's own key and a nominal lead voice for episode insertion.
    """
    if entry == "cadence":
        return (None, None)

    assert isinstance(entry, dict), f"entry must be dict or 'cadence', got {type(entry).__name__}"

    # Special entry types: extract key from their own fields
    entry_type: str | None = entry.get("type")
    if entry_type == "hold_exchange":
        return (0, home_key.modulate_to(entry["key"]))
    if entry_type == "stretto":
        return (0, home_key.modulate_to(entry["key"]))
    if entry_type == "pedal":
        return (0, home_key)

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


def _slots_per_beat(metre: str) -> int:
    """Semiquaver slots per beat for the given metre."""
    parts: list[str] = metre.split("/")
    denom: int = int(parts[1])
    if denom == 4:
        return _SLOTS_PER_CROTCHET
    if denom == 8:
        return _SLOTS_PER_QUAVER
    if denom == 2:
        return _SLOTS_PER_CROTCHET * 2
    assert False, f"Unsupported metre denominator: {denom}"


def plan_subject(
    thematic_config: dict,
    subject_bars: int,
    home_key: Key,
    metre: str,
    sections: tuple[dict, ...],
    stretto_offsets: tuple[LoadedStretto, ...] = (),
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
    cadence_schema: str = thematic_config.get("cadence", "cadenza_composta")
    templates = load_cadence_templates()
    cadence_key: tuple[str, str] = (cadence_schema, metre)
    assert cadence_key in templates, (
        f"No cadence template for '{cadence_schema}' in metre '{metre}'. "
        f"Add it to data/cadence_templates/templates.yaml"
    )
    cadence_bars: int = templates[cadence_key].bars

    if "entry_sequence" in thematic_config:
        # Legacy: literal entry_sequence (backward compat for other genres)
        raw_sequence: list = thematic_config["entry_sequence"]
    else:
        vocabulary: dict = thematic_config["vocabulary"]
        brief: dict = thematic_config.get("brief", {})
        raw_sequence = generate_entry_sequence(
            vocabulary=vocabulary,
            brief=brief,
            home_key=home_key,
            stretto_offsets=stretto_offsets,
        )
    assert len(raw_sequence) > 0, "entry_sequence is empty"

    # Expand stretto_section into stretto entries.
    # Peroration strettos (key="I") use the tightest offset for maximum urgency.
    # Development strettos cycle widest-first for variety and forward arc.
    spb: int = _slots_per_beat(metre=metre)
    sorted_stretto_offsets: list[LoadedStretto] = sorted(
        stretto_offsets, key=lambda s: s.offset_slots, reverse=True
    )  # index 0 = widest; index -1 = tightest
    dev_stretto_count: int = 0
    entry_sequence: list = []
    for entry in raw_sequence:
        if isinstance(entry, dict) and entry.get("type") == "stretto_section":
            section_key: str = entry["key"]
            assert len(sorted_stretto_offsets) > 0, (
                "stretto_section requested but no viable stretto offsets found"
            )
            is_peroration: bool = section_key == "I"
            if is_peroration:
                chosen: LoadedStretto = sorted_stretto_offsets[-1]  # tightest
            else:
                chosen = sorted_stretto_offsets[dev_stretto_count % len(sorted_stretto_offsets)]
                dev_stretto_count += 1
            delay_beats: int = chosen.offset_slots // spb
            assert delay_beats * spb == chosen.offset_slots, (
                f"Stretto offset {chosen.offset_slots} slots not divisible by "
                f"{spb} slots/beat"
            )
            entry_sequence.append({
                "type": "stretto",
                "key": section_key,
                "delay": delay_beats,
            })
        else:
            entry_sequence.append(entry)

    # Read answer_offset_beats (optional, defaults to 0 for bar-aligned entry)
    answer_offset_beats: int = thematic_config.get("answer_offset_beats", 0)

    # ── 1. Compute per-entry bar costs (no episodes yet) ────────────
    entry_costs: list[int] = []
    for entry in entry_sequence:
        if entry == "cadence":
            entry_costs.append(cadence_bars)
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
            _delay: int = entry["delay"]
            _extra: int = math.ceil(_delay / int(metre.split("/")[0]))
            entry_costs.append(subject_bars + _extra)
            continue
        # Guard against unsupported roles
        for slot_key in ("upper", "lower"):
            slot = entry.get(slot_key)
            if isinstance(slot, list) and len(slot) >= 1:
                assert slot[0] not in _UNSUPPORTED_ROLES, (
                    f"{slot[0]} entries not yet supported (IMP-5)"
                )
        entry_costs.append(subject_bars)

    # EXP-1: When answer_offset_beats > 0 the answer enters mid-way through
    # the preceding (solo-subject) entry.  Shorten that entry by overlap_bars
    # so that phrase [1] starts exactly where the answer enters.  After this
    # adjustment the answer's render_offset is 0 — no backward shift needed.
    if answer_offset_beats > 0:
        beats_per_bar_expos: int = int(metre.split("/")[0])
        assert answer_offset_beats % beats_per_bar_expos == 0, (
            f"answer_offset_beats={answer_offset_beats} must be divisible by "
            f"beats_per_bar={beats_per_bar_expos} — sub-bar overlaps are not supported"
        )
        overlap_bars: int = answer_offset_beats // beats_per_bar_expos
        _answer_found: bool = False
        for _ans_idx, _ans_entry in enumerate(entry_sequence):
            if not isinstance(_ans_entry, dict):
                continue
            _has_answer: bool = any(
                isinstance(_ans_entry.get(slot), list) and _ans_entry[slot][0] == "answer"
                for slot in ("upper", "lower")
            )
            if _has_answer:
                assert _ans_idx > 0, (
                    f"answer entry is at index 0 in entry_sequence — no preceding "
                    f"solo-subject entry to shorten for answer_offset_beats={answer_offset_beats}"
                )
                assert entry_costs[_ans_idx - 1] > overlap_bars, (
                    f"Preceding entry cost {entry_costs[_ans_idx - 1]} must exceed "
                    f"overlap_bars={overlap_bars}; reduce answer_offset_beats or lengthen subject"
                )
                entry_costs[_ans_idx - 1] -= overlap_bars
                _answer_found = True
                break
        assert _answer_found, (
            f"answer_offset_beats={answer_offset_beats} is set but no 'answer' entry "
            f"found in entry_sequence; add an answer entry or set answer_offset_beats=0"
        )

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
        prev_is_special = (entry_sequence[i - 1] == "cadence") if i > 0 else False
        curr_is_special = (entry_sequence[i] == "cadence")

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
                    entry_index=entry_idx,
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
                    iteration = -(bar_offset + 1)
                else:
                    iteration = bar_offset + 1

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
                    entry_index=entry_idx,
                ))

            bar_pointer += cost
            continue

        # Stretto entry
        if isinstance(entry, dict) and entry.get("type") == "stretto":
            stretto_key_label: str = entry["key"]
            stretto_delay: int = entry["delay"]
            stretto_key: Key = home_key.modulate_to(stretto_key_label)

            # Stretto spans subject_bars + extra bars for follower's delayed entry
            for offset in range(cost):
                bar_num: int = bar_pointer + offset
                voices: dict[int, VoiceAssignment] = {}

                # Voice 0 (upper/leader): SUBJECT throughout so grouping
                # keeps the stretto as one entry. The subject renderer
                # naturally produces no notes past its duration;
                # fill_free_bars handles the tail.
                voices[0] = VoiceAssignment(
                    role="subject",
                    material_key=stretto_key,
                    texture="plain",
                    pairing="independent",
                    fragment=None,
                    fragment_iteration=0,
                )

                # Voice 1 (lower/follower): stretto throughout
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
                    entry_index=entry_idx,
                ))

            bar_pointer += cost
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
                    entry_index=entry_idx,
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
                    entry_index=entry_idx,
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
                    texture="silent",
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
            cs_v: int | None = entry.get("cs_variant") if material_name == "cs" else None
            voice_assignments[voice_idx] = VoiceAssignment(
                role=material_name,
                material_key=material_key,
                texture="plain",
                pairing="independent",
                fragment=str(cs_v) if cs_v is not None else None,
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
                entry_index=entry_idx,
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
        cadence_schema=cadence_schema,
    )

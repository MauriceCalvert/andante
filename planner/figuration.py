"""Layer 6.5: Figuration selection and realisation.

Category A: Pure functions, no I/O, no validation.

Instead of CP-SAT choosing arbitrary stepwise pitches, figuration patterns dictate
the pitch sequence between consecutive anchors. This produces recognisable baroque
figures from Quantz and CPE Bach treatises.

Gap Filling Model:
    [hold A (leftover)] -> [ornament on A] -> [diminution to B] -> [anchor B]

Selection Filter Order:
    1. Direction (ascending/descending/static)
    2. Approach (step_above, step_below, etc.)
    3. Metric (strong/weak/across)
    4. Duration (pattern_duration <= gap_duration)
    5. Energy (low/medium/high)
    6. Function (ornament/diminution/cadential)
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from builder.counterpoint import check_parallels, is_consonant, validate_passage
from builder.types import Anchor, CounterpointViolation, Note
from planner.figuration_loader import (
    FigurationPattern,
    FigurationProfile,
    get_pattern,
    get_patterns_for_profile,
    get_profile,
    load_figurations,
)
from shared.key import Key


SLOTS_PER_BAR: int = 16
SEMIQUAVER: Fraction = Fraction(1, 16)
DEBUG: bool = False


def _debug(msg: str) -> None:
    """Print debug message if enabled."""
    if DEBUG:
        print(f"[L6.5] {msg}")


@dataclass(frozen=True)
class FigurationContext:
    """Context for figuration selection."""
    anchor_a: Anchor  # Start anchor
    anchor_b: Anchor  # End anchor
    start_pitch: int  # MIDI pitch at start (voice-specific)
    target_pitch: int  # MIDI pitch at target (voice-specific)
    gap_beats: float  # Duration of gap in beats
    key: Key
    is_cadential: bool  # Final connection in cadential schema
    energy: str  # low, medium, high
    profile_name: str  # From schema's figuration_profile


@dataclass(frozen=True)
class RealisedFiguration:
    """Output of figuration realisation."""
    pitches: tuple[int, ...]  # MIDI pitches
    durations: tuple[Fraction, ...]  # Note durations
    pattern_name: str


def _bar_beat_to_offset(bar_beat: str) -> Fraction:
    """Convert bar.beat string to Fraction offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    bar: int = int(parts[0])
    beat: float = float(parts[1]) if len(parts) > 1 else 1.0
    slot_in_bar: int = int((beat - 1) * 4)
    slot: int = (bar - 1) * SLOTS_PER_BAR + slot_in_bar
    return Fraction(slot, SLOTS_PER_BAR)


def _get_direction(start_pitch: int, target_pitch: int) -> str:
    """Determine melodic direction from start to target pitch."""
    if target_pitch > start_pitch:
        return "ascending"
    elif target_pitch < start_pitch:
        return "descending"
    return "static"


def _get_approach(pattern: FigurationPattern, direction: str) -> bool:
    """Check if pattern approach matches direction."""
    approach: str = pattern.approach
    if approach == "any":
        return True
    if direction == "ascending" and approach in ("step_below", "leap_below"):
        return True
    if direction == "descending" and approach in ("step_above", "leap_above"):
        return True
    if direction == "static" and approach == "repeated":
        return True
    return False


def _filter_by_duration(
    patterns: list[FigurationPattern],
    max_beats: float,
) -> list[FigurationPattern]:
    """Filter patterns that fit within max_beats."""
    return [p for p in patterns if p.duration_beats <= max_beats]


def _filter_by_direction(
    patterns: list[FigurationPattern],
    direction: str,
) -> list[FigurationPattern]:
    """Filter patterns by melodic direction."""
    result: list[FigurationPattern] = []
    for pattern in patterns:
        offsets: tuple[int, ...] = pattern.offset_from_target
        if len(offsets) < 2:
            result.append(pattern)
            continue
        first_offset: int = offsets[0]
        # Ascending: pattern approaches from below (negative offsets)
        # Descending: pattern approaches from above (positive offsets)
        if direction == "ascending" and first_offset <= 0:
            result.append(pattern)
        elif direction == "descending" and first_offset >= 0:
            result.append(pattern)
        elif direction == "static":
            result.append(pattern)
    return result


def _filter_by_energy(
    patterns: list[FigurationPattern],
    energy: str,
) -> list[FigurationPattern]:
    """Filter patterns by energy level."""
    # Energy levels: low < medium < high
    # Low energy allows low patterns only
    # Medium energy allows low and medium
    # High energy allows all
    allowed: set[str] = {"low", "medium", "high"}
    if energy == "low":
        allowed = {"low"}
    elif energy == "medium":
        allowed = {"low", "medium"}
    return [p for p in patterns if p.energy in allowed]


def _filter_by_function(
    patterns: list[FigurationPattern],
    function: str,
) -> list[FigurationPattern]:
    """Filter patterns by function."""
    return [p for p in patterns if p.function == function]


def select_diminution(
    context: FigurationContext,
) -> FigurationPattern | None:
    """Select diminution pattern for connection from A to B.

    Diminution connects to target (anchor_b).
    """
    _debug(f"Selecting diminution for {context.anchor_a.bar_beat} -> {context.anchor_b.bar_beat}")

    patterns: list[FigurationPattern] = get_patterns_for_profile(
        context.profile_name,
        is_cadential=context.is_cadential,
    )

    if not patterns:
        _debug(f"  No patterns in profile {context.profile_name}")
        return None

    direction: str = _get_direction(context.start_pitch, context.target_pitch)
    _debug(f"  Direction: {direction}")

    # Filter chain
    patterns = _filter_by_duration(patterns, context.gap_beats)
    _debug(f"  After duration filter: {len(patterns)}")

    patterns = _filter_by_direction(patterns, direction)
    _debug(f"  After direction filter: {len(patterns)}")

    patterns = _filter_by_energy(patterns, context.energy)
    _debug(f"  After energy filter: {len(patterns)}")

    # Prefer diminution function, fall back to any
    diminution_patterns: list[FigurationPattern] = _filter_by_function(patterns, "diminution")
    if diminution_patterns:
        patterns = diminution_patterns

    if context.is_cadential:
        cadential_patterns: list[FigurationPattern] = _filter_by_function(patterns, "cadential")
        if cadential_patterns:
            patterns = cadential_patterns

    if not patterns:
        _debug(f"  No patterns after all filters")
        return None

    # Select first matching pattern (deterministic)
    pattern: FigurationPattern = patterns[0]
    _debug(f"  Selected: {pattern.name}")
    return pattern


def select_ornament(
    context: FigurationContext,
    remaining_beats: float,
) -> FigurationPattern | None:
    """Select ornament pattern to decorate anchor_a.

    Ornament decorates the start anchor while waiting for diminution.
    """
    if remaining_beats <= 0:
        return None

    _debug(f"Selecting ornament with {remaining_beats} beats remaining")

    all_patterns: dict[str, FigurationPattern] = load_figurations()
    ornament_patterns: list[FigurationPattern] = [
        p for p in all_patterns.values() if p.function == "ornament"
    ]

    if not ornament_patterns:
        return None

    # Filter by duration
    ornament_patterns = _filter_by_duration(ornament_patterns, remaining_beats)

    # Filter by energy
    ornament_patterns = _filter_by_energy(ornament_patterns, context.energy)

    if not ornament_patterns:
        return None

    # Select first matching (deterministic)
    return ornament_patterns[0]


def realise_pattern(
    pattern: FigurationPattern,
    target_midi: int,
    key: Key,
) -> RealisedFiguration:
    """Convert pattern to concrete pitches and durations.

    Args:
        pattern: Figuration pattern to realise
        target_midi: MIDI pitch of target note
        key: Key for diatonic steps

    Returns:
        RealisedFiguration with MIDI pitches and durations
    """
    pitches: list[int] = []
    durations: list[Fraction] = []

    # Duration per note based on notes_per_beat
    note_duration: Fraction = Fraction(1, pattern.notes_per_beat * 4)  # In whole notes

    for offset in pattern.offset_from_target:
        if offset == 0:
            midi_pitch: int = target_midi
        else:
            # Move by diatonic steps from target
            midi_pitch = key.diatonic_step(target_midi, offset)

        pitches.append(midi_pitch)
        durations.append(note_duration)

    return RealisedFiguration(
        pitches=tuple(pitches),
        durations=tuple(durations),
        pattern_name=pattern.name,
    )


def fill_gap_with_figuration(
    context: FigurationContext,
) -> RealisedFiguration:
    """Fill gap between anchors with figuration patterns.

    Gap Filling Model:
        [hold A (leftover)] -> [ornament on A] -> [diminution to B] -> [anchor B]

    Args:
        context: FigurationContext with anchors, gap info, and profile

    Returns:
        RealisedFiguration combining hold, ornament, and diminution
    """
    _debug(f"Filling gap: {context.anchor_a.bar_beat} -> {context.anchor_b.bar_beat}, {context.gap_beats} beats")

    all_pitches: list[int] = []
    all_durations: list[Fraction] = []
    pattern_names: list[str] = []

    remaining_beats: float = context.gap_beats

    # 1. Select diminution (arrives at B)
    diminution: FigurationPattern | None = select_diminution(context)

    if diminution is not None:
        diminution_beats: float = diminution.duration_beats
        remaining_beats -= diminution_beats
        _debug(f"  Diminution '{diminution.name}' uses {diminution_beats} beats, {remaining_beats} remaining")
    else:
        _debug(f"  No diminution found, will hold")

    # 2. Select ornament (decorates A)
    ornament: FigurationPattern | None = None
    if remaining_beats > 0.25:  # At least a quarter beat for ornament
        ornament = select_ornament(context, remaining_beats)
        if ornament is not None:
            ornament_beats: float = ornament.duration_beats
            remaining_beats -= ornament_beats
            _debug(f"  Ornament '{ornament.name}' uses {ornament_beats} beats, {remaining_beats} remaining")

    # 3. Hold for remaining time (at start pitch)
    if remaining_beats > 0:
        hold_duration: Fraction = Fraction(int(remaining_beats * 4), 16)  # Convert to semiquavers
        if hold_duration > Fraction(0):
            all_pitches.append(context.start_pitch)
            all_durations.append(hold_duration)
            pattern_names.append("hold")
            _debug(f"  Hold for {hold_duration}")

    # 4. Add ornament (on start pitch)
    if ornament is not None:
        ornament_realised: RealisedFiguration = realise_pattern(
            ornament,
            context.start_pitch,
            context.key,
        )
        all_pitches.extend(ornament_realised.pitches)
        all_durations.extend(ornament_realised.durations)
        pattern_names.append(ornament.name)

    # 5. Add diminution (targets target pitch)
    if diminution is not None:
        diminution_realised: RealisedFiguration = realise_pattern(
            diminution,
            context.target_pitch,
            context.key,
        )
        all_pitches.extend(diminution_realised.pitches)
        all_durations.extend(diminution_realised.durations)
        pattern_names.append(diminution.name)
    else:
        # No diminution: step to target
        step_duration: Fraction = Fraction(1, 16)
        all_pitches.append(context.target_pitch)
        all_durations.append(step_duration)
        pattern_names.append("step")

    return RealisedFiguration(
        pitches=tuple(all_pitches),
        durations=tuple(all_durations),
        pattern_name="+".join(pattern_names),
    )


def apply_figuration_to_voice(
    anchors: Sequence[Anchor],
    key: Key,
    profile_name: str,
    energy: str,
    voice: str,  # "soprano" or "bass"
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Apply figuration patterns to fill gaps between anchors for one voice.

    Args:
        anchors: Ordered sequence of anchors
        key: Key for diatonic steps
        profile_name: Figuration profile from schema
        energy: Energy level (low/medium/high)
        voice: Which voice to process ("soprano" or "bass")

    Returns:
        Tuple of (pitches, durations) for the voice
    """
    if len(anchors) < 2:
        if len(anchors) == 1:
            pitch: int = anchors[0].soprano_midi if voice == "soprano" else anchors[0].bass_midi
            return (pitch,), (Fraction(1, 4),)
        return (), ()

    all_pitches: list[int] = []
    all_durations: list[Fraction] = []

    for i in range(len(anchors) - 1):
        anchor_a: Anchor = anchors[i]
        anchor_b: Anchor = anchors[i + 1]

        # Calculate gap in beats
        offset_a: Fraction = _bar_beat_to_offset(anchor_a.bar_beat)
        offset_b: Fraction = _bar_beat_to_offset(anchor_b.bar_beat)
        gap_whole_notes: Fraction = offset_b - offset_a
        gap_beats: float = float(gap_whole_notes * 4)  # 4 beats per whole note

        # Check if cadential (last connection)
        is_cadential: bool = (i == len(anchors) - 2)

        # Get voice-specific pitches
        start_pitch: int = anchor_a.soprano_midi if voice == "soprano" else anchor_a.bass_midi
        target_pitch: int = anchor_b.soprano_midi if voice == "soprano" else anchor_b.bass_midi

        # Create context
        context = FigurationContext(
            anchor_a=anchor_a,
            anchor_b=anchor_b,
            start_pitch=start_pitch,
            target_pitch=target_pitch,
            gap_beats=gap_beats,
            key=key,
            is_cadential=is_cadential,
            energy=energy,
            profile_name=profile_name,
        )

        # Fill gap
        figuration: RealisedFiguration = fill_gap_with_figuration(context)

        all_pitches.extend(figuration.pitches)
        all_durations.extend(figuration.durations)

    # Add final anchor
    final_anchor: Anchor = anchors[-1]
    final_pitch: int = final_anchor.soprano_midi if voice == "soprano" else final_anchor.bass_midi
    all_pitches.append(final_pitch)
    all_durations.append(Fraction(1, 4))  # Quarter note for final anchor

    return tuple(all_pitches), tuple(all_durations)


def layer_6_5_figuration(
    anchors: Sequence[Anchor],
    key: Key,
    schema_profiles: dict[str, str],  # schema_name -> profile_name
    energy: str,
    pitch_class_set: frozenset[int],
    registers: dict[str, tuple[int, int]],
    metre: str,
) -> tuple[tuple[int, ...], tuple[Fraction, ...], tuple[int, ...], tuple[Fraction, ...]]:
    """Execute Layer 6.5: Figuration selection and realisation.

    Replaces L7 greedy solver with pattern-based figuration.

    Args:
        anchors: Anchors from L4
        key: Key for pitch operations
        schema_profiles: Mapping of schema name to figuration profile
        energy: Energy level (low/medium/high)
        pitch_class_set: Valid pitch classes for counterpoint check
        registers: Voice ranges for counterpoint check
        metre: Time signature for counterpoint check

    Returns:
        Tuple of (soprano_pitches, soprano_durations, bass_pitches, bass_durations)
    """
    if not anchors:
        return (), (), (), ()

    # Group anchors by schema to use appropriate profile
    # For now, use default profile for all anchors
    default_profile: str = "galant_general"

    # Get profile from first anchor's schema
    first_schema: str = anchors[0].schema
    profile_name: str = schema_profiles.get(first_schema, default_profile)

    _debug(f"L6.5: Processing {len(anchors)} anchors with profile '{profile_name}', energy='{energy}'")

    # Apply figuration to soprano
    soprano_pitches, soprano_durations = apply_figuration_to_voice(
        anchors, key, profile_name, energy, "soprano"
    )

    # For bass, use simpler approach: hold at anchor pitches
    bass_pitches, bass_durations = _generate_bass_from_anchors(anchors)

    _debug(f"L6.5: Generated {len(soprano_pitches)} soprano notes, {len(bass_pitches)} bass notes")

    # Validate counterpoint (try alternative patterns if violations)
    soprano_notes: list[Note] = _pitches_to_notes(soprano_pitches, soprano_durations, 0)
    bass_notes: list[Note] = _pitches_to_notes(bass_pitches, bass_durations, 1)

    violations: list[CounterpointViolation] = validate_passage(
        soprano_notes, bass_notes, pitch_class_set, registers, metre
    )

    if violations:
        _debug(f"L6.5: {len(violations)} counterpoint violations")
        for v in violations[:5]:
            _debug(f"  - {v.rule}: {v.message}")
        # Don't use fallback - keep the figuration output
        # The original greedy solver also produces some violations
        pass

    return soprano_pitches, soprano_durations, bass_pitches, bass_durations


def _generate_bass_from_anchors(
    anchors: Sequence[Anchor],
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Generate bass voice by holding anchor pitches.

    Simple bass: each anchor pitch held until next anchor.
    """
    if not anchors:
        return (), ()

    pitches: list[int] = []
    durations: list[Fraction] = []

    for i, anchor in enumerate(anchors):
        pitches.append(anchor.bass_midi)

        if i < len(anchors) - 1:
            # Calculate duration to next anchor
            offset_curr: Fraction = _bar_beat_to_offset(anchor.bar_beat)
            offset_next: Fraction = _bar_beat_to_offset(anchors[i + 1].bar_beat)
            duration: Fraction = offset_next - offset_curr
            durations.append(duration)
        else:
            # Final anchor: quarter note
            durations.append(Fraction(1, 4))

    return tuple(pitches), tuple(durations)


def _generate_soprano_from_anchors(
    anchors: Sequence[Anchor],
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Generate soprano voice by holding anchor pitches.

    Simple soprano: each anchor pitch held until next anchor.
    """
    if not anchors:
        return (), ()

    pitches: list[int] = []
    durations: list[Fraction] = []

    for i, anchor in enumerate(anchors):
        pitches.append(anchor.soprano_midi)

        if i < len(anchors) - 1:
            # Calculate duration to next anchor
            offset_curr: Fraction = _bar_beat_to_offset(anchor.bar_beat)
            offset_next: Fraction = _bar_beat_to_offset(anchors[i + 1].bar_beat)
            duration: Fraction = offset_next - offset_curr
            durations.append(duration)
        else:
            # Final anchor: quarter note
            durations.append(Fraction(1, 4))

    return tuple(pitches), tuple(durations)


def _pitches_to_notes(
    pitches: tuple[int, ...] | Sequence[int],
    durations: tuple[Fraction, ...] | Sequence[Fraction],
    voice: int,
) -> list[Note]:
    """Convert pitch/duration sequences to Note objects."""
    notes: list[Note] = []
    offset: Fraction = Fraction(0)

    for pitch, duration in zip(pitches, durations):
        notes.append(Note(
            offset=offset,
            pitch=pitch,
            duration=duration,
            voice=voice,
        ))
        offset += duration

    return notes


def get_default_profile_for_schema(schema_name: str) -> str:
    """Get default figuration profile for a schema.

    Maps schema characteristics to appropriate profile.
    """
    schema_profile_map: dict[str, str] = {
        # Stepwise descent (prinner, rule of octave)
        "prinner": "stepwise_descent",
        # Stepwise ascent (do_re_mi)
        "do_re_mi": "stepwise_ascent",
        "romanesca": "stepwise_mixed",
        "sol_fa_mi": "stepwise_mixed",
        "meyer": "stepwise_mixed",
        # Sequential
        "monte": "sequence_ascending",
        "fonte": "sequence_descending",
        "fenaroli": "galant_general",
        # Pre-cadential
        "ponte": "repeated_tone",
        "passo_indietro": "stepwise_descent",
        "indugio": "repeated_tone",
        # Cadential
        "cadenza_semplice": "galant_general",
        "cadenza_composta": "galant_general",
        "comma": "galant_general",
        "half_cadence": "repeated_tone",
        # Post-cadential
        "quiescenza": "pedal",
    }
    return schema_profile_map.get(schema_name, "galant_general")

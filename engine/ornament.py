"""Ornament application for realised notes.

Phase 7 implementation (baroque_plan.md):
- 7.1: Appoggiatura with duple/triple time durations
- 7.2: Trill with upper note start, augmented 2nd avoidance, cadential suffix
- 7.3: Context-based ornament placement rules
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from engine.key import Key
from shared.tracer import get_tracer
from engine.engine_types import RealisedNote
from engine.vocabulary import ORNAMENTS, Ornament

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_I: dict = _P["intervals"]
_O: dict = _P["ornaments"]

# Load ornaments.yaml for extended ornament definitions
with open(DATA_DIR / "ornaments.yaml", encoding="utf-8") as _f:
    ORNAMENT_DEFS: dict = yaml.safe_load(_f)


# =============================================================================
# Phase 7.2: Trill Rules
# =============================================================================

# Augmented 2nd interval in semitones (to avoid in trills)
AUGMENTED_SECOND: int = 3


@dataclass(frozen=True)
class TrillValidation:
    """Result of trill validation."""
    valid: bool
    reason: str | None = None


def validate_trill_interval(note_pitch: int, upper_pitch: int, key: Key) -> TrillValidation:
    """Validate that a trill doesn't create an augmented 2nd.

    baroque_plan.md item 7.2: Trills must avoid augmented 2nd intervals,
    which sound awkward and are non-idiomatic.

    Args:
        note_pitch: MIDI pitch of principal note
        upper_pitch: MIDI pitch of upper auxiliary
        key: Current key for context

    Returns:
        TrillValidation with validity and reason if invalid
    """
    interval = abs(upper_pitch - note_pitch)

    # Augmented 2nd = 3 semitones (avoid)
    if interval == AUGMENTED_SECOND:
        return TrillValidation(False, "augmented_2nd")

    # Also check for larger than major 2nd (unusual)
    if interval > 2:
        return TrillValidation(False, "interval_too_large")

    return TrillValidation(True)


def get_trill_upper_note(note_pitch: int, key: Key) -> int:
    """Get the upper auxiliary note for a trill.

    baroque_plan.md item 7.2: Trills start on upper note.
    Returns the diatonic step above, checking for augmented 2nd.

    Args:
        note_pitch: MIDI pitch of principal note
        key: Current key

    Returns:
        MIDI pitch of upper auxiliary (adjusted if needed)
    """
    upper = key.diatonic_step(note_pitch, 1)

    # Validate and adjust if augmented 2nd
    validation = validate_trill_interval(note_pitch, upper, key)
    if not validation.valid and validation.reason == "augmented_2nd":
        # Lower the upper note by a semitone to make it a major 2nd
        upper = upper - 1

    return upper


# =============================================================================
# Phase 7.3: Ornament Placement Rules
# =============================================================================

@dataclass(frozen=True)
class OrnamentContext:
    """Context for ornament selection decisions."""
    tempo: str  # "slow", "moderate", "fast"
    is_strong_beat: bool
    is_cadence: bool
    duration: Fraction
    next_interval: int | None  # Interval to next note (semitones)
    is_detached: bool  # Not followed by stepwise motion down
    meter: str  # "duple" or "triple"


def classify_tempo(tempo_bpm: int | None, tempo_marking: str | None) -> str:
    """Classify tempo for ornament decisions.

    Args:
        tempo_bpm: BPM if known
        tempo_marking: Tempo marking string (adagio, allegro, etc.)

    Returns:
        "slow", "moderate", or "fast"
    """
    if tempo_marking:
        slow_markings = {"adagio", "largo", "lento", "grave"}
        fast_markings = {"allegro", "vivace", "presto", "prestissimo"}
        if tempo_marking.lower() in slow_markings:
            return "slow"
        if tempo_marking.lower() in fast_markings:
            return "fast"

    if tempo_bpm:
        if tempo_bpm < 60:
            return "slow"
        if tempo_bpm > 120:
            return "fast"

    return "moderate"


def select_ornament_for_context(ctx: OrnamentContext) -> str | None:
    """Select appropriate ornament based on baroque conventions.

    baroque_plan.md item 7.3:
    - Long notes in slow movements → TRILL
    - Short detached (not on descending 2nds) → MORDENT
    - Sustained notes → TURN
    - Fast passages → unornamented

    Args:
        ctx: OrnamentContext with all relevant information

    Returns:
        Ornament name or None if no ornament appropriate
    """
    # Fast passages: generally unornamented
    if ctx.tempo == "fast" and ctx.duration < Fraction(1, 4):
        return None

    # Cadential position: always trill (with suffix in slow tempos)
    if ctx.is_cadence:
        if ctx.tempo == "slow":
            return "trill_cadential"  # Trill with suffix
        return "trill"

    # Long notes in slow movements: trill
    if ctx.tempo == "slow" and ctx.duration >= Fraction(1, 2):
        return "trill"

    # Strong beat with sufficient duration: appoggiatura or mordent
    if ctx.is_strong_beat and ctx.duration >= Fraction(1, 4):
        # Appoggiatura for expressive contexts
        if ctx.tempo == "slow":
            if ctx.meter == "triple":
                return "appoggiatura_triple"
            return "appoggiatura_duple"

        # Short detached notes not on descending seconds: mordent
        if ctx.is_detached:
            return "mordent"

    # Descending stepwise motion: turn
    if ctx.next_interval is not None:
        if -3 <= ctx.next_interval <= -1:  # Descending step
            if ctx.duration >= Fraction(1, 4):
                return "turn"

    # Sustained notes: turn
    if ctx.duration >= Fraction(1, 2) and ctx.tempo != "fast":
        return "turn"

    return None


def is_meter_triple(time_sig: tuple[int, int] | None) -> bool:
    """Check if time signature is triple meter."""
    if time_sig is None:
        return False
    numerator, _ = time_sig
    return numerator in (3, 6, 9, 12)


def is_power_of_two(n: int) -> bool:
    """Check if n is a power of 2."""
    return n > 0 and (n & (n - 1)) == 0


def can_ornament(duration: Fraction) -> bool:
    """Only ornament notes with clean binary subdivisions.

    Duration must be >= min and have power-of-2 numerator (1, 2, 4...).
    This ensures 4-way subdivision produces clean durations.
    """
    min_dur: Fraction = Fraction(_O["min_duration"])
    if duration < min_dur:
        return False
    return is_power_of_two(duration.numerator)


def select_ornament(
    note: RealisedNote,
    next_note: RealisedNote | None,
    is_cadence: bool,
    bar_dur: Fraction,
    phrase_index: int = 0,
    tempo: str = "moderate",
    time_sig: tuple[int, int] | None = None,
) -> Ornament | None:
    """Select ornament based on baroque conventions.

    Enhanced with Phase 7 rules:
    - Long notes in slow movements → TRILL
    - Short detached (not on descending 2nds) → MORDENT
    - Sustained notes → TURN
    - Fast passages → unornamented
    - Cadential notes → TRILL (with suffix in slow tempos)

    Args:
        note: The note to potentially ornament
        next_note: Following note (for interval calculation)
        is_cadence: Whether this is a cadential position
        bar_dur: Duration of one bar
        phrase_index: Index of current phrase (for variety)
        tempo: Tempo classification ("slow", "moderate", "fast")
        time_sig: Time signature tuple (numerator, denominator)

    Returns:
        Ornament or None if no ornament appropriate
    """
    if not can_ornament(note.duration):
        return None

    # Calculate interval to next note
    next_interval: int | None = None
    if next_note is not None:
        next_interval = next_note.pitch - note.pitch

    # Determine if note is detached (not followed by descending stepwise motion)
    is_detached = next_interval is None or next_interval >= 0 or abs(next_interval) > 2

    # Build context
    is_strong_beat = note.offset % bar_dur == 0
    meter = "triple" if is_meter_triple(time_sig) else "duple"

    ctx = OrnamentContext(
        tempo=tempo,
        is_strong_beat=is_strong_beat,
        is_cadence=is_cadence,
        duration=note.duration,
        next_interval=next_interval,
        is_detached=is_detached,
        meter=meter,
    )

    # Use context-based selection
    ornament_name = select_ornament_for_context(ctx)

    if ornament_name is None:
        # Fallback to original logic for variety
        if is_strong_beat and note.duration >= Fraction(1, 4):
            ornament_options: list[str | None] = ["mordent", "turn", None, "mordent"]
            choice: str | None = ornament_options[phrase_index % len(ornament_options)]
            if choice is not None:
                return ORNAMENTS.get(choice)
        return None

    return ORNAMENTS.get(ornament_name)


def apply_ornament(
    note: RealisedNote,
    ornament: Ornament,
    key: Key,
) -> tuple[RealisedNote, ...]:
    """Expand a note into ornamented notes.

    Phase 7.2 enhancements:
    - Trills start on upper note (baroque convention)
    - Augmented 2nd intervals are avoided in trills
    - No range checking (L003) - pitches are diatonic steps from note

    Args:
        note: The note to ornament
        ornament: The ornament to apply
        key: Current key for diatonic calculations

    Returns:
        Tuple of ornamented RealisedNotes
    """
    tracer = get_tracer()
    result: list[RealisedNote] = []
    current_offset: Fraction = note.offset

    # For trills, pre-calculate upper note with augmented 2nd check
    upper_pitch: int | None = None
    if "trill" in ornament.name:
        upper_pitch = get_trill_upper_note(note.pitch, key)

    for step, dur_frac in zip(ornament.steps, ornament.durations, strict=True):
        actual_dur: Fraction = note.duration * dur_frac

        if step == 0:
            pitch = note.pitch
        elif "trill" in ornament.name and step == 1 and upper_pitch is not None:
            # Use pre-calculated upper note (with augmented 2nd correction)
            pitch = upper_pitch
        else:
            pitch = key.diatonic_step(note.pitch, step)

        ornamented: RealisedNote = RealisedNote(
            offset=current_offset,
            pitch=pitch,
            duration=actual_dur,
            voice=note.voice,
        )
        result.append(ornamented)
        current_offset += actual_dur

    pitches: list[int] = [n.pitch for n in result]
    durs: list[Fraction] = [n.duration for n in result]
    tracer.trace("ORNAMENT", f"{note.voice}/{ornament.name}", f"applied at {float(note.offset):.3f}",
                 original_pitch=note.pitch, original_dur=note.duration,
                 result_pitches=pitches, result_durs=durs)
    return tuple(result)


def apply_ornaments(
    notes: tuple[RealisedNote, ...],
    key: Key,
    is_cadence: bool,
    bar_dur: Fraction,
    phrase_index: int = 0,
) -> tuple[RealisedNote, ...]:
    """Apply ornaments sparingly - max per phrase from predicates.yaml."""
    if len(notes) < 2:
        return notes
    max_ornaments: int = _O["max_per_phrase"]
    result: list[RealisedNote] = []
    applied: int = 0
    for i, note in enumerate(notes):
        if applied >= max_ornaments:
            result.append(note)
            continue
        next_note: RealisedNote | None = notes[i + 1] if i < len(notes) - 1 else None
        is_note_cadence: bool = is_cadence and i == len(notes) - 1
        ornament: Ornament | None = select_ornament(note, next_note, is_note_cadence, bar_dur, phrase_index)
        if ornament is not None:
            result.extend(apply_ornament(note, ornament, key))
            applied += 1
        else:
            result.append(note)
    return tuple(result)

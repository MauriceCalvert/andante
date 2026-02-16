"""Countersubject Viterbi writer: generates CS voice against a fixed companion.

CP2: Instead of stamping in pre-composed CS pitches verbatim, uses the CS
contour as structural hints (knots) and the CS rhythm as the grid, letting
the Viterbi solver choose pitches that are consonant with the companion voice.
"""
import logging
from dataclasses import replace
from fractions import Fraction

from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from shared.constants import STRONG_BEAT_DISSONANT
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range
from viterbi.generate import generate_voice
from viterbi.mtypes import ExistingVoice, Knot
from viterbi.scale import KeyInfo

logger = logging.getLogger(__name__)

DURATION_DENOMINATOR_LIMIT: int = 64


def _companion_at(
    companion_notes: tuple[Note, ...],
    offset: Fraction,
) -> int | None:
    """Return companion MIDI pitch sounding at offset (sustain lookup)."""
    for note in companion_notes:
        if note.offset <= offset < note.offset + note.duration:
            return note.pitch
    return None


def _strong_beat_offsets(bar_length: Fraction, metre: str) -> frozenset[Fraction]:
    """Return strong-beat offsets within a bar for the given metre.

    4/4: downbeat and half-bar (beats 1, 3).
    6/8: downbeat and half-bar (beats 1, 4).
    All others: downbeat only.
    """
    parts: list[str] = metre.split("/")
    numerator: int = int(parts[0])

    if numerator in (4, 6):
        return frozenset({Fraction(0), bar_length / 2})
    return frozenset({Fraction(0)})


def _find_consonant_near(
    cs_midi: int,
    companion_midi: int,
    range_low: int,
    range_high: int,
) -> int:
    """Find nearest pitch to cs_midi that is consonant with companion_midi.

    Searches outward from cs_midi within target range.  Falls back to
    range midpoint if nothing consonant is reachable (should not happen
    in practice).
    """
    for distance in range(13):
        for candidate in (cs_midi + distance, cs_midi - distance):
            if range_low <= candidate <= range_high:
                if abs(candidate - companion_midi) % 12 not in STRONG_BEAT_DISSONANT:
                    return candidate
    return (range_low + range_high) // 2


def generate_cs_viterbi(
    fugue: LoadedFugue,
    companion_notes: tuple[Note, ...],
    companion_is_above: bool,
    start_offset: Fraction,
    end_offset: Fraction,
    target_key: Key,
    target_track: int,
    target_range: Range,
    metre: str,
    local_key: Key,
    cadential_approach: bool,
) -> tuple[Note, ...]:
    """Generate countersubject via Viterbi against a fixed companion voice.

    Uses the pre-composed CS contour as structural hints (knots) and the
    CS rhythm as the grid, letting Viterbi choose pitches that are consonant
    with the companion.

    Args:
        fugue: LoadedFugue containing the CS data
        companion_notes: Already-rendered companion voice notes
        companion_is_above: True if companion is registrally above the CS
        start_offset: Absolute offset where the CS starts
        end_offset: Absolute offset where the CS time window ends
        target_key: Key for CS pitch transposition
        target_track: Track number for generated notes
        target_range: Voice range for the CS
        metre: Metre string (e.g. "4/4")
        local_key: Current local key for Viterbi scale
        cadential_approach: Whether to use cadential pitch set

    Returns:
        Tuple of notes for the CS voice, labelled with lyric="cs".
    """
    bar_length: Fraction
    beat_unit: Fraction
    bar_length, beat_unit = parse_metre(metre=metre)

    # ================================================================
    # Step 1 -- Get CS MIDI pitches and durations
    # ================================================================
    tonic_midi: int = 60 + target_key.tonic_pc
    target_mode: str = target_key.mode
    midi_pitches: tuple[int, ...] = fugue.countersubject_midi(tonic_midi=tonic_midi, mode=target_mode)
    durations: tuple[float, ...] = fugue.countersubject.durations
    assert len(midi_pitches) == len(durations), (
        f"CS pitch count {len(midi_pitches)} != duration count {len(durations)}"
    )

    # ================================================================
    # Step 2 -- Octave-shift into target_range
    # ================================================================
    highest: int = max(midi_pitches)
    shift: int = 0
    while highest + shift > target_range.high:
        shift -= 12
    while min(midi_pitches) + shift < target_range.low:
        shift += 12
    shifted_pitches: tuple[int, ...] = tuple(p + shift for p in midi_pitches)
    assert min(shifted_pitches) >= target_range.low, (
        f"CS cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {min(shifted_pitches)} < {target_range.low}"
    )
    assert max(shifted_pitches) <= target_range.high, (
        f"CS cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {max(shifted_pitches)} > {target_range.high}"
    )

    # ================================================================
    # Step 3 -- Build rhythm grid from CS durations
    # ================================================================
    grid_positions: list[tuple[Fraction, Fraction]] = []
    cumulative: Fraction = Fraction(0)
    for dur_float in durations:
        dur: Fraction = Fraction(dur_float).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        onset: Fraction = start_offset + cumulative
        if onset >= end_offset:
            break
        grid_positions.append((onset, dur))
        cumulative += dur

    assert len(grid_positions) > 0, "Empty rhythm grid for CS Viterbi"

    # Final marker at end_offset if needed (same pattern as bass_viterbi)
    last_onset: Fraction = grid_positions[-1][0]
    if abs(float(last_onset - end_offset)) > 1e-6:
        grid_positions.append((end_offset, Fraction(-1)))

    assert len(grid_positions) >= 2, (
        f"CS grid too short ({len(grid_positions)} positions) for Viterbi -- "
        f"need at least 2"
    )

    # ================================================================
    # Step 4 -- Build Knots from CS contour
    # ================================================================
    strong_offsets: frozenset[Fraction] = _strong_beat_offsets(
        bar_length=bar_length, metre=metre,
    )

    # Find last real (non-marker) grid index
    last_real_idx: int = len(grid_positions) - 1
    if grid_positions[last_real_idx][1] < 0:
        last_real_idx -= 1

    knots: list[Knot] = []

    # -- First knot (boundary, always present -- solver requires it) --
    first_onset: Fraction = grid_positions[0][0]
    first_cs_midi: int = shifted_pitches[0]
    first_comp: int | None = _companion_at(
        companion_notes=companion_notes, offset=first_onset,
    )
    if first_comp is not None and abs(first_cs_midi - first_comp) % 12 in STRONG_BEAT_DISSONANT:
        first_cs_midi = _find_consonant_near(
            cs_midi=first_cs_midi,
            companion_midi=first_comp,
            range_low=target_range.low,
            range_high=target_range.high,
        )
    knots.append(Knot(beat=float(first_onset), midi_pitch=first_cs_midi))

    # -- Middle knots (strong-beat CS notes, dropped if dissonant) --
    for i in range(1, last_real_idx):
        grid_onset: Fraction = grid_positions[i][0]
        offset_in_bar: Fraction = grid_onset % bar_length
        if offset_in_bar not in strong_offsets:
            continue

        cs_midi: int = shifted_pitches[i] if i < len(shifted_pitches) else shifted_pitches[-1]
        comp_pitch: int | None = _companion_at(
            companion_notes=companion_notes, offset=grid_onset,
        )
        if comp_pitch is not None and abs(cs_midi - comp_pitch) % 12 in STRONG_BEAT_DISSONANT:
            continue  # Drop dissonant knot

        knots.append(Knot(beat=float(grid_onset), midi_pitch=cs_midi))

    # -- Last knot (boundary, always present -- solver requires it) --
    last_grid_onset: Fraction = grid_positions[-1][0]
    last_cs_midi: int = (
        shifted_pitches[last_real_idx]
        if last_real_idx < len(shifted_pitches)
        else shifted_pitches[-1]
    )
    last_comp: int | None = _companion_at(
        companion_notes=companion_notes, offset=last_grid_onset,
    )
    if last_comp is not None and abs(last_cs_midi - last_comp) % 12 in STRONG_BEAT_DISSONANT:
        last_cs_midi = _find_consonant_near(
            cs_midi=last_cs_midi,
            companion_midi=last_comp,
            range_low=target_range.low,
            range_high=target_range.high,
        )
    knots.append(Knot(beat=float(last_grid_onset), midi_pitch=last_cs_midi))

    # Deduplicate knots at the same beat (keep first occurrence)
    seen_beats: set[float] = set()
    unique_knots: list[Knot] = []
    for k in knots:
        if k.beat not in seen_beats:
            unique_knots.append(k)
            seen_beats.add(k.beat)
    knots = unique_knots

    assert len(knots) >= 2, (
        f"Need at least 2 knots for CS Viterbi, got {len(knots)}"
    )

    # ================================================================
    # Step 5 -- Build ExistingVoice from companion_notes
    # ================================================================
    companion_pitches_at_beat: dict[float, int] = {}
    prev_comp_val: int | None = None
    for onset_frac, _dur in grid_positions:
        cp: int | None = _companion_at(
            companion_notes=companion_notes, offset=onset_frac,
        )
        if cp is None:
            cp = prev_comp_val
        assert cp is not None, (
            f"No companion pitch at CS grid offset {onset_frac} and no previous to sustain"
        )
        companion_pitches_at_beat[float(onset_frac)] = cp
        prev_comp_val = cp

    companion_voice: ExistingVoice = ExistingVoice(
        pitches_at_beat=companion_pitches_at_beat,
        is_above=companion_is_above,
    )

    # ================================================================
    # Step 6 -- Build KeyInfo from local_key
    # ================================================================
    pitch_classes: frozenset[int] = (
        local_key.cadential_pitch_class_set
        if cadential_approach
        else local_key.pitch_class_set
    )
    key_info: KeyInfo = KeyInfo(
        pitch_class_set=pitch_classes,
        tonic_pc=local_key.degree_to_midi(degree=1, octave=0) % 12,
    )

    # ================================================================
    # Step 7 -- Call generate_voice
    # ================================================================
    notes_tuple: tuple[Note, ...] = generate_voice(
        structural_knots=knots,
        rhythm_grid=grid_positions,
        existing_voices=[companion_voice],
        range_low=target_range.low,
        range_high=target_range.high,
        key=key_info,
        voice_id=target_track,
        beats_per_bar=float(bar_length),
    )

    # ================================================================
    # Step 8 -- Apply time-window contract (truncate at end_offset)
    # ================================================================
    windowed: list[Note] = []
    for n in notes_tuple:
        if n.offset >= end_offset:
            break
        note_end: Fraction = n.offset + n.duration
        if note_end > end_offset:
            windowed.append(replace(n, duration=end_offset - n.offset))
        else:
            windowed.append(n)

    # ================================================================
    # Step 9 -- Label first note with lyric="cs"
    # ================================================================
    if windowed:
        windowed[0] = replace(windowed[0], lyric="cs")

    return tuple(windowed)

"""Slice-by-slice inner voice solver with parallel voice optimization.

At each slice, enumerates all valid 4-voice configurations (soprano fixed,
bass/alto/tenor from candidates), scores each configuration holistically,
and picks the best.

Configuration score combines:
- Vertical sonority (chord tones on strong beats)
- Voice leading from previous slice (all voices)
- Spacing between adjacent voices
- Parallel motion violations (all pairs)

Inner voices are output as MidiPitch for direct use by realiser (no conversion).
"""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from pathlib import Path
from typing import Tuple

import yaml

from engine.harmonic_context import (
    HarmonicContext,
    generate_chord_tone_candidates,
    generate_scale_candidates,
    infer_harmony_from_outer,
)
from engine.key import Key
from shared.pitch import FloatingNote, MidiPitch, Pitch, Rest, is_rest
from engine.subdivision import (
    SliceSequence,
    VerticalSlice,
    build_slice_sequence,
    collect_attack_points,
    pitch_at_offset,
)
from engine.voice_config import VoiceSet
from engine.voice_material import ExpandedVoices, VoiceMaterial

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_VOICE_RANGES: dict = _P.get("voice_ranges", {})
VOICE_RANGES: dict[str, Tuple[int, int]] = {
    k: tuple(v) for k, v in _VOICE_RANGES.items()
} if _VOICE_RANGES else {
    "soprano": (60, 81),
    "alto": (53, 74),
    "tenor": (48, 67),
    "bass": (40, 60),
}
_INTERLEAVED_RANGES: dict = _P.get("interleaved_ranges", {})
INTERLEAVED_RANGES: dict[str, Tuple[int, int]] = {
    k: tuple(v) for k, v in _INTERLEAVED_RANGES.items()
} if _INTERLEAVED_RANGES else {
    "voice_1": (55, 74),
    "voice_2": (55, 74),
}
MIN_VOICE_SEPARATION: int = 3  # Minimum semitones between adjacent voices


@dataclass(frozen=True)
class SolvedSlice:
    """Solved vertical slice with all pitches assigned."""
    offset: Fraction
    pitches: Tuple[int, ...]


def get_voice_range(
    voice_index: int,
    voice_count: int,
    interleaved: bool = False,
) -> Tuple[int, int]:
    """Get MIDI range for voice by index.

    Args:
        voice_index: Index of voice (0 = soprano/voice_1)
        voice_count: Total voice count
        interleaved: If True, use shared tessitura ranges for Goldberg-style crossing
    """
    if interleaved and voice_count == 2:
        # Both voices share the same range in interleaved mode
        name: str = f"voice_{voice_index + 1}"
        return INTERLEAVED_RANGES.get(name, (55, 74))
    if voice_count == 2:
        names: Tuple[str, ...] = ("soprano", "bass")
    elif voice_count == 3:
        names = ("soprano", "alto", "bass")
    else:
        names = ("soprano", "alto", "tenor", "bass")
    name = names[voice_index] if voice_index < len(names) else "alto"
    return VOICE_RANGES.get(name, (48, 72))


def check_voice_crossing(
    candidate: int,
    voice_index: int,
    other_pitches: dict[int, int],
    voice_count: int,
) -> bool:
    """Check if candidate crosses another voice.

    Per L004: Voice crossing allowed — Bach crosses freely in counterpoint.
    Only prevents inner voice going above soprano or below bass.
    Spacing preferences are handled in voice_leading_cost, not here.
    """
    for other_idx, other_pitch in other_pitches.items():
        if other_idx < voice_index and candidate > other_pitch:
            return True
        if other_idx > voice_index and candidate < other_pitch:
            return True
    return False


def filter_candidates(
    candidates: Tuple[int, ...],
    voice_index: int,
    curr_pitches: dict[int, int],
    prev_pitches: dict[int, int] | None,
    voice_count: int,
) -> Tuple[int, ...]:
    """Filter candidates by voice crossing and parallel motion with outer voices.

    For inner voices, checks parallel 5th/8ve with soprano (index 0) and bass
    (index voice_count-1). Inner-to-inner parallels are handled by guards.
    """
    from shared.parallels import is_parallel_fifth, is_parallel_octave

    if not candidates:
        return candidates

    outer_indices: list[int] = [0, voice_count - 1]

    def creates_outer_parallel(c: int) -> bool:
        if prev_pitches is None:
            return False
        prev_inner: int | None = prev_pitches.get(voice_index)
        if prev_inner is None:
            return False
        for outer_idx in outer_indices:
            prev_outer: int | None = prev_pitches.get(outer_idx)
            curr_outer: int | None = curr_pitches.get(outer_idx)
            if prev_outer is None or curr_outer is None:
                continue
            # Check inner voice (candidate) against outer voice
            # Voice index 0 = soprano (highest), higher index = lower pitch
            # So lower voice_index = upper voice
            if voice_index < outer_idx:
                # Inner has lower index = inner is upper voice
                if is_parallel_fifth(prev_inner, prev_outer, c, curr_outer):
                    return True
                if is_parallel_octave(prev_inner, prev_outer, c, curr_outer):
                    return True
            else:
                # Inner has higher index = inner is lower voice
                if is_parallel_fifth(prev_outer, prev_inner, curr_outer, c):
                    return True
                if is_parallel_octave(prev_outer, prev_inner, curr_outer, c):
                    return True
        return False

    filtered: list[int] = [
        c for c in candidates
        if not check_voice_crossing(c, voice_index, curr_pitches, voice_count)
        and not creates_outer_parallel(c)
    ]

    # If all candidates create parallels, return originals filtered only by crossing
    # (backtracking will handle it)
    if not filtered:
        return tuple(
            c for c in candidates
            if not check_voice_crossing(c, voice_index, curr_pitches, voice_count)
        )
    return tuple(filtered)


def voice_leading_cost(
    candidate: int,
    prev_pitch: int | None,
    median: int,
    curr_pitches: dict[int, int] | None = None,
    voice_index: int | None = None,
) -> float:
    """Calculate voice-leading cost for candidate.

    Penalizes: staying still (encourages motion), large leaps,
    doubling (unison/octave), and close spacing with adjacent voices.
    Per D010: generators prevent problems via soft cost preferences.
    """
    cost: float = 0.0
    if prev_pitch is not None:
        interval: int = abs(candidate - prev_pitch)
        if interval == 0:
            cost += 15.0  # Strong penalty for drone behavior
        elif interval <= 2:
            cost += -3.0  # Reward steps (negative cost)
        elif interval <= 4:
            cost += 0.3  # Small leaps ok
        elif interval <= 7:
            cost += 0.8  # Larger leaps less preferred
        else:
            cost += interval * 0.15  # Very large leaps expensive
    cost += abs(candidate - median) * 0.02  # Reduced median pull
    if curr_pitches is not None:
        for other_idx, other_pitch in curr_pitches.items():
            separation: int = abs(candidate - other_pitch)
            if separation == 0:
                cost += 100.0  # Unisons forbidden - match parallel penalty
            elif separation % 12 == 0:
                cost += 10.0  # High penalty for octave doublings
            if voice_index is not None and abs(other_idx - voice_index) == 1:
                if separation < MIN_VOICE_SEPARATION:
                    cost += (MIN_VOICE_SEPARATION - separation) * 3.0
                # Penalize spacing above maximum too
                if separation > 14:  # MAX_VOICE_SPACING
                    cost += (separation - 14) * 5.0
    return cost


def rank_candidates(
    candidates: Tuple[int, ...],
    prev_pitch: int | None,
    median: int,
    curr_pitches: dict[int, int] | None = None,
    voice_index: int | None = None,
) -> Tuple[int, ...]:
    """Rank candidates by voice-leading cost (best first)."""
    if len(candidates) <= 1:
        return candidates
    scored: list[tuple[int, float]] = []
    for c in candidates:
        cost: float = voice_leading_cost(c, prev_pitch, median, curr_pitches, voice_index)
        scored.append((c, cost))
    scored.sort(key=lambda x: x[1])
    return tuple(c for c, _ in scored)


NON_CHORD_TONE_PENALTY: float = 20.0  # Strongly prefer chord tones for baroque sonorities


def rank_candidates_with_harmony(
    candidates: Tuple[int, ...],
    prev_pitch: int | None,
    median: int,
    curr_pitches: dict[int, int] | None,
    voice_index: int | None,
    chord_tones: set[int],
) -> Tuple[int, ...]:
    """Rank candidates with harmony awareness (chord vs scale tones).

    Non-chord tones receive a penalty to prefer chord tones, but the penalty
    is less than the unison penalty so scale tones are chosen over doublings.
    """
    if len(candidates) <= 1:
        return candidates
    scored: list[tuple[int, float]] = []
    for c in candidates:
        cost: float = voice_leading_cost(c, prev_pitch, median, curr_pitches, voice_index)
        if c % 12 not in {ct % 12 for ct in chord_tones}:
            cost += NON_CHORD_TONE_PENALTY
        scored.append((c, cost))
    scored.sort(key=lambda x: x[1])
    return tuple(c for c, _ in scored)


def resolve_outer_pitch(pitch: Pitch, key: Key, median: int) -> int:
    """Resolve outer voice pitch to MIDI.

    Accepts MidiPitch or FloatingNote.
    """
    assert not is_rest(pitch), "Cannot resolve rest"
    if isinstance(pitch, MidiPitch):
        return pitch.midi
    elif isinstance(pitch, FloatingNote):
        return key.floating_to_midi(pitch, median, median)
    else:
        raise TypeError(f"Unexpected pitch type: {type(pitch)}")


def get_inner_voice_candidates(
    inner_idx: int,
    context: HarmonicContext,
    curr_pitches: dict[int, int],
    prev_pitches: dict[int, int] | None,
    key: Key,
    voice_count: int,
) -> Tuple[int, ...]:
    """Get ranked candidates for a single inner voice given current state.

    Generates both chord tones and scale tones as candidates. Scale tones
    receive a cost penalty but provide alternatives when chord tones would
    create unisons. This is essential for 4-voice textures where 3 chord
    tones cannot cover 4 voices without doubling.
    """
    voice_range: Tuple[int, int] = get_voice_range(inner_idx, voice_count)
    median: int = (voice_range[0] + voice_range[1]) // 2
    chord_tones: Tuple[int, ...] = generate_chord_tone_candidates(
        context, voice_range[0], voice_range[1], key
    )
    scale_tones: Tuple[int, ...] = generate_scale_candidates(
        context, voice_range[0], voice_range[1], key
    )
    chord_set: set[int] = set(chord_tones)
    all_candidates: list[int] = list(chord_tones)
    for s in scale_tones:
        if s not in chord_set:
            all_candidates.append(s)
    candidates: Tuple[int, ...] = tuple(all_candidates)
    if not candidates:
        candidates = (median,)
    candidates = filter_candidates(candidates, inner_idx, curr_pitches, prev_pitches, voice_count)
    if not candidates:
        candidates = tuple(all_candidates) if all_candidates else (median,)
    prev_inner: int | None = None
    if prev_pitches is not None and inner_idx in prev_pitches:
        prev_inner = prev_pitches[inner_idx]
    return rank_candidates_with_harmony(
        candidates, prev_inner, median, curr_pitches, inner_idx, chord_set
    )


def get_thematic_candidates(
    thematic_pitch: Pitch,
    inner_idx: int,
    context: HarmonicContext,
    curr_pitches: dict[int, int],
    prev_pitches: dict[int, int] | None,
    key: Key,
    voice_count: int,
) -> Tuple[int, ...]:
    """Get candidates for thematic pitch with chord-tone preference.

    For polyphonic texture: prefer the thematic pitch at valid octaves,
    but only if it's a chord tone. Non-chord-tone thematic pitches fall
    back to chord tones to avoid dissonant vertical sonorities on strong beats.
    """
    voice_range: Tuple[int, int] = get_voice_range(inner_idx, voice_count)
    median: int = (voice_range[0] + voice_range[1]) // 2
    if is_rest(thematic_pitch):
        return ()
    if isinstance(thematic_pitch, MidiPitch):
        base_midi: int = thematic_pitch.midi
    elif isinstance(thematic_pitch, FloatingNote):
        base_midi = key.floating_to_midi(thematic_pitch, median, median)
    else:
        base_midi = median
    # Check if thematic pitch is a chord tone
    thematic_pc: int = base_midi % 12
    is_chord_tone: bool = thematic_pc in {ct % 12 for ct in context.chord_tones}
    # If thematic pitch is not a chord tone, fall back to chord tones directly
    # This ensures baroque-style consonant sonorities on strong beats
    if not is_chord_tone:
        return get_inner_voice_candidates(
            inner_idx, context, curr_pitches, prev_pitches, key, voice_count
        )
    # Thematic pitch is a chord tone - use it at valid octaves
    octave_variants: list[int] = []
    for octave_shift in [0, 12, -12, 24, -24]:
        candidate: int = base_midi + octave_shift
        if voice_range[0] <= candidate <= voice_range[1]:
            octave_variants.append(candidate)
    if not octave_variants:
        octave_variants = [base_midi]
    filtered: Tuple[int, ...] = filter_candidates(
        tuple(octave_variants), inner_idx, curr_pitches, prev_pitches, voice_count
    )
    # Check if any thematic candidate avoids parallels
    crossing_only: Tuple[int, ...] = tuple(
        c for c in octave_variants
        if not check_voice_crossing(c, inner_idx, curr_pitches, voice_count)
    )
    # If filtered == crossing_only, all parallel-avoiding candidates were removed
    # (i.e., all candidates create parallels) - fall back to chord tones
    if filtered and filtered != crossing_only:
        prev_inner: int | None = prev_pitches.get(inner_idx) if prev_pitches else None
        return rank_candidates(filtered, prev_inner, median, curr_pitches, inner_idx)
    # Fall back to chord tones when thematic candidates all create parallels
    chord_fallback: Tuple[int, ...] = get_inner_voice_candidates(
        inner_idx, context, curr_pitches, prev_pitches, key, voice_count
    )
    return chord_fallback


def solve_slice(
    slice_offset: Fraction,
    soprano_pitch: Pitch,
    bass_pitch: Pitch,
    prev_solved: SolvedSlice | None,
    key: Key,
    voice_set: VoiceSet,
    texture: str,
    choice_indices: Tuple[int, ...] | None = None,
) -> SolvedSlice:
    """Solve a single vertical slice.

    Inner voices are selected sequentially: alto first, then tenor. Each inner
    voice's candidates are filtered against all already-selected voices (outer
    and preceding inner) to prevent parallel fifths/octaves between ALL pairs.

    choice_indices: tuple of indices into ranked candidates per inner voice.
    Default (None or all zeros) selects best candidate for each voice.
    """
    voice_count: int = voice_set.count
    soprano_range: Tuple[int, int] = get_voice_range(0, voice_count)
    bass_range: Tuple[int, int] = get_voice_range(voice_count - 1, voice_count)
    soprano_midi: int = resolve_outer_pitch(soprano_pitch, key, (soprano_range[0] + soprano_range[1]) // 2)
    bass_midi: int = resolve_outer_pitch(bass_pitch, key, (bass_range[0] + bass_range[1]) // 2)
    if voice_count == 2:
        return SolvedSlice(offset=slice_offset, pitches=(soprano_midi, bass_midi))
    prev_pitches: dict[int, int] | None = None
    if prev_solved is not None:
        prev_pitches = {i: p for i, p in enumerate(prev_solved.pitches)}
    context: HarmonicContext = infer_harmony_from_outer(soprano_pitch, bass_pitch, key)
    curr_pitches: dict[int, int] = {0: soprano_midi, voice_count - 1: bass_midi}
    inner_count: int = voice_count - 2
    if choice_indices is None:
        choice_indices = tuple(0 for _ in range(inner_count))
    result_pitches: list[int] = [soprano_midi]
    for i, inner_idx in enumerate(range(1, voice_count - 1)):
        candidates: Tuple[int, ...] = get_inner_voice_candidates(
            inner_idx, context, curr_pitches, prev_pitches, key, voice_count
        )
        idx: int = choice_indices[i] % len(candidates)
        selected: int = candidates[idx]
        result_pitches.append(selected)
        curr_pitches[inner_idx] = selected
    result_pitches.append(bass_midi)
    return SolvedSlice(offset=slice_offset, pitches=tuple(result_pitches))


# =============================================================================
# Parallel 4-voice slice solver
# =============================================================================

# Scoring weights for configuration evaluation
PARALLEL_FIFTH_PENALTY: float = 100.0  # Hard constraint
PARALLEL_OCTAVE_PENALTY: float = 100.0  # Hard constraint
NON_CHORD_TONE_COST: float = 15.0  # Strong preference for chord tones
VOICE_CROSSING_PENALTY: float = 50.0  # Prevent crossing outer voices
VOICE_CROSSING_REWARD: float = -30.0  # Reward crossing in interleaved mode (negative = reward)
UNISON_PENALTY: float = 100.0  # Match parallel penalty - unisons are forbidden
OCTAVE_DOUBLING_COST: float = 8.0  # Mild preference against octave doublings
VOICE_LEADING_LEAP_COST: float = 0.15  # Per semitone for large leaps
SPACING_VIOLATION_COST: float = 3.0  # Per semitone below MIN_VOICE_SEPARATION
MAX_VOICE_SPACING: float = 14.0  # Maximum semitones between adjacent voices
MAX_SPACING_VIOLATION_COST: float = 50.0  # Per semitone above max (high to prevent gaps)
STATIC_VOICE_COST: float = 15.0  # Penalize not moving - discourage drone inner voices
STEP_REWARD: float = -3.0  # Reward stepwise motion (negative = reward)


def _get_voice_candidates(
    voice_idx: int,
    soprano_midi: int,
    key: Key,
    voice_count: int,
) -> Tuple[int, ...]:
    """Get all candidate pitches for a voice (bass, alto, or tenor).

    For bass: generates scale tones in bass range (chord inferred from bass choice).
    For inner voices: generates scale tones in voice range.
    """
    voice_range: Tuple[int, int] = get_voice_range(voice_idx, voice_count)
    # Generate all scale tones in range
    scale: Tuple[int, ...] = key.scale
    candidates: list[int] = []
    for semitone in scale:
        pc: int = (key.tonic_pc + semitone) % 12
        midi: int = pc
        while midi < voice_range[0]:
            midi += 12
        while midi <= voice_range[1]:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates))


def _check_all_parallels(
    config: Tuple[int, ...],
    prev_config: Tuple[int, ...] | None,
) -> float:
    """Check for parallel fifths/octaves between ALL voice pairs.

    Returns total penalty for all parallel violations.
    """
    from shared.parallels import is_parallel_fifth, is_parallel_octave

    if prev_config is None:
        return 0.0

    penalty: float = 0.0
    voice_count: int = len(config)

    # Check all pairs (upper_idx < lower_idx means upper_idx is higher voice)
    for upper_idx in range(voice_count):
        for lower_idx in range(upper_idx + 1, voice_count):
            prev_upper: int = prev_config[upper_idx]
            prev_lower: int = prev_config[lower_idx]
            curr_upper: int = config[upper_idx]
            curr_lower: int = config[lower_idx]

            # Skip if either voice was resting
            if prev_upper == -1 or prev_lower == -1:
                continue
            if curr_upper == -1 or curr_lower == -1:
                continue

            if is_parallel_fifth(prev_upper, prev_lower, curr_upper, curr_lower):
                penalty += PARALLEL_FIFTH_PENALTY
            if is_parallel_octave(prev_upper, prev_lower, curr_upper, curr_lower):
                penalty += PARALLEL_OCTAVE_PENALTY

    return penalty


def _check_voice_crossings(
    config: Tuple[int, ...],
    crossing_mode: str = "penalize",
) -> float:
    """Check for voice crossings (higher index voice above lower index voice).

    Args:
        config: Voice configuration (pitches by index)
        crossing_mode: "penalize" (default), "reward" (for interleaved), or "allow"

    Returns penalty (positive) or reward (negative) for crossings.
    """
    cost: float = 0.0
    crossing_count: int = 0
    for i in range(len(config) - 1):
        if config[i] != -1 and config[i + 1] != -1:
            if config[i] < config[i + 1]:  # Higher index has higher pitch = crossing
                crossing_count += 1
    if crossing_mode == "reward":
        cost = crossing_count * VOICE_CROSSING_REWARD  # Negative = reward
    elif crossing_mode == "penalize":
        cost = crossing_count * VOICE_CROSSING_PENALTY
    # "allow" mode: cost stays 0
    return cost


def _score_sonority(
    config: Tuple[int, ...],
    chord_tones_pc: set[int],
) -> float:
    """Score vertical sonority - penalize non-chord tones.

    Soprano and bass define the chord, so only penalize inner voices.
    """
    cost: float = 0.0
    # Inner voices are indices 1 to len-2
    for i in range(1, len(config) - 1):
        pitch: int = config[i]
        if pitch == -1:
            continue
        pc: int = pitch % 12
        if pc not in chord_tones_pc:
            cost += NON_CHORD_TONE_COST
    return cost


def _score_spacing(config: Tuple[int, ...]) -> float:
    """Score spacing between adjacent voices."""
    cost: float = 0.0
    for i in range(len(config) - 1):
        if config[i] == -1 or config[i + 1] == -1:
            continue
        separation: int = config[i] - config[i + 1]  # Higher voice - lower voice
        if separation < MIN_VOICE_SEPARATION:
            cost += (MIN_VOICE_SEPARATION - separation) * SPACING_VIOLATION_COST
        # Penalize wide spacing
        if separation > MAX_VOICE_SPACING:
            cost += (separation - MAX_VOICE_SPACING) * MAX_SPACING_VIOLATION_COST
        # Penalize unisons
        if separation == 0:
            cost += UNISON_PENALTY
        # Penalize octave doublings
        elif separation % 12 == 0:
            cost += OCTAVE_DOUBLING_COST
    return cost


def _score_voice_leading(
    config: Tuple[int, ...],
    prev_config: Tuple[int, ...] | None,
) -> float:
    """Score voice leading from previous configuration.

    Strongly penalizes static voices (drone behavior) and rewards stepwise motion.
    """
    if prev_config is None:
        return 0.0

    cost: float = 0.0
    for i in range(len(config)):
        curr: int = config[i]
        prev: int = prev_config[i]
        if curr == -1 or prev == -1:
            continue
        interval: int = abs(curr - prev)
        if interval == 0:
            cost += STATIC_VOICE_COST  # Strongly discourage drone behavior
        elif interval <= 2:
            cost += STEP_REWARD  # Reward steps (negative cost)
        elif interval <= 4:
            cost += 0.2  # Small leaps ok
        elif interval <= 7:
            cost += 0.6  # Larger leaps less preferred
        else:
            cost += interval * VOICE_LEADING_LEAP_COST
    return cost


def _score_configuration(
    config: Tuple[int, ...],
    prev_config: Tuple[int, ...] | None,
    chord_tones_pc: set[int],
    crossing_mode: str = "penalize",
) -> float:
    """Score a complete voice configuration.

    Lower score is better.

    Args:
        config: Voice configuration (pitches by index)
        prev_config: Previous slice configuration for voice leading
        chord_tones_pc: Pitch classes that are chord tones
        crossing_mode: "penalize" (default), "reward" (for interleaved), or "allow"
    """
    cost: float = 0.0
    cost += _check_all_parallels(config, prev_config)
    cost += _check_voice_crossings(config, crossing_mode)
    cost += _score_sonority(config, chord_tones_pc)
    cost += _score_spacing(config)
    cost += _score_voice_leading(config, prev_config)
    return cost


def _get_thematic_inner_candidates(
    thematic_pitch: Pitch,
    inner_idx: int,
    voice_count: int,
    key: Key,
    chord_pc: set[int],
) -> Tuple[int, ...]:
    """Get inner voice candidates preferring thematic pitch octave variants.

    Returns octave variants of thematic pitch that are chord tones,
    falling back to all chord tones in range if thematic pitch isn't a chord tone.
    """
    voice_range: Tuple[int, int] = get_voice_range(inner_idx, voice_count)
    median: int = (voice_range[0] + voice_range[1]) // 2

    if is_rest(thematic_pitch):
        return ()

    # Resolve thematic pitch to MIDI
    if isinstance(thematic_pitch, MidiPitch):
        base_midi: int = thematic_pitch.midi
    elif isinstance(thematic_pitch, FloatingNote):
        base_midi = key.floating_to_midi(thematic_pitch, median, median)
    else:
        base_midi = median

    thematic_pc: int = base_midi % 12

    # If thematic pitch is a chord tone, use octave variants
    if thematic_pc in chord_pc:
        candidates: list[int] = []
        for octave_shift in [0, 12, -12, 24, -24]:
            candidate: int = base_midi + octave_shift
            if voice_range[0] <= candidate <= voice_range[1]:
                candidates.append(candidate)
        if candidates:
            return tuple(sorted(candidates))

    # Fall back to all chord tones in range
    candidates = []
    for pc in chord_pc:
        midi: int = pc
        while midi < voice_range[0]:
            midi += 12
        while midi <= voice_range[1]:
            candidates.append(midi)
            midi += 12
    return tuple(sorted(candidates)) if candidates else (median,)


def solve_slice_parallel(
    slice_offset: Fraction,
    soprano_pitch: Pitch,
    prev_solved: SolvedSlice | None,
    key: Key,
    voice_count: int,
    choice_index: int = 0,
    bass_pitch: Pitch | None = None,
    inner_thematic: dict[int, Pitch] | None = None,
    crossing_mode: str = "penalize",
) -> Tuple[SolvedSlice, int]:
    """Solve a vertical slice by evaluating all voice configurations in parallel.

    Soprano is fixed. Bass and inner voices use candidates based on:
    - bass_pitch: if provided, use it; otherwise enumerate bass candidates
    - inner_thematic: if provided for an inner voice, prefer thematic pitch octaves

    Each complete configuration is scored holistically.
    Returns the n-th best configuration (0 = best).

    Args:
        slice_offset: Time offset for this slice
        soprano_pitch: Fixed soprano pitch
        prev_solved: Previous slice solution for voice leading
        key: Musical key
        voice_count: Number of voices (2, 3, or 4)
        choice_index: Index into ranked configurations (0 = best)
        bass_pitch: Optional fixed bass pitch (from expanded phrase)
        inner_thematic: Optional dict mapping inner voice index to thematic pitch
        crossing_mode: "penalize" (default), "reward" (for interleaved), or "allow"

    Returns:
        Tuple of (solved slice, number of valid configurations)
    """
    soprano_range: Tuple[int, int] = get_voice_range(0, voice_count)
    soprano_median: int = (soprano_range[0] + soprano_range[1]) // 2
    soprano_midi: int = resolve_outer_pitch(soprano_pitch, key, soprano_median)

    prev_config: Tuple[int, ...] | None = prev_solved.pitches if prev_solved else None

    # Resolve bass - either from provided pitch or generate candidates
    bass_range: Tuple[int, int] = get_voice_range(voice_count - 1, voice_count)
    bass_median: int = (bass_range[0] + bass_range[1]) // 2

    if bass_pitch is not None and not is_rest(bass_pitch):
        # Bass is fixed from expanded phrase
        bass_midi: int = resolve_outer_pitch(bass_pitch, key, bass_median)
        bass_candidates: Tuple[int, ...] = (bass_midi,)
    else:
        # Generate bass candidates
        bass_candidates = _get_voice_candidates(voice_count - 1, soprano_midi, key, voice_count)

    if voice_count == 2:
        # 2-voice: just soprano and bass
        configs: list[Tuple[Tuple[int, ...], float]] = []
        for bass in bass_candidates:
            config: Tuple[int, ...] = (soprano_midi, bass)
            chord_tones: Tuple[int, ...] = infer_chord_from_bass_midi(bass, key)
            chord_pc: set[int] = {ct % 12 for ct in chord_tones}
            score: float = _score_configuration(config, prev_config, chord_pc, crossing_mode)
            configs.append((config, score))

        configs.sort(key=lambda x: x[1])
        idx: int = choice_index % len(configs) if configs else 0
        best_config: Tuple[int, ...] = configs[idx][0] if configs else (soprano_midi, soprano_midi - 12)
        return SolvedSlice(offset=slice_offset, pitches=best_config), len(configs)

    # 3+ voices: enumerate all combinations
    configs = []
    for bass in bass_candidates:
        # Infer chord from bass
        chord_tones: Tuple[int, ...] = infer_chord_from_bass_midi(bass, key)
        chord_pc: set[int] = {ct % 12 for ct in chord_tones}

        # Get candidates for each inner voice
        inner_cands: list[Tuple[int, ...]] = []
        inner_resting: list[bool] = []
        for inner_idx in range(1, voice_count - 1):
            thematic: Pitch | None = inner_thematic.get(inner_idx) if inner_thematic else None
            if thematic is not None and is_rest(thematic):
                # Voice is resting at this slice
                inner_resting.append(True)
                inner_cands.append((-1,))  # Rest marker
            elif thematic is not None:
                # Use thematic candidates
                cands = _get_thematic_inner_candidates(
                    thematic, inner_idx, voice_count, key, chord_pc
                )
                inner_resting.append(False)
                inner_cands.append(cands if cands else _get_voice_candidates(inner_idx, soprano_midi, key, voice_count))
            else:
                # Fall back to scale tones
                inner_resting.append(False)
                inner_cands.append(_get_voice_candidates(inner_idx, soprano_midi, key, voice_count))

        # Generate inner voice combinations
        if inner_cands:
            for inner_combo in product(*inner_cands):
                config = (soprano_midi,) + inner_combo + (bass,)
                score = _score_configuration(config, prev_config, chord_pc, crossing_mode)
                configs.append((config, score))
        else:
            config = (soprano_midi, bass)
            score = _score_configuration(config, prev_config, chord_pc, crossing_mode)
            configs.append((config, score))

    # Sort by score (lower is better)
    configs.sort(key=lambda x: x[1])

    # Return n-th best configuration
    idx: int = choice_index % len(configs) if configs else 0
    best_config: Tuple[int, ...] = configs[idx][0] if configs else tuple([soprano_midi] * voice_count)

    return SolvedSlice(offset=slice_offset, pitches=best_config), len(configs)


def infer_chord_from_bass_midi(bass_midi: int, key: Key) -> Tuple[int, ...]:
    """Infer chord tones from bass MIDI pitch.

    Returns tuple of pitch classes for the triad built on bass.
    """
    from engine.harmonic_context import pc_to_degree, infer_chord_from_bass

    bass_pc: int = bass_midi % 12
    degree: int | None = pc_to_degree(bass_pc, key)
    if degree is None:
        # Chromatic - default to tonic triad
        degree = 1
    return infer_chord_from_bass(degree, key)


@dataclass(frozen=True)
class TimedNote:
    """Note with onset, pitch (MIDI), and duration."""
    onset: Fraction
    pitch: int
    duration: Fraction


def build_timed_notes(
    pitches: list[Pitch],
    durations: list[Fraction],
) -> list[TimedNote]:
    """Convert pitch/duration lists to TimedNote sequence."""
    notes: list[TimedNote] = []
    offset: Fraction = Fraction(0)
    for p, d in zip(pitches, durations):
        if isinstance(p, MidiPitch):
            notes.append(TimedNote(onset=offset, pitch=p.midi, duration=d))
        offset += d
    return notes


def sounding_pitch_at(notes: list[TimedNote], offset: Fraction) -> int | None:
    """Get the sounding MIDI pitch at a given offset, or None if rest/gap."""
    for n in reversed(notes):
        if n.onset <= offset < n.onset + n.duration:
            return n.pitch
    return None


def build_solved_voices(
    solved_slices: list[SolvedSlice],
    original_voices: ExpandedVoices,
    key: Key,
) -> ExpandedVoices:
    """Convert solved slices back to ExpandedVoices.

    Pipeline is diatonic - all pitches should be FloatingNote (scale degrees).
    Outer voices: preserve original FloatingNote pitches.
    Inner voices: convert slice-derived MIDI pitches back to FloatingNote.
    """
    voice_count: int = original_voices.count
    if voice_count == 2:
        return original_voices
    inner_count: int = voice_count - 2
    inner_pitches: list[list[Pitch]] = [[] for _ in range(inner_count)]
    inner_durations: list[list[Fraction]] = [[] for _ in range(inner_count)]
    # Prepend rest if first slice doesn't start at 0
    if solved_slices and solved_slices[0].offset > Fraction(0):
        rest_dur: Fraction = solved_slices[0].offset
        for inner_idx in range(inner_count):
            inner_pitches[inner_idx].append(Rest())
            inner_durations[inner_idx].append(rest_dur)
    for i, solved in enumerate(solved_slices):
        if i < len(solved_slices) - 1:
            dur: Fraction = solved_slices[i + 1].offset - solved.offset
        else:
            dur = original_voices.soprano.budget - solved.offset
        if dur <= Fraction(0):
            continue
        for inner_idx in range(inner_count):
            midi: int = solved.pitches[inner_idx + 1]
            if midi == -1:
                # Rest marker - voice is silent at this slice
                inner_pitches[inner_idx].append(Rest())
            else:
                # Convert MIDI back to scale degree for diatonic pipeline
                inner_pitches[inner_idx].append(key.midi_to_floating(midi))
            inner_durations[inner_idx].append(dur)
    # Outer voices: preserve original FloatingNote pitches (no conversion)
    soprano_mat: VoiceMaterial = VoiceMaterial(
        voice_index=0,
        pitches=list(original_voices.soprano.pitches),
        durations=list(original_voices.soprano.durations),
    )
    materials: list[VoiceMaterial] = [soprano_mat]
    for i in range(inner_count):
        materials.append(VoiceMaterial(
            voice_index=i + 1,
            pitches=inner_pitches[i],
            durations=inner_durations[i],
        ))
    materials.append(VoiceMaterial(
        voice_index=voice_count - 1,
        pitches=list(original_voices.bass.pitches),
        durations=list(original_voices.bass.durations),
    ))
    return ExpandedVoices(voices=materials)

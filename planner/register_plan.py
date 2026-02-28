"""Register planner: computes soprano/bass target pitches for episode phrases (REG-1).

Two-pass algorithm:
  Pass 1 — collect anchor pitches (first MIDI note of each non-episode,
            non-cadential phrase) by inspecting thematic_roles.
  Pass 2 — for each episode phrase compute start/end MIDI targets using
            contrary motion (soprano descends, bass ascends) with:
            - ascending soprano override when descent can't bridge to next anchor
            - splice clamping (gap to next anchor <= MAX_SPLICE_DISTANCE)
            - range clamping
            - voice separation enforcement (>= MIN_VOICE_SEPARATION)

Back-to-back episodes use the previous episode's end pitch as start.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from shared.voice_types import Range

if TYPE_CHECKING:
    from builder.phrase_types import PhrasePlan
    from motifs.subject_loader import SubjectTriple

_log: logging.Logger = logging.getLogger(__name__)

# ── Constants (L002) ─────────────────────────────────────────────────────────
SEMITONES_PER_BAR: int = 2        # budget per bar: ~1 diatonic step
MAX_SPLICE_DISTANCE: int = 12     # max gap (semitones) between episode end and next anchor
MIN_VOICE_SEPARATION: int = 16    # min separation (10th) between soprano and bass at endpoints
_CS_SPACING_TIGHT: int = 10       # mirrors viterbi.costs.SPACING_TIGHT used in cs_writer.py
_ENDPOINT_MARGIN: int = 4         # semitones of headroom below range ceiling for episode endpoints;
                                  # prevents episode dialogue from overshooting the range boundary
_MIN_MEANINGFUL_MOTION: int = 4   # ascending override is skipped when the clamped result would
                                  # move the soprano fewer than this many semitones


@dataclass(frozen=True)
class RegisterTarget:
    """Planned registral start and end pitches for one episode phrase (REG-1)."""
    start_upper_midi: int
    end_upper_midi: int
    start_lower_midi: int
    end_lower_midi: int


def _sequence_fit_shift(midi_pitches: tuple[int, ...], voice_range: Range) -> int:
    """Return the octave-multiple shift that places midi_pitches within voice_range.

    Replicates the algorithm in builder.imitation._fit_shift without importing
    from the builder package (which would create a circular dependency).
    Finds the k*12 shift closest to zero such that every pitch in the
    sequence lands within [voice_range.low, voice_range.high].
    If no octave multiple fits (sequence span > range span), picks the
    shift nearest to the midpoint of the valid interval.

    Args:
        midi_pitches: Tuple of absolute MIDI pitch values for the sequence.
        voice_range: The target voice range the sequence must fit within.

    Returns:
        Shift in semitones (always a multiple of 12).
    """
    lo: int = min(midi_pitches)
    hi: int = max(midi_pitches)
    shift_lo: int = voice_range.low - lo
    shift_hi: int = voice_range.high - hi
    k_lo: int = math.ceil(shift_lo / 12)
    k_hi: int = math.floor(shift_hi / 12)
    best: int | None = None
    best_dist: int = 9999
    for k in range(k_lo, k_hi + 1):
        candidate: int = k * 12
        dist: int = abs(candidate)
        if dist < best_dist:
            best = candidate
            best_dist = dist
    if best is not None:
        return best
    # No octave multiple fits — use shift nearest to midpoint of valid interval.
    mid: float = (shift_lo + shift_hi) / 2
    k_near: int = round(mid / 12)
    candidates_k: list[int] = [k_near - 1, k_near, k_near + 1]
    best_k: int = k_near
    best_dist_f: float = float("inf")
    for k in candidates_k:
        candidate = k * 12
        dist_f: float = abs(candidate - mid)
        if dist_f < best_dist_f or (dist_f == best_dist_f and abs(candidate) < abs(best_k * 12)):
            best_k = k
            best_dist_f = dist_f
    _log.warning(
        "No octave-multiple shift fits sequence [%d..%d] in range [%d, %d]; using k=%d",
        lo, hi, voice_range.low, voice_range.high, best_k,
    )
    return best_k * 12


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp integer to [low, high]."""
    return max(low, min(high, value))


def _has_cs_role(plan: PhrasePlan, voice: int) -> bool:
    """Return True if voice has ThematicRole.CS on beat 0 of the phrase."""
    from fractions import Fraction
    from planner.thematic import ThematicRole

    if plan.thematic_roles is None:
        return False
    for br in plan.thematic_roles:
        if br.voice == voice and br.beat == Fraction(0):
            return br.role == ThematicRole.CS
    return False


def _anchor_pitch(
    plan: PhrasePlan,
    voice: int,
    fugue: SubjectTriple,
    voice_range: Range,
) -> int | None:
    """Return the first MIDI pitch for one voice in a thematic phrase.

    Supports SUBJECT, STRETTO, ANSWER, and CS roles.  Returns None for
    HOLD/FREE/EPISODE/CADENCE/PEDAL where pitch is not predetermined.

    The lazy import of ThematicRole avoids circular imports at module init.
    Uses _sequence_fit_shift (whole-sequence octave placement) to mirror
    the exact register the builder will place each entry in.

    Args:
        plan: The phrase plan (must have thematic_roles populated).
        voice: 0 for soprano/upper, 1 for bass/lower.
        fugue: Subject triple supplying MIDI pitch sequences.
        voice_range: The voice's allowed MIDI range for octave placement.

    Returns:
        MIDI pitch of the first note after whole-sequence octave placement,
        matching the register the builder will render, or None.
    """
    from planner.thematic import ThematicRole

    if plan.thematic_roles is None:
        return None

    for br in plan.thematic_roles:
        if br.voice != voice:
            continue
        tonic_midi: int = 60 + br.material_key.tonic_pc
        if br.role in (ThematicRole.SUBJECT, ThematicRole.STRETTO):
            pitches: tuple[int, ...] = fugue.subject_midi(tonic_midi=tonic_midi, mode=br.material_key.mode)
            shift: int = _sequence_fit_shift(midi_pitches=pitches, voice_range=voice_range)
            return pitches[0] + shift
        if br.role == ThematicRole.ANSWER:
            pitches = fugue.answer_midi()
            shift = _sequence_fit_shift(midi_pitches=pitches, voice_range=voice_range)
            return pitches[0] + shift
        if br.role == ThematicRole.CS:
            cs_index: int = 0
            if br.material is not None and str(br.material).isdigit():
                cs_index = int(br.material)
            pitches = fugue.get_countersubject_midi(
                index=cs_index, tonic_midi=tonic_midi, mode=br.material_key.mode,
            )
            shift = _sequence_fit_shift(midi_pitches=pitches, voice_range=voice_range)
            return pitches[0] + shift
        # HOLD, FREE, EPISODE, CADENCE, PEDAL: pitch not computable ahead of time.
        return None

    return None


def compute_register_targets(
    phrases: list[PhrasePlan],
    upper_range: Range,
    lower_range: Range,
    fugue: SubjectTriple,
) -> dict[int, RegisterTarget]:
    """Compute episode register targets with full piece-level visibility (REG-1).

    Pass 1: For every non-episode, non-cadential phrase collect the first
    MIDI pitch of soprano (voice 0) and bass (voice 1) by inspecting
    thematic_roles.  These become anchor points for the episode budget
    computation.

    Pass 2: Walk phrases in order tracking a running (cur_upper, cur_lower)
    start pitch.  For each episode phrase:
      - budget = bar_span * SEMITONES_PER_BAR
      - direction: soprano descends, bass ascends (contrary motion norm)
      - override: if descending soprano can't reach within MAX_SPLICE_DISTANCE
        of the next anchor, ascend instead
      - splice clamp: pull end_pitch toward next anchor when gap > MAX_SPLICE_DISTANCE
      - range clamp: keep pitches inside voice_range
      - separation: push voices apart if end_upper - end_lower < MIN_VOICE_SEPARATION

    Back-to-back episodes use the previous episode's end pitch as their start.

    Args:
        phrases: Full phrase plan sequence in bar order.
        upper_range: Soprano voice range (MIDI).
        lower_range: Bass voice range (MIDI).
        fugue: Subject triple for computing thematic entry pitches.

    Returns:
        Dict mapping phrase index to RegisterTarget, for episode phrases only.
    """
    # ── Pass 1: anchor pitches ───────────────────────────────────────────────
    anchors: dict[int, tuple[int | None, int | None]] = {}
    for i, plan in enumerate(phrases):
        if plan.schema_name == "episode" or plan.is_cadential:
            continue
        upper_pitch: int | None = _anchor_pitch(
            plan=plan, voice=0, fugue=fugue, voice_range=upper_range,
        )
        lower_pitch: int | None = _anchor_pitch(
            plan=plan, voice=1, fugue=fugue, voice_range=lower_range,
        )
        # CS spacing correction: generate_cs_viterbi shifts the CS boundary knot
        # up (or down) by an octave when it lands within _CS_SPACING_TIGHT semitones
        # of the companion voice.  Replicate that adjustment so anchor pitches
        # match the register the builder will actually place.
        if upper_pitch is not None and lower_pitch is not None:
            gap: int = upper_pitch - lower_pitch
            if gap < _CS_SPACING_TIGHT:
                if _has_cs_role(plan, 0):
                    # Upper voice has CS: push it up by an octave (companion is below)
                    candidate_up: int = upper_pitch + 12
                    if candidate_up <= upper_range.high:
                        upper_pitch = candidate_up
                elif _has_cs_role(plan, 1):
                    # Lower voice has CS: push it down by an octave (companion is above)
                    candidate_dn: int = lower_pitch - 12
                    if candidate_dn >= lower_range.low:
                        lower_pitch = candidate_dn

        if upper_pitch is not None or lower_pitch is not None:
            anchors[i] = (upper_pitch, lower_pitch)

    # ── Pass 2: episode targets ──────────────────────────────────────────────
    targets: dict[int, RegisterTarget] = {}
    cur_upper: int | None = None
    cur_lower: int | None = None

    for i, plan in enumerate(phrases):
        if plan.schema_name != "episode":
            # Non-episode: update running start from anchor if available.
            if i in anchors:
                a_upper, a_lower = anchors[i]
                if a_upper is not None:
                    cur_upper = a_upper
                if a_lower is not None:
                    cur_lower = a_lower
            continue

        # Episode phrase — running start must be known.
        assert cur_upper is not None, (
            f"Episode at phrase {i} (bars {plan.start_bar}-"
            f"{plan.start_bar + plan.bar_span - 1}) has no prior soprano pitch — "
            f"ensure at least one thematic entry precedes this episode."
        )
        assert cur_lower is not None, (
            f"Episode at phrase {i} (bars {plan.start_bar}-"
            f"{plan.start_bar + plan.bar_span - 1}) has no prior bass pitch — "
            f"ensure at least one thematic entry precedes this episode."
        )

        start_upper: int = cur_upper
        start_lower: int = cur_lower
        budget: int = plan.bar_span * SEMITONES_PER_BAR

        # Find next anchor for splice clamping.
        next_anchor_upper: int | None = None
        next_anchor_lower: int | None = None
        for j in range(i + 1, len(phrases)):
            if j in anchors:
                next_anchor_upper, next_anchor_lower = anchors[j]
                break

        # Contrary motion default: soprano descends, bass ascends.
        # Override soprano to ascending when descending can't bridge to next anchor,
        # but only when the ascending result (after margin clamp) would produce at
        # least _MIN_MEANINGFUL_MOTION semitones of motion — otherwise the ascent
        # overshoots the range ceiling and gets clamped back to the start pitch.
        raw_desc_upper: int = start_upper - budget
        raw_asc_upper: int = start_upper + budget
        eff_asc_upper: int = _clamp(
            raw_asc_upper, upper_range.low, upper_range.high - _ENDPOINT_MARGIN,
        )
        _asc_override: bool = (
            next_anchor_upper is not None
            and abs(raw_desc_upper - next_anchor_upper) > MAX_SPLICE_DISTANCE
            and eff_asc_upper - start_upper >= _MIN_MEANINGFUL_MOTION
        )
        end_upper: int = eff_asc_upper if _asc_override else raw_desc_upper

        # Bass ascends by default; fall back to descent when ascending would yield
        # zero motion (start already at or above the clamped ceiling).
        raw_asc_lower: int = start_lower + budget
        end_lower: int = _clamp(
            raw_asc_lower, lower_range.low, lower_range.high - _ENDPOINT_MARGIN,
        )
        if end_lower == start_lower:
            # Ascending gives no movement — descend for registral breathing.
            end_lower = _clamp(
                start_lower - budget, lower_range.low, lower_range.high - _ENDPOINT_MARGIN,
            )

        # Splice clamp: pull end pitch toward next anchor so gap <= MAX_SPLICE_DISTANCE.
        if next_anchor_upper is not None and abs(end_upper - next_anchor_upper) > MAX_SPLICE_DISTANCE:
            if next_anchor_upper > end_upper:
                end_upper = next_anchor_upper - MAX_SPLICE_DISTANCE
            else:
                end_upper = next_anchor_upper + MAX_SPLICE_DISTANCE

        if next_anchor_lower is not None and abs(end_lower - next_anchor_lower) > MAX_SPLICE_DISTANCE:
            if next_anchor_lower > end_lower:
                end_lower = next_anchor_lower - MAX_SPLICE_DISTANCE
            else:
                end_lower = next_anchor_lower + MAX_SPLICE_DISTANCE

        # Range clamp for soprano (bass was already clamped with margin above).
        # Keeps _ENDPOINT_MARGIN semitones inside the range boundary so the episode
        # dialogue has headroom to overshoot without triggering tessitura_excursion.
        end_upper = _clamp(
            value=end_upper,
            low=upper_range.low,
            high=upper_range.high - _ENDPOINT_MARGIN,
        )

        # Voice separation: ensure end_upper - end_lower >= MIN_VOICE_SEPARATION.
        if end_upper - end_lower < MIN_VOICE_SEPARATION:
            dist_lower_to_high: int = lower_range.high - end_lower
            dist_upper_to_low: int = end_upper - upper_range.low
            if dist_lower_to_high <= dist_upper_to_low:
                # Lower closer to its ceiling: push upper up.
                end_upper = _clamp(
                    value=end_lower + MIN_VOICE_SEPARATION,
                    low=upper_range.low,
                    high=upper_range.high,
                )
            else:
                # Upper closer to its floor: push lower down.
                end_lower = _clamp(
                    value=end_upper - MIN_VOICE_SEPARATION,
                    low=lower_range.low,
                    high=lower_range.high,
                )

        targets[i] = RegisterTarget(
            start_upper_midi=start_upper,
            end_upper_midi=end_upper,
            start_lower_midi=start_lower,
            end_lower_midi=end_lower,
        )

        _log.debug(
            "Register[%d] ep bars %d-%d: U %d->%d  L %d->%d",
            i, plan.start_bar, plan.start_bar + plan.bar_span - 1,
            start_upper, end_upper, start_lower, end_lower,
        )

        # Back-to-back episode: next episode starts where this one ends.
        cur_upper = end_upper
        cur_lower = end_lower

    return targets

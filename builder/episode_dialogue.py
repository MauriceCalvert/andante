"""Episode dialogue: imitative two-voice episode generation.

Generates episodes as imitative dialogue where two voices trade a 1-bar
fragment derived from the subject, imitating each other at a lower 10th
with a 1-beat offset, transposing stepwise through the key journey, and
compressing the fragment in the final iterations to build urgency.

When paired kernels are available (EpisodeKernelSource returns a chain),
the two voices each play their own rhythmically independent material from
the CS/Answer overlap, sequenced stepwise.  The fallback uses the EPI-5b
single-fragment imitative approach.
"""
import logging
from dataclasses import replace
from fractions import Fraction
from builder.types import Note
from motifs.episode_kernel import EpisodeKernelSource
from motifs.extract_kernels import PairedKernel
from motifs.fragment_catalogue import extract_head, extract_tail
from motifs.head_generator import degrees_to_midi
from motifs.subject_loader import SubjectTriple
from shared.constants import (
    CONSONANT_INTERVALS_ABOVE_BASS,
    TRACK_BASS,
    TRACK_SOPRANO,
)
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMITATION_DEGREE_OFFSET: int = -9        # lower 10th in diatonic space
IMITATION_BEAT_DELAY: Fraction = Fraction(1, 4)  # 1 crotchet beat
VOICE_EXCHANGE_THRESHOLD: int = 6        # swap voices for 6+ bar episodes

_DEGREE_SEARCH_LO: int = -7
_DEGREE_SEARCH_HI: int = 14
_DEFAULT_START_DEGREE: int = 4           # dominant (0-indexed)


# ---------------------------------------------------------------------------
# Helpers (shared by both paired-kernel and fallback paths)
# ---------------------------------------------------------------------------


def _midi_to_nearest_degree(
    midi: int,
    tonic_midi: int,
    mode: str,
) -> int:
    """Find the scale degree whose MIDI pitch is closest to target."""
    best_deg: int = _DEFAULT_START_DEGREE
    best_dist: int = 9999
    for deg in range(_DEGREE_SEARCH_LO, _DEGREE_SEARCH_HI + 1):
        m: int = degrees_to_midi((deg,), tonic_midi, mode)[0]
        dist: int = abs(m - midi)
        if dist < best_dist:
            best_dist = dist
            best_deg = deg
    return best_deg


def _compute_step_schedule(start_deg: int, end_deg: int, bar_count: int) -> list[int]:
    """Cumulative degree offsets for each bar (index 0..bar_count-1).

    schedule[i] is the cumulative degree offset for bar i relative to start_deg.
    Front-loaded: first r bars get (q+1) steps; remaining bars get q steps.
    This gives larger steps early and commits the voice to its direction.
    """
    total_steps: int = end_deg - start_deg
    sign: int = 1 if total_steps >= 0 else -1
    q, r = divmod(abs(total_steps), bar_count)
    schedule: list[int] = []
    cumulative: int = 0
    for i in range(bar_count):
        step: int = (q + 1) if i < r else q
        cumulative += step * sign
        schedule.append(cumulative)
    return schedule


def _build_bar_fragment(
    triple: SubjectTriple,
    bar_length: Fraction,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Extract 1-bar fragment from subject (head + enough tail to fill bar)."""
    head = extract_head(fugue=triple, bar_length=bar_length)
    head_total: Fraction = sum(head.durations, Fraction(0))
    if head_total >= bar_length:
        return head.degrees, head.durations

    tail = extract_tail(fugue=triple, bar_length=bar_length)
    degrees: list[int] = list(head.degrees)
    durations: list[Fraction] = list(head.durations)
    cumulative: Fraction = head_total

    for deg, dur in zip(tail.degrees, tail.durations):
        remaining: Fraction = bar_length - cumulative
        if dur <= remaining:
            degrees.append(deg)
            durations.append(dur)
            cumulative += dur
            if cumulative == bar_length:
                break
        else:
            if remaining > 0:
                degrees.append(deg)
                durations.append(remaining)
            break

    return tuple(degrees), tuple(durations)


def _build_half_fragment(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    half_length: Fraction,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Extract first-half fragment: notes up to half_length, truncating last if needed."""
    half_degrees: list[int] = []
    half_durations: list[Fraction] = []
    cumulative: Fraction = Fraction(0)

    for deg, dur in zip(degrees, durations):
        remaining: Fraction = half_length - cumulative
        if dur <= remaining:
            half_degrees.append(deg)
            half_durations.append(dur)
            cumulative += dur
            if cumulative == half_length:
                break
        else:
            if remaining > 0:
                half_degrees.append(deg)
                half_durations.append(remaining)
            break

    return tuple(half_degrees), tuple(half_durations)


def _adapt_to_available(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    available: Fraction,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Fit fragment exactly into `available` duration.

    Truncation removes notes from the end when the last note would become
    zero or negative; extension grows the last note to fill any shortfall.
    """
    total: Fraction = sum(durations, Fraction(0))
    if total == available:
        return degrees, durations

    adapted_deg: list[int] = list(degrees)
    adapted_dur: list[Fraction] = list(durations)

    if total > available:
        while adapted_dur:
            over: Fraction = sum(adapted_dur, Fraction(0)) - available
            if over <= 0:
                break
            if adapted_dur[-1] <= over:
                adapted_deg.pop()
                adapted_dur.pop()
            else:
                adapted_dur[-1] = adapted_dur[-1] - over
                break
    else:
        adapted_dur[-1] = adapted_dur[-1] + (available - total)

    assert len(adapted_dur) > 0, (
        f"Fragment completely consumed by truncation: "
        f"total={total}, available={available}. "
        "Increase bar_length or decrease IMITATION_BEAT_DELAY."
    )
    return tuple(adapted_deg), tuple(adapted_dur)


def _emit_voice_notes(
    iter_start: Fraction,
    bar_length: Fraction,
    fragment_degrees: tuple[int, ...],
    fragment_durations: tuple[Fraction, ...],
    base_degree: int,
    tonic_midi: int,
    mode: str,
    is_leader: bool,
    track: int,
) -> list[Note]:
    """Emit notes for one voice in one fallback-path iteration.

    Leader plays immediately; follower has a gap-fill sustain first.
    """
    delay: Fraction = Fraction(0) if is_leader else IMITATION_BEAT_DELAY
    available: Fraction = bar_length - delay

    emit_degrees, adapted_durations = _adapt_to_available(
        degrees=fragment_degrees,
        durations=fragment_durations,
        available=available,
    )

    notes: list[Note] = []
    offset: Fraction = iter_start

    if not is_leader:
        first_midi: int = degrees_to_midi(
            (emit_degrees[0] + base_degree,), tonic_midi, mode,
        )[0]
        notes.append(Note(
            offset=offset,
            pitch=first_midi,
            duration=IMITATION_BEAT_DELAY,
            voice=track,
        ))
        offset = iter_start + IMITATION_BEAT_DELAY

    for deg, dur in zip(emit_degrees, adapted_durations):
        absolute_deg: int = deg + base_degree
        midi: int = degrees_to_midi((absolute_deg,), tonic_midi, mode)[0]
        notes.append(Note(
            offset=offset,
            pitch=midi,
            duration=dur,
            voice=track,
        ))
        offset += dur

    return notes


def _place_near(
    notes: tuple[Note, ...],
    prev_pitch: int,
    label: str,
) -> tuple[Note, ...]:
    """Shift all notes by the octave multiple placing first note nearest prev_pitch."""
    if not notes:
        return notes
    first_raw: int = notes[0].pitch
    delta: int = prev_pitch - first_raw
    # Nearest octave multiple to delta.
    shift: int = round(delta / 12) * 12
    if shift == 0:
        return notes
    return tuple(replace(n, pitch=n.pitch + shift) for n in notes)


def _build_onsets(durations: tuple[Fraction, ...]) -> list[Fraction]:
    """Build note-onset list from a duration sequence."""
    onsets: list[Fraction] = []
    cumulative: Fraction = Fraction(0)
    for dur in durations:
        onsets.append(cumulative)
        cumulative += dur
    return onsets


def _emit_paired_voice_notes(
    iter_start: Fraction,
    bar_length: Fraction,
    abs_degrees: list[int],
    durations: tuple[Fraction, ...],
    tonic_midi: int,
    mode: str,
    track: int,
) -> list[Note]:
    """Emit notes for one voice in one paired-kernel iteration.

    No leader/follower gap-fill: each voice starts at iter_start and fills
    bar_length independently.
    """
    adapted_degs, adapted_durs = _adapt_to_available(
        degrees=tuple(abs_degrees),
        durations=durations,
        available=bar_length,
    )
    notes: list[Note] = []
    offset: Fraction = iter_start
    for deg, dur in zip(adapted_degs, adapted_durs):
        midi: int = degrees_to_midi((deg,), tonic_midi, mode)[0]
        notes.append(Note(
            offset=offset,
            pitch=midi,
            duration=dur,
            voice=track,
        ))
        offset += dur
    return notes


def _apply_consonance_check(
    upper_abs_degs: list[int],
    lower_abs_degs: list[int],
    upper_durs: tuple[Fraction, ...],
    lower_durs: tuple[Fraction, ...],
    tonic_midi: int,
    mode: str,
    lower_range: Range,
) -> None:
    """Adjust lower_abs_degs in-place to restore consonance at shared attacks.

    For each time point where both voices have a note onset, checks the
    semitone interval against CONSONANT_INTERVALS_ABOVE_BASS.  If the original
    (un-transposed) position was consonant but the transposed version is
    dissonant, adjusts the lower voice by ±1 diatonic degree.
    """
    u_onsets: list[Fraction] = _build_onsets(upper_durs)
    l_onsets: list[Fraction] = _build_onsets(lower_durs)
    shared_attacks: set[Fraction] = set(u_onsets) & set(l_onsets)

    if not shared_attacks:
        return

    center_lower: int = (lower_range.low + lower_range.high) // 2

    for t in sorted(shared_attacks):
        i_u: int = u_onsets.index(t)
        i_l: int = l_onsets.index(t)

        u_midi: int = degrees_to_midi((upper_abs_degs[i_u],), tonic_midi, mode)[0]
        l_midi: int = degrees_to_midi((lower_abs_degs[i_l],), tonic_midi, mode)[0]
        interval: int = abs(u_midi - l_midi) % 12

        if interval in CONSONANT_INTERVALS_ABOVE_BASS:
            continue  # Already consonant — nothing to do.

        # Dissonant: try ±1 diatonic adjustment on the lower voice.
        best_deg: int = lower_abs_degs[i_l]
        best_consonant: bool = False

        for adj in (+1, -1):
            cand_deg: int = lower_abs_degs[i_l] + adj
            cand_midi: int = degrees_to_midi((cand_deg,), tonic_midi, mode)[0]
            cand_interval: int = abs(u_midi - cand_midi) % 12
            if cand_interval not in CONSONANT_INTERVALS_ABOVE_BASS:
                continue
            if not best_consonant:
                # First consonant candidate — take it.
                best_deg = cand_deg
                best_consonant = True
            else:
                # Second consonant candidate — prefer the one closer to range centre.
                current_midi: int = degrees_to_midi((best_deg,), tonic_midi, mode)[0]
                if abs(cand_midi - center_lower) < abs(current_midi - center_lower):
                    best_deg = cand_deg

        if best_consonant:
            lower_abs_degs[i_l] = best_deg


# ---------------------------------------------------------------------------
# EpisodeDialogue
# ---------------------------------------------------------------------------


class EpisodeDialogue:
    """Generates two-voice episodes from subject material.

    Primary path: paired-kernel chains from EpisodeKernelSource (EPI-6).
    Fallback path: single-fragment imitative dialogue (EPI-5b).
    """

    def __init__(self, triple: SubjectTriple) -> None:
        metre_str: str = f"{triple.metre[0]}/{triple.metre[1]}"
        self._bar_length: Fraction = parse_metre(metre=metre_str)[0]
        self._tonic_midi: int = triple.tonic_midi
        self._mode: str = triple.subject.mode
        self._kernel_source: EpisodeKernelSource = EpisodeKernelSource(triple=triple)
        self._init_fallback(triple=triple)

    def _init_fallback(self, triple: SubjectTriple) -> None:
        """Initialise fallback state (EPI-5b single-fragment approach)."""
        frag_degrees_raw, frag_durations = _build_bar_fragment(
            triple=triple,
            bar_length=self._bar_length,
        )
        assert len(frag_degrees_raw) >= 2, (
            f"Episode fragment has {len(frag_degrees_raw)} notes; need >= 2. "
            f"Subject degrees: {triple.subject.degrees}, "
            f"durations: {triple.subject.durations}. "
            "Ensure the subject has at least 2 notes in the first bar."
        )
        offset0: int = frag_degrees_raw[0]
        self._fragment_degrees: tuple[int, ...] = tuple(
            d - offset0 for d in frag_degrees_raw
        )
        self._fragment_durations: tuple[Fraction, ...] = frag_durations

        self._half_degrees, self._half_durations = _build_half_fragment(
            degrees=self._fragment_degrees,
            durations=self._fragment_durations,
            half_length=self._bar_length / 2,
        )
        assert len(self._half_degrees) >= 1, (
            f"Half-fragment is empty for bar_length={self._bar_length}. "
            "Ensure the first bar of the subject contains notes."
        )

        _raw_head_deg, _raw_head_dur = _build_half_fragment(
            degrees=self._fragment_degrees,
            durations=self._fragment_durations,
            half_length=IMITATION_BEAT_DELAY,
        )
        assert len(_raw_head_deg) >= 1, (
            f"Head-fragment is empty for IMITATION_BEAT_DELAY={IMITATION_BEAT_DELAY}. "
            "Ensure the subject head contains notes shorter than IMITATION_BEAT_DELAY."
        )
        if len(_raw_head_deg) > 1:
            self._head_degrees: tuple[int, ...] = _raw_head_deg[:-1]
            self._head_durations: tuple[Fraction, ...] = _raw_head_dur[:-1]
        else:
            self._head_degrees = _raw_head_deg
            self._head_durations = _raw_head_dur

    def generate(
        self,
        bar_count: int,
        episode_key: Key,
        start_offset: Fraction,
        lead_voice: int,
        upper_range: Range,
        lower_range: Range,
        prior_upper_midi: int,
        prior_lower_midi: int,
        target_upper_midi: int,
        target_lower_midi: int,
        journey: str = "stepwise",
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Generate both episode voices.  Returns (soprano_notes, bass_notes)."""
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
        assert journey in ("stepwise",), (
            f"Unsupported journey '{journey}'. Only 'stepwise' is implemented."
        )

        tonic_midi: int = episode_key.tonic_pc + 60
        mode: str = episode_key.mode

        # Snap prior and target pitches to nearest diatonic degrees.
        start_upper_deg: int = _midi_to_nearest_degree(
            midi=prior_upper_midi, tonic_midi=tonic_midi, mode=mode,
        )
        end_upper_deg: int = _midi_to_nearest_degree(
            midi=target_upper_midi, tonic_midi=tonic_midi, mode=mode,
        )
        start_lower_deg: int = _midi_to_nearest_degree(
            midi=prior_lower_midi, tonic_midi=tonic_midi, mode=mode,
        )
        end_lower_deg: int = _midi_to_nearest_degree(
            midi=target_lower_midi, tonic_midi=tonic_midi, mode=mode,
        )

        # Per-voice cumulative step schedules.
        upper_schedule: list[int] = _compute_step_schedule(
            start_upper_deg, end_upper_deg, bar_count,
        )
        lower_schedule: list[int] = _compute_step_schedule(
            start_lower_deg, end_lower_deg, bar_count,
        )

        # Try paired-kernel path first.
        chain: list[PairedKernel] | None = self._kernel_source.generate(
            bar_count=bar_count,
        )
        if chain is not None:
            _log.debug(
                "Episode bar_count=%d: paired-kernel path (%d kernels in pool)",
                bar_count, len(self._kernel_source.pool),
            )
            return self._generate_paired(
                chain=chain,
                bar_count=bar_count,
                start_offset=start_offset,
                tonic_midi=tonic_midi,
                mode=mode,
                start_upper_deg=start_upper_deg,
                start_lower_deg=start_lower_deg,
                upper_schedule=upper_schedule,
                lower_schedule=lower_schedule,
                upper_range=upper_range,
                lower_range=lower_range,
                prior_upper_midi=prior_upper_midi,
                prior_lower_midi=prior_lower_midi,
            )

        # Fallback: EPI-5b single-fragment imitative dialogue.
        _log.warning(
            "Episode bar_count=%d: fallback path (pool size=%d)",
            bar_count, len(self._kernel_source.pool),
        )
        return self._generate_fallback(
            bar_count=bar_count,
            start_offset=start_offset,
            tonic_midi=tonic_midi,
            mode=mode,
            start_upper_deg=start_upper_deg,
            start_lower_deg=start_lower_deg,
            upper_schedule=upper_schedule,
            lower_schedule=lower_schedule,
            lead_voice=lead_voice,
            upper_range=upper_range,
            lower_range=lower_range,
            prior_upper_midi=prior_upper_midi,
            prior_lower_midi=prior_lower_midi,
        )

    # -----------------------------------------------------------------------
    # Paired-kernel path
    # -----------------------------------------------------------------------

    def _generate_paired(
        self,
        chain: list[PairedKernel],
        bar_count: int,
        start_offset: Fraction,
        tonic_midi: int,
        mode: str,
        start_upper_deg: int,
        start_lower_deg: int,
        upper_schedule: list[int],
        lower_schedule: list[int],
        upper_range: Range,
        lower_range: Range,
        prior_upper_midi: int,
        prior_lower_midi: int,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Generate episode using paired-kernel chain."""
        # Voice exchange at midpoint of long episodes.
        # Each voice takes the other's melodic contour but stays in its own register:
        #   soprano ← lower_degrees renormalized by −lower_degrees[0] → starts at 0
        #   bass    ← upper_degrees shifted by  +lower_degrees[0]     → stays at bass register
        exchange_point: int = (
            len(chain) // 2 if bar_count >= VOICE_EXCHANGE_THRESHOLD else len(chain)
        )

        soprano_notes: list[Note] = []
        bass_notes: list[Note] = []
        cumulative_offset: Fraction = Fraction(0)
        # Bar index increments once per bar, not once per kernel.
        cumulative_bars: int = 0

        for i, pk in enumerate(chain):
            # pk_lower_base: register gap between voices (lower_degrees[0] ≤ 0).
            pk_lower_base: int = pk.lower_degrees[0] if pk.lower_degrees else 0
            voice_exchanged: bool = i >= exchange_point
            if voice_exchanged:
                # Soprano takes bass contour, renormalized to 0 so it stays at soprano register.
                upper_pk_degs: list[int] = [d - pk_lower_base for d in pk.lower_degrees]
                # Bass takes soprano contour as-is: upper_degrees[0]==0 and start_lower_deg
                # already encodes bass register, so no additional shift is needed.
                lower_pk_degs: list[int] = list(pk.upper_degrees)
                upper_durs: tuple[Fraction, ...] = pk.lower_durations
                lower_durs: tuple[Fraction, ...] = pk.upper_durations
            else:
                upper_pk_degs = list(pk.upper_degrees)
                lower_pk_degs = list(pk.lower_degrees)
                upper_durs = pk.upper_durations
                lower_durs = pk.lower_durations

            # Per-voice offsets from endpoint-driven schedules (EPI-8).
            bar_idx: int = min(cumulative_bars, len(upper_schedule) - 1)
            upper_offset: int = upper_schedule[bar_idx]
            lower_offset: int = lower_schedule[bar_idx]

            # Absolute degrees for this iteration — IMITATION_DEGREE_OFFSET no longer
            # applied to the trajectory; each voice navigates its own endpoint.
            upper_abs: list[int] = [
                d + upper_offset + start_upper_deg for d in upper_pk_degs
            ]
            lower_abs: list[int] = [
                d + lower_offset + start_lower_deg for d in lower_pk_degs
            ]

            # Consonance check: adjust lower in-place where needed.
            _apply_consonance_check(
                upper_abs_degs=upper_abs,
                lower_abs_degs=lower_abs,
                upper_durs=upper_durs,
                lower_durs=lower_durs,
                tonic_midi=tonic_midi,
                mode=mode,
                lower_range=lower_range,
            )

            iter_start: Fraction = start_offset + cumulative_offset

            sop_iter_notes: list[Note] = _emit_paired_voice_notes(
                iter_start=iter_start,
                bar_length=pk.total_duration,
                abs_degrees=upper_abs,
                durations=upper_durs,
                tonic_midi=tonic_midi,
                mode=mode,
                track=TRACK_SOPRANO,
            )
            bass_iter_notes: list[Note] = _emit_paired_voice_notes(
                iter_start=iter_start,
                bar_length=pk.total_duration,
                abs_degrees=lower_abs,
                durations=lower_durs,
                tonic_midi=tonic_midi,
                mode=mode,
                track=TRACK_BASS,
            )

            # Place each iteration relative to previous exit pitch.
            sop_prev: int = (
                soprano_notes[-1].pitch if soprano_notes
                else prior_upper_midi
            )
            bass_prev: int = (
                bass_notes[-1].pitch if bass_notes
                else prior_lower_midi
            )
            sop_shifted: tuple[Note, ...] = _place_near(
                notes=tuple(sop_iter_notes),
                prev_pitch=sop_prev,
                label="Episode soprano",
            )
            bass_shifted: tuple[Note, ...] = _place_near(
                notes=tuple(bass_iter_notes),
                prev_pitch=bass_prev,
                label="Episode bass",
            )

            soprano_notes.extend(sop_shifted)
            bass_notes.extend(bass_shifted)
            cumulative_offset += pk.total_duration
            # Track bar crossings for pitch transposition.
            cumulative_bars = int(cumulative_offset / self._bar_length)

        episode_end: Fraction = start_offset + cumulative_offset
        return self._finalise(
            soprano_notes=soprano_notes,
            bass_notes=bass_notes,
            episode_end=episode_end,
        )

    # -----------------------------------------------------------------------
    # Fallback path (EPI-5b single-fragment imitative dialogue)
    # -----------------------------------------------------------------------

    def _generate_fallback(
        self,
        bar_count: int,
        start_offset: Fraction,
        tonic_midi: int,
        mode: str,
        start_upper_deg: int,
        start_lower_deg: int,
        upper_schedule: list[int],
        lower_schedule: list[int],
        lead_voice: int,
        upper_range: Range,
        lower_range: Range,
        prior_upper_midi: int,
        prior_lower_midi: int,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Generate episode using EPI-5b single-fragment approach (fallback)."""
        assert len(self._fragment_degrees) >= 2, (
            "Fragment has fewer than 2 notes; cannot generate dialogue. "
            "Verify subject extraction produced a valid fragment."
        )

        frag_count: int = min(2, bar_count // 3)
        full_count: int = bar_count - frag_count
        exchange_point: int = (
            bar_count // 2 if bar_count >= VOICE_EXCHANGE_THRESHOLD else bar_count
        )

        soprano_notes: list[Note] = []
        bass_notes: list[Note] = []

        for i in range(bar_count):
            current_leader: int = lead_voice if i < exchange_point else 1 - lead_voice

            if i < full_count:
                leader_degrees: tuple[int, ...] = self._fragment_degrees
                leader_durations: tuple[Fraction, ...] = self._fragment_durations
                follower_degrees: tuple[int, ...] = self._head_degrees
                follower_durations: tuple[Fraction, ...] = self._head_durations
            else:
                leader_degrees = self._half_degrees
                leader_durations = self._half_durations
                follower_degrees = self._half_degrees
                follower_durations = self._half_durations

            iter_start: Fraction = start_offset + i * self._bar_length

            # Per-voice base degrees from endpoint-driven schedules (EPI-8).
            sop_base: int = upper_schedule[i] + start_upper_deg
            sop_is_leader: bool = (current_leader == 0)
            sop_frag_degrees: tuple[int, ...] = (
                leader_degrees if sop_is_leader else follower_degrees
            )
            sop_frag_durations: tuple[Fraction, ...] = (
                leader_durations if sop_is_leader else follower_durations
            )
            sop_iter_notes: list[Note] = _emit_voice_notes(
                iter_start=iter_start,
                bar_length=self._bar_length,
                fragment_degrees=sop_frag_degrees,
                fragment_durations=sop_frag_durations,
                base_degree=sop_base,
                tonic_midi=tonic_midi,
                mode=mode,
                is_leader=sop_is_leader,
                track=TRACK_SOPRANO,
            )

            # IMITATION_DEGREE_OFFSET no longer applied to trajectory (EPI-8).
            bass_base: int = lower_schedule[i] + start_lower_deg
            bass_is_leader: bool = (current_leader == 1)
            bass_frag_degrees: tuple[int, ...] = (
                leader_degrees if bass_is_leader else follower_degrees
            )
            bass_frag_durations: tuple[Fraction, ...] = (
                leader_durations if bass_is_leader else follower_durations
            )
            bass_iter_notes: list[Note] = _emit_voice_notes(
                iter_start=iter_start,
                bar_length=self._bar_length,
                fragment_degrees=bass_frag_degrees,
                fragment_durations=bass_frag_durations,
                base_degree=bass_base,
                tonic_midi=tonic_midi,
                mode=mode,
                is_leader=bass_is_leader,
                track=TRACK_BASS,
            )

            sop_prev: int = (
                soprano_notes[-1].pitch if soprano_notes
                else prior_upper_midi
            )
            bass_prev: int = (
                bass_notes[-1].pitch if bass_notes
                else prior_lower_midi
            )
            sop_shifted: tuple[Note, ...] = _place_near(
                notes=tuple(sop_iter_notes),
                prev_pitch=sop_prev,
                label="Episode soprano",
            )
            bass_shifted: tuple[Note, ...] = _place_near(
                notes=tuple(bass_iter_notes),
                prev_pitch=bass_prev,
                label="Episode bass",
            )

            soprano_notes.extend(sop_shifted)
            bass_notes.extend(bass_shifted)

        episode_end: Fraction = start_offset + bar_count * self._bar_length
        return self._finalise(
            soprano_notes=soprano_notes,
            bass_notes=bass_notes,
            episode_end=episode_end,
        )

    # -----------------------------------------------------------------------
    # Shared utilities
    # -----------------------------------------------------------------------


    def _finalise(
        self,
        soprano_notes: list[Note],
        bass_notes: list[Note],
        episode_end: Fraction,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Stamp creator="episode", assert positive durations."""
        soprano_tuple: tuple[Note, ...] = tuple(
            replace(n, creator="episode") for n in soprano_notes
        )
        bass_tuple: tuple[Note, ...] = tuple(
            replace(n, creator="episode") for n in bass_notes
        )
        assert all(n.duration > 0 for n in soprano_tuple), (
            "Episode soprano contains a non-positive note duration. "
            "Check fragment extraction and bar_length."
        )
        assert all(n.duration > 0 for n in bass_tuple), (
            "Episode bass contains a non-positive note duration. "
            "Check fragment extraction and bar_length."
        )
        return soprano_tuple, bass_tuple

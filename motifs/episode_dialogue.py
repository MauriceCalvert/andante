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

from builder.imitation import _fit_shift
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


def _apply_octave_shift(
    notes: tuple[Note, ...],
    target_range: Range,
    label: str,
    prev_last_pitch: int | None = None,
) -> tuple[Note, ...]:
    """Octave-shift all notes into target_range using _fit_shift.

    When prev_last_pitch is supplied, prefers the octave offset that keeps
    the first note closest to prev_last_pitch, as long as all notes remain
    within target_range.
    """
    if not notes:
        return notes
    midi_pitches: tuple[int, ...] = tuple(n.pitch for n in notes)
    base_shift: int = _fit_shift(
        midi_pitches=midi_pitches,
        target_range=target_range,
        label=label,
    )
    if prev_last_pitch is None:
        shift = base_shift
    else:
        lo: int = min(midi_pitches)
        hi: int = max(midi_pitches)
        best_shift: int = base_shift
        best_gap: int = abs(notes[0].pitch + base_shift - prev_last_pitch)
        for alt in (base_shift - 12, base_shift + 12):
            if lo + alt >= target_range.low and hi + alt <= target_range.high:
                gap: int = abs(notes[0].pitch + alt - prev_last_pitch)
                if gap < best_gap:
                    best_gap = gap
                    best_shift = alt
        shift = best_shift
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
            _log.debug(
                "Consonance fix at shared attack t=%s: lower deg %d → %d",
                t, lower_abs_degs[i_l], best_deg,
            )
            lower_abs_degs[i_l] = best_deg
        else:
            _log.debug(
                "Consonance fix failed at t=%s: no consonant ±1 adjustment available",
                t,
            )


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
        prior_upper_midi: int | None,
        prior_lower_midi: int | None,
        ascending: bool,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Generate both episode voices.  Returns (soprano_notes, bass_notes)."""
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"

        tonic_midi: int = episode_key.tonic_pc + 60
        mode: str = episode_key.mode
        step: int = 1 if ascending else -1

        # Determine start_degree from prior soprano pitch (ascending-aware).
        start_degree: int = _DEFAULT_START_DEGREE
        if prior_upper_midi is not None:
            nearest: int = _midi_to_nearest_degree(
                midi=prior_upper_midi,
                tonic_midi=tonic_midi,
                mode=mode,
            )
            if ascending or nearest >= _DEFAULT_START_DEGREE:
                start_degree = nearest

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
                step=step,
                start_degree=start_degree,
                upper_range=upper_range,
                lower_range=lower_range,
                prior_upper_midi=prior_upper_midi,
                prior_lower_midi=prior_lower_midi,
            )

        # Fallback: EPI-5b single-fragment imitative dialogue.
        _log.debug(
            "Episode bar_count=%d: fallback path (pool size=%d)",
            bar_count, len(self._kernel_source.pool),
        )
        return self._generate_fallback(
            bar_count=bar_count,
            start_offset=start_offset,
            tonic_midi=tonic_midi,
            mode=mode,
            step=step,
            start_degree=start_degree,
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
        step: int,
        start_degree: int,
        upper_range: Range,
        lower_range: Range,
        prior_upper_midi: int | None,
        prior_lower_midi: int | None,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Generate episode using paired-kernel chain."""
        exchange_point: int = (
            bar_count // 2 if bar_count >= VOICE_EXCHANGE_THRESHOLD else bar_count
        )

        soprano_notes: list[Note] = []
        bass_notes: list[Note] = []

        for i, pk in enumerate(chain):
            # Voice assignment: after exchange_point, swap upper/lower.
            voice_exchanged: bool = i >= exchange_point
            if voice_exchanged:
                upper_pk_degs = list(pk.lower_degrees)
                lower_pk_degs = list(pk.upper_degrees)
                upper_durs: tuple[Fraction, ...] = pk.lower_durations
                lower_durs: tuple[Fraction, ...] = pk.upper_durations
            else:
                upper_pk_degs = list(pk.upper_degrees)
                lower_pk_degs = list(pk.lower_degrees)
                upper_durs = pk.upper_durations
                lower_durs = pk.lower_durations

            pitch_offset: int = i * step

            # Absolute degrees for this iteration.
            upper_abs: list[int] = [
                d + pitch_offset + start_degree for d in upper_pk_degs
            ]
            lower_abs: list[int] = [
                d + pitch_offset + start_degree + IMITATION_DEGREE_OFFSET
                for d in lower_pk_degs
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

            iter_start: Fraction = start_offset + i * self._bar_length

            sop_iter_notes: list[Note] = _emit_paired_voice_notes(
                iter_start=iter_start,
                bar_length=self._bar_length,
                abs_degrees=upper_abs,
                durations=upper_durs,
                tonic_midi=tonic_midi,
                mode=mode,
                track=TRACK_SOPRANO,
            )
            bass_iter_notes: list[Note] = _emit_paired_voice_notes(
                iter_start=iter_start,
                bar_length=self._bar_length,
                abs_degrees=lower_abs,
                durations=lower_durs,
                tonic_midi=tonic_midi,
                mode=mode,
                track=TRACK_BASS,
            )

            # Per-iteration octave shift.
            sop_shifted: tuple[Note, ...] = _apply_octave_shift(
                notes=tuple(sop_iter_notes),
                target_range=upper_range,
                label="Episode soprano",
                prev_last_pitch=soprano_notes[-1].pitch if soprano_notes else None,
            )
            bass_shifted: tuple[Note, ...] = _apply_octave_shift(
                notes=tuple(bass_iter_notes),
                target_range=lower_range,
                label="Episode bass",
                prev_last_pitch=bass_notes[-1].pitch if bass_notes else None,
            )

            # Entry anchoring at i == 0.
            if i == 0:
                sop_shifted, bass_shifted = self._anchor_entry(
                    sop_shifted=sop_shifted,
                    bass_shifted=bass_shifted,
                    prior_upper_midi=prior_upper_midi,
                    prior_lower_midi=prior_lower_midi,
                    upper_range=upper_range,
                    lower_range=lower_range,
                )

            soprano_notes.extend(sop_shifted)
            bass_notes.extend(bass_shifted)

        return self._finalise(soprano_notes=soprano_notes, bass_notes=bass_notes)

    # -----------------------------------------------------------------------
    # Fallback path (EPI-5b single-fragment imitative dialogue)
    # -----------------------------------------------------------------------

    def _generate_fallback(
        self,
        bar_count: int,
        start_offset: Fraction,
        tonic_midi: int,
        mode: str,
        step: int,
        start_degree: int,
        lead_voice: int,
        upper_range: Range,
        lower_range: Range,
        prior_upper_midi: int | None,
        prior_lower_midi: int | None,
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

            pitch_offset: int = i * step
            iter_start: Fraction = start_offset + i * self._bar_length

            sop_base: int = pitch_offset + start_degree
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

            bass_base: int = pitch_offset + start_degree + IMITATION_DEGREE_OFFSET
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

            sop_shifted: tuple[Note, ...] = _apply_octave_shift(
                notes=tuple(sop_iter_notes),
                target_range=upper_range,
                label="Episode soprano",
                prev_last_pitch=soprano_notes[-1].pitch if soprano_notes else None,
            )
            bass_shifted: tuple[Note, ...] = _apply_octave_shift(
                notes=tuple(bass_iter_notes),
                target_range=lower_range,
                label="Episode bass",
                prev_last_pitch=bass_notes[-1].pitch if bass_notes else None,
            )

            if i == 0:
                sop_shifted, bass_shifted = self._anchor_entry(
                    sop_shifted=sop_shifted,
                    bass_shifted=bass_shifted,
                    prior_upper_midi=prior_upper_midi,
                    prior_lower_midi=prior_lower_midi,
                    upper_range=upper_range,
                    lower_range=lower_range,
                )

            soprano_notes.extend(sop_shifted)
            bass_notes.extend(bass_shifted)

        return self._finalise(soprano_notes=soprano_notes, bass_notes=bass_notes)

    # -----------------------------------------------------------------------
    # Shared utilities
    # -----------------------------------------------------------------------

    def _anchor_entry(
        self,
        sop_shifted: tuple[Note, ...],
        bass_shifted: tuple[Note, ...],
        prior_upper_midi: int | None,
        prior_lower_midi: int | None,
        upper_range: Range,
        lower_range: Range,
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Apply entry anchoring: correct octave if first note leaps > P5 from prior."""
        if prior_upper_midi is not None and sop_shifted:
            sop_gap: int = sop_shifted[0].pitch - prior_upper_midi
            if abs(sop_gap) > 7:
                sop_corr: int = -12 if sop_gap > 0 else 12
                sop_cand: tuple[Note, ...] = tuple(
                    replace(n, pitch=n.pitch + sop_corr) for n in sop_shifted
                )
                cand_lo: int = min(n.pitch for n in sop_cand)
                cand_hi: int = max(n.pitch for n in sop_cand)
                if cand_lo >= upper_range.low and cand_hi <= upper_range.high:
                    sop_shifted = sop_cand

        if prior_lower_midi is not None and bass_shifted:
            bass_gap: int = bass_shifted[0].pitch - prior_lower_midi
            if abs(bass_gap) > 7:
                bass_corr: int = -12 if bass_gap > 0 else 12
                bass_cand: tuple[Note, ...] = tuple(
                    replace(n, pitch=n.pitch + bass_corr) for n in bass_shifted
                )
                cand_lo = min(n.pitch for n in bass_cand)
                cand_hi = max(n.pitch for n in bass_cand)
                if cand_lo >= lower_range.low and cand_hi <= lower_range.high:
                    bass_shifted = bass_cand

        return sop_shifted, bass_shifted

    def _finalise(
        self,
        soprano_notes: list[Note],
        bass_notes: list[Note],
    ) -> tuple[tuple[Note, ...], tuple[Note, ...]]:
        """Stamp creator="episode" and assert positive durations."""
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

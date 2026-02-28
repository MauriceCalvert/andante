"""Episode dialogue: imitative two-voice episode generation.

Generates episodes as imitative dialogue where two voices trade a 1-bar
fragment derived from the subject, imitating each other at a lower 10th
with a 1-beat offset, transposing stepwise through the key journey, and
compressing the fragment in the final iterations to build urgency.
"""
import logging
from dataclasses import replace
from fractions import Fraction

from builder.imitation import _fit_shift
from builder.types import Note
from motifs.fragment_catalogue import extract_head, extract_tail
from motifs.head_generator import degrees_to_midi
from motifs.subject_loader import SubjectTriple
from shared.constants import TRACK_BASS, TRACK_SOPRANO
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range

_log: logging.Logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IMITATION_DEGREE_OFFSET: int = -9        # lower 10th in diatonic space
IMITATION_BEAT_DELAY: Fraction = Fraction(1, 4)  # 1 crotchet beat
VOICE_EXCHANGE_THRESHOLD: int = 6        # swap leader for 6+ bar episodes

_DEGREE_SEARCH_LO: int = -7
_DEGREE_SEARCH_HI: int = 14
_DEFAULT_START_DEGREE: int = 4           # dominant (0-indexed: degree 4 = 5th scale degree)


# ---------------------------------------------------------------------------
# Helpers
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

    # Head does not fill the bar; append tail notes until bar_length is reached.
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
        # Remove/trim from end until total == available.
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
    """Emit notes for one voice in one iteration.

    The voice plays the fragment (relative degrees + base_degree), preceded
    by a gap fill note if it is the follower.  Notes are adapted so that the
    voice fills exactly bar_length: notes are removed/truncated from the end
    if total exceeds available time, or the last note is extended if short.
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

    # Gap fill for follower: sustained note at the follower's first pitch.
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

    # Fragment notes.
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

    When prev_last_pitch is supplied, the function also tries the two
    neighbouring octave multiples (base ± 12) and prefers whichever
    keeps the first note closest to prev_last_pitch, as long as all notes
    stay within target_range.  This prevents grotesque inter-iteration
    jumps when per-iteration shifting is used.
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


# ---------------------------------------------------------------------------
# EpisodeDialogue
# ---------------------------------------------------------------------------


class EpisodeDialogue:
    """Generates two-voice imitative dialogue episodes from subject material.

    Both voices state a 1-bar fragment from the subject in close imitation
    (1 beat offset, lower 10th).  The dialogue sequences stepwise through
    the key journey, compresses to a half-fragment in the final iterations,
    and exchanges leading voice at the midpoint for episodes of 6+ bars.
    """

    def __init__(self, triple: SubjectTriple) -> None:
        metre_str: str = f"{triple.metre[0]}/{triple.metre[1]}"
        self._bar_length: Fraction = parse_metre(metre=metre_str)[0]
        self._tonic_midi: int = triple.tonic_midi
        self._mode: str = triple.subject.mode

        # Build full 1-bar fragment.
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

        # Normalise: shift so first degree = 0.
        offset0: int = frag_degrees_raw[0]
        self._fragment_degrees: tuple[int, ...] = tuple(
            d - offset0 for d in frag_degrees_raw
        )
        self._fragment_durations: tuple[Fraction, ...] = frag_durations

        # Build half-fragment (first half of bar): used for compression iterations.
        self._half_degrees, self._half_durations = _build_half_fragment(
            degrees=self._fragment_degrees,
            durations=self._fragment_durations,
            half_length=self._bar_length / 2,
        )
        assert len(self._half_degrees) >= 1, (
            f"Half-fragment is empty for bar_length={self._bar_length}. "
            f"Fragment degrees: {self._fragment_degrees}, "
            f"durations: {self._fragment_durations}. "
            "Ensure the first bar of the subject contains notes."
        )

        # Build head fragment (notes up to IMITATION_BEAT_DELAY only).
        # The follower in a full-fragment iteration plays these notes and then
        # sustains the last pitch via _adapt_to_available extension.  Because
        # this fragment ends with the last semiquaver — not with the first
        # crotchet of the descending tail — the sustained pitch is a 10th below
        # the leader's beat-2 note.  The leader then descends through the
        # crotchet tail in oblique motion against the follower's held pitch.
        #
        # One note is trimmed from the built head so the follower sustains at
        # degree -2 (not -3).  With a 3-semiquaver head the inter-iteration gap
        # for ascending episodes is a P4 (3 diatonic steps) rather than a
        # tritone (4 diatonic steps), eliminating ugly cross-iteration leaps
        # while the oblique-motion guarantee is unchanged: the follower's last
        # pitch change still falls strictly between consecutive leader crotchet
        # boundaries.
        _raw_head_deg, _raw_head_dur = _build_half_fragment(
            degrees=self._fragment_degrees,
            durations=self._fragment_durations,
            half_length=IMITATION_BEAT_DELAY,
        )
        assert len(_raw_head_deg) >= 1, (
            f"Head-fragment is empty for IMITATION_BEAT_DELAY={IMITATION_BEAT_DELAY}. "
            f"Fragment degrees: {self._fragment_degrees}, "
            f"durations: {self._fragment_durations}. "
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
        """Generate both episode voices in imitative dialogue.

        Returns (soprano_notes, bass_notes).
        """
        assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"
        assert len(self._fragment_degrees) >= 2, (
            "Fragment has fewer than 2 notes; cannot generate dialogue. "
            "Verify subject extraction produced a valid fragment."
        )

        frag_count: int = min(2, bar_count // 3)
        full_count: int = bar_count - frag_count
        step: int = 1 if ascending else -1
        exchange_point: int = (
            bar_count // 2 if bar_count >= VOICE_EXCHANGE_THRESHOLD else bar_count
        )

        tonic_midi: int = episode_key.tonic_pc + 60
        mode: str = episode_key.mode

        # Starting degree: nearest to prior soprano pitch, or default dominant.
        # For descending episodes, do not lower start_degree below the default:
        # a low starting degree causes later iterations to go below the soprano
        # range floor, forcing a +12 octave shift that creates a grotesque leap.
        # For ascending episodes the risk is absent, so cross-phrase priors are
        # applied freely in both directions.
        start_degree: int = _DEFAULT_START_DEGREE
        if prior_upper_midi is not None:
            nearest: int = _midi_to_nearest_degree(
                midi=prior_upper_midi,
                tonic_midi=tonic_midi,
                mode=mode,
            )
            if ascending or nearest >= _DEFAULT_START_DEGREE:
                start_degree = nearest

        soprano_notes: list[Note] = []
        bass_notes: list[Note] = []

        for i in range(bar_count):
            current_leader: int = lead_voice if i < exchange_point else 1 - lead_voice

            # Full-fragment iterations: leader plays the complete 1-bar fragment
            # (including the crotchet descending tail); follower plays only the
            # semiquaver head and sustains the last semiquaver pitch for the
            # remaining bar time.  Because the head ends with the last semiquaver
            # (not the first crotchet), _adapt_to_available extends that note
            # into a hold.  The leader then descends in oblique motion against
            # the follower's held pitch, preventing the lockstep parallel octaves.
            # Compression iterations: both voices use the half-fragment as before.
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

            # Soprano (upper voice, track 0): no IMITATION_DEGREE_OFFSET.
            sop_base: int = pitch_offset + start_degree
            sop_is_leader: bool = (current_leader == 0)
            sop_frag_degrees: tuple[int, ...] = leader_degrees if sop_is_leader else follower_degrees
            sop_frag_durations: tuple[Fraction, ...] = leader_durations if sop_is_leader else follower_durations
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

            # Bass (lower voice, track 3): IMITATION_DEGREE_OFFSET places it a 10th below.
            bass_base: int = pitch_offset + start_degree + IMITATION_DEGREE_OFFSET
            bass_is_leader: bool = (current_leader == 1)
            bass_frag_degrees: tuple[int, ...] = leader_degrees if bass_is_leader else follower_degrees
            bass_frag_durations: tuple[Fraction, ...] = leader_durations if bass_is_leader else follower_durations
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

            # Per-iteration octave shift: each iteration is shifted independently
            # so that descending sequences stay in range throughout the episode.
            # The smooth shift prefers the octave offset that keeps the first
            # note of this iteration close to the last note of the previous
            # iteration, avoiding grotesque inter-iteration leaps.
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

            # Entry anchoring: if the first iteration leaps more than a P5 from
            # the prior voice, shift the whole first iteration by one octave —
            # but only if the shift keeps all notes within the voice range.
            if i == 0:
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

            soprano_notes.extend(sop_shifted)
            bass_notes.extend(bass_shifted)

        # Stamp creator on all notes.
        soprano_tuple: tuple[Note, ...] = tuple(replace(n, creator="episode") for n in soprano_notes)
        bass_tuple: tuple[Note, ...] = tuple(replace(n, creator="episode") for n in bass_notes)

        assert all(n.duration > 0 for n in soprano_tuple), (
            "Episode soprano contains a non-positive note duration. "
            "Check fragment extraction and IMITATION_BEAT_DELAY vs bar_length."
        )
        assert all(n.duration > 0 for n in bass_tuple), (
            "Episode bass contains a non-positive note duration. "
            "Check fragment extraction and IMITATION_BEAT_DELAY vs bar_length."
        )

        return soprano_tuple, bass_tuple

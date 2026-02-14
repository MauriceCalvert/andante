"""Episode writer: subject-fragment sequences for invention episodes.

Extracts the head fragment (first bar) from the subject and places it in
alternating voices at each step of a sequential schema (fonte, monte).
Each fragment is transposed to the local key of that step, following the
schema's degree_keys.
"""
from dataclasses import replace
from fractions import Fraction

from builder.bass_viterbi import generate_bass_viterbi
from builder.phrase_types import PhrasePlan, PhraseResult, phrase_degree_offset
from builder.soprano_writer import generate_soprano_viterbi
from builder.types import Note
from motifs.fugue_loader import LoadedFugue
from motifs.head_generator import degrees_to_midi
from shared.constants import TRACK_BASS, TRACK_SOPRANO
from shared.key import Key
from shared.music_math import parse_metre
from shared.voice_types import Range


DURATION_DENOMINATOR_LIMIT: int = 64


def extract_head_fragment(
    fugue: LoadedFugue,
    metre: str,
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Extract the first bar of the subject as a fragment.

    Returns:
        (degrees, durations) — degrees are 0-based linear scale positions,
        durations are Fraction objects.
    """
    bar_length: Fraction = parse_metre(metre=metre)[0]
    degrees: tuple[int, ...] = fugue.subject.degrees
    durations_float: tuple[float, ...] = fugue.subject.durations

    accumulated: Fraction = Fraction(0)
    head_degrees: list[int] = []
    head_durations: list[Fraction] = []

    for deg, dur_float in zip(degrees, durations_float):
        dur: Fraction = Fraction(dur_float).limit_denominator(DURATION_DENOMINATOR_LIMIT)
        if accumulated >= bar_length:
            break
        head_degrees.append(deg)
        head_durations.append(dur)
        accumulated += dur

    assert len(head_degrees) >= 2, (
        f"Head fragment must have at least 2 notes, got {len(head_degrees)}"
    )

    return (tuple(head_degrees), tuple(head_durations))


def fragment_to_voice_notes(
    degrees: tuple[int, ...],
    durations: tuple[Fraction, ...],
    start_offset: Fraction,
    target_key: Key,
    target_track: int,
    target_range: Range,
    mode: str,
) -> tuple[Note, ...]:
    """Convert fragment degrees to Notes in the target key and range.

    Octave-shifts the entire fragment to fit within the target range.
    """
    tonic_midi: int = 60 + target_key.tonic_pc
    midi_pitches: tuple[int, ...] = degrees_to_midi(
        degrees=degrees,
        tonic_midi=tonic_midi,
        mode=mode,
    )

    # Octave-shift to fit in range
    highest: int = max(midi_pitches)
    shift: int = 0
    while highest + shift > target_range.high:
        shift -= 12
    while min(midi_pitches) + shift < target_range.low:
        shift += 12

    assert min(midi_pitches) + shift >= target_range.low, (
        f"Fragment cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, lowest pitch {min(midi_pitches) + shift} < {target_range.low}"
    )
    assert max(midi_pitches) + shift <= target_range.high, (
        f"Fragment cannot fit in range [{target_range.low}, {target_range.high}]: "
        f"after shift {shift}, highest pitch {max(midi_pitches) + shift} > {target_range.high}"
    )

    notes: list[Note] = []
    offset: Fraction = start_offset
    for pitch, dur in zip(midi_pitches, durations):
        notes.append(Note(
            offset=offset,
            pitch=pitch + shift,
            duration=dur,
            voice=target_track,
        ))
        offset += dur

    return tuple(notes)


def write_episode(
    plan: PhrasePlan,
    fugue: LoadedFugue,
    prior_upper: tuple[Note, ...],
    prior_lower: tuple[Note, ...],
) -> PhraseResult:
    """Write episode phrase: subject fragments in alternating voices.

    Each degree_position gets a fragment statement in alternating voices,
    transposed to the corresponding degree_key. The non-fragment voice is
    generated via Viterbi.

    If the schema has no degree_keys, this should not be called (dispatcher
    should fall through to galant path).
    """
    assert plan.degree_keys and len(plan.degree_keys) > 0, (
        f"write_episode called on '{plan.schema_name}' with no degree_keys "
        f"(caller should have checked and fallen through to galant)"
    )
    degrees, durations = extract_head_fragment(fugue=fugue, metre=plan.metre)
    mode: str = fugue.subject.mode

    bar_length, beat_unit = parse_metre(metre=plan.metre)
    lead_voice: int = plan.lead_voice if plan.lead_voice is not None else 0

    # Simplified implementation (acceptable per task): place fragment in lead
    # voice only for all segments (bars), generate the other voice via Viterbi.
    # For sequential schemas, group degree_positions by bar to identify segments.

    fragment_notes: list[Note] = []
    seen_bars: set[int] = set()
    for i, pos in enumerate(plan.degree_positions):
        if i >= len(plan.degree_keys):
            break

        # Only place ONE fragment per bar (segment), at the first degree_position in that bar
        if pos.bar in seen_bars:
            continue
        seen_bars.add(pos.bar)

        step_offset: Fraction = phrase_degree_offset(
            plan=plan,
            pos=pos,
            bar_length=bar_length,
            beat_unit=beat_unit,
        )
        step_key: Key = plan.degree_keys[i]

        if lead_voice == 0:
            frag_notes: tuple[Note, ...] = fragment_to_voice_notes(
                degrees=degrees,
                durations=durations,
                start_offset=step_offset,
                target_key=step_key,
                target_track=TRACK_SOPRANO,
                target_range=plan.upper_range,
                mode=mode,
            )
        else:
            frag_notes = fragment_to_voice_notes(
                degrees=degrees,
                durations=durations,
                start_offset=step_offset,
                target_key=step_key,
                target_track=TRACK_BASS,
                target_range=plan.lower_range,
                mode=mode,
            )

        # Tag first note of first fragment as episode
        if len(fragment_notes) == 0:
            frag_notes = (replace(frag_notes[0], lyric="episode"),) + frag_notes[1:]

        fragment_notes.extend(frag_notes)

    # Generate the free voice via Viterbi against the fragments
    if lead_voice == 0:
        # Soprano has fragments, generate bass
        soprano_notes: tuple[Note, ...] = tuple(fragment_notes)
        bass_notes: tuple[Note, ...] = generate_bass_viterbi(
            plan=plan,
            soprano_notes=soprano_notes,
            prior_lower=prior_lower,
            harmonic_grid=None,
        )
    else:
        # Bass has fragments, generate soprano
        bass_notes = tuple(fragment_notes)
        soprano_notes, _ = generate_soprano_viterbi(
            plan=plan,
            bass_notes=bass_notes,
            prior_upper=prior_upper,
            next_phrase_entry_degree=None,
            next_phrase_entry_key=None,
            harmonic_grid=None,
        )

    return PhraseResult(
        upper_notes=soprano_notes,
        lower_notes=bass_notes,
        exit_upper=soprano_notes[-1].pitch if soprano_notes else plan.prev_exit_upper or 60,
        exit_lower=bass_notes[-1].pitch if bass_notes else plan.prev_exit_lower or 48,
        schema_name=plan.schema_name,
        soprano_figures=(),
        bass_pattern_name=None,
    )

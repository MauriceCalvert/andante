"""Soprano phrase generation and validation."""
import logging
from fractions import Fraction

from builder.phrase_types import PhrasePlan, phrase_degree_offset
from builder.strategies.diminution import DiminutionFill
from builder.types import Note
from builder.voice_types import DiminutionMetadata, StructuralTone, VoiceConfig, WriteResult
from builder.voice_writer import write_voice
from shared.constants import MIN_SOPRANO_MIDI, TRACK_SOPRANO, TRACK_BASS
from shared.key import Key
from shared.music_math import parse_metre
from shared.pitch import degree_to_nearest_midi

logger = logging.getLogger(__name__)


def _place_structural_tones(
    plan: PhrasePlan,
    prev_exit_midi: int | None,
) -> list[tuple[Fraction, int, Key]]:
    """Place structural tones with octave selection and floor clamp.

    Returns list of (offset, midi, key) triples.
    """
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    structural_tones: list[tuple[Fraction, int, Key]] = []
    biased_upper_median: int = plan.upper_median + plan.registral_bias
    prev_midi: int = (
        prev_exit_midi if prev_exit_midi is not None
        else biased_upper_median
    )
    actual_prev: int | None = prev_exit_midi
    prev_prev: int | None = None
    for i, degree in enumerate(plan.degrees_upper):
        pos = plan.degree_positions[i]
        offset: Fraction = phrase_degree_offset(
            plan=plan, pos=pos, bar_length=bar_length, beat_unit=beat_unit,
        )
        key_for_degree: Key = plan.degree_keys[i]
        midi: int = degree_to_nearest_midi(
            degree=degree,
            key=key_for_degree,
            target_midi=prev_midi,
            midi_range=(plan.upper_range.low, plan.upper_range.high),
            prev_midi=actual_prev,
            prev_prev_midi=prev_prev,
        )
        # Soprano floor clamp: preserve degree, shift up by octave
        if midi < MIN_SOPRANO_MIDI:
            midi += 12
        structural_tones.append((offset, midi, key_for_degree))
        prev_prev = actual_prev
        actual_prev = midi
        prev_midi = midi
    return structural_tones


def generate_soprano_phrase(
    plan: PhrasePlan,
    prior_upper: tuple[Note, ...] = (),
    lower_notes: tuple[Note, ...] = (),
    next_phrase_entry_degree: int | None = None,
    next_phrase_entry_key: Key | None = None,
    recall_figure_name: str | None = None,
) -> tuple[tuple[Note, ...], tuple[str, ...]]:
    """Generate soprano notes for one phrase.

    Returns (notes, figure_names) where figure_names lists the figuration
    patterns used for each span between structural tones.
    """
    assert not plan.is_cadential, (
        f"generate_soprano_phrase called with cadential plan '{plan.schema_name}'; "
        f"use write_phrase() which delegates to write_cadence()"
    )

    # Step 1: Place structural tones
    prev_exit_midi: int | None = prior_upper[-1].pitch if prior_upper else None
    structural_tones: list[tuple[Fraction, int, Key]] = _place_structural_tones(
        plan=plan, prev_exit_midi=prev_exit_midi,
    )

    # Step 2: Compute phrase exit target
    next_entry_midi: int | None = None
    if (
        next_phrase_entry_degree is not None
        and next_phrase_entry_key is not None
        and len(structural_tones) > 0
    ):
        next_entry_midi = degree_to_nearest_midi(
            degree=next_phrase_entry_degree,
            key=next_phrase_entry_key,
            target_midi=structural_tones[-1][1],
            midi_range=(plan.upper_range.low, plan.upper_range.high),
        )

    # Convert structural tones to StructuralTone objects
    structural_tone_objects: tuple[StructuralTone, ...] = tuple(
        StructuralTone(offset=st[0], midi=st[1], key=st[2])
        for st in structural_tones
    )

    # Build VoiceConfig
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    voice_config: VoiceConfig = VoiceConfig(
        voice_id=TRACK_SOPRANO,
        range_low=plan.upper_range.low,
        range_high=plan.upper_range.high,
        key=plan.local_key,
        metre=plan.metre,
        bar_length=bar_length,
        beat_unit=beat_unit,
        phrase_start=plan.start_offset,
        genre=plan.rhythm_profile,
        character=plan.character,
        is_minor=plan.degree_keys[0].mode == "minor",
        guard_tolerance=frozenset(),
        cadence_type=plan.cadence_type,
    )

    # Build other_voices dict
    other_voices: dict[int, tuple[Note, ...]] = {}
    if lower_notes:
        other_voices[TRACK_BASS] = lower_notes

    # Build strategy
    strategy: DiminutionFill = DiminutionFill(
        character=plan.character,
        recall_figure_name=recall_figure_name,
    )

    # Prior phrase tail for boundary checking
    prior_phrase_tail: Note | None = prior_upper[-1] if prior_upper else None

    # Call write_voice
    result: WriteResult = write_voice(
        structural_tones=structural_tone_objects,
        phrase_start=plan.start_offset,
        phrase_duration=plan.phrase_duration,
        fill_strategy=strategy,
        other_voices=other_voices,
        config=voice_config,
        next_entry_midi=next_entry_midi,
        prior_phrase_tail=prior_phrase_tail,
        strict_audit=False,
    )

    # Log any audit violations
    for violation in result.audit_violations:
        logger.warning("soprano audit: %s at offset %s", violation.detail, violation.offset)

    # Extract figure names from span metadata
    figure_names: list[str] = [
        m.figure_name
        for m in result.span_metadata
        if isinstance(m, DiminutionMetadata)
    ]

    return result.notes, tuple(figure_names)

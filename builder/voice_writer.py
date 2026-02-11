"""Voice writer pipeline.

Public functions:
- validate_voice: Hard invariant assertions (range, durations, gaps, total duration, melodic intervals)
- audit_voice: Counterpoint detection pass (parallels, cross-relations, voice crossing, etc.)
- write_voice: Pipeline connecting callers → strategies → validation → audit
"""
from fractions import Fraction

from builder.types import Note
from builder.voice_types import (
    AuditViolation,
    FillStrategy,
    SpanBoundary,
    StructuralTone,
    VoiceConfig,
    VoiceContext,
    WriteResult,
)
from shared.constants import MAX_MELODIC_INTERVAL, VALID_DURATIONS_SET
from shared.counterpoint import (
    has_consecutive_leaps,
    has_cross_relation,
    has_parallel_perfect,
    is_cross_bar_repetition,
    is_ugly_melodic_interval,
    needs_step_recovery,
    would_cross_voice,
)


def audit_voice(
    notes: tuple[Note, ...],
    other_voices: dict[int, tuple[Note, ...]],
    structural_offsets: frozenset[Fraction],
    config: VoiceConfig,
    prior_phrase_tail: Note | None = None,
    strict: bool = True,
) -> list[AuditViolation]:
    """Detect counterpoint and melodic faults.

    Checks using shared counterpoint functions:
    - Parallel perfect intervals at common onsets
    - Cross-relations within beat window
    - Voice crossing
    - Ugly melodic intervals
    - Cross-bar pitch repetition (non-structural)
    - Leap-step recovery (except structural-to-structural)
    - Consecutive same-direction leaps
    - Phrase boundary continuity (if prior_phrase_tail provided)

    If strict=True: raises AssertionError on first violation.
    If strict=False: collects all violations and returns them.
    Returns empty list if no violations found.
    """
    violations: list[AuditViolation] = []

    # Check phrase boundary continuity if prior_phrase_tail provided
    if prior_phrase_tail is not None and len(notes) > 0:
        first_note: Note = notes[0]
        # Ugly melodic interval at phrase boundary
        if is_ugly_melodic_interval(prior_phrase_tail.pitch, first_note.pitch):
            detail: str = f"ugly interval from phrase tail {prior_phrase_tail.pitch} to {first_note.pitch}"
            if strict:
                assert False, detail
            violations.append(AuditViolation(
                rule="ugly_melodic_interval",
                offset=first_note.offset,
                pitch=first_note.pitch,
                detail=detail,
            ))
        # Cross-bar repetition at phrase boundary
        if is_cross_bar_repetition(
            pitch=first_note.pitch,
            offset=first_note.offset,
            previous_note=prior_phrase_tail,
            bar_length=config.bar_length,
            phrase_start=config.phrase_start,
            structural_offsets=structural_offsets,
        ):
            detail = f"cross-bar repetition at phrase boundary: {first_note.pitch}"
            if strict:
                assert False, detail
            violations.append(AuditViolation(
                rule="cross_bar_repetition",
                offset=first_note.offset,
                pitch=first_note.pitch,
                detail=detail,
            ))

    # Check consecutive notes
    for i, note in enumerate(notes):
        # Ugly melodic interval
        if i > 0:
            prev_note: Note = notes[i - 1]
            if is_ugly_melodic_interval(prev_note.pitch, note.pitch):
                detail = f"ugly interval from {prev_note.pitch} to {note.pitch}"
                if strict:
                    assert False, detail
                violations.append(AuditViolation(
                    rule="ugly_melodic_interval",
                    offset=note.offset,
                    pitch=note.pitch,
                    detail=detail,
                ))

        # Cross-bar repetition
        if i > 0:
            prev_note = notes[i - 1]
            if is_cross_bar_repetition(
                pitch=note.pitch,
                offset=note.offset,
                previous_note=prev_note,
                bar_length=config.bar_length,
                phrase_start=config.phrase_start,
                structural_offsets=structural_offsets,
            ):
                detail = f"cross-bar repetition: {note.pitch}"
                if strict:
                    assert False, detail
                violations.append(AuditViolation(
                    rule="cross_bar_repetition",
                    offset=note.offset,
                    pitch=note.pitch,
                    detail=detail,
                ))

        # Leap-step recovery
        if needs_step_recovery(
            previous_notes=notes[:i],
            candidate_pitch=note.pitch,
            structural_offsets=structural_offsets,
        ):
            detail = f"needs step recovery at {note.pitch}"
            if strict:
                assert False, detail
            violations.append(AuditViolation(
                rule="needs_step_recovery",
                offset=note.offset,
                pitch=note.pitch,
                detail=detail,
            ))

        # Consecutive leaps
        if i >= 2:
            prev_prev_note: Note = notes[i - 2]
            prev_note = notes[i - 1]
            if has_consecutive_leaps(
                prev_prev_pitch=prev_prev_note.pitch,
                prev_pitch=prev_note.pitch,
                candidate_pitch=note.pitch,
            ):
                detail = f"consecutive leaps: {prev_prev_note.pitch} -> {prev_note.pitch} -> {note.pitch}"
                if strict:
                    assert False, detail
                violations.append(AuditViolation(
                    rule="consecutive_leaps",
                    offset=note.offset,
                    pitch=note.pitch,
                    detail=detail,
                ))

        # Parallel perfect intervals at common onsets
        for other_voice_id, other_voice_notes in other_voices.items():
            own_previous_note: Note | None = notes[i - 1] if i > 0 else prior_phrase_tail
            if has_parallel_perfect(
                pitch=note.pitch,
                offset=note.offset,
                other_voice_notes=other_voice_notes,
                own_previous_note=own_previous_note,
                tolerance=config.guard_tolerance,
            ):
                detail = f"parallel perfect interval with voice {other_voice_id} at {note.pitch}"
                if strict:
                    assert False, detail
                violations.append(AuditViolation(
                    rule="parallel_perfect",
                    offset=note.offset,
                    pitch=note.pitch,
                    detail=detail,
                ))

        # Cross-relations
        for other_voice_notes in other_voices.values():
            if has_cross_relation(
                pitch=note.pitch,
                other_notes=other_voice_notes,
                offset=note.offset,
                beat_unit=config.beat_unit,
            ):
                detail = f"cross-relation at {note.pitch}"
                if strict:
                    assert False, detail
                violations.append(AuditViolation(
                    rule="cross_relation",
                    offset=note.offset,
                    pitch=note.pitch,
                    detail=detail,
                ))

        # Voice crossing
        for other_voice_id, other_voice_notes in other_voices.items():
            for other_note in other_voice_notes:
                if other_note.offset == note.offset:
                    if would_cross_voice(
                        pitch=note.pitch,
                        other_voice_pitch=other_note.pitch,
                        voice_id=config.voice_id,
                        other_voice_id=other_voice_id,
                    ):
                        detail = f"voice crossing with voice {other_voice_id}: {note.pitch} vs {other_note.pitch}"
                        if strict:
                            assert False, detail
                        violations.append(AuditViolation(
                            rule="voice_crossing",
                            offset=note.offset,
                            pitch=note.pitch,
                            detail=detail,
                        ))

    return violations


def validate_voice(
    notes: tuple[Note, ...],
    config: VoiceConfig,
    phrase_start: Fraction,
    phrase_duration: Fraction,
) -> None:
    """Assert structural invariants. Raises AssertionError on failure.

    Checks:
    - All pitches in [config.range_low, config.range_high]
    - All durations in VALID_DURATIONS_SET
    - No gaps or overlaps between consecutive notes
    - Total duration == phrase_duration
    - No melodic intervals exceeding MAX_MELODIC_INTERVAL
    """
    assert len(notes) > 0, "notes must not be empty"

    # Check range
    for note in notes:
        assert config.range_low <= note.pitch <= config.range_high, \
            f"pitch {note.pitch} outside range [{config.range_low}, {config.range_high}]"

    # Check durations
    for note in notes:
        assert note.duration in VALID_DURATIONS_SET, \
            f"duration {note.duration} not in VALID_DURATIONS_SET"

    # Check gaps and overlaps
    for i in range(len(notes) - 1):
        current_end: Fraction = notes[i].offset + notes[i].duration
        next_start: Fraction = notes[i + 1].offset
        assert current_end == next_start, \
            f"gap or overlap between notes at {notes[i].offset} and {notes[i + 1].offset}"

    # Check total duration
    first_offset: Fraction = notes[0].offset
    last_offset: Fraction = notes[-1].offset
    last_duration: Fraction = notes[-1].duration
    assert first_offset == phrase_start, \
        f"first note offset {first_offset} != phrase_start {phrase_start}"
    assert last_offset + last_duration == phrase_start + phrase_duration, \
        f"total duration mismatch: expected {phrase_start + phrase_duration}, got {last_offset + last_duration}"

    # Check max melodic interval
    for i in range(len(notes) - 1):
        interval: int = abs(notes[i + 1].pitch - notes[i].pitch)
        assert interval <= MAX_MELODIC_INTERVAL, \
            f"melodic interval {interval} exceeds MAX_MELODIC_INTERVAL {MAX_MELODIC_INTERVAL}"


def write_voice(
    structural_tones: tuple[StructuralTone, ...],
    phrase_start: Fraction,
    phrase_duration: Fraction,
    fill_strategy: FillStrategy,
    other_voices: dict[int, tuple[Note, ...]],
    config: VoiceConfig,
    next_entry_midi: int | None = None,
    prior_phrase_tail: Note | None = None,
    strict_audit: bool = True,
) -> WriteResult:
    """Generate a complete voice for one phrase.

    Steps:
    1. Compute structural_offsets from structural_tones
    2. Build SpanBoundary for each pair of adjacent structural tones
    3. For each span:
       a. Build VoiceContext (immutable, rebuilt each iteration)
       b. Call fill_strategy.fill_span(span, config, context)
       c. Accumulate notes for next iteration
    4. Concatenate all span notes
    5. validate_voice (hard invariants)
    6. audit_voice (counterpoint and melodic style rules)
    7. Return WriteResult
    """
    # Step 1: Compute structural offsets
    structural_offsets: frozenset[Fraction] = frozenset(t.offset for t in structural_tones)

    # Step 2: Build spans
    total_bars: int = int(phrase_duration / config.bar_length)
    spans: list[SpanBoundary] = []
    for i in range(len(structural_tones)):
        start_tone: StructuralTone = structural_tones[i]
        start_offset: Fraction = start_tone.offset
        start_midi: int = start_tone.midi
        start_key = start_tone.key
        if i < len(structural_tones) - 1:
            end_tone: StructuralTone = structural_tones[i + 1]
            end_offset = end_tone.offset
            end_midi: int | None = end_tone.midi
            end_key = end_tone.key
            is_final: bool = False
        else:
            end_offset = phrase_start + phrase_duration
            end_midi = next_entry_midi
            end_key = None
            is_final = True
        phrase_bar: int = int((start_offset - phrase_start) / config.bar_length) + 1
        spans.append(SpanBoundary(
            start_offset=start_offset,
            start_midi=start_midi,
            start_key=start_key,
            end_offset=end_offset,
            end_midi=end_midi,
            end_key=end_key,
            phrase_bar=phrase_bar,
            total_bars=total_bars,
            is_final_span=is_final,
        ))

    # Step 3: Fill spans
    accumulated_notes: list[Note] = []
    accumulated_metadata: list = []
    for span in spans:
        context: VoiceContext = VoiceContext(
            other_voices=other_voices,
            own_prior_notes=tuple(accumulated_notes),
            prior_phrase_tail=prior_phrase_tail,
            structural_offsets=structural_offsets,
        )
        result = fill_strategy.fill_span(span=span, config=config, context=context)
        accumulated_notes.extend(result.notes)
        accumulated_metadata.append(result.metadata)

    # Step 4: Concatenate
    final_notes: tuple[Note, ...] = tuple(accumulated_notes)

    # Step 5: Validate
    validate_voice(
        notes=final_notes,
        config=config,
        phrase_start=phrase_start,
        phrase_duration=phrase_duration,
    )

    # Step 6: Audit
    violations: list[AuditViolation] = audit_voice(
        notes=final_notes,
        other_voices=other_voices,
        structural_offsets=structural_offsets,
        config=config,
        prior_phrase_tail=prior_phrase_tail,
        strict=strict_audit,
    )

    # Step 7: Return
    return WriteResult(
        notes=final_notes,
        span_metadata=tuple(accumulated_metadata),
        structural_offsets=structural_offsets,
        audit_violations=tuple(violations),
    )

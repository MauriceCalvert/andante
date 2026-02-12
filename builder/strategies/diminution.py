"""Diminution fill strategy for soprano voice.

Wraps existing soprano figuration pipeline with counterpoint-aware checking.
Tries figures in preference order, falls back to stepwise motion if needed.
"""
from fractions import Fraction

from builder.figuration.loader import (
    get_diminutions,
    get_rhythm_templates,
    select_rhythm_template,
)
from builder.figuration.rhythm_calc import compute_rhythmic_distribution
from builder.figuration.selection import classify_interval, select_figure
from builder.figuration.soprano import character_to_density, realise_pitches
from builder.types import Note
from builder.voice_types import (
    DiminutionMetadata,
    SpanBoundary,
    SpanResult,
    VoiceConfig,
    VoiceContext,
)
from shared.constants import TRACK_SOPRANO, VALID_DURATIONS_SET
from shared.counterpoint import (
    has_consecutive_leaps,
    has_cross_relation,
    has_parallel_perfect,
    is_cross_bar_repetition,
    is_ugly_melodic_interval,
    needs_step_recovery,
    would_cross_voice,
)
from shared.pitch_selection import select_best_pitch


class DiminutionFill:
    """Soprano fill strategy using baroque diminution figures."""

    def __init__(
        self,
        character: str,
        recall_figure_name: str | None = None,
    ) -> None:
        """Initialize diminution strategy.

        Args:
            character: Figure character ("plain", "expressive", etc.)
            recall_figure_name: Optional figure name to prefer on first span
        """
        self.character: str = character
        self.recall_figure_name: str | None = recall_figure_name
        self.prev_figure_name: str | None = None
        self._first_span_done: bool = False

    def fill_span(
        self,
        span: SpanBoundary,
        config: VoiceConfig,
        context: VoiceContext,
    ) -> SpanResult:
        """Fill one span between structural tones with diminution figures.

        Steps:
        1. Compute span parameters (gap, density, rhythm)
        2. Try preferred figure with counterpoint checking
        3. Try alternative figures if preferred rejected
        4. Stepwise fallback if all figures rejected
        5. Build result with metadata

        Args:
            span: Boundary pitches and offsets for this span
            config: Voice configuration (range, key, metre, etc.)
            context: Other voices and prior notes for checking

        Returns:
            SpanResult with notes and metadata
        """
        # Step 1: Compute span parameters
        gap: Fraction = span.end_offset - span.start_offset
        assert gap > 0, f"Gap must be positive, got {gap}"

        end_midi: int = (
            span.end_midi if span.end_midi is not None
            else span.start_midi
        )

        interval: str = classify_interval(
            from_midi=span.start_midi,
            to_midi=end_midi,
            key=span.start_key,
        )

        density: str = character_to_density(character=self.character)
        note_count: int
        unit_dur: Fraction
        note_count, unit_dur = compute_rhythmic_distribution(
            gap=gap,
            density=density,
        )

        # Try rhythm templates for full-bar gaps
        durations: tuple[Fraction, ...] | None = None
        if gap == config.bar_length and self.character != "plain":
            templates = get_rhythm_templates()
            template_key: tuple[int, str] = (note_count, config.metre)
            if template_key in templates:
                template_list = templates[template_key]
                position_str: str = "cadential" if span.is_final_span else "passing"
                template = select_rhythm_template(
                    templates=template_list,
                    character=self.character,
                    position=position_str,
                    bar_num=span.phrase_bar,
                )
                scaled: tuple[Fraction, ...] = tuple(
                    d * config.beat_unit for d in template.durations
                )
                if all(d in VALID_DURATIONS_SET for d in scaled):
                    durations = scaled

        # Fall back to equal subdivision
        if durations is None:
            count: int = int(gap / unit_dur) if unit_dur > 0 else note_count
            if count < 1:
                count = 1
            actual_dur: Fraction = gap / count
            durations = tuple(actual_dur for _ in range(count))

        actual_count: int = len(durations)
        position: str = "cadential" if span.is_final_span else "passing"

        # Determine recall for this span (only first span)
        span_recall: str | None = (
            self.recall_figure_name if not self._first_span_done else None
        )

        # Step 2: Try preferred figure
        figure = select_figure(
            interval=interval,
            note_count=actual_count,
            character=self.character,
            position=position,
            is_minor=config.is_minor,
            bar_num=span.phrase_bar,
            prev_figure_name=self.prev_figure_name,
            recall_figure_name=span_recall,
        )

        midi_range: tuple[int, int] = (config.range_low, config.range_high)
        pitches: list[int] = realise_pitches(
            figure=figure,
            note_count=actual_count,
            start_midi=span.start_midi,
            end_midi=end_midi,
            key=span.start_key,
            midi_range=midi_range,
        )

        # Check preferred figure against counterpoint
        figure_accepted: bool
        figure_accepted, notes_if_accepted = self._check_figure_pitches(
            pitches=pitches,
            durations=durations,
            span=span,
            config=config,
            context=context,
        )

        if figure_accepted:
            self.prev_figure_name = figure.name
            self._first_span_done = True
            return SpanResult(
                notes=notes_if_accepted,
                metadata=DiminutionMetadata(
                    strategy_name="diminution",
                    figure_name=figure.name,
                    used_stepwise_fallback=False,
                ),
            )

        # Step 3: Try alternative figures
        diminutions = get_diminutions()
        pool: list = diminutions[interval]

        # Filter to matching note count (exact or chainable)
        from builder.figuration.soprano import fit_degrees_to_count

        candidates = [
            f for f in pool
            if f.name != figure.name  # Exclude already-tried
        ]

        for alt_figure in candidates:
            alt_pitches: list[int] = realise_pitches(
                figure=alt_figure,
                note_count=actual_count,
                start_midi=span.start_midi,
                end_midi=end_midi,
                key=span.start_key,
                midi_range=midi_range,
            )

            alt_accepted: bool
            alt_accepted, alt_notes = self._check_figure_pitches(
                pitches=alt_pitches,
                durations=durations,
                span=span,
                config=config,
                context=context,
            )

            if alt_accepted:
                self.prev_figure_name = alt_figure.name
                self._first_span_done = True
                return SpanResult(
                    notes=alt_notes,
                    metadata=DiminutionMetadata(
                        strategy_name="diminution",
                        figure_name=alt_figure.name,
                        used_stepwise_fallback=False,
                    ),
                )

        # Step 4: Stepwise fallback
        fallback_notes: tuple[Note, ...] = self._stepwise_fallback(
            span=span,
            config=config,
            context=context,
            durations=durations,
            end_midi=end_midi,
        )

        self.prev_figure_name = figure.name  # Keep original for continuity
        self._first_span_done = True

        # Step 5: Build result
        return SpanResult(
            notes=fallback_notes,
            metadata=DiminutionMetadata(
                strategy_name="diminution",
                figure_name=f"{figure.name}_stepwise",
                used_stepwise_fallback=True,
            ),
        )

    def _check_figure_pitches(
        self,
        pitches: list[int],
        durations: tuple[Fraction, ...],
        span: SpanBoundary,
        config: VoiceConfig,
        context: VoiceContext,
    ) -> tuple[bool, tuple[Note, ...]]:
        """Check figure pitches against counterpoint rules.

        Returns (accepted, notes) where accepted is True if all checks pass.
        If rejected, notes is empty tuple.
        """
        assert len(pitches) == len(durations), (
            f"Pitch count {len(pitches)} != duration count {len(durations)}"
        )

        # Build notes as we check
        notes_so_far: list[Note] = []
        offset: Fraction = span.start_offset

        for i, (pitch, dur) in enumerate(zip(pitches, durations)):
            # First pitch is structural tone - no checking
            if i == 0:
                notes_so_far.append(Note(
                    offset=offset,
                    pitch=pitch,
                    duration=dur,
                    voice=config.voice_id,
                ))
                offset += dur
                continue

            # Build temporary note for checking
            temp_note = Note(
                offset=offset,
                pitch=pitch,
                duration=dur,
                voice=config.voice_id,
            )

            # Accumulate own_previous from context + notes so far
            own_previous: tuple[Note, ...] = context.own_prior_notes + tuple(notes_so_far)

            # Check parallel perfects against each other voice
            for other_voice_id, other_voice_notes in context.other_voices.items():
                if has_parallel_perfect(
                    pitch=pitch,
                    offset=offset,
                    other_voice_notes=other_voice_notes,
                    own_previous_note=own_previous[-1] if own_previous else context.prior_phrase_tail,
                    tolerance=config.guard_tolerance,
                ):
                    return False, ()

            # Check cross-relations against each other voice
            for other_voice_notes in context.other_voices.values():
                if has_cross_relation(
                    pitch=pitch,
                    other_notes=other_voice_notes,
                    offset=offset,
                    beat_unit=config.beat_unit,
                ):
                    return False, ()

            # Check ugly melodic interval against previous pitch
            if own_previous or context.prior_phrase_tail:
                prev_pitch: int = (
                    own_previous[-1].pitch if own_previous
                    else context.prior_phrase_tail.pitch if context.prior_phrase_tail
                    else pitch
                )
                if is_ugly_melodic_interval(
                    from_pitch=prev_pitch,
                    to_pitch=pitch,
                ):
                    return False, ()

            # Check voice crossing at common onsets
            for other_voice_id, other_voice_notes in context.other_voices.items():
                for other_note in other_voice_notes:
                    if other_note.offset == offset:
                        if would_cross_voice(
                            pitch=pitch,
                            other_voice_pitch=other_note.pitch,
                            voice_id=config.voice_id,
                            other_voice_id=other_voice_id,
                        ):
                            return False, ()

            # Check cross-bar repetition (D007)
            # Determine previous note for cross-bar check
            prev_note_for_xbar: Note | None = (
                notes_so_far[-1] if notes_so_far
                else (own_previous[-1] if own_previous else context.prior_phrase_tail)
            )
            if prev_note_for_xbar is not None:
                if is_cross_bar_repetition(
                    pitch=pitch,
                    offset=offset,
                    previous_note=prev_note_for_xbar,
                    bar_length=config.bar_length,
                    phrase_start=config.phrase_start,
                    structural_offsets=context.structural_offsets,
                ):
                    return False, ()

            # Check leap-step recovery
            all_previous: tuple[Note, ...] = own_previous + tuple(notes_so_far)
            if needs_step_recovery(
                previous_notes=all_previous,
                candidate_pitch=pitch,
                structural_offsets=context.structural_offsets,
            ):
                return False, ()

            # Check consecutive leaps
            if len(notes_so_far) >= 1:
                prev_pitch_for_leaps: int = notes_so_far[-1].pitch
                prev_prev_pitch_for_leaps: int | None = (
                    notes_so_far[-2].pitch if len(notes_so_far) >= 2
                    else (own_previous[-1].pitch if own_previous else None)
                )
                if has_consecutive_leaps(
                    prev_prev_pitch=prev_prev_pitch_for_leaps,
                    prev_pitch=prev_pitch_for_leaps,
                    candidate_pitch=pitch,
                ):
                    return False, ()

            notes_so_far.append(temp_note)
            offset += dur

        return True, tuple(notes_so_far)

    def _stepwise_fallback(
        self,
        span: SpanBoundary,
        config: VoiceConfig,
        context: VoiceContext,
        durations: tuple[Fraction, ...],
        end_midi: int,
    ) -> tuple[Note, ...]:
        """Generate stepwise diatonic motion toward target.

        Always produces output - uses select_best_pitch when constrained.
        """
        notes: list[Note] = []
        offset: Fraction = span.start_offset
        current_pitch: int = span.start_midi

        for i, dur in enumerate(durations):
            if i == 0:
                # First note is always structural tone
                notes.append(Note(
                    offset=offset,
                    pitch=current_pitch,
                    duration=dur,
                    voice=config.voice_id,
                ))
                offset += dur
                continue

            # Generate candidate pitches - diatonic steps toward end_midi
            candidates: list[int] = []
            for step_dir in (-1, +1):
                candidate: int = span.start_key.diatonic_step(
                    midi=current_pitch,
                    steps=step_dir,
                )
                if config.range_low <= candidate <= config.range_high:
                    candidates.append(candidate)

            # Prefer direction toward end_midi
            if end_midi > current_pitch:
                candidates.sort(reverse=True)  # Higher first
            else:
                candidates.sort()  # Lower first

            if not candidates:
                # Degenerate case - stay put
                candidates.append(current_pitch)

            # Select best pitch using shared logic
            own_previous: tuple[Note, ...] = context.own_prior_notes + tuple(notes)
            best_pitch: int = select_best_pitch(
                candidates=tuple(candidates),
                offset=offset,
                config=config,
                context=context,
                own_previous=own_previous,
            )

            notes.append(Note(
                offset=offset,
                pitch=best_pitch,
                duration=dur,
                voice=config.voice_id,
            ))

            current_pitch = best_pitch
            offset += dur

        return tuple(notes)

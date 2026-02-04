"""Voice writer: produces notes for one voice from its VoicePlan.

One class, one instance per voice.  Receives all decisions from the
plan and executes them mechanically.  Makes zero compositional choices.

Supports section-by-section composition for lead-voice scheduling.
"""
import logging
from dataclasses import replace
from fractions import Fraction
from random import Random
from builder.arpeggiated_strategy import ArpeggiatedStrategy
from builder.cadential_strategy import CadentialStrategy
from builder.figuration_strategy import FigurationStrategy
from builder.junction import check_junction
from builder.pillar_strategy import PillarStrategy
from builder.staggered_strategy import StaggeredStrategy
from builder.types import FigureRejection, FigureRejectionError, Note
from builder.voice_checks import (
    check_direct_motion,
    check_melodic_interval,
    check_parallels,
    check_range,
    check_strong_beat_consonance,
    check_voice_overlap,
    format_interval,
)
from builder.writing_strategy import WritingStrategy
from shared.constants import GATE_FACTOR
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import (
    AnacrusisPlan,
    GapPlan,
    PlanAnchor,
    SectionPlan,
    VoicePlan,
    WritingMode,
)
from shared.voice_types import Range, Role

_log: logging.Logger = logging.getLogger(__name__)
_IMPLEMENTED_MODES: frozenset[WritingMode] = frozenset({
    WritingMode.PILLAR,
    WritingMode.FIGURATION,
    WritingMode.CADENTIAL,
    WritingMode.STAGGERED,
    WritingMode.ARPEGGIATED,
})
_IMPLEMENTED_SEQUENCING: frozenset[str] = frozenset({
    "independent",
    "repeating",
    "static",
})


_DISSONANT_ICS: frozenset[int] = frozenset({1, 2, 6, 10, 11})


def _is_consonant(midi: int, prior_pitches: list[int]) -> bool:
    """Check if midi is consonant with all prior pitches."""
    for p in prior_pitches:
        ic: int = abs(midi - p) % 12
        if ic in _DISSONANT_ICS:
            return False
    return True


def _ascending_hint_for_resolve(
    source_anchor: PlanAnchor,
    target_anchor: PlanAnchor,
    role: Role,
    gap_ascending: bool,
) -> bool | None:
    """Compute ascending hint for target resolution.

    Same degree: return None (nearest octave, no forced direction).
    Different degree: return gap_ascending to guide octave selection.
    """
    if role == Role.SCHEMA_UPPER:
        src_deg: int = source_anchor.upper_degree
        tgt_deg: int = target_anchor.upper_degree
    else:
        src_deg = source_anchor.lower_degree
        tgt_deg = target_anchor.lower_degree
    if src_deg == tgt_deg:
        return None
    return gap_ascending


class VoiceWriter:
    """Produce notes for one voice, section by section."""

    def __init__(
        self,
        plan: VoicePlan,
        home_key: Key,
        anchors: tuple[PlanAnchor, ...],
        prior_voices: dict[str, tuple[Note, ...]],
        upbeat: Fraction = Fraction(0),
    ) -> None:
        self._plan: VoicePlan = plan
        self._home_key: Key = home_key
        self._upbeat: Fraction = upbeat
        self._anchors: tuple[PlanAnchor, ...] = anchors
        self._prior_voices: dict[str, tuple[Note, ...]] = prior_voices
        self._rng: Random = Random(plan.seed)
        self._pillar: PillarStrategy = PillarStrategy()
        self._figuration: FigurationStrategy = FigurationStrategy()
        self._cadential: CadentialStrategy = CadentialStrategy()
        self._staggered: StaggeredStrategy = StaggeredStrategy(
            fill_strategy=self._figuration,
        )
        self._arpeggiated: ArpeggiatedStrategy | None = (
            ArpeggiatedStrategy(plan.bass_pattern)
            if plan.bass_pattern is not None
            else None
        )
        self._prev_figure_name: str = ""
        self._prev_leap_direction: int = 0
        self._prev_exit_pitch: DiatonicPitch | None = None
        self._prior_at_offset: dict[Fraction, list[int]] = _build_offset_index(
            prior_voices,
        )
        self._prev_prior_at_offset: dict[Fraction, list[int]] = {}
        self._current_voice_notes: list[Note] = []
        self._prev_candidate_midi: int | None = None
        self._prev_candidate_offset: Fraction | None = None
        self._anacrusis_composed: bool = False
        self._sections_composed: set[int] = set()

    def compose(self) -> tuple[Note, ...]:
        """Compose all sections and return sorted notes."""
        all_notes: list[Note] = []
        if self._plan.anacrusis is not None and not self._anacrusis_composed:
            anacrusis_notes: list[Note] = self._compose_anacrusis()
            all_notes.extend(anacrusis_notes)
            self._anacrusis_composed = True
        for section_idx in range(len(self._plan.sections)):
            if section_idx not in self._sections_composed:
                notes: list[Note] = self._compose_section(
                    self._plan.sections[section_idx],
                )
                all_notes.extend(notes)
                self._sections_composed.add(section_idx)
        all_notes.sort(key=lambda n: n.offset)
        return tuple(all_notes)

    def compose_section(self, section_idx: int) -> list[Note]:
        """Compose a single section by index.
        
        Called by compose_voices() for lead-voice scheduling.
        Handles anacrusis before first section if needed.
        """
        result: list[Note] = []
        if section_idx == 0:
            if self._plan.anacrusis is not None and not self._anacrusis_composed:
                result.extend(self._compose_anacrusis())
                self._anacrusis_composed = True
        if section_idx in self._sections_composed:
            return result
        section: SectionPlan = self._plan.sections[section_idx]
        section_notes: list[Note] = self._compose_section(section)
        result.extend(section_notes)
        self._sections_composed.add(section_idx)
        return result

    def update_prior_voices(
        self,
        prior_voices: dict[str, tuple[Note, ...]],
    ) -> None:
        """Update prior voices after other voice composed a section."""
        self._prior_voices = prior_voices
        self._prior_at_offset = _build_offset_index(prior_voices)

    # ── Section-level ─────────────────────────────────────

    def _compose_section(self, section: SectionPlan) -> list[Note]:
        """Compose one section."""
        if section.role == Role.IMITATIVE:
            return self._compose_imitative_section(section)
        assert section.role in (Role.SCHEMA_UPPER, Role.SCHEMA_LOWER), (
            f"Role {section.role.name} not yet implemented"
        )
        assert section.sequencing in _IMPLEMENTED_SEQUENCING, (
            f"Sequencing '{section.sequencing}' not yet implemented"
        )
        self._prev_figure_name = ""
        self._prev_leap_direction = 0
        self._prev_exit_pitch = None
        if section.sequencing == "independent":
            return self._compose_independent(section)
        return self._compose_sequenced(section)

    def _compose_independent(self, section: SectionPlan) -> list[Note]:
        """Compose section with independent gap selection."""
        result: list[Note] = []
        prev_anchor_midi: int | None = self._prev_candidate_midi
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            if gap.bar_function == "final":
                final_anchor: PlanAnchor = self._anchors[-1]
                source_pitch: DiatonicPitch = self._resolve_anchor_pitch(
                    final_anchor, section.role, prev_anchor_midi,
                )
                target_pitch: DiatonicPitch = source_pitch
                source_anchor: PlanAnchor = final_anchor
            else:
                source_anchor = self._anchors[anchor_idx]
                target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
                source_pitch = self._resolve_anchor_pitch(
                    source_anchor, section.role, prev_anchor_midi,
                )
                source_midi: int = self._home_key.diatonic_to_midi(source_pitch)
                if anchor_idx == 0 and self._anacrusis_composed:
                    prev_anchor_midi = source_midi
                    self._prev_exit_pitch = source_pitch
                    continue
                ascending_hint: bool | None = _ascending_hint_for_resolve(
                    source_anchor, target_anchor, section.role, gap.ascending,
                )
                target_pitch = self._resolve_anchor_pitch(
                    target_anchor, section.role, source_midi, ascending_hint,
                )
            gap_offset: Fraction = _bar_beat_to_offset(
                source_anchor.bar_beat, self._plan.metre, self._upbeat,
            )
            notes: list[Note] = self._compose_gap(
                gap, source_pitch, target_pitch, gap_offset,
            )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note: Note = notes[-1]
                prev_anchor_midi = last_note.pitch
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    last_note.pitch,
                )
                self._update_leap_direction(notes)
        return result

    def _compose_sequenced(self, section: SectionPlan) -> list[Note]:
        """Compose section with sequencing (repeating, static)."""
        result: list[Note] = []
        base_figure: tuple[tuple[DiatonicPitch, Fraction], ...] | None = None
        prev_anchor_midi: int | None = self._prev_candidate_midi
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            if gap.bar_function == "final":
                final_anchor: PlanAnchor = self._anchors[-1]
                source_pitch: DiatonicPitch = self._resolve_anchor_pitch(
                    final_anchor, section.role, prev_anchor_midi,
                )
                target_pitch: DiatonicPitch = source_pitch
                source_anchor: PlanAnchor = final_anchor
            else:
                source_anchor = self._anchors[anchor_idx]
                target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
                source_pitch = self._resolve_anchor_pitch(
                    source_anchor, section.role, prev_anchor_midi,
                )
                source_midi: int = self._home_key.diatonic_to_midi(source_pitch)
                if anchor_idx == 0 and self._anacrusis_composed:
                    prev_anchor_midi = source_midi
                    self._prev_exit_pitch = source_pitch
                    continue
                ascending_hint: bool | None = _ascending_hint_for_resolve(
                    source_anchor, target_anchor, section.role, gap.ascending,
                )
                target_pitch = self._resolve_anchor_pitch(
                    target_anchor, section.role, source_midi, ascending_hint,
                )
            gap_offset: Fraction = _bar_beat_to_offset(
                source_anchor.bar_beat, self._plan.metre, self._upbeat,
            )
            if gap_idx == 0 or base_figure is None:
                notes: list[Note] = self._compose_gap(
                    gap, source_pitch, target_pitch, gap_offset,
                )
                if notes and gap.writing_mode == WritingMode.FIGURATION:
                    base_figure = self._extract_relative_figure(
                        notes, source_pitch, gap_offset,
                    )
            else:
                notes = self._apply_sequenced_figure(
                    base_figure, source_pitch, gap, gap_offset,
                    section.sequencing,
                )
                if not notes:
                    notes = self._compose_gap(
                        gap, source_pitch, target_pitch, gap_offset,
                    )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note = notes[-1]
                prev_anchor_midi = last_note.pitch
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    last_note.pitch,
                )
                self._update_leap_direction(notes)
        return result

    def _compose_gap(
        self,
        gap: GapPlan,
        source_pitch: DiatonicPitch,
        target_pitch: DiatonicPitch,
        gap_offset: Fraction,
    ) -> list[Note]:
        """Fill one gap using the strategy selected by writing_mode.

        The candidate filter skips melodic-interval checking for the first
        note of the gap because it IS the anchor pitch — a harmonic
        requirement that must be honoured regardless of the approach interval.
        """
        delay: Fraction = self._compute_delay(gap)
        effective_gap: GapPlan = gap
        if delay > 0:
            effective_gap = replace(gap, gap_duration=gap.gap_duration - delay)
        strategy: WritingStrategy = self._strategy_for_mode(gap.writing_mode)
        if gap.writing_mode in (WritingMode.PILLAR, WritingMode.ARPEGGIATED):
            candidate_filter = lambda dp, offset, is_first: self._check_candidate(
                dp, gap_offset + delay + offset, check_melodic=False,
            )
        else:
            def candidate_filter(
                dp: DiatonicPitch, offset: Fraction, is_first: bool,
            ) -> str | None:
                if is_first:
                    # Anchor note is a harmonic obligation — skip checks but
                    # update state so subsequent notes measure motion from here,
                    # not from the previous gap's exit pitch.
                    midi: int = self._home_key.diatonic_to_midi(dp)
                    self._prev_candidate_midi = midi
                    self._prev_candidate_offset = gap_offset + delay + offset
                    return None
                return self._check_candidate(
                    dp, gap_offset + delay + offset,
                    check_melodic=False,
                    check_consonance=False,
                )
        pairs: tuple[tuple[DiatonicPitch, Fraction], ...] = strategy.fill_gap(
            gap=effective_gap,
            source_pitch=source_pitch,
            target_pitch=target_pitch,
            home_key=self._home_key,
            metre=self._plan.metre,
            rng=self._rng,
            candidate_filter=candidate_filter,
        )
        notes: list[Note] = []
        elapsed: Fraction = delay
        for dp, dur in pairs:
            note: Note = self._to_note(dp, gap_offset + elapsed, dur)
            notes.append(note)
            self._prev_candidate_midi = note.pitch
            self._prev_candidate_offset = note.offset
            elapsed += dur
        return notes

    def _compose_imitative_section(self, section: SectionPlan) -> list[Note]:
        """Compose section by imitating another voice."""
        assert section.follows is not None
        assert section.follow_interval is not None
        assert section.follow_delay is not None
        source_voice: str = section.follows
        assert source_voice in self._prior_voices, (
            f"Imitation source '{source_voice}' not in prior voices"
        )
        source_notes: tuple[Note, ...] = self._prior_voices[source_voice]
        interval: int = section.follow_interval
        delay: Fraction = section.follow_delay
        section_start: Fraction = self._get_section_start_offset(section)
        section_end: Fraction = self._get_section_end_offset(section)
        result: list[Note] = []
        is_first: bool = True
        for note in source_notes:
            if note.offset < section_start - delay:
                continue
            if note.offset >= section_end - delay:
                continue
            dp: DiatonicPitch = self._home_key.midi_to_diatonic(note.pitch)
            transposed: DiatonicPitch = dp.transpose(interval)
            new_offset: Fraction = note.offset + delay
            if self._check_candidate(transposed, new_offset, check_melodic=is_first) is None:
                new_note: Note = self._to_note(
                    transposed, new_offset, note.duration / GATE_FACTOR,
                )
                result.append(new_note)
                self._prev_candidate_midi = new_note.pitch
                self._prev_candidate_offset = new_note.offset
                is_first = False
        return result

    def _compose_anacrusis(self) -> list[Note]:
        """Compose anacrusis (upbeat) before first section."""
        ana: AnacrusisPlan | None = self._plan.anacrusis
        assert ana is not None
        note_count: int = ana.note_count
        assert note_count >= 1
        dur_each: Fraction = ana.duration / note_count
        start_offset: Fraction = Fraction(0)
        target_midi: int = self._place_degree_near_median(
            self._home_key, ana.target_degree, self._plan.actuator_range,
        )
        target_pitch: DiatonicPitch = self._home_key.midi_to_diatonic(target_midi)
        result: list[Note] = []
        for i in range(note_count):
            if ana.ascending:
                step_offset: int = i - note_count + 1
            else:
                step_offset = note_count - 1 - i
            pitch: DiatonicPitch = target_pitch.transpose(step_offset)
            offset: Fraction = start_offset + i * dur_each
            is_first: bool = i == 0
            if self._check_candidate(pitch, offset, check_melodic=is_first) is None:
                note: Note = self._to_note(pitch, offset, dur_each)
                result.append(note)
                self._prev_candidate_midi = note.pitch
                self._prev_candidate_offset = note.offset
        return result

    # ── Anchor resolution ─────────────────────────────────

    def _resolve_anchor_pitch(
        self,
        anchor: PlanAnchor,
        role: Role,
        prev_midi: int | None,
        ascending_hint: bool | None = None,
    ) -> DiatonicPitch:
        """Resolve anchor degree to DiatonicPitch using previous pitch context.

        First anchor: place degree near tessitura median.
        Subsequent: use direction hint relative to previous pitch.
        If anchor's direction is None, use ascending_hint from gap plan.

        After initial placement, checks consonance with prior voices at
        the anchor's offset.  If dissonant, tries alternative octaves.
        """
        if role == Role.SCHEMA_UPPER:
            degree: int = anchor.upper_degree
            direction: str | None = anchor.upper_direction
        elif role == Role.SCHEMA_LOWER:
            degree = anchor.lower_degree
            direction = anchor.lower_direction
        else:
            assert False, f"Unsupported role: {role.name}"
        if direction is None and ascending_hint is not None:
            direction = "up" if ascending_hint else "down"
        key: Key = anchor.local_key
        rng: Range = self._plan.actuator_range
        if prev_midi is None:
            midi: int = self._place_degree_near_median(key, degree, rng)
        else:
            midi = self._place_degree_with_direction(key, degree, prev_midi, direction, rng)
        midi = self._adjust_for_consonance(key, degree, midi, anchor.bar_beat, rng)
        return self._home_key.midi_to_diatonic(midi)

    def _adjust_for_consonance(
        self,
        key: Key,
        degree: int,
        preferred_midi: int,
        bar_beat: str,
        rng: Range,
    ) -> int:
        """Adjust octave if preferred placement is dissonant with prior voice.

        Generates all valid octave placements of the degree, checks each
        for consonance with prior voices at the anchor's offset, and
        picks the closest consonant one to the preferred placement.
        Falls back to preferred if no consonant alternative exists.
        """
        offset: Fraction = _bar_beat_to_offset(bar_beat, self._plan.metre, self._upbeat)
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        if not prior_pitches:
            return preferred_midi
        if _is_consonant(preferred_midi, prior_pitches):
            return preferred_midi
        base_pc: int = key.degree_to_midi(degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        consonant: list[int] = [
            m for m in candidates if _is_consonant(m, prior_pitches)
        ]
        if consonant:
            return min(consonant, key=lambda m: abs(m - preferred_midi))
        return preferred_midi

    def _place_degree_near_median(self, key: Key, degree: int, rng: Range) -> int:
        """Place degree as MIDI near tessitura median.

        Generates all valid octave placements of the degree within the
        actuator range, then picks the one closest to the median.
        Prefers placements within a safe margin to leave room for figuration.
        Never clamps to arbitrary MIDI values — that would corrupt the degree.
        """
        margin: int = 10
        safe_low: int = rng.low + margin
        safe_high: int = rng.high - margin
        median: int = self._plan.tessitura_median
        base_pc: int = key.degree_to_midi(degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        assert candidates, (
            f"No valid octave for degree {degree} in range {rng.low}-{rng.high}"
        )
        safe: list[int] = [m for m in candidates if safe_low <= m <= safe_high]
        if safe:
            return min(safe, key=lambda m: abs(m - median))
        return min(candidates, key=lambda m: abs(m - median))

    def _place_degree_with_direction(
        self,
        key: Key,
        degree: int,
        prev_midi: int,
        direction: str | None,
        rng: Range,
    ) -> int:
        """Place degree relative to previous pitch using direction hint.
        
        Leaves margin (10 semitones) from range edges to allow figuration.
        """
        margin: int = 10
        safe_low: int = rng.low + margin
        safe_high: int = rng.high - margin
        base_pc: int = key.degree_to_midi(degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        assert candidates, (
            f"No valid octave for degree {degree} in range {rng.low}-{rng.high}"
        )
        safe: list[int] = [m for m in candidates if safe_low <= m <= safe_high]
        if direction == "up":
            above: list[int] = [m for m in candidates if m > prev_midi]
            safe_above: list[int] = [m for m in above if m <= safe_high]
            if safe_above:
                return min(safe_above)
            if safe:
                return min(safe, key=lambda m: abs(m - prev_midi))
            return min(candidates, key=lambda m: abs(m - prev_midi))
        if direction == "down":
            below: list[int] = [m for m in candidates if m < prev_midi]
            safe_below: list[int] = [m for m in below if m >= safe_low]
            if safe_below:
                return max(safe_below)
            if safe:
                return min(safe, key=lambda m: abs(m - prev_midi))
            return min(candidates, key=lambda m: abs(m - prev_midi))
        if safe:
            return min(safe, key=lambda m: abs(m - prev_midi))
        return min(candidates, key=lambda m: abs(m - prev_midi))

    # ── Checking ──────────────────────────────────────────

    def _check_candidate(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
        check_melodic: bool = True,
        check_consonance: bool = True,
    ) -> str | None:
        """Return None if candidate passes, else rejection reason."""
        midi: int = self._home_key.diatonic_to_midi(pitch)
        rng: Range = self._plan.actuator_range
        if not check_range(midi, rng):
            return f"range({rng.low}-{rng.high})"
        if check_melodic and self._prev_candidate_midi is not None:
            if not check_melodic_interval(self._prev_candidate_midi, midi):
                interval: int = midi - self._prev_candidate_midi
                return f"melodic_interval({format_interval(interval)})"
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        if check_consonance:
            for prior_midi in prior_pitches:
                if not check_strong_beat_consonance(
                    midi, prior_midi, offset, self._plan.metre,
                ):
                    ic: int = abs(midi - prior_midi) % 12
                    return f"strong_beat_dissonance(ic={ic})"
        if not check_voice_overlap(
            midi, offset, self._prior_at_offset, self._prev_candidate_offset,
        ):
            return "voice_overlap"
        if self._prev_candidate_midi is not None and prior_pitches:
            prev_prior: list[int] = self._find_prev_prior_pitches(offset)
            for i, prior_midi in enumerate(prior_pitches):
                if i < len(prev_prior):
                    prev_prior_midi: int = prev_prior[i]
                    if not check_parallels(
                        self._prev_candidate_midi, prev_prior_midi,
                        midi, prior_midi,
                    ):
                        curr_ic: int = abs(midi - prior_midi) % 12
                        return f"parallel({format_interval(curr_ic)})"
                    if not check_direct_motion(
                        self._prev_candidate_midi, prev_prior_midi,
                        midi, prior_midi,
                    ):
                        curr_ic = abs(midi - prior_midi) % 12
                        return f"direct_motion_to({format_interval(curr_ic)})"
        return None

    def _find_prev_prior_pitches(self, current_offset: Fraction) -> list[int]:
        """Find prior voice pitches at the previous offset."""
        prev_offset: Fraction | None = None
        for off in sorted(self._prior_at_offset.keys()):
            if off < current_offset:
                prev_offset = off
            else:
                break
        if prev_offset is None:
            return []
        return self._prior_at_offset.get(prev_offset, [])

    # ── Conversion ────────────────────────────────────────

    def _to_note(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
        duration: Fraction,
    ) -> Note:
        """Convert DiatonicPitch + timing to a Note."""
        midi: int = self._home_key.diatonic_to_midi(pitch)
        gated_duration: Fraction = duration * GATE_FACTOR
        return Note(
            offset=offset,
            pitch=midi,
            duration=gated_duration,
            voice=self._plan.composition_order,
            lyric=self._prev_figure_name,
        )

    # ── Strategy dispatch ─────────────────────────────────

    def _strategy_for_mode(self, mode: WritingMode) -> WritingStrategy:
        """Return the strategy instance for a given writing mode."""
        assert mode in _IMPLEMENTED_MODES, (
            f"WritingMode.{mode.name} not yet implemented — "
            f"available: {', '.join(m.name for m in _IMPLEMENTED_MODES)}"
        )
        if mode == WritingMode.PILLAR:
            return self._pillar
        if mode == WritingMode.FIGURATION:
            return self._figuration
        if mode == WritingMode.CADENTIAL:
            return self._cadential
        if mode == WritingMode.STAGGERED:
            return self._staggered
        if mode == WritingMode.ARPEGGIATED:
            assert self._arpeggiated is not None, (
                "WritingMode.ARPEGGIATED requires bass_pattern in VoicePlan"
            )
            return self._arpeggiated
        assert False, f"Unreachable: {mode.name}"

    # ── Sequencing helpers ────────────────────────────────

    def _extract_relative_figure(
        self,
        notes: list[Note],
        source_pitch: DiatonicPitch,
        gap_offset: Fraction,
    ) -> tuple[tuple[DiatonicPitch, Fraction], ...]:
        """Extract relative pitch offsets from realized notes."""
        source_midi: int = self._home_key.diatonic_to_midi(source_pitch)
        result: list[tuple[DiatonicPitch, Fraction]] = []
        for note in notes:
            rel_offset: Fraction = note.offset - gap_offset
            dp: DiatonicPitch = self._home_key.midi_to_diatonic(note.pitch)
            interval: int = dp.step - source_pitch.step
            result.append((DiatonicPitch(step=interval), note.duration / GATE_FACTOR))
        return tuple(result)

    def _apply_sequenced_figure(
        self,
        base_figure: tuple[tuple[DiatonicPitch, Fraction], ...],
        source_pitch: DiatonicPitch,
        gap: GapPlan,
        gap_offset: Fraction,
        sequencing: str,
    ) -> list[Note]:
        """Apply base figure transposed to new source pitch."""
        notes: list[Note] = []
        elapsed: Fraction = Fraction(0)
        for i, (rel_dp, dur) in enumerate(base_figure):
            pitch: DiatonicPitch = source_pitch.transpose(rel_dp.step)
            abs_offset: Fraction = gap_offset + elapsed
            is_first: bool = i == 0
            if self._check_candidate(pitch, abs_offset, check_melodic=is_first) is not None:
                return []
            notes.append(self._to_note(pitch, abs_offset, dur))
            self._prev_candidate_midi = self._home_key.diatonic_to_midi(pitch)
            self._prev_candidate_offset = abs_offset
            elapsed += dur
        return notes

    def _update_leap_direction(self, notes: list[Note]) -> None:
        """Update leap direction state from completed notes."""
        if len(notes) < 2:
            self._prev_leap_direction = 0
            return
        last_midi: int = notes[-1].pitch
        prev_midi: int = notes[-2].pitch
        diff: int = last_midi - prev_midi
        if abs(diff) > 4:
            self._prev_leap_direction = 1 if diff > 0 else -1
        else:
            self._prev_leap_direction = 0

    def _get_section_start_offset(self, section: SectionPlan) -> Fraction:
        """Get absolute offset of section start."""
        anchor: PlanAnchor = self._anchors[section.start_gap_index]
        return _bar_beat_to_offset(anchor.bar_beat, self._plan.metre, self._upbeat)

    def _get_section_end_offset(self, section: SectionPlan) -> Fraction:
        """Get absolute offset of section end."""
        anchor: PlanAnchor = self._anchors[section.end_gap_index]
        return _bar_beat_to_offset(anchor.bar_beat, self._plan.metre, self._upbeat)

    # ── Helpers ───────────────────────────────────────────

    def _compute_delay(self, gap: GapPlan) -> Fraction:
        """Compute initial rest for STAGGERED mode; zero otherwise."""
        if gap.writing_mode != WritingMode.STAGGERED:
            return Fraction(0)
        num_str, den_str = self._plan.metre.split("/")
        beat_unit: Fraction = Fraction(1, int(den_str))
        delay: Fraction = beat_unit * max(gap.start_beat - 1, 0)
        if delay >= gap.gap_duration:
            return Fraction(0)
        return delay


# ── Module-level helpers ──────────────────────────────────────────────────────

def _build_offset_index(
    prior_voices: dict[str, tuple[Note, ...]],
) -> dict[Fraction, list[int]]:
    """Build offset -> MIDI pitch index for all prior voices."""
    result: dict[Fraction, list[int]] = {}
    for voice_notes in prior_voices.values():
        for note in voice_notes:
            result.setdefault(note.offset, []).append(note.pitch)
    return result


def _bar_beat_to_offset(
    bar_beat: str,
    metre: str,
    upbeat: Fraction = Fraction(0),
) -> Fraction:
    """Convert 'bar.beat' string to absolute offset in whole notes.

    When upbeat > 0, offsets are shifted so the piece starts at offset 0.
    Bar 0 (the anacrusis bar) maps to non-negative offsets.
    """
    parts: list[str] = bar_beat.split(".")
    assert len(parts) == 2, f"bar_beat must be 'bar.beat', got '{bar_beat}'"
    bar: int = int(parts[0])
    beat: int = int(parts[1])
    assert bar >= 0, f"Bar must be >= 0, got {bar}"
    assert beat >= 1, f"Beat must be >= 1, got {beat}"
    num_str, den_str = metre.split("/")
    den: int = int(den_str)
    num: int = int(num_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    result: Fraction = (bar - 1) * bar_length + (beat - 1) * beat_unit + upbeat
    assert result >= 0, (
        f"Negative offset {result} from bar_beat '{bar_beat}' "
        f"with upbeat {upbeat}"
    )
    return result

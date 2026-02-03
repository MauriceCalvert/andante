"""Voice writer: produces notes for one voice from its VoicePlan.

One class, one instance per voice.  Receives all decisions from the
plan and executes them mechanically.  Makes zero compositional choices.
"""
import logging
from dataclasses import replace
from fractions import Fraction
from random import Random
from builder.cadential_strategy import CadentialStrategy
from builder.figuration_strategy import FigurationStrategy
from builder.junction import check_junction
from builder.pillar_strategy import PillarStrategy
from builder.staggered_strategy import StaggeredStrategy
from builder.types import Note
from builder.voice_checks import (
    check_direct_motion,
    check_parallels,
    check_range,
    check_strong_beat_consonance,
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
from shared.voice_types import Role

_log: logging.Logger = logging.getLogger(__name__)
_IMPLEMENTED_MODES: frozenset[WritingMode] = frozenset({
    WritingMode.PILLAR,
    WritingMode.FIGURATION,
    WritingMode.CADENTIAL,
    WritingMode.STAGGERED,
})
_IMPLEMENTED_SEQUENCING: frozenset[str] = frozenset({
    "independent",
    "repeating",
    "static",
})


class VoiceWriter:
    """Produce a tuple[Note, ...] for one voice."""

    def __init__(
        self,
        plan: VoicePlan,
        home_key: Key,
        anchors: tuple[PlanAnchor, ...],
        prior_voices: dict[str, tuple[Note, ...]],
    ) -> None:
        self._plan: VoicePlan = plan
        self._home_key: Key = home_key
        self._anchors: tuple[PlanAnchor, ...] = anchors
        self._prior_voices: dict[str, tuple[Note, ...]] = prior_voices
        self._rng: Random = Random(plan.seed)
        self._pillar: PillarStrategy = PillarStrategy()
        self._figuration: FigurationStrategy = FigurationStrategy()
        self._cadential: CadentialStrategy = CadentialStrategy()
        self._staggered: StaggeredStrategy = StaggeredStrategy(
            fill_strategy=self._figuration,
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

    def compose(self) -> tuple[Note, ...]:
        """Compose all sections and return sorted notes."""
        all_notes: list[Note] = []
        if self._plan.anacrusis is not None:
            anacrusis_notes: list[Note] = self._compose_anacrusis()
            all_notes.extend(anacrusis_notes)
        for section in self._plan.sections:
            notes: list[Note] = self._compose_section(section)
            all_notes.extend(notes)
        all_notes.sort(key=lambda n: n.offset)
        return tuple(all_notes)

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
        self._prev_candidate_midi = None
        if section.sequencing == "independent":
            return self._compose_independent(section)
        return self._compose_sequenced(section)

    def _compose_independent(self, section: SectionPlan) -> list[Note]:
        """Compose section with independent gap selection."""
        result: list[Note] = []
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            source_anchor: PlanAnchor = self._anchors[anchor_idx]
            target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
            source_pitch: DiatonicPitch = self._pitch_for_role(
                source_anchor, section.role,
            )
            target_pitch: DiatonicPitch = self._pitch_for_role(
                target_anchor, section.role,
            )
            gap_offset: Fraction = _bar_beat_to_offset(
                source_anchor.bar_beat, self._plan.metre,
            )
            notes: list[Note] = self._compose_gap(
                gap, source_pitch, target_pitch, gap_offset,
            )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note: Note = notes[-1]
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    last_note.pitch,
                )
                self._update_leap_direction(notes)
        return result

    def _compose_sequenced(self, section: SectionPlan) -> list[Note]:
        """Compose section with sequencing (repeating, static)."""
        result: list[Note] = []
        base_figure: tuple[tuple[DiatonicPitch, Fraction], ...] | None = None
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            source_anchor: PlanAnchor = self._anchors[anchor_idx]
            target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
            source_pitch: DiatonicPitch = self._pitch_for_role(
                source_anchor, section.role,
            )
            target_pitch: DiatonicPitch = self._pitch_for_role(
                target_anchor, section.role,
            )
            gap_offset: Fraction = _bar_beat_to_offset(
                source_anchor.bar_beat, self._plan.metre,
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
        """Fill one gap using the strategy selected by writing_mode."""
        delay: Fraction = self._compute_delay(gap)
        effective_gap: GapPlan = gap
        if delay > 0:
            effective_gap = replace(gap, gap_duration=gap.gap_duration - delay)
        strategy: WritingStrategy = self._strategy_for_mode(gap.writing_mode)
        pairs: tuple[tuple[DiatonicPitch, Fraction], ...] = strategy.fill_gap(
            gap=effective_gap,
            source_pitch=source_pitch,
            target_pitch=target_pitch,
            home_key=self._home_key,
            metre=self._plan.metre,
            rng=self._rng,
            candidate_filter=lambda dp, offset: self._check_candidate(
                dp, gap_offset + delay + offset,
            ),
        )
        notes: list[Note] = []
        elapsed: Fraction = delay
        for dp, dur in pairs:
            note: Note = self._to_note(dp, gap_offset + elapsed, dur)
            notes.append(note)
            self._prev_candidate_midi = note.pitch
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
        for note in source_notes:
            if note.offset < section_start - delay:
                continue
            if note.offset >= section_end - delay:
                continue
            dp: DiatonicPitch = self._home_key.midi_to_diatonic(note.pitch)
            transposed: DiatonicPitch = dp.transpose(interval)
            new_offset: Fraction = note.offset + delay
            if self._check_candidate(transposed, new_offset):
                result.append(self._to_note(
                    transposed, new_offset, note.duration / GATE_FACTOR,
                ))
        return result

    def _compose_anacrusis(self) -> list[Note]:
        """Compose anacrusis (upbeat) before first section."""
        ana: AnacrusisPlan | None = self._plan.anacrusis
        assert ana is not None
        note_count: int = ana.note_count
        assert note_count >= 1
        dur_each: Fraction = ana.duration / note_count
        start_offset: Fraction = -ana.duration
        result: list[Note] = []
        for i in range(note_count):
            if ana.ascending:
                step_offset: int = i - note_count + 1
            else:
                step_offset = note_count - 1 - i
            pitch: DiatonicPitch = ana.target_pitch.transpose(step_offset)
            offset: Fraction = start_offset + i * dur_each
            if self._check_candidate(pitch, offset):
                result.append(self._to_note(pitch, offset, dur_each))
        return result

    # ── Anchor reading ────────────────────────────────────

    def _pitch_for_role(self, anchor: PlanAnchor, role: Role) -> DiatonicPitch:
        """Read the anchor pitch appropriate to this voice's role."""
        if role == Role.SCHEMA_UPPER:
            return anchor.upper_pitch
        if role == Role.SCHEMA_LOWER:
            return anchor.lower_pitch
        assert False, f"Unsupported role for pitch reading: {role.name}"

    # ── Checking ──────────────────────────────────────────

    def _check_candidate(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
    ) -> bool:
        """Return True if candidate passes all counterpoint checks."""
        midi: int = self._home_key.diatonic_to_midi(pitch)
        if not check_range(midi, self._plan.actuator_range):
            return False
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        for prior_midi in prior_pitches:
            if not check_strong_beat_consonance(
                midi, prior_midi, offset, self._plan.metre,
            ):
                return False
        if self._prev_candidate_midi is not None and prior_pitches:
            prev_prior: list[int] = self._find_prev_prior_pitches(offset)
            for i, prior_midi in enumerate(prior_pitches):
                if i < len(prev_prior):
                    prev_prior_midi: int = prev_prior[i]
                    if not check_parallels(
                        self._prev_candidate_midi, prev_prior_midi,
                        midi, prior_midi,
                    ):
                        return False
                    if not check_direct_motion(
                        self._prev_candidate_midi, prev_prior_midi,
                        midi, prior_midi,
                    ):
                        return False
        return True

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
        for rel_dp, dur in base_figure:
            pitch: DiatonicPitch = source_pitch.transpose(rel_dp.step)
            abs_offset: Fraction = gap_offset + elapsed
            if not self._check_candidate(pitch, abs_offset):
                return []
            notes.append(self._to_note(pitch, abs_offset, dur))
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
        return _bar_beat_to_offset(anchor.bar_beat, self._plan.metre)

    def _get_section_end_offset(self, section: SectionPlan) -> Fraction:
        """Get absolute offset of section end."""
        anchor: PlanAnchor = self._anchors[section.end_gap_index]
        return _bar_beat_to_offset(anchor.bar_beat, self._plan.metre)

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


def _bar_beat_to_offset(bar_beat: str, metre: str) -> Fraction:
    """Convert 'bar.beat' string to absolute offset in whole notes."""
    parts: list[str] = bar_beat.split(".")
    assert len(parts) == 2, f"bar_beat must be 'bar.beat', got '{bar_beat}'"
    bar: int = int(parts[0])
    beat: int = int(parts[1])
    assert bar >= 1, f"Bar must be >= 1, got {bar}"
    assert beat >= 1, f"Beat must be >= 1, got {beat}"
    num_str, den_str = metre.split("/")
    den: int = int(den_str)
    num: int = int(num_str)
    bar_length: Fraction = Fraction(num, den)
    beat_unit: Fraction = Fraction(1, den)
    return (bar - 1) * bar_length + (beat - 1) * beat_unit

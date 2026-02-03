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
from builder.pillar_strategy import PillarStrategy
from builder.staggered_strategy import StaggeredStrategy
from builder.types import Note
from builder.voice_checks import check_range
from builder.writing_strategy import WritingStrategy
from shared.constants import GATE_FACTOR
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key
from shared.plan_types import (
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

    def compose(self) -> tuple[Note, ...]:
        """Compose all sections and return sorted notes."""
        all_notes: list[Note] = []
        for section in self._plan.sections:
            notes: list[Note] = self._compose_section(section)
            all_notes.extend(notes)
        all_notes.sort(key=lambda n: n.offset)
        return tuple(all_notes)

    # ── Section-level ─────────────────────────────────────

    def _compose_section(self, section: SectionPlan) -> list[Note]:
        """Compose one section (independent sequencing only for 6a/6b)."""
        assert section.role in (Role.SCHEMA_UPPER, Role.SCHEMA_LOWER), (
            f"Role {section.role.name} not yet implemented"
        )
        assert section.sequencing == "independent", (
            f"Sequencing '{section.sequencing}' not yet implemented"
        )
        self._prev_figure_name = ""
        self._prev_leap_direction = 0
        self._prev_exit_pitch = None
        result: list[Note] = []
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            source_anchor: PlanAnchor = self._anchors[anchor_idx]
            target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
            source_pitch: DiatonicPitch = self._pitch_for_role(source_anchor, section.role)
            target_pitch: DiatonicPitch = self._pitch_for_role(target_anchor, section.role)
            gap_offset: Fraction = _bar_beat_to_offset(source_anchor.bar_beat, self._plan.metre)
            notes: list[Note] = self._compose_gap(gap, source_pitch, target_pitch, gap_offset)
            result.extend(notes)
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
                dp, gap_offset + delay + offset, Fraction(0),
            ),
        )
        notes: list[Note] = []
        elapsed: Fraction = delay
        for dp, dur in pairs:
            note: Note = self._to_note(dp, gap_offset + elapsed, dur)
            notes.append(note)
            elapsed += dur
        return notes

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
        duration: Fraction,
    ) -> bool:
        """Return True if candidate passes all checks (6b: range only)."""
        midi: int = self._home_key.diatonic_to_midi(pitch)
        return check_range(midi, self._plan.actuator_range)

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

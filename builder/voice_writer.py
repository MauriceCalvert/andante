"""Voice writer: produces notes for one voice from its VoicePlan.

One class, one instance per voice.  Receives all decisions from the
plan and executes them mechanically.  Makes zero compositional choices.

Supports section-by-section composition for lead-voice scheduling.
"""
import logging
import math
from dataclasses import replace
from fractions import Fraction
from random import Random
from typing import TYPE_CHECKING
from builder.arpeggiated_strategy import ArpeggiatedStrategy

if TYPE_CHECKING:
    from motifs.fugue_loader import LoadedFugue
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
from shared.constants import ANCHOR_DEPARTURE_HEADROOM, STRONG_BEAT_DISSONANT
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
_MATERIAL_LYRICS: dict[str, str] = {
    "subject": "S",
    "answer": "A",
    "countersubject": "CS",
}


def _material_to_lyric(material: str) -> str:
    """Convert fugue material name to concise lyric label."""
    return _MATERIAL_LYRICS.get(material, material)


def _is_consonant(midi: int, prior_pitches: list[int]) -> bool:
    """Check if midi is consonant with all prior pitches."""
    for p in prior_pitches:
        ic: int = abs(midi - p) % 12
        if ic in STRONG_BEAT_DISSONANT:
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
        fugue: 'LoadedFugue | None' = None,
    ) -> None:
        self._plan: VoicePlan = plan
        self._home_key: Key = home_key
        self._upbeat: Fraction = upbeat
        self._anchors: tuple[PlanAnchor, ...] = anchors
        self._prior_voices: dict[str, tuple[Note, ...]] = prior_voices
        self._fugue: 'LoadedFugue | None' = fugue
        self._rng: Random = Random(plan.seed)
        self._pillar: PillarStrategy = PillarStrategy()
        self._figuration: FigurationStrategy = FigurationStrategy()
        self._cadential: CadentialStrategy = CadentialStrategy()
        self._staggered: StaggeredStrategy = StaggeredStrategy(
            fill_strategy=self._figuration,
        )
        self._arpeggiated: ArpeggiatedStrategy | None = (
            ArpeggiatedStrategy(pattern_name=plan.bass_pattern)
            if plan.bass_pattern is not None
            else None
        )
        self._prev_figure_name: str = ""
        self._prev_leap_direction: int = 0
        self._prev_exit_pitch: DiatonicPitch | None = None
        self._prior_at_offset: dict[Fraction, list[int]] = _build_offset_index(
            prior_voices=prior_voices,
        )
        self._prev_prior_at_offset: dict[Fraction, list[int]] = {}
        self._current_voice_notes: list[Note] = []
        self._prev_candidate_midi: int | None = None
        self._prev_candidate_offset: Fraction | None = None
        self._anacrusis_composed: bool = False
        self._sections_composed: set[int] = set()
        self._gaps_composed: set[tuple[int, int]] = set()
        self._section_initialized: set[int] = set()
        self._prev_anchor_midi: dict[int, int | None] = {}

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
                    section=self._plan.sections[section_idx],
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
        section_notes: list[Note] = self._compose_section(section=section)
        result.extend(section_notes)
        self._sections_composed.add(section_idx)
        return result

    def update_prior_voices(
        self,
        prior_voices: dict[str, tuple[Note, ...]],
    ) -> None:
        """Update prior voices after other voice composed a gap."""
        self._prior_voices = prior_voices
        self._prior_at_offset = _build_offset_index(prior_voices=prior_voices)

    def compose_single_gap(
        self,
        section_idx: int,
        gap_idx: int,
    ) -> list[Note]:
        """Compose a single gap within a section.

        Called by compose_voices() for gap-by-gap interleaved composition.
        Handles anacrusis before first gap of first section.
        Handles section initialization on first gap of each section.
        For IMITATIVE or fugue-thematic sections, composes entire section.
        """
        result: list[Note] = []
        gap_key: tuple[int, int] = (section_idx, gap_idx)
        if gap_key in self._gaps_composed:
            return result
        if section_idx == 0 and gap_idx == 0:
            if self._plan.anacrusis is not None and not self._anacrusis_composed:
                result.extend(self._compose_anacrusis())
                self._anacrusis_composed = True
        section: SectionPlan = self._plan.sections[section_idx]
        if section.role == Role.IMITATIVE:
            if section_idx not in self._sections_composed:
                result.extend(self._compose_imitative_section(section=section))
                self._sections_composed.add(section_idx)
                for i in range(len(section.gaps)):
                    self._gaps_composed.add((section_idx, i))
            return result
        fugue_material = self._get_fugue_material_for_section(section=section)
        if fugue_material is not None:
            if section_idx not in self._sections_composed:
                result.extend(self._compose_fugue_thematic(
                    section=section,
                    pitches=fugue_material[0],
                    durations=fugue_material[1],
                    material_name=fugue_material[2],
                ))
                self._sections_composed.add(section_idx)
                for i in range(len(section.gaps)):
                    self._gaps_composed.add((section_idx, i))
            return result
        if section_idx not in self._section_initialized:
            self._prev_figure_name = ""
            self._prev_leap_direction = 0
            self._prev_exit_pitch = None
            self._prev_anchor_midi[section_idx] = self._prev_candidate_midi
            self._section_initialized.add(section_idx)
        gap: GapPlan = section.gaps[gap_idx]
        anchor_idx: int = section.start_gap_index + gap_idx
        prev_anchor_midi: int | None = self._prev_anchor_midi.get(section_idx)
        if gap.bar_function == "final":
            final_anchor: PlanAnchor = self._anchors[-1]
            source_pitch: DiatonicPitch = self._resolve_anchor_pitch(
                anchor=final_anchor,
                role=section.role,
                prev_midi=prev_anchor_midi,
            )
            target_pitch: DiatonicPitch = source_pitch
            source_anchor: PlanAnchor = final_anchor
        else:
            source_anchor = self._anchors[anchor_idx]
            target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
            source_pitch = self._resolve_anchor_pitch(
                anchor=source_anchor,
                role=section.role,
                prev_midi=prev_anchor_midi,
                departure_ascending=gap.ascending,
            )
            source_midi: int = self._home_key.diatonic_to_midi(dp=source_pitch)
            if anchor_idx == 0 and self._anacrusis_composed:
                self._prev_anchor_midi[section_idx] = source_midi
                self._prev_exit_pitch = source_pitch
                self._gaps_composed.add(gap_key)
                return result
            ascending_hint: bool | None = _ascending_hint_for_resolve(
                source_anchor=source_anchor,
                target_anchor=target_anchor,
                role=section.role,
                gap_ascending=gap.ascending,
            )
            target_pitch = self._resolve_anchor_pitch(
                anchor=target_anchor,
                role=section.role,
                prev_midi=source_midi,
                ascending_hint=ascending_hint,
            )
        gap_offset: Fraction = _bar_beat_to_offset(
            bar_beat=source_anchor.bar_beat,
            metre=self._plan.metre,
            upbeat=self._upbeat,
        )
        notes: list[Note] = self._compose_gap(
            gap=gap,
            source_pitch=source_pitch,
            target_pitch=target_pitch,
            gap_offset=gap_offset,
        )
        result.extend(notes)
        self._current_voice_notes.extend(notes)
        if notes:
            last_note: Note = notes[-1]
            self._prev_anchor_midi[section_idx] = last_note.pitch
            self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                midi=last_note.pitch,
            )
            self._update_leap_direction(notes=notes)
        self._gaps_composed.add(gap_key)
        return result

    # ── Section-level ─────────────────────────────────────

    def _compose_section(self, section: SectionPlan) -> list[Note]:
        """Compose one section."""
        if section.role == Role.IMITATIVE:
            return self._compose_imitative_section(section=section)
        assert section.role in (Role.SCHEMA_UPPER, Role.SCHEMA_LOWER), (
            f"Role {section.role.name} not yet implemented"
        )
        fugue_material = self._get_fugue_material_for_section(section=section)
        if fugue_material is not None:
            return self._compose_fugue_thematic(
                section=section,
                pitches=fugue_material[0],
                durations=fugue_material[1],
                material_name=fugue_material[2],
            )
        assert section.sequencing in _IMPLEMENTED_SEQUENCING, (
            f"Sequencing '{section.sequencing}' not yet implemented"
        )
        self._prev_figure_name = ""
        self._prev_leap_direction = 0
        self._prev_exit_pitch = None
        if section.sequencing == "independent":
            return self._compose_independent(section=section)
        return self._compose_sequenced(section=section)

    def _get_fugue_material_for_section(
        self,
        section: SectionPlan,
    ) -> tuple[tuple[int, ...], tuple[float, ...], str] | None:
        """Determine which fugue material to use for this section, if any.

        Uses section.lead_material and section.accompany_material from plan.
        Lead voice gets lead_material, accompanying voice gets accompany_material.
        Material values: 'subject', 'answer', 'countersubject', 'free', None.

        Returns:
            (pitches, durations, material_name) or None if no fugue material.

        TODO: Extract subject fragments for episode sequences in remaining gaps.
        Currently gaps after fugue material are filled with normal figuration.
        """
        if self._fugue is None:
            return None
        is_lead: bool = self._is_lead_voice(section=section)
        material: str | None = (
            section.lead_material if is_lead else section.accompany_material
        )
        if material is None or material == "free":
            return None
        tonic_midi: int = self._get_material_tonic(section=section, material=material)
        pitches_durations = self._get_material_pitches(material=material, tonic_midi=tonic_midi)
        if pitches_durations is None:
            return None
        return (pitches_durations[0], pitches_durations[1], material)

    def _is_lead_voice(self, section: SectionPlan) -> bool:
        """Determine if this voice is the lead for a section."""
        form_lead: int | None = section.form_lead_voice
        if form_lead is None:
            return section.role == Role.SCHEMA_UPPER
        is_upper: bool = self._plan.midi_track == 0
        lead_is_upper: bool = form_lead == 0
        return is_upper == lead_is_upper

    def _get_material_tonic(self, section: SectionPlan, material: str) -> int:
        """Get the tonic MIDI for fugue material."""
        if material == "answer":
            return self._fugue.tonic_midi
        section_idx: int = self._plan.sections.index(section)
        if section_idx >= 2:
            return self._get_section_local_tonic(section=section)
        return self._fugue.tonic_midi

    def _get_material_pitches(
        self,
        material: str,
        tonic_midi: int,
    ) -> tuple[tuple[int, ...], tuple[float, ...]] | None:
        """Get MIDI pitches and durations for a fugue material type."""
        if material == "subject":
            return (self._fugue.subject_midi(tonic_midi=tonic_midi), self._fugue.subject.durations)
        if material == "answer":
            return (self._fugue.answer_midi(tonic_midi=tonic_midi), self._fugue.answer.durations)
        if material == "countersubject":
            return (self._fugue.countersubject_midi(tonic_midi=tonic_midi), self._fugue.countersubject.durations)
        return None

    def _get_section_local_tonic(self, section: SectionPlan) -> int:
        """Get the local tonic MIDI for a section from its first anchor.

        Returns tonic at octave 4 (e.g., C4=60, G4=67). The pitches will
        be transposed to voice range by _transpose_to_range anyway.
        """
        first_anchor: PlanAnchor = self._anchors[section.start_gap_index]
        tonic_pc: int = first_anchor.local_key.tonic_pc
        tonic_octave_4: int = tonic_pc + 60
        return tonic_octave_4

    def _compose_fugue_thematic(
        self,
        section: SectionPlan,
        pitches: tuple[int, ...],
        durations: tuple[float, ...],
        material_name: str,
    ) -> list[Note]:
        """Compose section using literal fugue pitches, then fill remaining gaps."""
        lyric: str = _material_to_lyric(material=material_name)
        section_start: Fraction = self._get_section_start_offset(section=section)
        transposed: tuple[int, ...] = self._transpose_to_range_avoiding_crossing(
            pitches=pitches,
            durations=durations,
            start_offset=section_start,
        )
        result: list[Note] = []
        offset: Fraction = section_start
        for i, (midi, dur) in enumerate(zip(transposed, durations)):
            adjusted: int = self._adjust_fugue_pitch_for_consonance(
                midi=midi,
                offset=offset,
            )
            frac_dur: Fraction = Fraction(dur).limit_denominator(64)
            note: Note = Note(
                offset=offset,
                pitch=adjusted,
                duration=frac_dur,
                voice=self._plan.midi_track,
                lyric=lyric if i == 0 else "",
            )
            result.append(note)
            self._prev_candidate_midi = adjusted
            self._prev_candidate_offset = offset
            offset += frac_dur
        self._current_voice_notes.extend(result)
        if result:
            self._prev_exit_pitch = self._home_key.midi_to_diatonic(midi=result[-1].pitch)
        fugue_end: Fraction = offset
        remaining: list[Note] = self._fill_remaining_gaps(
            section=section,
            filled_until=fugue_end,
        )
        result.extend(remaining)
        return result

    def _adjust_fugue_pitch_for_consonance(
        self,
        midi: int,
        offset: Fraction,
    ) -> int:
        """Adjust fugue pitch by octave if dissonant or crossing prior voices."""
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        if not prior_pitches:
            return midi
        rng: Range = self._plan.actuator_range
        is_upper: bool = self._plan.midi_track == 0
        def is_valid(candidate: int) -> bool:
            if candidate < rng.low or candidate > rng.high:
                return False
            if not _is_consonant(midi=candidate, prior_pitches=prior_pitches):
                return False
            for prior in prior_pitches:
                if is_upper and candidate < prior:
                    return False
                if not is_upper and candidate > prior:
                    return False
            return True
        if is_valid(candidate=midi):
            return midi
        for shift in (12, -12, 24, -24):
            candidate: int = midi + shift
            if is_valid(candidate=candidate):
                return candidate
        return midi

    def _transpose_to_range_avoiding_crossing(
        self,
        pitches: tuple[int, ...],
        durations: tuple[float, ...],
        start_offset: Fraction,
    ) -> tuple[int, ...]:
        """Transpose pitches to range, then adjust to avoid crossing prior voices."""
        transposed: tuple[int, ...] = self._transpose_to_range(pitches=pitches)
        if not transposed:
            return transposed
        is_upper: bool = self._plan.midi_track == 0
        rng: Range = self._plan.actuator_range
        offset: Fraction = start_offset
        crossing_count: int = 0
        for midi, dur in zip(transposed, durations):
            prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
            for prior in prior_pitches:
                if is_upper and midi < prior:
                    crossing_count += 1
                elif not is_upper and midi > prior:
                    crossing_count += 1
            offset += Fraction(dur).limit_denominator(64)
        if crossing_count == 0:
            return transposed
        shift: int = 12 if is_upper else -12
        shifted: tuple[int, ...] = tuple(p + shift for p in transposed)
        if all(rng.low <= p <= rng.high for p in shifted):
            return shifted
        return transposed

    def _transpose_to_range(self, pitches: tuple[int, ...]) -> tuple[int, ...]:
        """Transpose pitches by octaves to fit within actuator_range.

        Finds an octave shift such that all transposed pitches lie within
        the voice's actuator_range, preferring shifts that centre the
        material near the tessitura median.
        """
        if not pitches:
            return pitches
        rng: Range = self._plan.actuator_range
        min_pitch: int = min(pitches)
        max_pitch: int = max(pitches)
        pitch_span: int = max_pitch - min_pitch
        voice_span: int = rng.high - rng.low
        assert pitch_span <= voice_span, (
            f"Fugue pitch span ({pitch_span} semitones) exceeds voice range "
            f"({voice_span} semitones): cannot fit within [{rng.low}-{rng.high}]"
        )
        min_shift: int = math.ceil((rng.low - min_pitch) / 12)
        max_shift: int = math.floor((rng.high - max_pitch) / 12)
        assert min_shift <= max_shift, (
            f"No valid octave shift: need >= {min_shift} and <= {max_shift}"
        )
        median: int = self._plan.tessitura_median
        pitch_centre: int = (min_pitch + max_pitch) // 2
        best_shift: int = min_shift
        best_distance: int = abs(pitch_centre + min_shift * 12 - median)
        for shift in range(min_shift, max_shift + 1):
            distance: int = abs(pitch_centre + shift * 12 - median)
            if distance < best_distance:
                best_distance = distance
                best_shift = shift
        transposed: tuple[int, ...] = tuple(p + best_shift * 12 for p in pitches)
        return transposed

    def _fill_remaining_gaps(
        self,
        section: SectionPlan,
        filled_until: Fraction,
    ) -> list[Note]:
        """Fill gaps in section that start at or after filled_until."""
        result: list[Note] = []
        prev_anchor_midi: int | None = self._prev_candidate_midi
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            source_anchor: PlanAnchor = self._anchors[anchor_idx]
            gap_offset: Fraction = _bar_beat_to_offset(
                bar_beat=source_anchor.bar_beat,
                metre=self._plan.metre,
                upbeat=self._upbeat,
            )
            if gap_offset < filled_until:
                continue
            if gap.bar_function == "final":
                final_anchor: PlanAnchor = self._anchors[-1]
                source_pitch: DiatonicPitch = self._resolve_anchor_pitch(
                    anchor=final_anchor,
                    role=section.role,
                    prev_midi=prev_anchor_midi,
                )
                target_pitch: DiatonicPitch = source_pitch
            else:
                target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
                source_pitch = self._resolve_anchor_pitch(
                    anchor=source_anchor,
                    role=section.role,
                    prev_midi=prev_anchor_midi,
                    departure_ascending=gap.ascending,
                )
                source_midi: int = self._home_key.diatonic_to_midi(dp=source_pitch)
                ascending_hint: bool | None = _ascending_hint_for_resolve(
                    source_anchor=source_anchor,
                    target_anchor=target_anchor,
                    role=section.role,
                    gap_ascending=gap.ascending,
                )
                target_pitch = self._resolve_anchor_pitch(
                    anchor=target_anchor,
                    role=section.role,
                    prev_midi=source_midi,
                    ascending_hint=ascending_hint,
                )
            notes: list[Note] = self._compose_gap(
                gap=gap,
                source_pitch=source_pitch,
                target_pitch=target_pitch,
                gap_offset=gap_offset,
            )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note: Note = notes[-1]
                prev_anchor_midi = last_note.pitch
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    midi=last_note.pitch,
                )
                self._update_leap_direction(notes=notes)
        return result

    def _compose_independent(self, section: SectionPlan) -> list[Note]:
        """Compose section with independent gap selection."""
        result: list[Note] = []
        prev_anchor_midi: int | None = self._prev_candidate_midi
        for gap_idx, gap in enumerate(section.gaps):
            anchor_idx: int = section.start_gap_index + gap_idx
            if gap.bar_function == "final":
                final_anchor: PlanAnchor = self._anchors[-1]
                source_pitch: DiatonicPitch = self._resolve_anchor_pitch(
                    anchor=final_anchor, role=section.role, prev_midi=prev_anchor_midi,
                )
                target_pitch: DiatonicPitch = source_pitch
                source_anchor: PlanAnchor = final_anchor
            else:
                source_anchor = self._anchors[anchor_idx]
                target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
                source_pitch = self._resolve_anchor_pitch(
                    anchor=source_anchor, role=section.role, prev_midi=prev_anchor_midi,
                    departure_ascending=gap.ascending,
                )
                source_midi: int = self._home_key.diatonic_to_midi(dp=source_pitch)
                if anchor_idx == 0 and self._anacrusis_composed:
                    prev_anchor_midi = source_midi
                    self._prev_exit_pitch = source_pitch
                    continue
                ascending_hint: bool | None = _ascending_hint_for_resolve(
                    source_anchor=source_anchor, target_anchor=target_anchor, role=section.role, gap_ascending=gap.ascending,
                )
                target_pitch = self._resolve_anchor_pitch(
                    anchor=target_anchor, role=section.role, prev_midi=source_midi, ascending_hint=ascending_hint,
                )
            gap_offset: Fraction = _bar_beat_to_offset(
                bar_beat=source_anchor.bar_beat, metre=self._plan.metre, upbeat=self._upbeat,
            )
            notes: list[Note] = self._compose_gap(
                gap=gap, source_pitch=source_pitch, target_pitch=target_pitch, gap_offset=gap_offset,
            )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note: Note = notes[-1]
                prev_anchor_midi = last_note.pitch
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    midi=last_note.pitch,
                )
                self._update_leap_direction(notes=notes)
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
                    anchor=final_anchor, role=section.role, prev_midi=prev_anchor_midi,
                )
                target_pitch: DiatonicPitch = source_pitch
                source_anchor: PlanAnchor = final_anchor
            else:
                source_anchor = self._anchors[anchor_idx]
                target_anchor: PlanAnchor = self._anchors[anchor_idx + 1]
                source_pitch = self._resolve_anchor_pitch(
                    anchor=source_anchor, role=section.role, prev_midi=prev_anchor_midi,
                    departure_ascending=gap.ascending,
                )
                source_midi: int = self._home_key.diatonic_to_midi(dp=source_pitch)
                if anchor_idx == 0 and self._anacrusis_composed:
                    prev_anchor_midi = source_midi
                    self._prev_exit_pitch = source_pitch
                    continue
                ascending_hint: bool | None = _ascending_hint_for_resolve(
                    source_anchor=source_anchor, target_anchor=target_anchor, role=section.role, gap_ascending=gap.ascending,
                )
                target_pitch = self._resolve_anchor_pitch(
                    anchor=target_anchor, role=section.role, prev_midi=source_midi, ascending_hint=ascending_hint,
                )
            gap_offset: Fraction = _bar_beat_to_offset(
                bar_beat=source_anchor.bar_beat, metre=self._plan.metre, upbeat=self._upbeat,
            )
            if gap_idx == 0 or base_figure is None:
                notes: list[Note] = self._compose_gap(
                    gap=gap, source_pitch=source_pitch, target_pitch=target_pitch, gap_offset=gap_offset,
                )
                if notes and gap.writing_mode == WritingMode.FIGURATION:
                    base_figure = self._extract_relative_figure(
                        notes=notes, source_pitch=source_pitch, gap_offset=gap_offset,
                    )
            else:
                notes = self._apply_sequenced_figure(
                    base_figure=base_figure, source_pitch=source_pitch, gap=gap, gap_offset=gap_offset,
                    sequencing=section.sequencing,
                )
                if not notes:
                    notes = self._compose_gap(
                        gap=gap, source_pitch=source_pitch, target_pitch=target_pitch, gap_offset=gap_offset,
                    )
            result.extend(notes)
            self._current_voice_notes.extend(notes)
            if notes:
                last_note = notes[-1]
                prev_anchor_midi = last_note.pitch
                self._prev_exit_pitch = self._home_key.midi_to_diatonic(
                    midi=last_note.pitch,
                )
                self._update_leap_direction(notes=notes)
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
        delay: Fraction = self._compute_delay(gap=gap)
        effective_gap: GapPlan = gap
        if delay > 0:
            effective_gap = replace(gap, gap_duration=gap.gap_duration - delay)
        strategy: WritingStrategy = self._strategy_for_mode(mode=gap.writing_mode)
        if gap.writing_mode in (WritingMode.PILLAR, WritingMode.ARPEGGIATED):
            candidate_filter = lambda dp, offset, is_first: self._check_candidate(
                pitch=dp, offset=gap_offset + delay + offset, check_melodic=False,
            )
        else:
            def candidate_filter(
                dp: DiatonicPitch, offset: Fraction, is_first: bool,
            ) -> str | None:
                if is_first:
                    # Anchor note is a harmonic obligation — skip checks but
                    # update state so subsequent notes measure motion from here,
                    # not from the previous gap's exit pitch.
                    midi: int = self._home_key.diatonic_to_midi(dp=dp)
                    self._prev_candidate_midi = midi
                    self._prev_candidate_offset = gap_offset + delay + offset
                    return None
                return self._check_candidate(
                    pitch=dp, offset=gap_offset + delay + offset,
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
            note: Note = self._to_note(pitch=dp, offset=gap_offset + elapsed, duration=dur)
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
        section_start: Fraction = self._get_section_start_offset(section=section)
        section_end: Fraction = self._get_section_end_offset(section=section)
        used_offsets: set[Fraction] = {n.offset for n in self._current_voice_notes}
        result: list[Note] = []
        for note in source_notes:
            if note.offset < section_start:
                continue
            if note.offset >= section_end:
                continue
            new_offset: Fraction = note.offset + delay
            if new_offset in used_offsets:
                continue
            dp: DiatonicPitch = self._home_key.midi_to_diatonic(midi=note.pitch)
            transposed: DiatonicPitch = dp.transpose(steps=interval)
            rejection: str | None = self._check_candidate(
                pitch=transposed, offset=new_offset, check_melodic=False, check_consonance=False,
            )
            if rejection is None:
                new_note: Note = self._to_note(
                    pitch=transposed, offset=new_offset, duration=note.duration,
                )
                result.append(new_note)
                used_offsets.add(new_offset)
                self._prev_candidate_midi = new_note.pitch
                self._prev_candidate_offset = new_note.offset
        self._current_voice_notes.extend(result)
        if result:
            last_note: Note = result[-1]
            self._prev_exit_pitch = self._home_key.midi_to_diatonic(midi=last_note.pitch)
        return result

    def _compose_anacrusis(self) -> list[Note]:
        """Compose anacrusis (upbeat) before first section."""
        ana: AnacrusisPlan | None = self._plan.anacrusis
        assert ana is not None
        note_count: int = ana.note_count
        assert note_count >= 1
        dur_each: Fraction = ana.duration / note_count
        start_offset: Fraction = -ana.duration
        target_midi: int = self._place_degree_near_median(
            key=self._home_key, degree=ana.target_degree, rng=self._plan.actuator_range,
        )
        target_pitch: DiatonicPitch = self._home_key.midi_to_diatonic(midi=target_midi)
        result: list[Note] = []
        for i in range(note_count):
            if ana.ascending:
                step_offset: int = i - note_count + 1
            else:
                step_offset = note_count - 1 - i
            pitch: DiatonicPitch = target_pitch.transpose(steps=step_offset)
            offset: Fraction = start_offset + i * dur_each
            is_first: bool = i == 0
            if self._check_candidate(pitch=pitch, offset=offset, check_melodic=is_first) is None:
                note: Note = self._to_note(pitch=pitch, offset=offset, duration=dur_each)
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
        departure_ascending: bool | None = None,
    ) -> DiatonicPitch:
        """Resolve anchor degree to DiatonicPitch using previous pitch context.

        First anchor: place degree near tessitura median.
        Subsequent: use direction hint relative to previous pitch.
        If anchor's direction is None, use ascending_hint from gap plan.

        departure_ascending: if True, the figuration leaving this anchor goes
        UP, so leave headroom above. If False, leave headroom below.

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
            midi: int = self._place_degree_near_median(
                key=key,
                degree=degree,
                rng=rng,
                departure_ascending=departure_ascending,
            )
        else:
            midi = self._place_degree_with_direction(
                key=key,
                degree=degree,
                prev_midi=prev_midi,
                direction=direction,
                rng=rng,
                departure_ascending=departure_ascending,
            )
        midi = self._adjust_for_consonance(key=key, degree=degree, preferred_midi=midi, bar_beat=anchor.bar_beat, rng=rng)
        return self._home_key.midi_to_diatonic(midi=midi)


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
        offset: Fraction = _bar_beat_to_offset(bar_beat=bar_beat, metre=self._plan.metre, upbeat=self._upbeat)
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        if not prior_pitches:
            return preferred_midi
        if _is_consonant(midi=preferred_midi, prior_pitches=prior_pitches):
            return preferred_midi
        base_pc: int = key.degree_to_midi(degree=degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        consonant: list[int] = [
            m for m in candidates if _is_consonant(midi=m, prior_pitches=prior_pitches)
        ]
        if consonant:
            return min(consonant, key=lambda m: abs(m - preferred_midi))
        return preferred_midi

    def _place_degree_near_median(
        self,
        key: Key,
        degree: int,
        rng: Range,
        departure_ascending: bool | None = None,
    ) -> int:
        """Place degree as MIDI near tessitura median with departure headroom.

        Generates all valid octave placements of the degree within the
        actuator range. Filters for departure headroom first (if specified),
        then picks the one closest to the median.
        Never clamps to arbitrary MIDI values — that would corrupt the degree.
        """
        median: int = self._plan.tessitura_median
        base_pc: int = key.degree_to_midi(degree=degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        assert candidates, (
            f"No valid octave for degree {degree} in range {rng.low}-{rng.high}"
        )
        with_headroom: list[int] = self._filter_for_departure_headroom(
            candidates=candidates,
            rng=rng,
            departure_ascending=departure_ascending,
        )
        pool: list[int] = with_headroom if with_headroom else candidates
        return min(pool, key=lambda m: abs(m - median))

    def _place_degree_with_direction(
        self,
        key: Key,
        degree: int,
        prev_midi: int,
        direction: str | None,
        rng: Range,
        departure_ascending: bool | None = None,
    ) -> int:
        """Place degree relative to previous pitch with approach and departure constraints.

        Approach direction (direction): whether to place above/below prev_midi.
        Departure direction (departure_ascending): which edge needs headroom.
        Both constraints are applied during initial candidate selection.
        """
        base_pc: int = key.degree_to_midi(degree=degree, octave=0)
        candidates: list[int] = []
        for octave in range(0, 10):
            midi: int = base_pc + octave * 12
            if rng.low <= midi <= rng.high:
                candidates.append(midi)
        assert candidates, (
            f"No valid octave for degree {degree} in range {rng.low}-{rng.high}"
        )
        with_headroom: list[int] = self._filter_for_departure_headroom(
            candidates=candidates,
            rng=rng,
            departure_ascending=departure_ascending,
        )
        pool: list[int] = with_headroom if with_headroom else candidates
        if direction == "up":
            above: list[int] = [m for m in pool if m > prev_midi]
            if above:
                return min(above)
            return min(pool, key=lambda m: abs(m - prev_midi))
        if direction == "down":
            below: list[int] = [m for m in pool if m < prev_midi]
            if below:
                return max(below)
            return min(pool, key=lambda m: abs(m - prev_midi))
        return min(pool, key=lambda m: abs(m - prev_midi))

    def _filter_for_departure_headroom(
        self,
        candidates: list[int],
        rng: Range,
        departure_ascending: bool | None,
    ) -> list[int]:
        """Filter candidates to ensure headroom for figuration departure direction.

        Ascending departure needs room above (midi <= high - margin).
        Descending departure needs room below (midi >= low + margin).
        Returns filtered list, or empty if no candidates satisfy constraint.
        """
        if departure_ascending is None:
            return candidates
        if departure_ascending:
            ceiling: int = rng.high - ANCHOR_DEPARTURE_HEADROOM
            return [m for m in candidates if m <= ceiling]
        floor: int = rng.low + ANCHOR_DEPARTURE_HEADROOM
        return [m for m in candidates if m >= floor]

    # ── Checking ──────────────────────────────────────────

    def _check_candidate(
        self,
        pitch: DiatonicPitch,
        offset: Fraction,
        check_melodic: bool = True,
        check_consonance: bool = True,
    ) -> str | None:
        """Return None if candidate passes, else rejection reason.

        Parallels and direct motion to perfect consonances are only checked
        on strong beats (beat 1 in any metre). Off-beat figuration has more
        freedom per baroque practice, enabling invertible counterpoint.
        """
        midi: int = self._home_key.diatonic_to_midi(dp=pitch)
        rng: Range = self._plan.actuator_range
        if not check_range(midi=midi, actuator_range=rng):
            return f"range({rng.low}-{rng.high})"
        if check_melodic and self._prev_candidate_midi is not None:
            if not check_melodic_interval(prev_midi=self._prev_candidate_midi, curr_midi=midi):
                interval: int = midi - self._prev_candidate_midi
                return f"melodic_interval({format_interval(semitones=interval)})"
        prior_pitches: list[int] = self._prior_at_offset.get(offset, [])
        if check_consonance:
            for prior_midi in prior_pitches:
                if not check_strong_beat_consonance(
                    candidate_midi=midi, prior_midi=prior_midi, offset=offset, metre=self._plan.metre,
                ):
                    ic: int = abs(midi - prior_midi) % 12
                    return f"strong_beat_dissonance(ic={ic})"
        if not check_voice_overlap(
            candidate_midi=midi, candidate_offset=offset, prior_notes_by_offset=self._prior_at_offset, prev_offset=self._prev_candidate_offset,
        ):
            return "voice_overlap"
        is_strong_beat: bool = _is_strong_beat(offset=offset, metre=self._plan.metre)
        if is_strong_beat and self._prev_candidate_midi is not None and prior_pitches:
            prev_prior: list[int] = self._find_prev_prior_pitches(current_offset=offset)
            for i, prior_midi in enumerate(prior_pitches):
                if i < len(prev_prior):
                    prev_prior_midi: int = prev_prior[i]
                    if not check_parallels(
                        prev_upper=self._prev_candidate_midi, prev_lower=prev_prior_midi,
                        curr_upper=midi, curr_lower=prior_midi,
                    ):
                        curr_ic: int = abs(midi - prior_midi) % 12
                        return f"parallel({format_interval(semitones=curr_ic)})"
                    if not check_direct_motion(
                        prev_upper=self._prev_candidate_midi, prev_lower=prev_prior_midi,
                        curr_upper=midi, curr_lower=prior_midi,
                    ):
                        curr_ic = abs(midi - prior_midi) % 12
                        return f"direct_motion_to({format_interval(semitones=curr_ic)})"
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
        midi: int = self._home_key.diatonic_to_midi(dp=pitch)
        return Note(
            offset=offset,
            pitch=midi,
            duration=duration,
            voice=self._plan.midi_track,
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
        source_midi: int = self._home_key.diatonic_to_midi(dp=source_pitch)
        result: list[tuple[DiatonicPitch, Fraction]] = []
        for note in notes:
            rel_offset: Fraction = note.offset - gap_offset
            dp: DiatonicPitch = self._home_key.midi_to_diatonic(midi=note.pitch)
            interval: int = dp.step - source_pitch.step
            result.append((DiatonicPitch(step=interval), note.duration))
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
            pitch: DiatonicPitch = source_pitch.transpose(steps=rel_dp.step)
            abs_offset: Fraction = gap_offset + elapsed
            is_first: bool = i == 0
            if self._check_candidate(pitch=pitch, offset=abs_offset, check_melodic=is_first) is not None:
                return []
            notes.append(self._to_note(pitch=pitch, offset=abs_offset, duration=dur))
            self._prev_candidate_midi = self._home_key.diatonic_to_midi(dp=pitch)
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
        return _bar_beat_to_offset(bar_beat=anchor.bar_beat, metre=self._plan.metre, upbeat=self._upbeat)

    def _get_section_end_offset(self, section: SectionPlan) -> Fraction:
        """Get absolute offset of section end."""
        anchor: PlanAnchor = self._anchors[section.end_gap_index]
        return _bar_beat_to_offset(bar_beat=anchor.bar_beat, metre=self._plan.metre, upbeat=self._upbeat)

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


def _is_strong_beat(offset: Fraction, metre: str) -> bool:
    """Check if offset falls on beat 1 of a bar.

    Strong beats are where parallels/direct motion rules apply strictly.
    Off-beat notes have more freedom in baroque figuration.
    """
    num_str, den_str = metre.split("/")
    den: int = int(den_str)
    num: int = int(num_str)
    bar_length: Fraction = Fraction(num, den)
    position_in_bar: Fraction = offset % bar_length
    return position_in_bar == Fraction(0)


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

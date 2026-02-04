"""Entry point: execute a CompositionPlan to produce a Composition.

Section-aware composition order: lead voice composes first per section,
giving it rhythmic freedom while the following voice adapts.
"""
from dataclasses import dataclass
from builder.types import Composition, Note
from builder.voice_writer import VoiceWriter
from shared.plan_types import CompositionPlan, SectionPlan, VoicePlan


@dataclass
class CompositionTask:
    """One section to compose, with scheduling priority."""
    voice_idx: int
    section_idx: int
    start_gap: int
    end_gap: int
    is_lead: bool


def compose_voices(plan: CompositionPlan) -> Composition:
    """Execute a CompositionPlan to produce a Composition.
    
    Schedules sections so lead voice composes first within each time span,
    allowing the following voice to adapt to the leader's rhythm.
    """
    assert len(plan.voice_plans) > 0, "CompositionPlan must have at least one voice"
    schedule: list[CompositionTask] = _build_schedule(plan)
    voice_notes: dict[str, list[Note]] = {
        vp.voice_id: [] for vp in plan.voice_plans
    }
    writers: dict[str, VoiceWriter] = {}
    for task in schedule:
        voice_plan: VoicePlan = plan.voice_plans[task.voice_idx]
        voice_id: str = voice_plan.voice_id
        prior: dict[str, tuple[Note, ...]] = {
            vid: tuple(notes)
            for vid, notes in voice_notes.items()
            if vid != voice_id
        }
        if voice_id not in writers:
            writers[voice_id] = VoiceWriter(
                plan=voice_plan,
                home_key=plan.home_key,
                anchors=plan.anchors,
                prior_voices=prior,
            )
        else:
            writers[voice_id].update_prior_voices(prior)
        section_notes: list[Note] = writers[voice_id].compose_section(
            task.section_idx,
        )
        voice_notes[voice_id].extend(section_notes)
    final_voices: dict[str, tuple[Note, ...]] = {}
    for voice_plan in plan.voice_plans:
        vid: str = voice_plan.voice_id
        notes: list[Note] = voice_notes[vid]
        notes.sort(key=lambda n: n.offset)
        final_voices[vid] = tuple(notes)
    return Composition(
        voices=final_voices,
        metre=plan.voice_plans[0].metre,
        tempo=plan.tempo,
        upbeat=plan.upbeat,
    )


def _build_schedule(plan: CompositionPlan) -> list[CompositionTask]:
    """Build composition task schedule ordered by (start_gap, not is_lead).
    
    Lead voice sections come first within overlapping time spans.
    """
    tasks: list[CompositionTask] = []
    for voice_idx, voice_plan in enumerate(plan.voice_plans):
        for section_idx, section in enumerate(voice_plan.sections):
            is_lead: bool = _section_is_lead(section)
            tasks.append(CompositionTask(
                voice_idx=voice_idx,
                section_idx=section_idx,
                start_gap=section.start_gap_index,
                end_gap=section.end_gap_index,
                is_lead=is_lead,
            ))
    tasks.sort(key=lambda t: (t.start_gap, not t.is_lead))
    return tasks


def _section_is_lead(section: SectionPlan) -> bool:
    """Determine if section is the lead voice.
    
    Lead sections have higher-density figuration; following sections
    have low density (accompaniment texture).
    """
    if not section.gaps:
        return True
    lead_count: int = 0
    for gap in section.gaps:
        if gap.density != "low":
            lead_count += 1
    return lead_count > len(section.gaps) // 2

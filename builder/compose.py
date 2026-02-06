"""Entry point: execute a CompositionPlan to produce a Composition.

Gap-by-gap interleaved composition: both voices see each other's notes
at every offset, enabling invertible counterpoint and avoiding parallel
motion conflicts in contrapuntal textures.

Dual-path dispatch:
- compose_phrases(): new phrase-based path for genres with rhythm cells
- compose_voices(): legacy gap-based path for other genres
- compose(): top-level dispatch, chooses path based on phrase_plans argument
"""
from dataclasses import dataclass
from fractions import Fraction
from builder.phrase_types import PhrasePlan, PhraseContext, PhraseResult
from builder.phrase_writer import write_phrase
from builder.types import Composition, Note
from builder.voice_writer import VoiceWriter
from shared.key import Key
from shared.plan_types import CompositionPlan, SectionPlan, VoicePlan, WritingMode
from shared.voice_types import Role


def compose_phrases(
    phrase_plans: tuple[PhrasePlan, ...],
    home_key: Key,
    metre: str,
    tempo: int,
    upbeat: Fraction,
) -> Composition:
    """Compose a piece phrase by phrase using the new phrase writer.

    Args:
        phrase_plans: Sequence of PhrasePlans, one per schema in the chain.
        home_key: Home key of the composition.
        metre: Time signature string (e.g., "3/4").
        tempo: Tempo in BPM.
        upbeat: Anacrusis duration in whole notes.

    Returns:
        Composition with "soprano" and "bass" voice entries.
    """
    assert len(phrase_plans) > 0, "Must have at least one PhrasePlan"
    upper_notes: list[Note] = []
    lower_notes: list[Note] = []
    context: PhraseContext | None = None
    for plan in phrase_plans:
        result: PhraseResult = write_phrase(plan=plan, context=context)
        upper_notes.extend(result.upper_notes)
        lower_notes.extend(result.lower_notes)
        context = PhraseContext(
            home_key=home_key,
            completed_upper=tuple(upper_notes),
            completed_lower=tuple(lower_notes),
        )
    return Composition(
        voices={
            "soprano": tuple(upper_notes),
            "bass": tuple(lower_notes),
        },
        metre=metre,
        tempo=tempo,
        upbeat=upbeat,
    )


def compose(
    plan: CompositionPlan,
    phrase_plans: tuple[PhrasePlan, ...] | None = None,
) -> Composition:
    """Compose a piece. Uses phrase path if phrase_plans provided.

    Args:
        plan: CompositionPlan (always required for key, tempo, upbeat).
        phrase_plans: If provided, uses the new phrase-based path.
            If None, falls back to legacy gap-based compose_voices().

    Returns:
        Composition with voice notes.
    """
    if phrase_plans is not None:
        return compose_phrases(
            phrase_plans=phrase_plans,
            home_key=plan.home_key,
            metre=plan.voice_plans[0].metre,
            tempo=plan.tempo,
            upbeat=plan.upbeat,
        )
    return compose_voices(plan=plan)


@dataclass
class GapTask:
    """One gap to compose, with scheduling priority."""
    voice_idx: int
    section_idx: int
    gap_idx: int
    anchor_idx: int
    is_lead: bool


def compose_voices(plan: CompositionPlan) -> Composition:
    """Execute a CompositionPlan to produce a Composition.

    Uses gap-by-gap interleaved composition: after each gap, the other
    voice's prior_voices index is updated so it sees the new notes.
    This enables invertible counterpoint and avoids voice-leading
    conflicts when both voices have active figuration.
    """
    assert len(plan.voice_plans) > 0, "CompositionPlan must have at least one voice"
    voice_notes: dict[str, list[Note]] = {
        vp.voice_id: [] for vp in plan.voice_plans
    }
    writers: dict[int, VoiceWriter] = {}
    for voice_idx, voice_plan in enumerate(plan.voice_plans):
        prior: dict[str, tuple[Note, ...]] = {
            vp.voice_id: ()
            for vp in plan.voice_plans
            if vp.voice_id != voice_plan.voice_id
        }
        writers[voice_idx] = VoiceWriter(
            plan=voice_plan,
            home_key=plan.home_key,
            anchors=plan.anchors,
            prior_voices=prior,
            upbeat=plan.upbeat,
            fugue=plan.fugue,
        )
    schedule: list[GapTask] = _build_gap_schedule(plan=plan)
    for task in schedule:
        voice_plan: VoicePlan = plan.voice_plans[task.voice_idx]
        voice_id: str = voice_plan.voice_id
        writer: VoiceWriter = writers[task.voice_idx]
        prior: dict[str, tuple[Note, ...]] = {
            vp.voice_id: tuple(voice_notes[vp.voice_id])
            for vp in plan.voice_plans
            if vp.voice_id != voice_id
        }
        writer.update_prior_voices(prior_voices=prior)
        gap_notes: list[Note] = writer.compose_single_gap(
            section_idx=task.section_idx,
            gap_idx=task.gap_idx,
        )
        voice_notes[voice_id].extend(gap_notes)
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


def _build_gap_schedule(plan: CompositionPlan) -> list[GapTask]:
    """Build gap-level schedule ordered by (anchor_idx, not is_lead, voice_idx).

    Lead voice gaps come first at each anchor position, so accompany voice
    sees lead's notes when choosing its figuration.
    """
    tasks: list[GapTask] = []
    for voice_idx, voice_plan in enumerate(plan.voice_plans):
        for section_idx, section in enumerate(voice_plan.sections):
            is_lead: bool = _section_is_lead(section=section)
            for gap_idx, gap in enumerate(section.gaps):
                anchor_idx: int = section.start_gap_index + gap_idx
                tasks.append(GapTask(
                    voice_idx=voice_idx,
                    section_idx=section_idx,
                    gap_idx=gap_idx,
                    anchor_idx=anchor_idx,
                    is_lead=is_lead,
                ))
    tasks.sort(key=lambda t: (t.anchor_idx, not t.is_lead, t.voice_idx))
    return tasks


def _section_is_lead(section: SectionPlan) -> bool:
    """Determine if section is the lead voice.

    IMITATIVE sections are never lead — they must wait for the source
    voice to compose first so its notes are available for copying.
    Lead sections have higher-density figuration; following sections
    have low density (accompaniment texture).
    """
    if section.role == Role.IMITATIVE:
        return False
    if not section.gaps:
        return True
    lead_count: int = 0
    for gap in section.gaps:
        if gap.density != "low":
            lead_count += 1
    return lead_count > len(section.gaps) // 2

"""Entry point: execute a CompositionPlan to produce a Composition."""
from builder.types import Composition, Note
from builder.voice_writer import VoiceWriter
from shared.plan_types import CompositionPlan


def compose_voices(plan: CompositionPlan) -> Composition:
    """Execute a CompositionPlan to produce a Composition."""
    assert len(plan.voice_plans) > 0, "CompositionPlan must have at least one voice"
    prior_voices: dict[str, tuple[Note, ...]] = {}
    for voice_plan in plan.voice_plans:
        writer: VoiceWriter = VoiceWriter(
            plan=voice_plan,
            home_key=plan.home_key,
            anchors=plan.anchors,
            prior_voices=prior_voices,
        )
        notes: tuple[Note, ...] = writer.compose()
        prior_voices[voice_plan.voice_id] = notes
    return Composition(
        voices=prior_voices,
        metre=plan.voice_plans[0].metre,
        tempo=plan.tempo,
        upbeat=plan.upbeat,
    )

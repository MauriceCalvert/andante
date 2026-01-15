"""N-voice expander: expand all voices from arc and voice_entries.

v6 architecture: each voice gets explicit treatment from arc voice_entries.
No FILL treatment. Inner voices with rest are placeholders for solver.
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from engine.arc_loader import ArcDefinition, get_default_treatment_for_voice
from shared.pitch import FloatingNote, Pitch, Rest
from engine.transform import apply_imitation, apply_transform
from engine.engine_types import MotifAST, PhraseAST
from engine.voice_config import VoiceSet
from engine.voice_entry import PhraseVoiceEntry, VoiceTreatmentSpec
from engine.voice_material import ExpandedVoices, VoiceMaterial
from shared.timed_material import TimedMaterial


DATA_DIR: Path = Path(__file__).parent.parent / "data"
TREATMENTS: dict = yaml.safe_load(open(DATA_DIR / "treatments.yaml", encoding="utf-8"))


@dataclass(frozen=True)
class VoiceExpansionContext:
    """Context for expanding a single voice."""
    subject: MotifAST
    counter_subject: MotifAST | None
    budget: Fraction
    phrase_index: int
    tonal_target: str


def get_source_pitches(
    spec: VoiceTreatmentSpec,
    ctx: VoiceExpansionContext,
) -> tuple[Pitch, ...]:
    """Get source pitches based on treatment source."""
    if spec.source == "subject":
        return ctx.subject.pitches
    if spec.source == "counter_subject" and ctx.counter_subject is not None:
        return ctx.counter_subject.pitches
    return ctx.subject.pitches


def get_source_durations(
    spec: VoiceTreatmentSpec,
    ctx: VoiceExpansionContext,
) -> tuple[Fraction, ...]:
    """Get source durations based on treatment source."""
    if spec.source == "subject":
        return ctx.subject.durations
    if spec.source == "counter_subject" and ctx.counter_subject is not None:
        return ctx.counter_subject.durations
    return ctx.subject.durations


def expand_single_voice(
    spec: VoiceTreatmentSpec,
    ctx: VoiceExpansionContext,
    voice_index: int,
) -> VoiceMaterial:
    """Expand a single voice based on its treatment spec."""
    if spec.is_rest:
        return VoiceMaterial(
            voice_index=voice_index,
            pitches=[Rest()],
            durations=[ctx.budget],
        )
    pitches: tuple[Pitch, ...] = get_source_pitches(spec, ctx)
    durations: tuple[Fraction, ...] = get_source_durations(spec, ctx)
    material: TimedMaterial = TimedMaterial(pitches, durations, sum(durations, Fraction(0)))
    if spec.treatment in ("invert", "retrograde", "augment", "diminish"):
        material = apply_transform(material, spec.treatment, {})
    elif spec.treatment == "inversion":
        material = apply_transform(material, "invert", {})
    elif spec.treatment == "augmentation":
        material = apply_transform(material, "augment", {})
    elif spec.treatment == "diminution":
        material = apply_transform(material, "diminish", {})
    pitches = material.pitches
    durations = material.durations
    if spec.interval != 0:
        pitches = apply_imitation(pitches, spec.interval)
    if spec.is_chordal:
        pitches = apply_imitation(pitches, spec.interval)
    material = TimedMaterial.repeat_to_budget(
        list(pitches), list(durations), ctx.budget
    )
    return VoiceMaterial(
        voice_index=voice_index,
        pitches=list(material.pitches),
        durations=list(material.durations),
    )


def expand_phrase_n_voice(
    phrase: PhraseAST,
    arc: ArcDefinition,
    voice_set: VoiceSet,
    ctx: VoiceExpansionContext,
) -> ExpandedVoices:
    """Expand all voices for a phrase using arc voice_entries.

    If arc has explicit voice_entries for this phrase, use them.
    Otherwise, outer voices get arc treatment, inner voices get rest.
    """
    entry: PhraseVoiceEntry | None = arc.voice_entries.entry_for_phrase(phrase.index)
    voice_materials: list[VoiceMaterial] = []
    for i in range(voice_set.count):
        if entry is not None:
            spec: VoiceTreatmentSpec = entry.spec_for_voice(i)
        else:
            spec = get_default_treatment_for_voice(
                phrase.index, i, voice_set.count, arc.treatments
            )
        material: VoiceMaterial = expand_single_voice(spec, ctx, i)
        voice_materials.append(material)
    return ExpandedVoices(voices=voice_materials)


def expand_outer_voices_only(
    phrase: PhraseAST,
    arc: ArcDefinition,
    voice_set: VoiceSet,
    ctx: VoiceExpansionContext,
) -> ExpandedVoices:
    """Expand only outer voices, leaving inner as rest placeholders.

    Used when no explicit voice_entries. Inner voices filled by solver.
    """
    voice_materials: list[VoiceMaterial] = []
    for i in range(voice_set.count):
        is_outer: bool = i == 0 or i == voice_set.count - 1
        if is_outer:
            spec: VoiceTreatmentSpec = get_default_treatment_for_voice(
                phrase.index, i, voice_set.count, arc.treatments
            )
        else:
            spec = VoiceTreatmentSpec.rest()
        material: VoiceMaterial = expand_single_voice(spec, ctx, i)
        voice_materials.append(material)
    return ExpandedVoices(voices=voice_materials)

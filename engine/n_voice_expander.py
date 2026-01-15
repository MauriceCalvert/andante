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
    bar_dur: Fraction = Fraction(1)


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
    bar_dur: Fraction = Fraction(1),
) -> VoiceMaterial:
    """Expand a single voice based on its treatment spec.

    Handles:
    - Rest voices (silent)
    - Free voices (placeholder for species counterpoint)
    - Delayed entries (prepend rest, truncate end)
    - Tonal answer (adjust intervals for dominant form)
    - Standard transformations (invert, retrograde, etc.)
    """
    if spec.is_rest:
        return VoiceMaterial(
            voice_index=voice_index,
            pitches=[Rest()],
            durations=[ctx.budget],
        )

    # Free counterpoint: placeholder for solver to fill
    # The inner voice solver will generate species counterpoint against the entries
    if spec.is_free:
        return VoiceMaterial(
            voice_index=voice_index,
            pitches=[Rest()],
            durations=[ctx.budget],
        )

    pitches: tuple[Pitch, ...] = get_source_pitches(spec, ctx)
    durations: tuple[Fraction, ...] = get_source_durations(spec, ctx)
    material: TimedMaterial = TimedMaterial(pitches, durations, sum(durations, Fraction(0)))

    # Apply tonal answer if entering on dominant
    if spec.needs_tonal_answer:
        from engine.transform import apply_tonal_answer
        material = apply_tonal_answer(material)

    # Apply melodic transformation
    # Extract base treatment name (strip ornament annotations like [circulatio])
    base_treatment: str = spec.treatment.split("[")[0] if spec.treatment else ""
    if base_treatment in ("invert", "retrograde", "augment", "diminish"):
        material = apply_transform(material, base_treatment, {})
    elif base_treatment == "inversion":
        material = apply_transform(material, "invert", {})
    elif base_treatment == "augmentation":
        material = apply_transform(material, "augment", {})
    elif base_treatment == "diminution":
        material = apply_transform(material, "diminish", {})

    pitches = material.pitches
    durations = material.durations

    # Apply interval transposition
    if spec.interval != 0:
        pitches = apply_imitation(pitches, spec.interval)
    if spec.is_chordal:
        pitches = apply_imitation(pitches, spec.interval)

    # Calculate delay in actual duration
    delay_dur: Fraction = spec.delay * bar_dur

    # Calculate available budget after delay
    fill_budget: Fraction = ctx.budget - delay_dur
    if fill_budget <= Fraction(0):
        # Entry delay exceeds phrase - voice is effectively silent
        return VoiceMaterial(
            voice_index=voice_index,
            pitches=[Rest()],
            durations=[ctx.budget],
        )

    # Extend material to fill available budget
    material = TimedMaterial.repeat_to_budget(
        list(pitches), list(durations), fill_budget
    )

    # Mark pitches as guard-exempt (thematic material is expected to repeat)
    exempt_pitches: tuple[Pitch, ...] = tuple(
        p.as_exempt() if isinstance(p, FloatingNote) else p for p in material.pitches
    )
    material = TimedMaterial(exempt_pitches, material.durations, material.budget)

    # Prepend delay rest if needed
    if delay_dur > Fraction(0):
        final_pitches: list[Pitch] = [Rest()] + list(material.pitches)
        final_durations: list[Fraction] = [delay_dur] + list(material.durations)
    else:
        final_pitches = list(material.pitches)
        final_durations = list(material.durations)

    return VoiceMaterial(
        voice_index=voice_index,
        pitches=final_pitches,
        durations=final_durations,
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
        material: VoiceMaterial = expand_single_voice(spec, ctx, i, ctx.bar_dur)
        voice_materials.append(material)
    return ExpandedVoices(voices=voice_materials)


def generate_baroque_entries(
    phrase_index: int,
    voice_count: int,
    treatment: str,
    subject_bars: int = 2,
    phrase_bars: int = 4,
) -> PhraseVoiceEntry:
    """Generate baroque-style entry schedule for a phrase.

    Baroque invention conventions:
    - Phrase 0: Subject in soprano, tonal answer in bass after subject_bars
    - Phrase 1: Subject (inverted) in bass, CS in soprano after delay
    - Phrase 2+: Rotate entries, vary treatments
    - Stretto: Both voices play subject with overlapping entries

    Args:
        phrase_index: Which phrase (0-indexed)
        voice_count: Number of voices (2 or 3)
        treatment: Phrase treatment (statement, inversion, stretto, etc.)
        subject_bars: Length of subject in bars
        phrase_bars: Length of phrase in bars (to cap delays)

    Returns:
        PhraseVoiceEntry with baroque-appropriate voice specs
    """
    specs: list[VoiceTreatmentSpec] = []

    # Extract base treatment name (strip ornament annotations like [circulatio])
    base_treatment: str = treatment.split("[")[0] if treatment else ""

    # Stretto: both voices play subject with overlapping entries
    if base_treatment == "stretto":
        # Stretto delay: second voice enters after half the subject length
        # This creates the characteristic overlapping effect
        stretto_delay = Fraction(subject_bars) / 2
        if voice_count == 2:
            # Soprano starts subject, bass enters with subject after stretto_delay
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, stretto_delay, "dominant"),
            ]
        else:
            # Three voices: stagger all three
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, stretto_delay, "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, stretto_delay * 2, "dominant"),
            ]
        return PhraseVoiceEntry(
            phrase_index=phrase_index,
            texture="baroque_invention",
            voice_specs=tuple(specs),
        )

    # Entry delay: stagger only when phrase is longer than subject
    # For short phrases (phrase_bars <= subject_bars), use simultaneous entries
    if phrase_bars > subject_bars:
        max_delay = Fraction(phrase_bars) / 2
        entry_delay = min(Fraction(subject_bars), max_delay)
    else:
        entry_delay = Fraction(0)  # Simultaneous: no room to stagger

    if voice_count == 2:
        # Two voices: alternating subject/counter_subject
        if phrase_index == 0:
            # Opening: soprano states subject, bass plays counter_subject
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
            ]
        elif phrase_index % 2 == 1:
            # Odd phrases: bass leads with subject (answer at dominant), soprano plays CS
            specs = [
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "dominant"),
            ]
        else:
            # Even phrases: soprano leads with subject, bass plays CS
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
            ]
    else:
        # Three voices: rotation through all voices
        rotation = phrase_index % 3

        if phrase_index == 0:
            # Opening: soprano has subject, alto has CS, bass has CS
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
            ]
        elif rotation == 0:
            # Soprano leads with subject, alto and bass have CS
            specs = [
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
            ]
        elif rotation == 1:
            # Bass leads with subject (answer), soprano and alto have CS
            specs = [
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "dominant"),
            ]
        else:
            # Alto leads with subject, soprano and bass have CS
            specs = [
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "subject", 0, Fraction(0), "tonic"),
                VoiceTreatmentSpec(treatment, "counter_subject", 0, Fraction(0), "tonic"),
            ]

    return PhraseVoiceEntry(
        phrase_index=phrase_index,
        texture="baroque_invention",
        voice_specs=tuple(specs),
    )


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
        material: VoiceMaterial = expand_single_voice(spec, ctx, i, ctx.bar_dur)
        voice_materials.append(material)
    return ExpandedVoices(voices=voice_materials)

"""Voice expansion pipeline - data-driven voice generation.

A voice is expanded through a pipeline of stages:
1. Source: Get pitches/durations from subject, counter_subject, or pattern
2. Transform: Apply invert, retrograde, head, tail, augment, diminish
3. Derivation: Apply imitation (transpose by interval)
4. Concatenate: Chain distinct bar treatments to fill budget (no repetition)
5. Delay: Prepend rest if bass_delay specified

Each stage reads from a treatment dict and applies if configured.
"""
from dataclasses import dataclass
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch, Rest
from engine.phrase_builder import build_phrase_soprano, build_phrase_bass
from engine.transform import apply_imitation, apply_transform
from engine.engine_types import MotifAST
from shared.timed_material import TimedMaterial


@dataclass(frozen=True)
class VoiceSpec:
    """Specification for expanding a voice from treatment config."""
    source: str  # "subject", "counter_subject", "sustained"
    transform: str  # "none", "invert", "retrograde", "head", "tail", "augment", "diminish"
    transform_params: dict
    derivation: str | None  # None or "imitation"
    derivation_params: dict
    delay: Fraction
    direct: bool  # True = use source directly without bar treatment cycling


def voice_spec_from_treatment(treatment: dict, voice: str) -> VoiceSpec:
    """Extract VoiceSpec for soprano or bass from treatment dict."""
    prefix: str = f"{voice}_"
    return VoiceSpec(
        source=treatment.get(f"{prefix}source", "subject"),
        transform=treatment.get(f"{prefix}transform", "none"),
        transform_params=treatment.get(f"{prefix}transform_params", {}),
        derivation=treatment.get(f"{prefix}derivation"),
        derivation_params=treatment.get(f"{prefix}derivation_params", {}),
        delay=Fraction(treatment.get(f"{prefix}delay", "0")),
        direct=treatment.get(f"{prefix}direct", False),
    )


def get_source_material(
    spec: VoiceSpec,
    subject: MotifAST,
    counter_subject: MotifAST | None,
) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Get source pitches and durations based on spec.source."""
    if spec.source == "subject":
        return subject.pitches, subject.durations
    elif spec.source == "counter_subject" and counter_subject is not None:
        return counter_subject.pitches, counter_subject.durations
    elif spec.source == "sustained":
        return (FloatingNote(1), FloatingNote(5)), (Fraction(1), Fraction(1))
    else:
        return subject.pitches, subject.durations


def apply_voice_delay(
    material: TimedMaterial,
    delay: Fraction,
    budget: Fraction,
) -> TimedMaterial:
    """Apply delay by prepending rest."""
    if delay <= Fraction(0):
        return material
    rest_pitch: tuple[Pitch, ...] = (Rest(),)
    rest_dur: tuple[Fraction, ...] = (delay,)
    return TimedMaterial(
        rest_pitch + material.pitches,
        rest_dur + material.durations,
        budget,
    )


def _extend_to_budget(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    budget: Fraction,
) -> TimedMaterial:
    """Extend material to budget by cycling (no pitch shifts)."""
    total: Fraction = sum(durations, Fraction(0))
    if total <= Fraction(0):
        return TimedMaterial(pitches, durations, budget)
    result_p: list[Pitch] = []
    result_d: list[Fraction] = []
    remaining: Fraction = budget
    idx: int = 0
    max_iter: int = 1000
    n: int = len(pitches)
    while remaining > Fraction(0) and idx < max_iter:
        p: Pitch = pitches[idx % n]
        d: Fraction = durations[idx % len(durations)]
        if d <= remaining:
            result_p.append(p)
            result_d.append(d)
            remaining -= d
        else:
            result_p.append(p)
            result_d.append(remaining)
            remaining = Fraction(0)
        idx += 1
    return TimedMaterial(tuple(result_p), tuple(result_d), budget)


def expand_voice(
    spec: VoiceSpec,
    subject: MotifAST,
    counter_subject: MotifAST | None,
    budget: Fraction,
    phrase_index: int,
    voice: str = "soprano",
) -> TimedMaterial:
    """Expand a single voice through the full pipeline.

    Pipeline: source → concatenate (with transform) → derivation → delay

    When spec.direct is True, bypasses bar treatment cycling and uses source
    material directly (with only the plan-level transform applied).
    """
    # Cap delay to leave room for at least one sixteenth note of content
    max_delay: Fraction = budget - Fraction(1, 16)
    effective_delay: Fraction = min(spec.delay, max_delay) if spec.delay > 0 else Fraction(0)
    fill_budget: Fraction = budget - effective_delay
    # Handle sustained source specially - no concatenation needed
    if spec.source == "sustained":
        pitches, durations = get_source_material(spec, subject, counter_subject)
        material: TimedMaterial = _extend_to_budget(pitches, durations, fill_budget)
        return apply_voice_delay(material, effective_delay, budget)
    # Direct mode: use source material directly without bar treatment cycling
    if spec.direct:
        pitches, durations = get_source_material(spec, subject, counter_subject)
        # Mark pitches as guard-exempt (subject material is expected to repeat)
        pitches = tuple(
            p.as_exempt() if isinstance(p, FloatingNote) else p for p in pitches
        )
        material = TimedMaterial(pitches, durations, sum(durations, Fraction(0)))
        # Apply plan-level transform
        material = apply_transform(material, spec.transform, spec.transform_params)
        # Extend to budget by cycling
        material = _extend_to_budget(material.pitches, material.durations, fill_budget)
        # Apply derivation if specified
        if spec.derivation == "imitation":
            interval: int = spec.derivation_params.get("interval", 4)
            new_pitches: tuple[Pitch, ...] = apply_imitation(material.pitches, interval)
            material = TimedMaterial(new_pitches, material.durations, material.budget)
        return apply_voice_delay(material, effective_delay, budget)
    # Build phrase using bar treatment concatenation (original behavior)
    use_cs: bool = spec.source == "counter_subject"
    if voice == "soprano":
        material = build_phrase_soprano(
            subject, counter_subject, fill_budget, phrase_index, spec.transform
        )
    else:
        material = build_phrase_bass(
            subject, counter_subject, fill_budget, phrase_index, spec.transform, use_cs
        )
    # Apply derivation if specified
    if spec.derivation == "imitation":
        interval: int = spec.derivation_params.get("interval", 4)
        new_pitches: tuple[Pitch, ...] = apply_imitation(material.pitches, interval)
        material = TimedMaterial(new_pitches, material.durations, material.budget)
    return apply_voice_delay(material, effective_delay, budget)

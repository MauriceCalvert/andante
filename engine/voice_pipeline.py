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
    """Extract VoiceSpec for soprano or bass from treatment dict.

    Note: direct mode is enforced at a higher level by _enforce_direct_for_cs
    in voice_expander.py when counter_subject is used.
    """
    prefix: str = f"{voice}_"
    # Bass defaults to counter_subject for proper counterpoint
    if voice == "bass":
        default_source = "counter_subject"
    else:
        default_source = "subject"
    source: str = treatment.get(f"{prefix}source", default_source)
    direct: bool = treatment.get(f"{prefix}direct", False)

    return VoiceSpec(
        source=source,
        transform=treatment.get(f"{prefix}transform", "none"),
        transform_params=treatment.get(f"{prefix}transform_params", {}),
        derivation=treatment.get(f"{prefix}derivation"),
        derivation_params=treatment.get(f"{prefix}derivation_params", {}),
        delay=Fraction(treatment.get(f"{prefix}delay", "0")),
        direct=direct,
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
    elif spec.source == "accompaniment":
        # Simple dance accompaniment: root-fifth-root pattern with quarter notes
        # This provides harmonic support without melodic competition
        return (
            (FloatingNote(1), FloatingNote(5), FloatingNote(1)),
            (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2)),
        )
    else:
        return subject.pitches, subject.durations


def apply_voice_delay(
    material: TimedMaterial,
    delay: Fraction,
    budget: Fraction,
    use_pedal: bool = True,
) -> TimedMaterial:
    """Apply delay by prepending pedal note or rest.

    Args:
        material: The voice material to delay
        delay: Duration of delay
        budget: Total phrase budget
        use_pedal: If True, use first pitch as pedal during delay (provides
                   metrical support per Koch rules 13-14). If False, use rest.
    """
    if delay <= Fraction(0):
        return material

    if use_pedal and material.pitches:
        # Use first pitch as pedal note for metrical support
        pedal_pitch: tuple[Pitch, ...] = (material.pitches[0],)
        pedal_dur: tuple[Fraction, ...] = (delay,)
        return TimedMaterial(
            pedal_pitch + material.pitches,
            pedal_dur + material.durations,
            budget,
        )
    else:
        # Fall back to rest
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
    """Extend material to budget by simple cycling."""
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

    When spec.direct is True:
    - If budget <= source_duration: use source verbatim
    - If budget > source_duration: present source once, then use bar treatment
      cycling for remainder (baroque practice: state then develop)
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
    # Direct mode: first statement literal, then sequence for remainder
    # This preserves CS alignment while adding variation
    if spec.direct:
        pitches, durations = get_source_material(spec, subject, counter_subject)
        source_duration: Fraction = sum(durations, Fraction(0))
        # Apply plan-level transform to source
        transformed = apply_transform(
            TimedMaterial(pitches, durations, source_duration),
            spec.transform,
            spec.transform_params,
        )
        transformed_duration: Fraction = sum(transformed.durations, Fraction(0))

        if fill_budget <= transformed_duration:
            # Budget fits within one statement - use verbatim
            material = _extend_to_budget(transformed.pitches, transformed.durations, fill_budget)
        else:
            # Budget exceeds source - first statement literal, then sequence
            from engine.sequence import build_sequence

            # First part: verbatim statement
            direct_part = TimedMaterial(
                transformed.pitches, transformed.durations, transformed_duration
            )

            # Remainder: descending sequence using same material
            remainder_budget: Fraction = fill_budget - transformed_duration
            seq_pitches, seq_durations = build_sequence(
                transformed.pitches,
                transformed.durations,
                remainder_budget,
                reps=4,      # Up to 4 sequence repetitions
                step=-1,     # Descending by step
                start=0,
                phrase_seed=phrase_index,
                vary=False,  # Don't vary rhythm, just transpose
            )
            seq_part = TimedMaterial(seq_pitches, seq_durations, remainder_budget)

            # Combine: literal statement + sequence development
            material = TimedMaterial(
                direct_part.pitches + seq_part.pitches,
                direct_part.durations + seq_part.durations,
                fill_budget,
            )

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
            subject, counter_subject, fill_budget, phrase_index, spec.transform, use_cs
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

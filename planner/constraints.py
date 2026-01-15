"""Constraint synthesis: translates planner decisions to realizer constraints.

This module bridges the planner and realizer by converting high-level
planning decisions into specific constraints that the realizer can use.
"""
from dataclasses import dataclass
from fractions import Fraction
from typing import Dict, List, Optional, Tuple

from planner.plannertypes import (
    Plan, Structure, Section, Episode, Phrase,
    RhetoricalStructure, TensionCurve, HarmonicPlan, CoherencePlan,
    Material, Callback, Surprise
)


@dataclass(frozen=True)
class BarConstraint:
    """Constraints for a single bar."""
    bar: int
    key_area: str
    tension: float
    rhetoric_section: str
    treatment: str
    devices: Tuple[str, ...]
    is_climax: bool
    cadence: Optional[str]
    callbacks: Tuple[Callback, ...]
    surprises: Tuple[Surprise, ...]


@dataclass(frozen=True)
class VoiceConstraint:
    """Constraints for a voice in a specific bar."""
    bar: int
    voice: int
    material: str  # subject, counter_subject, free, etc.
    transform: Optional[str]  # invert, retrograde, augment, diminish
    register: str  # high, middle, low
    texture: str  # melody, accompaniment, bass


@dataclass(frozen=True)
class PlanConstraints:
    """Complete constraints derived from a plan."""
    bar_constraints: Tuple[BarConstraint, ...]
    voice_constraints: Tuple[VoiceConstraint, ...]
    total_bars: int
    voices: int
    key: str
    mode: str
    metre: str
    tempo: str


def synthesize_constraints(plan: Plan) -> PlanConstraints:
    """Synthesize complete constraints from a plan.

    Args:
        plan: Complete plan from planner

    Returns:
        PlanConstraints ready for realizer
    """
    bar_constraints = _synthesize_bar_constraints(plan)
    voice_constraints = _synthesize_voice_constraints(plan, bar_constraints)

    return PlanConstraints(
        bar_constraints=tuple(bar_constraints),
        voice_constraints=tuple(voice_constraints),
        total_bars=plan.actual_bars,
        voices=plan.frame.voices,
        key=plan.frame.key,
        mode=plan.frame.mode,
        metre=plan.frame.metre,
        tempo=plan.frame.tempo,
    )


def _synthesize_bar_constraints(plan: Plan) -> List[BarConstraint]:
    """Synthesize per-bar constraints from plan."""
    constraints: List[BarConstraint] = []

    # Build bar-to-phrase mapping
    bar_to_phrase: Dict[int, Phrase] = {}
    bar_to_section: Dict[int, Section] = {}
    bar_to_episode: Dict[int, Episode] = {}

    current_bar = 1
    for section in plan.structure.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                for b in range(phrase.bars):
                    bar = current_bar + b
                    bar_to_phrase[bar] = phrase
                    bar_to_section[bar] = section
                    bar_to_episode[bar] = episode
                current_bar += phrase.bars

    # Synthesize constraints for each bar
    for bar in range(1, plan.actual_bars + 1):
        phrase = bar_to_phrase.get(bar)
        section = bar_to_section.get(bar)
        episode = bar_to_episode.get(bar)

        # Get key area from harmonic plan
        key_area = "I"
        if plan.harmonic_plan:
            key_area = _get_key_at_bar(plan.harmonic_plan, bar)

        # Get tension
        tension = 0.5
        if plan.tension_curve:
            tension = _get_tension_at_bar(
                plan.tension_curve, bar, plan.actual_bars
            )

        # Get rhetoric section
        rhetoric_section = "narratio"
        if plan.rhetoric:
            rhetoric_section = _get_rhetoric_at_bar(plan.rhetoric, bar)

        # Get treatment and devices
        treatment = phrase.treatment if phrase else "free"
        devices = _extract_devices(treatment)

        # Is this the climax?
        is_climax = False
        if plan.rhetoric and abs(bar - plan.rhetoric.climax_bar) <= 1:
            is_climax = True
        if phrase and phrase.is_climax:
            is_climax = True

        # Get cadence if at phrase end
        cadence = None
        if phrase and _is_phrase_end(bar, bar_to_phrase, plan.actual_bars):
            cadence = phrase.cadence

        # Get callbacks and surprises for this bar
        callbacks = ()
        surprises = ()
        if plan.coherence:
            callbacks = tuple(
                c for c in plan.coherence.callbacks if c.target_bar == bar
            )
            surprises = tuple(
                s for s in plan.coherence.surprises if s.bar == bar
            )

        constraints.append(BarConstraint(
            bar=bar,
            key_area=key_area,
            tension=tension,
            rhetoric_section=rhetoric_section,
            treatment=treatment,
            devices=devices,
            is_climax=is_climax,
            cadence=cadence,
            callbacks=callbacks,
            surprises=surprises,
        ))

    return constraints


def _synthesize_voice_constraints(
    plan: Plan,
    bar_constraints: List[BarConstraint],
) -> List[VoiceConstraint]:
    """Synthesize per-voice constraints."""
    constraints: List[VoiceConstraint] = []
    voices = plan.frame.voices

    for bc in bar_constraints:
        for voice in range(voices):
            # Determine material for this voice at this bar
            material, transform = _determine_material(
                bc, voice, plan.material, voices
            )

            # Determine register
            register = _voice_to_register(voice, voices)

            # Determine texture role
            texture = _voice_to_texture(voice, voices, bc)

            constraints.append(VoiceConstraint(
                bar=bc.bar,
                voice=voice,
                material=material,
                transform=transform,
                register=register,
                texture=texture,
            ))

    return constraints


def _get_key_at_bar(harmonic_plan: HarmonicPlan, bar: int) -> str:
    """Get key area at a specific bar."""
    current_key = "I"
    for target in harmonic_plan.targets:
        if target.bar <= bar:
            current_key = target.key_area
        else:
            break
    return current_key


def _get_tension_at_bar(
    tension_curve: TensionCurve,
    bar: int,
    total_bars: int,
) -> float:
    """Get tension at a specific bar."""
    position = bar / total_bars
    best_dist = float("inf")
    best_level = 0.5

    for point in tension_curve.points:
        dist = abs(point.position - position)
        if dist < best_dist:
            best_dist = dist
            best_level = point.level

    return best_level


def _get_rhetoric_at_bar(rhetoric: RhetoricalStructure, bar: int) -> str:
    """Get rhetorical section at a specific bar."""
    for section in rhetoric.sections:
        if section.start_bar <= bar <= section.end_bar:
            return section.name
    return "narratio"


def _extract_devices(treatment: str) -> Tuple[str, ...]:
    """Extract device names from treatment string.

    Treatment format: "treatment_name[device1+device2]"
    """
    if "[" not in treatment:
        return ()

    start = treatment.index("[") + 1
    end = treatment.index("]")
    devices_str = treatment[start:end]

    if not devices_str:
        return ()

    return tuple(devices_str.split("+"))


def _is_phrase_end(
    bar: int,
    bar_to_phrase: Dict[int, Phrase],
    total_bars: int,
) -> bool:
    """Check if this bar is the last bar of its phrase."""
    if bar >= total_bars:
        return True

    current_phrase = bar_to_phrase.get(bar)
    next_phrase = bar_to_phrase.get(bar + 1)

    return current_phrase != next_phrase


def _determine_material(
    bc: BarConstraint,
    voice: int,
    material: Material,
    voices: int,
) -> Tuple[str, Optional[str]]:
    """Determine what material a voice should use.

    Returns (material_name, transform_or_none).
    """
    # Check callbacks first
    for callback in bc.callbacks:
        if callback.voice == voice:
            return callback.material, callback.transform

    # Default assignment based on voice and rhetoric
    if voice == 0:
        # Top voice usually has subject
        if bc.rhetoric_section in ["exordium", "peroratio"]:
            return "subject", None
        elif bc.rhetoric_section == "confutatio":
            return "subject", "invert"
        else:
            return "free", None

    elif voice == voices - 1:
        # Bass voice
        return "bass", None

    else:
        # Inner voices
        if material.counter_subject and bc.rhetoric_section != "exordium":
            return "counter_subject", None
        return "free", None


def _voice_to_register(voice: int, voices: int) -> str:
    """Map voice number to register."""
    if voices <= 2:
        return "high" if voice == 0 else "low"

    if voice == 0:
        return "high"
    elif voice == voices - 1:
        return "low"
    else:
        return "middle"


def _voice_to_texture(voice: int, voices: int, bc: BarConstraint) -> str:
    """Determine texture role for a voice."""
    if voice == 0:
        return "melody"
    elif voice == voices - 1:
        return "bass"
    else:
        return "accompaniment"


def format_constraints_yaml(constraints: PlanConstraints) -> str:
    """Format constraints as YAML for debugging/inspection."""
    lines = [
        "# Synthesized Constraints",
        f"total_bars: {constraints.total_bars}",
        f"voices: {constraints.voices}",
        f"key: {constraints.key}",
        f"mode: {constraints.mode}",
        f"metre: {constraints.metre}",
        f"tempo: {constraints.tempo}",
        "",
        "bar_constraints:",
    ]

    for bc in constraints.bar_constraints:
        lines.append(f"  - bar: {bc.bar}")
        lines.append(f"    key_area: {bc.key_area}")
        lines.append(f"    tension: {bc.tension:.2f}")
        lines.append(f"    rhetoric: {bc.rhetoric_section}")
        if bc.is_climax:
            lines.append("    is_climax: true")
        if bc.cadence:
            lines.append(f"    cadence: {bc.cadence}")
        if bc.devices:
            lines.append(f"    devices: [{', '.join(bc.devices)}]")

    return "\n".join(lines)

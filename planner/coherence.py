"""Coherence planning: long-range unity through callbacks and surprises.

Plans:
- Motivic callbacks (references to earlier material)
- Surprise devices (pauses, deceptive cadences, etc.)
- Structural proportions (golden ratio, climax placement)
"""
import math
from typing import Dict, List, Tuple

from planner.plannertypes import (
    Callback, Surprise, CoherencePlan, RhetoricalStructure, TensionCurve,
    Material, Structure
)


# Golden ratio for structural proportions
GOLDEN_RATIO = 1.618033988749895

# Surprise types with descriptions
SURPRISE_TYPES: Dict[str, str] = {
    "pause": "General pause (grand pause) - all voices rest",
    "deceptive_cadence": "Expected V-I resolves to vi or VI",
    "sudden_piano": "Sudden drop to piano dynamic",
    "sudden_forte": "Sudden forte after piano passage",
    "harmonic_shift": "Unexpected key change",
    "register_shift": "Sudden octave displacement",
    "texture_thin": "Sudden reduction to single voice",
    "augmentation": "Theme in longer note values",
    "stretto": "Overlapping entries of theme",
}


def plan_coherence(
    structure: Structure,
    material: Material,
    rhetoric: RhetoricalStructure,
    tension_curve: TensionCurve,
    total_bars: int,
    affect: str,
) -> CoherencePlan:
    """Plan long-range coherence for the piece.

    Args:
        structure: Planned structure
        material: Thematic material (subject, counter-subject, etc.)
        rhetoric: Rhetorical structure
        tension_curve: Tension curve
        total_bars: Total bars in piece
        affect: Target affect

    Returns:
        CoherencePlan with callbacks, surprises, and proportion analysis
    """
    # Plan callbacks
    callbacks = _plan_callbacks(structure=structure, material=material, rhetoric=rhetoric, total_bars=total_bars)

    # Plan surprises
    surprises = _plan_surprises(rhetoric=rhetoric, tension_curve=tension_curve, total_bars=total_bars, affect=affect)

    # Calculate golden ratio bar
    golden_bar = round(total_bars / GOLDEN_RATIO)

    # Calculate proportion score
    proportion_score = _calculate_proportion_score(
        climax_bar=rhetoric.climax_bar, golden_bar=golden_bar, total_bars=total_bars
    )

    return CoherencePlan(
        callbacks=tuple(callbacks),
        climax_bar=rhetoric.climax_bar,
        surprises=tuple(surprises),
        golden_ratio_bar=golden_bar,
        proportion_score=proportion_score,
    )


def _plan_callbacks(
    structure: Structure,
    material: Material,
    rhetoric: RhetoricalStructure,
    total_bars: int,
) -> List[Callback]:
    """Plan motivic callbacks for long-range coherence."""
    callbacks: List[Callback] = []

    # Get section boundaries for callback planning
    confirmatio_start = None
    peroratio_start = None

    for section in rhetoric.sections:
        if section.name == "confirmatio":
            confirmatio_start = section.start_bar
        elif section.name == "peroratio":
            peroratio_start = section.start_bar

    # Opening callback in confirmatio (recall of opening)
    if confirmatio_start and confirmatio_start > 4:
        callbacks.append(Callback(
            target_bar=confirmatio_start + 2,
            source_bar=1,
            transform="exact",
            voice=0,
            material="subject",
        ))

    # Inverted callback in confutatio (if piece is long enough)
    if total_bars >= 24:
        confutatio_mid = None
        for section in rhetoric.sections:
            if section.name == "confutatio":
                confutatio_mid = (section.start_bar + section.end_bar) // 2
                break

        if confutatio_mid:
            callbacks.append(Callback(
                target_bar=confutatio_mid,
                source_bar=1,
                transform="invert",
                voice=1,
                material="head_inverted",
            ))

    # Final callback in peroratio (triumphant return)
    if peroratio_start:
        callbacks.append(Callback(
            target_bar=peroratio_start,
            source_bar=1,
            transform="exact",
            voice=0,
            material="subject",
        ))

    # Counter-subject callback if we have one
    if material.counter_subject and total_bars >= 16:
        # Find a good spot in narratio
        for section in rhetoric.sections:
            if section.name == "narratio":
                cs_callback_bar = section.start_bar + 4
                if cs_callback_bar < section.end_bar:
                    callbacks.append(Callback(
                        target_bar=cs_callback_bar,
                        source_bar=section.start_bar,
                        transform="exact",
                        voice=1,
                        material="counter_subject",
                    ))
                break

    return callbacks


def _plan_surprises(
    rhetoric: RhetoricalStructure,
    tension_curve: TensionCurve,
    total_bars: int,
    affect: str,
) -> List[Surprise]:
    """Plan rhetorical surprises."""
    surprises: List[Surprise] = []

    # Surprise mapping by affect
    affect_surprises: Dict[str, List[str]] = {
        "Klage": ["pause", "deceptive_cadence", "sudden_piano"],
        "Sehnsucht": ["deceptive_cadence", "register_shift", "harmonic_shift"],
        "Freudigkeit": ["sudden_forte", "stretto", "register_shift"],
        "Majestaet": ["pause", "sudden_forte", "augmentation"],
        "Zaertlichkeit": ["sudden_piano", "texture_thin", "deceptive_cadence"],
        "Zorn": ["pause", "sudden_forte", "harmonic_shift"],
        "Verwunderung": ["pause", "harmonic_shift", "register_shift"],
        "Entschlossenheit": ["sudden_forte", "stretto", "augmentation"],
    }

    available = affect_surprises.get(affect, ["pause", "deceptive_cadence"])

    # Find high-tension moments for surprises
    high_tension_bars = []
    for point in tension_curve.points:
        if point.level >= 0.75:
            bar = round(point.position * total_bars)
            if 1 <= bar <= total_bars:
                high_tension_bars.append(bar)

    # Place surprises at tension peaks
    surprise_positions = high_tension_bars[:3]  # Max 3 surprises

    for i, bar in enumerate(surprise_positions):
        surprise_type = available[i % len(available)]
        surprises.append(Surprise(
            bar=bar,
            beat=1.0,  # First beat of bar
            type=surprise_type,
            duration=0.5 if surprise_type == "pause" else 2.0,
        ))

    # Always add a deceptive cadence before final cadence if appropriate
    if total_bars >= 12 and "deceptive_cadence" in available:
        # Find peroratio start
        for section in rhetoric.sections:
            if section.name == "peroratio":
                dc_bar = max(1, section.start_bar - 2)
                if dc_bar not in [s.bar for s in surprises]:
                    surprises.append(Surprise(
                        bar=dc_bar,
                        beat=3.0,  # Before expected cadence
                        type="deceptive_cadence",
                        duration=1.0,
                    ))
                break

    return surprises


def _calculate_proportion_score(
    climax_bar: int,
    golden_bar: int,
    total_bars: int,
) -> float:
    """Calculate how well proportions match ideal.

    Returns 1.0 if climax is exactly at golden ratio point,
    lower values for deviations.
    """
    if total_bars <= 0:
        return 0.0

    # Ideal: climax at golden ratio point
    deviation = abs(climax_bar - golden_bar)
    max_deviation = total_bars / 2

    # Score from 0 to 1
    score = 1.0 - (deviation / max_deviation)
    return max(0.0, min(1.0, score))


def get_callback_density(
    coherence: CoherencePlan,
    total_bars: int,
) -> float:
    """Get callbacks per bar (measure of motivic density)."""
    if total_bars <= 0:
        return 0.0
    return len(coherence.callbacks) / total_bars


def get_surprise_intensity(coherence: CoherencePlan) -> float:
    """Calculate overall surprise intensity (0-1)."""
    if not coherence.surprises:
        return 0.0

    # Weight surprises by their intensity
    intensity_weights = {
        "pause": 0.8,
        "deceptive_cadence": 0.6,
        "sudden_piano": 0.5,
        "sudden_forte": 0.7,
        "harmonic_shift": 0.9,
        "register_shift": 0.5,
        "texture_thin": 0.6,
        "augmentation": 0.4,
        "stretto": 0.7,
    }

    total_intensity = sum(
        intensity_weights.get(s.type, 0.5)
        for s in coherence.surprises
    )

    # Normalize to 0-1 range (assuming max ~3 surprises)
    return min(1.0, total_intensity / 3.0)

"""Load humanisation profiles from YAML files."""
from pathlib import Path
from typing import Any

import yaml

from humanisation.context.types import (
    ArticulationProfile,
    DynamicsProfile,
    HumanisationProfile,
    TimingProfile,
    DEFAULT_ARTICULATION,
    DEFAULT_DYNAMICS,
    DEFAULT_PROFILE,
    DEFAULT_TIMING,
)

DATA_DIR = Path(__file__).parent.parent / "data" / "humanisation"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML file, return empty dict if not found."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge override into base."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _build_timing_profile(data: dict[str, Any]) -> TimingProfile:
    """Build TimingProfile from dict, using defaults for missing values."""
    return TimingProfile(
        melodic_lead_ms=data.get("melodic_lead_ms", DEFAULT_TIMING.melodic_lead_ms),
        agogic_downbeat_ms=data.get("agogic_downbeat_ms", DEFAULT_TIMING.agogic_downbeat_ms),
        agogic_peak_ms=data.get("agogic_peak_ms", DEFAULT_TIMING.agogic_peak_ms),
        agogic_syncopation_ms=data.get("agogic_syncopation_ms", DEFAULT_TIMING.agogic_syncopation_ms),
        rubato_max_accel=data.get("rubato_max_accel", DEFAULT_TIMING.rubato_max_accel),
        rubato_max_decel=data.get("rubato_max_decel", DEFAULT_TIMING.rubato_max_decel),
        rubato_peak_position=data.get("rubato_peak_position", DEFAULT_TIMING.rubato_peak_position),
        rubato_cadence_start=data.get("rubato_cadence_start", DEFAULT_TIMING.rubato_cadence_start),
        stochastic_sigma=data.get("stochastic_sigma", DEFAULT_TIMING.stochastic_sigma),
        stochastic_theta=data.get("stochastic_theta", DEFAULT_TIMING.stochastic_theta),
        motor_interval_coef=data.get("motor_interval_coef", DEFAULT_TIMING.motor_interval_coef),
    )


def _build_dynamics_profile(data: dict[str, Any]) -> DynamicsProfile:
    """Build DynamicsProfile from dict, using defaults for missing values."""
    return DynamicsProfile(
        velocity_min=data.get("velocity_min", DEFAULT_DYNAMICS.velocity_min),
        velocity_max=data.get("velocity_max", DEFAULT_DYNAMICS.velocity_max),
        phrase_envelope_strength=data.get("phrase_envelope_strength", DEFAULT_DYNAMICS.phrase_envelope_strength),
        phrase_peak_position=data.get("phrase_peak_position", DEFAULT_DYNAMICS.phrase_peak_position),
        metric_weight_range=data.get("metric_weight_range", DEFAULT_DYNAMICS.metric_weight_range),
        harmonic_tension_boost=data.get("harmonic_tension_boost", DEFAULT_DYNAMICS.harmonic_tension_boost),
        contour_range=data.get("contour_range", DEFAULT_DYNAMICS.contour_range),
        voice_balance_melody=data.get("voice_balance_melody", DEFAULT_DYNAMICS.voice_balance_melody),
        voice_balance_thematic=data.get("voice_balance_thematic", DEFAULT_DYNAMICS.voice_balance_thematic),
        touch_variation=data.get("touch_variation", DEFAULT_DYNAMICS.touch_variation),
    )


def _build_articulation_profile(data: dict[str, Any]) -> ArticulationProfile:
    """Build ArticulationProfile from dict, using defaults for missing values."""
    return ArticulationProfile(
        default_gate=data.get("default_gate", DEFAULT_ARTICULATION.default_gate),
        legato_gate=data.get("legato_gate", DEFAULT_ARTICULATION.legato_gate),
        staccato_gate=data.get("staccato_gate", DEFAULT_ARTICULATION.staccato_gate),
        phrase_end_gate=data.get("phrase_end_gate", DEFAULT_ARTICULATION.phrase_end_gate),
        fast_passage_gate=data.get("fast_passage_gate", DEFAULT_ARTICULATION.fast_passage_gate),
        notes_inegales_ratio=data.get("notes_inegales_ratio", DEFAULT_ARTICULATION.notes_inegales_ratio),
        notes_inegales_threshold=data.get("notes_inegales_threshold", DEFAULT_ARTICULATION.notes_inegales_threshold),
    )


def load_profile(instrument: str, style: str) -> HumanisationProfile:
    """Load and merge instrument and style profiles.

    Style values override instrument defaults where specified.

    Args:
        instrument: Instrument name (harpsichord, piano, clavichord)
        style: Style name (baroque, galant)

    Returns:
        Merged HumanisationProfile
    """
    instrument_path = DATA_DIR / "instruments" / f"{instrument}.yaml"
    style_path = DATA_DIR / "styles" / f"{style}.yaml"

    instrument_data = _load_yaml(instrument_path)
    style_data = _load_yaml(style_path)

    # If neither file exists, return default
    if not instrument_data and not style_data:
        return DEFAULT_PROFILE

    # Merge style over instrument
    merged = _merge_dicts(instrument_data, style_data)

    # Build profiles from merged data
    timing_data = merged.get("timing", {})
    dynamics_data = merged.get("dynamics", {})
    articulation_data = merged.get("articulation", {})

    timing = _build_timing_profile(timing_data)
    dynamics = _build_dynamics_profile(dynamics_data)
    articulation = _build_articulation_profile(articulation_data)

    # Determine enabled models
    enabled = merged.get("enabled_models", ["timing", "dynamics", "articulation"])

    name = f"{instrument}_{style}"

    return HumanisationProfile(
        name=name,
        timing=timing,
        dynamics=dynamics,
        articulation=articulation,
        enabled_models=tuple(enabled),
    )

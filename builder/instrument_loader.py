"""Instrument definition loader.

Loads instrument definitions from data/instruments/*.yaml and resolves
voice ranges via scoring assignments per voices.md.
"""
from pathlib import Path
from typing import Any

import yaml

from builder.types import Actuator, InstrumentDef, Range


_INSTRUMENT_CACHE: dict[str, InstrumentDef] = {}
_INSTRUMENTS_DIR: Path = Path(__file__).parent.parent / "data" / "instruments"


def _load_instrument(name: str) -> InstrumentDef:
    """Load instrument definition from YAML."""
    if name in _INSTRUMENT_CACHE:
        return _INSTRUMENT_CACHE[name]
    path = _INSTRUMENTS_DIR / f"{name}.yaml"
    assert path.exists(), f"Instrument definition not found: {path}"
    with open(path) as f:
        data: dict[str, Any] = yaml.safe_load(f)
    actuators: list[Actuator] = []
    for act_data in data.get("actuators", []):
        act_name: str = act_data["name"]
        range_data = act_data["range"]
        actuators.append(Actuator(
            id=act_name,
            range=Range(low=range_data[0], high=range_data[1]),
        ))
    instrument = InstrumentDef(
        id=data.get("name", name),
        actuators=tuple(actuators),
    )
    _INSTRUMENT_CACHE[name] = instrument
    return instrument


def get_actuator_range(
    instrument_type: str,
    actuator_id: str,
) -> Range:
    """Get range for a specific actuator on an instrument type."""
    instrument = _load_instrument(instrument_type)
    for actuator in instrument.actuators:
        if actuator.id == actuator_id:
            return actuator.range
    raise ValueError(f"Actuator '{actuator_id}' not found on instrument '{instrument_type}'")


def resolve_voice_range(
    voice_id: str,
    scoring: dict[str, str],
    instruments: dict[str, str],
) -> Range:
    """Resolve voice range via scoring assignment.
    
    Args:
        voice_id: Voice identifier (e.g., "upper", "lower")
        scoring: voice_id -> "instrument.actuator" mapping
        instruments: instrument_id -> instrument_type mapping
        
    Returns:
        Range for the voice based on its assigned actuator.
        
    Example:
        scoring = {"upper": "keyboard.right_hand"}
        instruments = {"keyboard": "harpsichord"}
        resolve_voice_range("upper", scoring, instruments)
        -> Range(low=53, high=89)
    """
    assert voice_id in scoring, f"Voice '{voice_id}' not in scoring: {list(scoring.keys())}"
    assignment = scoring[voice_id]
    parts = assignment.split(".")
    assert len(parts) == 2, f"Invalid scoring format '{assignment}', expected 'instrument.actuator'"
    instrument_id, actuator_id = parts
    assert instrument_id in instruments, f"Instrument '{instrument_id}' not defined"
    instrument_type = instruments[instrument_id]
    return get_actuator_range(instrument_type, actuator_id)


def get_default_two_voice_ranges() -> dict[int, tuple[int, int]]:
    """Get default ranges for two-voice texture (backward compatibility).
    
    Uses harpsichord right_hand/left_hand as default for invention.
    Voice 0 = upper (right hand), Voice 1 = lower (left hand).
    """
    rh = get_actuator_range("harpsichord", "right_hand")
    lh = get_actuator_range("harpsichord", "left_hand")
    return {
        0: (rh.low, rh.high),
        1: (lh.low, lh.high),
    }


def get_default_four_voice_ranges() -> dict[int, tuple[int, int]]:
    """Get default ranges for four-voice texture (backward compatibility).
    
    Uses piano ranges as approximation for SATB.
    """
    rh = get_actuator_range("piano", "right_hand")
    lh = get_actuator_range("piano", "left_hand")
    return {
        0: (60, 81),   # Soprano: C4 to A5 (subset of RH)
        1: (53, 72),   # Alto: F3 to C5
        2: (48, 67),   # Tenor: C3 to G4
        3: (lh.low, 62),  # Bass: LH low to D4
    }

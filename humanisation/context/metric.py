"""Metric context analyzer for humanisation."""
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml

from engine.note import Note
from humanisation.context.types import MetricContext

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "humanisation"


def _load_metric_weights() -> dict[str, Any]:
    """Load metric weights from YAML."""
    path = DATA_DIR / "metric_weights.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _get_bar_duration(metre: str) -> float:
    """Get bar duration in whole notes from metre string."""
    parts = metre.split("/")
    if len(parts) != 2:
        return 1.0
    num, den = int(parts[0]), int(parts[1])
    return num / den


def _get_metric_weight(beat_pos: float, metre: str, weights_data: dict[str, Any]) -> float:
    """Get metric weight for a beat position.

    Args:
        beat_pos: Position within bar (0.0 to bar_duration)
        metre: Time signature string (e.g., "4/4")
        weights_data: Loaded metric weights data

    Returns:
        Metric weight from 0.0 to 1.0
    """
    metre_data = weights_data.get(metre, {})
    beats = metre_data.get("beats", {})
    subdivisions = metre_data.get("subdivisions", {})

    # Normalize beat_pos to be within one bar
    bar_dur = metre_data.get("bar_duration", _get_bar_duration(metre))
    beat_pos = beat_pos % bar_dur

    # Check exact beat matches first
    for pos_str, weight in beats.items():
        pos = float(pos_str)
        if abs(beat_pos - pos) < 0.001:
            return weight

    # Check subdivisions
    for subdiv_str, weight in subdivisions.items():
        subdiv = float(subdiv_str)
        # Check if beat_pos is on this subdivision grid
        if subdiv > 0:
            remainder = beat_pos % subdiv
            if abs(remainder) < 0.001 or abs(remainder - subdiv) < 0.001:
                return weight

    # Default: interpolate between beats or use low weight
    return 0.15


def _detect_syncopation(
    note: Note,
    metric_weight: float,
    note_duration: float,
    metre: str,
) -> bool:
    """Detect if a note is syncopated.

    A note is syncopated if:
    1. It's on a weak beat (low metric weight)
    2. Its duration extends past a stronger beat
    """
    # Short notes on weak beats with duration extending past beat
    if metric_weight < 0.5 and note_duration > 0.125:
        return True

    # Notes starting off-beat but lasting through downbeat
    bar_dur = _get_bar_duration(metre)
    beat_pos = note.Offset % bar_dur
    if beat_pos > 0.01 and note_duration > (bar_dur - beat_pos):
        return True

    return False


def _get_beat_subdivision(beat_pos: float, bar_dur: float) -> int:
    """Determine beat subdivision level.

    Returns:
        1 = on main beat, 2 = half beat, 4 = quarter, 8 = eighth, etc.
    """
    # Check common subdivisions
    for subdiv in [1, 2, 4, 8, 16]:
        grid = bar_dur / subdiv
        remainder = beat_pos % grid
        if abs(remainder) < 0.001 or abs(remainder - grid) < 0.001:
            return subdiv

    return 16  # Very fine subdivision


def analyze_metric(notes: list[Note], metre: str) -> list[MetricContext]:
    """Analyze metric context for each note.

    Uses Lerdahl & Jackendoff metric well-formedness rules to compute
    metric weight for each note based on its position within the bar.

    Args:
        notes: List of Note objects
        metre: Time signature string (e.g., "4/4")

    Returns:
        List of MetricContext, one per note
    """
    if not notes:
        return []

    weights_data = _load_metric_weights()
    bar_dur = _get_bar_duration(metre)

    contexts: list[MetricContext] = []
    for note in notes:
        # Position within bar
        beat_pos = note.Offset % bar_dur
        bar_position = beat_pos / bar_dur

        # Get metric weight
        metric_weight = _get_metric_weight(beat_pos, metre, weights_data)

        # Is this a downbeat?
        is_downbeat = abs(beat_pos) < 0.01

        # Detect syncopation
        is_syncopation = _detect_syncopation(note, metric_weight, note.Duration, metre)

        # Get beat subdivision
        beat_subdivision = _get_beat_subdivision(beat_pos, bar_dur)

        contexts.append(MetricContext(
            metric_weight=metric_weight,
            is_downbeat=is_downbeat,
            is_syncopation=is_syncopation,
            beat_subdivision=beat_subdivision,
            bar_position=bar_position,
        ))

    return contexts

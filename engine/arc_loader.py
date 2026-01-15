"""Arc loader: parses arcs.yaml with voice_entries.

Provides typed access to arc definitions including N-voice entries.
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from engine.voice_config import VoiceSet
from engine.voice_entry import ArcVoiceEntries, VoiceTreatmentSpec


DATA_DIR: Path = Path(__file__).parent.parent / "data"
_ARCS: dict = yaml.safe_load(open(DATA_DIR / "arcs.yaml", encoding="utf-8"))


@dataclass(frozen=True)
class ArcDefinition:
    """Parsed arc definition with voice entries."""
    name: str
    voice_count: int
    treatments: tuple[str, ...]
    climax: str | None
    surprise: str | None
    surprise_type: str | None
    voice_entries: ArcVoiceEntries

    @property
    def has_explicit_entries(self) -> bool:
        return self.voice_entries.has_explicit_entries()


def voice_names_for_count(n: int) -> tuple[str, ...]:
    """Get standard voice names for N voices."""
    if n == 2:
        return ("soprano", "bass")
    if n == 3:
        return ("soprano", "alto", "bass")
    if n == 4:
        return ("soprano", "alto", "tenor", "bass")
    raise ValueError(f"Unsupported voice count: {n}")


def load_arc(arc_name: str) -> ArcDefinition:
    """Load and parse arc definition."""
    assert arc_name in _ARCS, f"Unknown arc: {arc_name}"
    arc: dict = _ARCS[arc_name]
    voice_count: int = arc.get("voices", 2)
    treatments: tuple[str, ...] = tuple(arc.get("treatments", []))
    climax: str | None = arc.get("climax")
    surprise: str | None = arc.get("surprise")
    surprise_type: str | None = arc.get("surprise_type")
    voice_names: tuple[str, ...] = voice_names_for_count(voice_count)
    entries_list: list[dict] = arc.get("voice_entries", [])
    if entries_list:
        voice_entries: ArcVoiceEntries = ArcVoiceEntries.from_list(
            entries_list, voice_count, voice_names
        )
    else:
        voice_entries = ArcVoiceEntries.empty(voice_count)
    return ArcDefinition(
        name=arc_name,
        voice_count=voice_count,
        treatments=treatments,
        climax=climax,
        surprise=surprise,
        surprise_type=surprise_type,
        voice_entries=voice_entries,
    )


def get_arc_voice_count(arc_name: str) -> int:
    """Get voice count for arc without full parse."""
    assert arc_name in _ARCS, f"Unknown arc: {arc_name}"
    return _ARCS[arc_name].get("voices", 2)


def get_default_treatment_for_voice(
    phrase_index: int,
    voice_index: int,
    voice_count: int,
    arc_treatments: tuple[str, ...],
) -> VoiceTreatmentSpec:
    """Get default treatment when no explicit voice_entry.

    Baroque 4-voice fugal convention with staggered entries:
    - Soprano (0): subject, no delay
    - Alto (1): subject at 4th below, delay 1/2 bar (or counter_subject)
    - Tenor (2): counter_subject, delay 1 bar (or subject at 5th below)
    - Bass (n-1): subject at lower interval

    Staggered entries prevent parallel motion between voices.
    """
    from fractions import Fraction
    is_outer: bool = voice_index == 0 or voice_index == voice_count - 1
    if is_outer:
        treatment_idx: int = phrase_index % len(arc_treatments) if arc_treatments else 0
        treatment: str = arc_treatments[treatment_idx] if arc_treatments else "statement"
        source: str = "subject"
        interval: int = -7 if voice_index == voice_count - 1 else 0  # Bass at octave below
        return VoiceTreatmentSpec(treatment=treatment, source=source, interval=interval, delay=Fraction(0))
    if voice_count == 4:
        if voice_index == 1:  # Alto - enters after soprano
            use_cs: bool = phrase_index % 2 == 1
            source = "counter_subject" if use_cs else "subject"
            interval: int = -3 if not use_cs else 0
            delay: Fraction = Fraction(1, 2)  # Half-bar delay
            return VoiceTreatmentSpec(treatment="imitation", source=source, interval=interval, delay=delay)
        if voice_index == 2:  # Tenor - enters after alto
            use_cs = phrase_index % 2 == 0
            source = "counter_subject" if use_cs else "subject"
            interval = -4 if not use_cs else -7
            delay = Fraction(1)  # One-bar delay
            return VoiceTreatmentSpec(treatment="imitation", source=source, interval=interval, delay=delay)
    if voice_count == 3 and voice_index == 1:  # Alto in 3-voice
        source = "counter_subject" if phrase_index % 2 == 1 else "subject"
        interval = -3 if source == "subject" else 0
        delay = Fraction(1, 2)
        return VoiceTreatmentSpec(treatment="imitation", source=source, interval=interval, delay=delay)
    return VoiceTreatmentSpec.rest()

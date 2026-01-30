"""Per-bar context computation for figuration."""
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import yaml

from builder.figuration.types import PhrasePosition
from builder.types import Anchor, PassageAssignment, Role


_SCHEMA_TEXTURES: dict[str, str] | None = None
_SCHEMA_CADENCE_APPROACH: dict[str, bool] | None = None


def _load_schema_data() -> tuple[dict[str, str], dict[str, bool]]:
    """Load schema properties from schemas.yaml (cached)."""
    global _SCHEMA_TEXTURES, _SCHEMA_CADENCE_APPROACH
    if _SCHEMA_TEXTURES is not None and _SCHEMA_CADENCE_APPROACH is not None:
        return _SCHEMA_TEXTURES, _SCHEMA_CADENCE_APPROACH
    path = Path(__file__).parent.parent.parent / "data" / "schemas" / "schemas.yaml"
    if not path.exists():
        _SCHEMA_TEXTURES = {}
        _SCHEMA_CADENCE_APPROACH = {}
        return _SCHEMA_TEXTURES, _SCHEMA_CADENCE_APPROACH
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    textures: dict[str, str] = {}
    cadence_approach: dict[str, bool] = {}
    for name, schema_data in data.items():
        if isinstance(schema_data, dict):
            if "accompany_texture" in schema_data:
                textures[name] = schema_data["accompany_texture"]
            if "cadence_approach" in schema_data:
                cadence_approach[name] = schema_data["cadence_approach"]
    _SCHEMA_TEXTURES = textures
    _SCHEMA_CADENCE_APPROACH = cadence_approach
    return _SCHEMA_TEXTURES, _SCHEMA_CADENCE_APPROACH


def _load_schema_textures() -> dict[str, str]:
    """Load accompany_texture defaults from schemas.yaml (cached)."""
    textures, _ = _load_schema_data()
    return textures


def get_schema_texture(schema_name: str | None) -> str | None:
    """Get accompany_texture default for a schema."""
    if schema_name is None:
        return None
    textures = _load_schema_textures()
    return textures.get(schema_name.lower())


def get_schema_cadence_approach(schema_name: str | None) -> bool:
    """Check if schema has cadence_approach: true."""
    if schema_name is None:
        return False
    _, cadence_approach = _load_schema_data()
    return cadence_approach.get(schema_name.lower(), False)


def compute_harmonic_tension(
    anchor_a: Anchor,
    phrase_pos: PhrasePosition,
    role: Role,
) -> str:
    """Compute harmonic tension from schema type, bass degree, and bar function."""
    if phrase_pos.position == "cadence":
        base_tension = "low"
    elif phrase_pos.position == "continuation":
        base_tension = "medium"
    else:
        base_tension = "low"
    bass = anchor_a.lower_degree
    if bass in (2, 4, 7):
        if base_tension == "low":
            return "medium"
        return "high"
    if bass in (5,):
        return "medium"
    schema = anchor_a.schema.lower() if anchor_a.schema else ""
    if schema in ("monte", "fonte"):
        return "medium"
    return base_tension


def compute_bar_function(phrase_pos: PhrasePosition, bar_num: int, total_bars: int) -> str:
    """Compute bar function for rhythm realisation."""
    if phrase_pos.position == "cadence":
        return "cadential"
    if phrase_pos.sequential:
        return "schema_arrival"
    if bar_num == total_bars - 2:
        return "preparatory"
    return "passing"


def compute_next_anchor_strength(
    idx: int,
    anchors: Sequence[Anchor],
    total_bars: int,
) -> str:
    """Compute strength of next anchor for anacrusis handling."""
    if idx + 2 >= len(anchors):
        return "strong"
    next_bar = _parse_bar_beat(anchors[idx + 1].bar_beat)[0]
    if next_bar == 1 or next_bar == (total_bars // 2) + 1:
        return "strong"
    if next_bar >= total_bars - 1:
        return "strong"
    return "weak"


def should_use_hemiola(bar_num: int, total_bars: int, metre: str, deformation: str | None) -> bool:
    """Determine if hemiola should be used for this bar."""
    if metre != "3/4":
        return False
    if total_bars < 6:
        return False
    hemiola_bar = total_bars - 2
    if bar_num == hemiola_bar or bar_num == hemiola_bar + 1:
        if deformation == "early_cadence":
            return False
        return True
    return False


def should_use_overdotted(affect_character: str, phrase_pos: PhrasePosition) -> bool:
    """Determine if overdotted rhythms should be used."""
    return affect_character == "ornate"


def get_accompany_texture_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
    schema_texture: str | None = None,
) -> str:
    """Look up accompany texture for a given bar.

    Cascade: section override → schema default → "walking"

    Args:
        bar: Bar number
        assignments: Passage assignments (may have accompany_texture)
        schema_texture: Default from schema YAML

    Returns:
        One of: "pillar", "walking", "staggered", "complementary"
    """
    if assignments is not None:
        for assignment in assignments:
            if assignment.start_bar <= bar <= assignment.end_bar:
                if assignment.accompany_texture is not None:
                    return assignment.accompany_texture
                break
    if schema_texture is not None:
        return schema_texture
    return "walking"


def get_lead_voice_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> int | None:
    """Look up lead voice for a given bar number.

    Returns:
        0 if soprano leads, 1 if bass leads, None if equal.
    """
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.lead_voice
    return None


def compute_beat_class(
    voice: str,
    bar: int,
    passage_assignments: Sequence[PassageAssignment] | None,
) -> int:
    """Compute which beat this voice starts on for a given bar."""
    lead_voice = get_lead_voice_for_bar(bar, passage_assignments)
    voice_index = 0 if voice == "soprano" else 1
    if lead_voice is None:
        return 1  # Equal: both on beat 1
    if lead_voice == voice_index:
        return 1  # This voice leads
    return 2  # This voice accompanies


def compute_effective_gap(
    gap_duration: Fraction,
    start_beat: int,
    metre: str,
) -> Fraction:
    """Compute effective gap duration based on start beat.

    When voice starts on beat 2, reduce available duration by the delay.
    """
    if start_beat <= 1:
        return gap_duration
    parts = metre.split("/")
    beat_value = Fraction(1, int(parts[1]))
    delay = (start_beat - 1) * beat_value
    return gap_duration - delay


def reduce_density(density: str) -> str:
    """Reduce density by one level for accompanying voice."""
    if density == "high":
        return "medium"
    return "low"


def is_motor_context(
    bar: int,
    schema_sections: list[tuple[int, int]],
    anchors: Sequence[Anchor],
) -> bool:
    """Determine if this bar is within a motor rhythm context.

    Motor rhythm continues within schema sections.

    Args:
        bar: Current bar number
        schema_sections: List of (start_idx, end_idx) for schema sections
        anchors: Full anchor sequence

    Returns:
        True if bass should use continuous motor rhythm.
    """
    for start_idx, end_idx in schema_sections:
        if start_idx < len(anchors) and end_idx <= len(anchors):
            start_bar_beat = anchors[start_idx].bar_beat
            end_bar_beat = anchors[end_idx - 1].bar_beat
            start_bar = int(start_bar_beat.split(".")[0])
            end_bar = int(end_bar_beat.split(".")[0])
            if start_bar <= bar <= end_bar:
                return True
    return False


def should_generate_anacrusis(
    bar: int,
    voice: str,
    passage_assignments: Sequence[PassageAssignment] | None,
) -> bool:
    """Determine if anacrusis should be generated for this bar.

    Anacrusis is generated when:
    - This voice is accompanying (beat class = 2)
    - The passage function is 'subject' or 'answer'

    Args:
        bar: Bar number
        voice: "soprano" or "bass"
        passage_assignments: Passage assignments

    Returns:
        True if anacrusis should be generated.
    """
    if passage_assignments is None:
        return False
    beat_class = compute_beat_class(voice, bar, passage_assignments)
    if beat_class != 2:
        return False
    function = _get_function_for_bar(bar, passage_assignments)
    return function in ("subject", "answer")


def _get_function_for_bar(
    bar: int,
    assignments: Sequence[PassageAssignment] | None,
) -> str | None:
    """Look up passage function for a given bar number."""
    if assignments is None:
        return None
    for assignment in assignments:
        if assignment.start_bar <= bar <= assignment.end_bar:
            return assignment.function
    return None


def _parse_bar_beat(bar_beat: str) -> tuple[int, float]:
    """Parse bar.beat string into (bar, beat) tuple."""
    parts = bar_beat.split(".")
    bar = int(parts[0])
    beat = float(parts[1]) if len(parts) > 1 else 1.0
    return (bar, beat)

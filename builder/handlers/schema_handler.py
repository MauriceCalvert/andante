"""Schema-level voice generation.

Processes SchemaSlot nodes from schema-based plans, converting schema
definitions into voiced bars with soprano and bass from schema degrees.
"""
from fractions import Fraction
from typing import Any

from builder.domain.schema_ops import get_schema, stretch_schema, degrees_to_diatonic
from builder.handlers.core import elaborate
from builder.solver import generate_voice_cpsat, load_pattern, get_default_pattern, Pattern
from builder.tree import Node, yaml_to_tree
from builder.types import Notes
from shared.constants import DIATONIC_DEFAULTS

DEGREE_TO_CHORD: dict[int, str] = {
    1: "I", 2: "ii", 3: "iii", 4: "IV", 5: "V", 6: "vi", 7: "viio"
}


def build_schema_slot(
    schema_node: Node,
    section_node: Node,
    bar_duration: Fraction,
    voice_count: int,
    metre: str,
) -> Node:
    """Build a schema slot into bars with voices.

    Args:
        schema_node: Node with type, bars, texture, treatment, voice_entry, cadence
        section_node: Parent section node
        bar_duration: Duration of one bar
        voice_count: Number of voices (2, 3, or 4)
        metre: Metre string (e.g., "4/4")

    Returns:
        Node with bars containing voiced notes
    """
    # Extract schema slot fields
    schema_type: str = schema_node["type"].value
    target_bars: int = schema_node["bars"].value
    texture: str = schema_node["texture"].value
    treatment: str = schema_node["treatment"].value
    voice_entry: str = schema_node["voice_entry"].value
    cadence: str | None = schema_node["cadence"].value if "cadence" in schema_node else None

    # Load and stretch schema
    schema = get_schema(schema_type)
    stretched = stretch_schema(schema, target_bars)

    # Realise outer voices
    soprano, bass = _realise_voices(stretched, texture)

    # Derive harmony from bass degrees
    harmony: tuple[str, ...] = _bass_to_harmony(
        stretched["bass_degrees"],
        stretched["durations"],
        bar_duration,
    )

    # Build phrase-like structure for compatibility with existing handlers
    phrase_data: dict[str, Any] = {
        "treatment": treatment,
        "texture": texture,
        "voice_entry": voice_entry,
        "schema_type": schema_type,
        "bars_count": target_bars,
    }
    if cadence:
        phrase_data["cadence"] = cadence

    phrase_node: Node | None = yaml_to_tree(phrase_data, key="schema_phrase", parent=section_node)
    assert phrase_node is not None

    # Add soprano as melody
    phrase_with_voices = _add_voice_to_node(phrase_node, "melody", soprano)

    # Generate bass and inner voices using CP-SAT
    if voice_count >= 2:
        bass_pattern: Pattern = load_pattern(get_default_pattern("bass"), metre, "bass")
        bass_notes: Notes = generate_voice_cpsat([soprano], harmony, "bass", bar_duration, bass_pattern)
        phrase_with_voices = _add_voice_to_node(phrase_with_voices, "bass", bass_notes)

        if voice_count >= 3:
            alto_pattern: Pattern = load_pattern(get_default_pattern("alto"), metre, "alto")
            alto: Notes = generate_voice_cpsat([soprano, bass_notes], harmony, "alto", bar_duration, alto_pattern)
            phrase_with_voices = _add_voice_to_node(phrase_with_voices, "alto", alto)

            if voice_count >= 4:
                tenor_pattern: Pattern = load_pattern(get_default_pattern("tenor"), metre, "tenor")
                tenor: Notes = generate_voice_cpsat(
                    [soprano, bass_notes, alto], harmony, "tenor", bar_duration, tenor_pattern
                )
                phrase_with_voices = _add_voice_to_node(phrase_with_voices, "tenor", tenor)

    # Create bars
    bars_data: list[dict[str, Any]] = []
    for bar_idx in range(target_bars):
        bars_data.append({
            "bar_index": bar_idx,
            "voices": _create_voices_stub(voice_count),
        })

    bars_node: Node | None = yaml_to_tree(bars_data, key="bars", parent=phrase_with_voices)
    assert bars_node is not None
    built_bars: Node = elaborate(bars_node)

    results: list[Node] = list(phrase_with_voices.children) + [built_bars]
    return phrase_with_voices.with_children(tuple(results))


def _realise_voices(
    schema: dict,
    texture: str,
) -> tuple[Notes, Notes]:
    """Realise soprano and bass from schema degrees.

    Args:
        schema: Stretched schema with bass_degrees, soprano_degrees, durations
        texture: Texture type (imitative, melody_bass, homophonic)

    Returns:
        (soprano_notes, bass_notes)
    """
    soprano_octave: int = DIATONIC_DEFAULTS["soprano"] // 7
    bass_octave: int = DIATONIC_DEFAULTS["bass"] // 7

    soprano_pitches, soprano_durs = degrees_to_diatonic(
        schema["soprano_degrees"],
        schema["durations"],
        soprano_octave,
    )
    bass_pitches, bass_durs = degrees_to_diatonic(
        schema["bass_degrees"],
        schema["durations"],
        bass_octave,
    )

    soprano = Notes(soprano_pitches, soprano_durs)
    bass = Notes(bass_pitches, bass_durs)

    return soprano, bass


def _bass_to_harmony(
    bass_degrees: list,
    durations: list[Fraction],
    bar_duration: Fraction,
) -> tuple[str, ...]:
    """Derive one chord per bar from bass degrees.

    Args:
        bass_degrees: List of scale degrees (1-7) or dicts
        durations: List of durations
        bar_duration: Duration of one bar

    Returns:
        Tuple of Roman numeral chord symbols, one per bar
    """
    from builder.domain.schema_ops import extract_degree

    harmony: list[str] = []
    pos = Fraction(0)

    for degree, dur in zip(bass_degrees, durations):
        bar_idx = int(pos // bar_duration)
        if bar_idx >= len(harmony):
            deg, _ = extract_degree(degree)
            # Normalize degree to 1-7 range
            deg_normalized = ((deg - 1) % 7) + 1
            harmony.append(DEGREE_TO_CHORD.get(deg_normalized, "I"))
        pos += dur

    return tuple(harmony)


def _add_voice_to_node(node: Node, key: str, notes: Notes) -> Node:
    """Add a voice's notes to a node."""
    voice_data: dict[str, Any] = {
        "pitches": list(notes.pitches),
        "durations": [str(d) for d in notes.durations],
    }
    voice_node: Node | None = yaml_to_tree(voice_data, key=key, parent=node)
    return node.with_children(tuple(node.children) + (voice_node,))


def _create_voices_stub(voice_count: int) -> list[dict[str, str]]:
    """Create stub voice data."""
    assert 1 <= voice_count <= 4, f"voice_count must be 1-4, got {voice_count}"
    roles: list[str] = ["soprano", "bass", "alto", "tenor"][:voice_count]
    return [{"role": role} for role in roles]

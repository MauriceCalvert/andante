"""Schema-level voice generation.

Processes SchemaSlot nodes from schema-based plans, converting schema
definitions into voiced bars with soprano and bass from schema degrees.
Key area transposition is applied via the transpose module.
"""
from fractions import Fraction
from typing import Any

from builder.domain.schema_ops import get_schema, tile_schema, degrees_to_diatonic
from builder.domain.transpose import get_key_area_offset, transpose_degrees
from builder.handlers.core import elaborate
from builder.solver import generate_voice_cpsat, load_pattern, get_default_pattern, Pattern
from builder.tree import Node, yaml_to_tree
from builder.types import Notes
from shared.constants import DEGREE_TO_CHORD, DIATONIC_DEFAULTS


def build_schema_slot(
    schema_node: Node,
    section_node: Node,
    bar_duration: Fraction,
    voice_count: int,
    metre: str,
) -> Node:
    """Build a schema slot into bars with voices.

    Args:
        schema_node: Node with type, bars, texture, treatment, dux_voice, cadence
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
    dux_voice: str = schema_node["dux_voice"].value
    cadence: str | None = schema_node["cadence"].value if "cadence" in schema_node else None
    key_area: str = schema_node["key_area"].value if "key_area" in schema_node else "I"

    # Get key area offset for transposition
    key_area_offset: int = get_key_area_offset(key_area)

    # Load and tile schema (pure tiling, not stretching)
    schema = get_schema(schema_type)
    repetitions = target_bars // schema.get("bars", 1)
    tiled = tile_schema(schema, repetitions)

    # Realise outer voices with key area transposition
    soprano, bass = _realise_voices(tiled, texture, key_area_offset)

    # Derive harmony from bass degrees (transposed)
    harmony: tuple[str, ...] = _bass_to_harmony(
        tiled["bass_degrees"],
        tiled["durations"],
        bar_duration,
        key_area_offset,
    )

    # Build phrase-like structure for compatibility with existing handlers
    phrase_data: dict[str, Any] = {
        "treatment": treatment,
        "texture": texture,
        "dux_voice": dux_voice,
        "schema_type": schema_type,
        "bars_count": target_bars,
    }
    if cadence:
        phrase_data["cadence"] = cadence

    phrase_node: Node | None = yaml_to_tree(phrase_data, key="schema_phrase", parent=section_node)
    assert phrase_node is not None

    # Add soprano as melody
    phrase_with_voices = _add_voice_to_node(phrase_node, "melody", soprano)

    # Extract bass targets from schema for CP-SAT constraints
    bass_targets: list[tuple[Fraction, int]] = _extract_bass_targets(
        tiled["bass_degrees"],
        tiled["durations"],
        key_area_offset,
    )

    # Generate bass and inner voices using CP-SAT with key area offset
    if voice_count >= 2:
        bass_pattern: Pattern = load_pattern(get_default_pattern("bass"), metre, "bass")
        bass_notes: Notes = generate_voice_cpsat(
            [soprano], harmony, "bass", bar_duration, bass_pattern,
            key_area_offset=key_area_offset,
            schema_targets=bass_targets,
        )
        phrase_with_voices = _add_voice_to_node(phrase_with_voices, "bass", bass_notes)

        if voice_count >= 3:
            alto_pattern: Pattern = load_pattern(get_default_pattern("alto"), metre, "alto")
            alto: Notes = generate_voice_cpsat(
                [soprano, bass_notes], harmony, "alto", bar_duration, alto_pattern,
                key_area_offset=key_area_offset,
            )
            phrase_with_voices = _add_voice_to_node(phrase_with_voices, "alto", alto)

            if voice_count >= 4:
                tenor_pattern: Pattern = load_pattern(get_default_pattern("tenor"), metre, "tenor")
                tenor: Notes = generate_voice_cpsat(
                    [soprano, bass_notes, alto], harmony, "tenor", bar_duration, tenor_pattern,
                    key_area_offset=key_area_offset,
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
    key_area_offset: int = 0,
) -> tuple[Notes, Notes]:
    """Realise soprano and bass from schema degrees with key area transposition.

    Args:
        schema: Tiled schema with bass_degrees, soprano_degrees, durations
        texture: Texture type (imitative, melody_bass, homophonic)
        key_area_offset: Diatonic degree offset for key area transposition

    Returns:
        (soprano_notes, bass_notes)
    """
    soprano_octave: int = DIATONIC_DEFAULTS["soprano"] // 7
    bass_octave: int = DIATONIC_DEFAULTS["bass"] // 7

    # Transpose degrees if not in tonic
    soprano_degrees = schema["soprano_degrees"]
    bass_degrees = schema["bass_degrees"]

    if key_area_offset != 0:
        # Extract plain degrees for transposition
        soprano_degrees = [_extract_plain_degree(d) for d in soprano_degrees]
        bass_degrees = [_extract_plain_degree(d) for d in bass_degrees]

        # Transpose to key area
        soprano_degrees = transpose_degrees(soprano_degrees, _offset_to_area(key_area_offset))
        bass_degrees = transpose_degrees(bass_degrees, _offset_to_area(key_area_offset))

    soprano_pitches, soprano_durs = degrees_to_diatonic(
        soprano_degrees,
        schema["durations"],
        soprano_octave,
    )
    bass_pitches, bass_durs = degrees_to_diatonic(
        bass_degrees,
        schema["durations"],
        bass_octave,
    )

    soprano = Notes(soprano_pitches, soprano_durs)
    bass = Notes(bass_pitches, bass_durs)

    return soprano, bass


def _extract_plain_degree(d: int | dict) -> int:
    """Extract plain degree from degree spec."""
    if isinstance(d, dict):
        return d["degree"]
    return d


def _offset_to_area(offset: int) -> str:
    """Convert key area offset to Roman numeral."""
    offset_to_area = {0: "I", 1: "ii", 2: "iii", 3: "IV", 4: "V", 5: "vi", 6: "vii"}
    return offset_to_area.get(offset % 7, "I")


def _bass_to_harmony(
    bass_degrees: list,
    durations: list[Fraction],
    bar_duration: Fraction,
    key_area_offset: int = 0,
) -> tuple[str, ...]:
    """Derive one chord per bar from bass degrees with key area transposition.

    Args:
        bass_degrees: List of scale degrees (1-7) or dicts
        durations: List of durations
        bar_duration: Duration of one bar
        key_area_offset: Diatonic degree offset for key area transposition

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
            # Apply key area transposition
            if key_area_offset != 0:
                deg = ((deg - 1 + key_area_offset) % 7) + 1
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


def _extract_bass_targets(
    bass_degrees: list,
    durations: list[Fraction],
    key_area_offset: int,
) -> list[tuple[Fraction, int]]:
    """Extract (offset, diatonic_pitch) pairs from schema bass degrees.

    These become hard constraints in CP-SAT, ensuring bass hits schema skeleton.

    Args:
        bass_degrees: List of scale degrees (1-7) or dicts with alter
        durations: List of durations for each degree
        key_area_offset: Diatonic degree offset for key area transposition

    Returns:
        List of (time_offset, diatonic_pitch) tuples
    """
    bass_octave: int = DIATONIC_DEFAULTS["bass"] // 7
    targets: list[tuple[Fraction, int]] = []
    offset = Fraction(0)

    for degree, dur in zip(bass_degrees, durations):
        # Extract plain degree
        deg = _extract_plain_degree(degree)

        # Apply key area transposition
        if key_area_offset != 0:
            deg = deg + key_area_offset

        # Convert to diatonic pitch: degree 1 in octave N = N*7
        diatonic_pitch = (deg - 1) + (bass_octave * 7)

        targets.append((offset, diatonic_pitch))
        offset += dur

    return targets

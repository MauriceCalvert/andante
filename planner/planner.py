"""Main planner orchestrating composition layers.

generate() is the public entry point.

The layers:
1. Rhetorical: Genre → Trajectory + rhythm + tempo
2. Tonal: Affect → Tonal plan + density + modality
3. Schematic: Tonal plan → Schema chain
4. Metric: Schema chain + tonal plan → Bar assignments + anchors
5. Textural: Genre + bar assignments → Treatment assignments
6. Rhythmic: Currently unused (anchors provide timing directly)
7. Melodic: Currently unused (anchors provide pitches directly)

Category B: Orchestrator that validates and delegates.
"""
from pathlib import Path
from typing import Any

from builder.config_loader import load_configs
from builder.io import write_midi_file, write_musicxml_file, write_note_file
from builder.realisation import realise
from builder.types import NoteFile, SchemaChain, TreatmentAssignment
from planner.dramaturgy import get_suggested_key
from planner.metric import layer_4_metric
from planner.rhetorical import layer_1_rhetorical
from planner.schematic import layer_3_schematic
from planner.textural import layer_5_textural
from planner.tonal import layer_2_tonal


DEBUG: bool = True


def _debug(msg: str) -> None:
    """Print debug message if DEBUG is enabled."""
    if DEBUG:
        print(f"[DEBUG] {msg}")


def _derive_key_from_affect(affect: str) -> str:
    """Derive key from affect using Mattheson's Affektenlehre."""
    tonic: str = get_suggested_key(affect)
    if tonic[0].islower():
        mode = "minor"
        tonic = tonic.upper()
    else:
        mode = "major"
    if len(tonic) > 1 and tonic[1] == "b":
        tonic = tonic[0].lower() + "b"
    else:
        tonic = tonic.lower()
    return f"{tonic}_{mode}"


def generate(
    genre: str,
    affect: str,
    key: str | None = None,
) -> NoteFile:
    """Generate composition from genre and affect, with optional key."""
    if key is None:
        key = _derive_key_from_affect(affect)
    _debug(f"Config: genre={genre}, affect={affect}, key={key}")
    config: dict[str, Any] = load_configs(genre, key, affect)
    genre_config = config["genre"]
    key_config = config["key"]
    affect_config = config["affect"]
    form_config = config["form"]
    schemas = config["schemas"]
    trajectory, rhythm_vocab, tempo = layer_1_rhetorical(genre_config)
    _debug(f"L1 Rhetorical: trajectory={trajectory}, tempo={tempo}")
    tonal_plan, density, modality = layer_2_tonal(affect_config)
    _debug(f"L2 Tonal: tonal_plan={tonal_plan}, density={density}, modality={modality}")
    schema_chain: SchemaChain = layer_3_schematic(
        tonal_plan,
        genre_config,
        form_config,
        schemas,
    )
    _debug(f"L3 Schematic: schema_chain has {len(schema_chain.schemas)} schemas")
    for i, s in enumerate(schema_chain.schemas):
        _debug(f"  [{i}] {s}")
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain,
        genre_config,
        form_config,
        key_config,
        schemas,
        tonal_plan,
        affect_config.answer_interval,
    )
    _debug(f"L4 Metric: total_bars={total_bars}, anchors={len(anchors)}")
    _debug(f"  bar_assignments: {bar_assignments}")
    for a in anchors[:10]:
        _debug(f"  anchor {a.bar_beat}: S={a.soprano_midi} B={a.bass_midi} ({a.schema})")
    if len(anchors) > 10:
        _debug(f"  ... and {len(anchors) - 10} more anchors")
    treatment_assignments: list[TreatmentAssignment] = layer_5_textural(
        genre_config,
        bar_assignments,
    )
    _debug(f"L5 Textural: {len(treatment_assignments)} treatment assignments")
    for ta in treatment_assignments:
        _debug(f"  bars {ta.start_bar}-{ta.end_bar}: {ta.treatment}, voice={ta.subject_voice}")
    return realise(
        anchors,
        treatment_assignments,
        key_config,
        affect_config,
        genre_config,
        form_config,
    )


def generate_to_files(
    genre: str,
    affect: str,
    output_dir: Path,
    name: str,
    key: str | None = None,
) -> NoteFile:
    """Generate composition and write to files."""
    result: NoteFile = generate(genre, affect, key)
    note_path: Path = output_dir / f"{name}.note"
    midi_path: Path = output_dir / f"{name}.midi"
    xml_path: Path = output_dir / name
    write_note_file(result, note_path)
    write_midi_file(result, midi_path)
    tonic, mode = _parse_key(key) if key else ("C", "major")
    write_musicxml_file(result, xml_path, tonic, mode)
    return result


def _parse_key(key_str: str) -> tuple[str, str]:
    """Parse key string like 'c_major' to ('C', 'major')."""
    parts: list[str] = key_str.lower().split("_")
    tonic: str = parts[0].capitalize()
    if len(tonic) > 1 and tonic[1] == "b":
        tonic = tonic[0].upper() + "b"
    elif len(tonic) > 1 and tonic[1] == "#":
        tonic = tonic[0].upper() + "#"
    mode: str = parts[1] if len(parts) > 1 else "major"
    return tonic, mode

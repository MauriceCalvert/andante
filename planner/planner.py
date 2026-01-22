"""Main planner orchestrating 7 layers.

generate() is the public entry point matching architecture.md.

The seven layers:
1. Rhetorical: Genre → Trajectory + rhythm + tempo
2. Tonal: Affect → Tonal plan + density + modality
3. Schematic: Tonal plan → Schema chain
4. Metric: Schema chain + tonal plan → Bar assignments + phrase anchors
5. Textural: Genre + bar assignments → Treatment assignments (voice roles per bar)
6. Rhythmic: Anchors + treatments + density → Active slots + durations per voice
7. Melodic: Active slots + anchors → Pitches for active slots only

Category B: Orchestrator that validates and delegates.
"""
from pathlib import Path
from typing import Any

from builder.config_loader import load_configs
from builder.io import write_midi_file, write_note_file
from builder.realisation import realise
from builder.types import NoteFile, RhythmPlan, SchemaChain, Solution, TreatmentAssignment
from planner.dramaturgy import get_suggested_key
from planner.melodic import layer_7_melodic
from planner.metric import layer_4_metric
from planner.rhetorical import layer_1_rhetorical
from planner.rhythmic import layer_6_rhythmic
from planner.schematic import layer_3_schematic
from planner.textural import layer_5_textural, treatments_to_rhythm_input
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

    # Layer 1: Rhetorical
    trajectory, rhythm_vocab, tempo = layer_1_rhetorical(genre_config)
    _debug(f"L1 Rhetorical: trajectory={trajectory}, tempo={tempo}")

    # Layer 2: Tonal
    tonal_plan, density, modality = layer_2_tonal(affect_config)
    _debug(f"L2 Tonal: tonal_plan={tonal_plan}, density={density}, modality={modality}")

    # Layer 3: Schematic
    schema_chain: SchemaChain = layer_3_schematic(
        tonal_plan,
        genre_config,
        form_config,
        schemas,
    )
    _debug(f"L3 Schematic: schema_chain has {len(schema_chain.schemas)} schemas")
    for i, s in enumerate(schema_chain.schemas):
        _debug(f"  [{i}] {s}")

    # Layer 4: Metric (produces bar assignments + anchors)
    bar_assignments, arrivals, total_bars = layer_4_metric(
        schema_chain,
        genre_config,
        form_config,
        key_config,
        schemas,
        tonal_plan,
        affect_config.answer_interval,
    )
    _debug(f"L4 Metric: total_bars={total_bars}, arrivals={len(arrivals)}")
    _debug(f"  bar_assignments: {bar_assignments}")
    for a in arrivals[:10]:
        _debug(f"  anchor {a.bar_beat}: S={a.soprano_midi} B={a.bass_midi} ({a.schema})")
    if len(arrivals) > 10:
        _debug(f"  ... and {len(arrivals) - 10} more anchors")

    # Layer 5: Textural (treatment assignments)
    treatment_assignments: list[TreatmentAssignment] = layer_5_textural(
        genre_config,
        bar_assignments,
    )
    _debug(f"L5 Textural: {len(treatment_assignments)} treatment assignments")
    for ta in treatment_assignments:
        _debug(f"  bars {ta.start_bar}-{ta.end_bar}: {ta.treatment}, voice={ta.subject_voice}")

    # Layer 6: Rhythmic (active slots per voice)
    treatments_for_rhythm: list[dict] = treatments_to_rhythm_input(treatment_assignments)
    rhythm_plan: RhythmPlan = layer_6_rhythmic(
        anchors=arrivals,
        treatments=treatments_for_rhythm,
        density=density,
        total_bars=total_bars,
        metre=genre_config.metre,
    )
    _debug(f"L6 Rhythmic: soprano_active={len(rhythm_plan.soprano_active)}, bass_active={len(rhythm_plan.bass_active)}")

    # Layer 7: Melodic (pitches for active slots)
    _debug(f"L7 Melodic: sections from genre_config:")
    if genre_config.sections:
        for sec in genre_config.sections:
            _debug(f"  {sec['name']}: bars {sec['bars']}")
    else:
        _debug(f"  (no sections defined)")

    solution: Solution = layer_7_melodic(
        schema_chain,
        rhythm_vocab,
        density,
        affect_config,
        key_config,
        genre_config,
        schemas,
        total_bars,
        arrivals,
        rhythm_plan,
    )
    _debug(f"L7 Melodic: solution cost={solution.cost:.2f}, soprano_pitches={len(solution.soprano_pitches)}")

    return realise(
        solution,
        treatment_assignments,
        arrivals,
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
    write_note_file(result, note_path)
    write_midi_file(result, midi_path)
    return result

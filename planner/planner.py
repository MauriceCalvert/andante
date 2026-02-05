"""Main planner orchestrating composition layers.

generate() is the public entry point.

The layers:
1. Rhetorical: Genre -> Trajectory + rhythm + tempo
2. Tonal: Affect + Genre -> TonalPlan (key areas, cadences, density)
3. Schematic: TonalPlan -> SchemaChain (graph-walk selected schemas)
4. Metric: SchemaChain + TonalPlan -> Bar assignments + anchors
5. Textural: Genre + bar assignments -> Passage assignments
6. Voice Planning: Anchors + passages -> CompositionPlan

Category B: Orchestrator that validates and delegates.
"""
from pathlib import Path
from typing import Any

from builder.compose import compose_voices
from builder.config_loader import load_configs
from builder.io import write_midi_file, write_musicxml_file, write_note_file
from builder.types import Composition, PassageAssignment, RhythmPlan, SchemaChain, TonalPlan
from motifs.fugue_loader import LoadedFugue
from planner.dramaturgy import get_suggested_key
from planner.metric.layer import layer_4_metric
from planner.rhetorical import layer_1_rhetorical
from planner.schematic import layer_3_schematic
from planner.textural import layer_5_textural
from planner.tonal import layer_2_tonal
from planner.rhythmic import layer_6_rhythmic
from planner.voice_planning import build_composition_plan
from shared.plan_types import CompositionPlan
from shared.tracer import get_tracer


def _derive_key_from_affect(affect: str) -> str:
    """Derive key from affect using Mattheson's Affektenlehre."""
    tonic: str = get_suggested_key(affect=affect)
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


def _with_sections_override(
    genre_config: Any,
    sections_override: tuple[dict, ...],
) -> Any:
    """Return a new GenreConfig with sections replaced."""
    from dataclasses import replace
    return replace(genre_config, sections=sections_override)


def generate(
    genre: str,
    affect: str,
    key: str | None = None,
    tempo_override: int | None = None,
    fugue: LoadedFugue | None = None,
    sections_override: tuple[dict, ...] | None = None,
    seed: int = 42,
) -> Composition:
    """Generate composition from genre and affect, with optional key and tempo."""
    tracer = get_tracer()
    if key is None:
        key = _derive_key_from_affect(affect=affect)
    tracer.config(genre=genre, affect=affect, key=key)
    config: dict[str, Any] = load_configs(genre=genre, key=key, affect=affect)
    genre_config = config["genre"]
    if sections_override is not None:
        genre_config = _with_sections_override(
            genre_config=genre_config,
            sections_override=sections_override,
        )
    key_config = config["key"]
    affect_config = config["affect"]
    form_config = config["form"]
    schemas = config["schemas"]
    trajectory, rhythm_vocab, tempo = layer_1_rhetorical(genre_config=genre_config)
    if tempo_override is not None:
        tempo = tempo_override
    else:
        tempo = tempo + affect_config.tempo_modifier
    tracer.L1("Rhetorical", trajectory=trajectory, tempo=tempo)
    # Layer 2: Tonal planning (key areas + cadences)
    tonal_plan: TonalPlan = layer_2_tonal(
        affect_config=affect_config,
        genre_config=genre_config,
        seed=seed,
    )
    tracer.L2("Tonal", density=tonal_plan.density, modality=tonal_plan.modality)
    tracer.tonal_plan(plan={s.name: (s.key_area,) for s in tonal_plan.sections})
    # Layer 3: Schematic planning (graph-walk schema selection)
    schema_chain: SchemaChain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=genre_config,
        form_config=form_config,
        schemas=schemas,
        seed=seed + 1,
    )
    tracer.L3("Schematic", schema_count=len(schema_chain.schemas))
    tracer.schema_chain(schemas=schema_chain.schemas)
    # Layer 4: Metric planning (bar assignments + anchors)
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain=schema_chain,
        genre_config=genre_config,
        form_config=form_config,
        key_config=key_config,
        schemas=schemas,
        tonal_plan=tonal_plan,
        answer_interval=affect_config.answer_interval,
        modality=tonal_plan.modality,
    )
    tracer.L4("Metric", total_bars=total_bars, anchor_count=len(anchors))
    tracer.bar_assignments(assignments=bar_assignments)
    tracer.anchors_summary(anchors=anchors)
    passage_assignments: list[PassageAssignment] = layer_5_textural(
        genre_config=genre_config,
        bar_assignments=bar_assignments,
    )
    tracer.L5("Textural", passage_count=len(passage_assignments))
    tracer.passage_assignments(assignments=passage_assignments)
    # Layer 6: Rhythmic Planning
    rhythm_plan: RhythmPlan = layer_6_rhythmic(
        anchors=anchors,
        affect_config=affect_config,
        passage_assignments=passage_assignments,
        genre_config=genre_config,
        tonal_plan=tonal_plan,
        seed=seed + 2,
    )
    tracer.L6("Rhythmic", gap_rhythm_count=len(rhythm_plan.gap_rhythms))
    # Layer 7: Voice Planning
    plan: CompositionPlan = build_composition_plan(
        anchors=anchors,
        passage_assignments=passage_assignments,
        key_config=key_config,
        affect_config=affect_config,
        genre_config=genre_config,
        schemas=schemas,
        seed=seed,
        tempo_override=tempo,
        fugue=fugue,
        rhythm_plan=rhythm_plan,
    )
    tracer.L7("VoicePlanning", voice_count=len(plan.voice_plans))
    return compose_voices(plan=plan)


def generate_to_files(
    genre: str,
    affect: str,
    output_dir: Path,
    name: str,
    key: str | None = None,
    tempo: int | None = None,
    fugue: LoadedFugue | None = None,
    sections_override: tuple[dict, ...] | None = None,
) -> Composition:
    """Generate composition and write to files."""
    result: Composition = generate(genre=genre, affect=affect, key=key, tempo_override=tempo, fugue=fugue, sections_override=sections_override)
    note_path: Path = output_dir / f"{name}.note"
    midi_path: Path = output_dir / f"{name}.midi"
    xml_path: Path = output_dir / name
    write_note_file(comp=result, path=note_path)
    tonic, mode = _parse_key(key_str=key) if key else ("C", "major")
    write_midi_file(comp=result, path=midi_path, tonic=tonic, mode=mode)
    write_musicxml_file(comp=result, path=xml_path, tonic=tonic, mode=mode)
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

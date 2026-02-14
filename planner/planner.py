"""Main planner orchestrating composition layers.

generate() is the public entry point.

The layers:
1. Rhetorical: Genre -> Trajectory + rhythm + tempo
2. Tonal: Affect + Genre -> TonalPlan (key areas, cadences, density)
3. Schematic: TonalPlan -> SchemaChain (graph-walk selected schemas)
4. Metric: SchemaChain + TonalPlan -> Bar assignments + anchors
5. Phrase Planning: Anchors + schemas -> PhrasePlans
6. Composition: PhrasePlans -> Composition (notes)

Category B: Orchestrator that validates and delegates.
"""
from pathlib import Path
from typing import Any

import yaml

from builder.compose import compose_phrases
from builder.config_loader import load_configs
from builder.io import write_midi_file, write_musicxml_file
from builder.note_writer import write_note_file
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import PhrasePlan
from builder.types import Composition, SchemaChain, TonalPlan
from motifs.fugue_loader import LoadedFugue, load_fugue_path
from motifs.subject_generator import generate_fugue_triple, write_fugue_file
from planner.arc import load_named_curve
from planner.dramaturgy import get_suggested_key
from planner.metric.layer import layer_4_metric
from planner.plannertypes import TensionCurve
from planner.rhetorical import layer_1_rhetorical
from planner.schematic import layer_3_schematic
from planner.tonal import layer_2_tonal
from shared.constants import TONIC_TO_MIDI
from shared.key import Key
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


def _parse_key_string(key: str) -> tuple[str, int]:
    """Parse key string like 'c_major' or 'bb_minor' into (mode, tonic_midi).

    Returns:
        (mode, tonic_midi) e.g. ("major", 60) for "c_major"
    """
    parts: list[str] = key.rsplit("_", maxsplit=1)
    assert len(parts) == 2, f"Key string must be 'tonic_mode', got: {key}"
    tonic_name: str = parts[0]
    mode: str = parts[1]
    assert mode in ("major", "minor"), f"Unknown mode in key '{key}': {mode}"
    # Capitalise tonic for TONIC_TO_MIDI lookup (e.g. "bb" -> "Bb", "c" -> "C")
    tonic_upper: str = tonic_name[0].upper() + tonic_name[1:]
    assert tonic_upper in TONIC_TO_MIDI, (
        f"Unknown tonic '{tonic_name}' in key '{key}'. "
        f"Valid tonics: {sorted(TONIC_TO_MIDI.keys())}"
    )
    return mode, TONIC_TO_MIDI[tonic_upper]


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
) -> tuple[Composition, tuple[PhrasePlan, ...], Key]:
    """Generate composition from genre and affect, with optional key and tempo."""
    tracer = get_tracer()
    if key is None:
        key = _derive_key_from_affect(affect=affect)
    tracer.start(genre=genre, affect=affect, key=key)
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
    # Build tension curve only if genre opts in
    tension_curve: TensionCurve | None = None
    if genre_config.tension is not None:
        tension_curve = load_named_curve(name=genre_config.tension)
    if tempo_override is not None:
        tempo = tempo_override
    else:
        tempo = tempo + affect_config.tempo_modifier
    tracer.trace_L1(
        trajectory=trajectory,
        tempo=tempo,
        rhythmic_unit=genre_config.rhythmic_unit,
        metre=genre_config.metre,
    )
    # Layer 2: Tonal planning (key areas + cadences)
    home_mode: str = key_config.name.split()[-1].lower() if key_config else "major"
    tonal_plan: TonalPlan = layer_2_tonal(
        affect_config=affect_config,
        genre_config=genre_config,
        seed=seed,
        home_mode=home_mode,
    )
    tracer.trace_L2(tonal_plan=tonal_plan)
    # Layer 3: Schematic planning (graph-walk schema selection)
    schema_chain: SchemaChain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=genre_config,
        form_config=form_config,
        schemas=schemas,
        seed=seed + 1,
    )
    tracer.trace_L3(schema_chain=schema_chain)
    # Layer 4: Metric planning (bar assignments + anchors)
    bar_assignments, anchors, total_bars = layer_4_metric(
        schema_chain=schema_chain,
        genre_config=genre_config,
        form_config=form_config,
        key_config=key_config,
        schemas=schemas,
        tonal_plan=tonal_plan,
        answer_interval=affect_config.answer_interval,
    )
    tracer.trace_L4(
        bar_assignments=bar_assignments,
        anchors=anchors,
        total_bars=total_bars,
    )
    # Build phrase plans from Layer 4 output
    phrase_plans: tuple[PhrasePlan, ...] = build_phrase_plans(
        schema_chain=schema_chain,
        anchors=anchors,
        genre_config=genre_config,
        schemas=schemas,
        total_bars=total_bars,
        tension_curve=tension_curve,
    )
    tracer.trace_L5(plans=phrase_plans)
    # Compose from phrase plans
    assert len(anchors) > 0, "Layer 4 produced no anchors; cannot determine home key"
    home_key: Key = anchors[0].local_key
    comp: Composition = compose_phrases(
        phrase_plans=phrase_plans,
        home_key=home_key,
        metre=genre_config.metre,
        tempo=tempo,
        upbeat=genre_config.upbeat,
        fugue=fugue,
    )
    return comp, phrase_plans, home_key


def generate_to_files(
    genre: str,
    affect: str,
    output_dir: Path,
    name: str,
    key: str | None = None,
    tempo: int | None = None,
    fugue: LoadedFugue | None = None,
    sections_override: tuple[dict, ...] | None = None,
    seed: int = 42,
) -> Composition:
    """Generate composition and write to files."""
    # For invention genre: generate or load cached fugue triple
    if genre == "invention" and fugue is None and key is not None:
        # Read genre YAML for metre and optional subject name
        genre_yaml_path: Path = Path(__file__).parent.parent / "data" / "genres" / f"{genre}.yaml"
        assert genre_yaml_path.exists(), f"Genre YAML not found: {genre_yaml_path}"
        with open(genre_yaml_path, encoding="utf-8") as f:
            genre_data: dict = yaml.safe_load(f)
        metre_str: str = genre_data["metre"]
        metre_parts: list[str] = metre_str.split("/")
        metre_tuple: tuple[int, int] = (int(metre_parts[0]), int(metre_parts[1]))
        # Priority: 1) library subject from YAML, 2) cached output, 3) generate
        subject_name: str | None = genre_data.get("subject")
        library_dir: Path = Path(__file__).parent.parent / "motifs" / "library"
        if subject_name is not None:
            library_path: Path = library_dir / f"{subject_name}.fugue"
            assert library_path.exists(), (
                f"Subject '{subject_name}' not found at {library_path}"
            )
            fugue = load_fugue_path(path=library_path)
            print(f"  Loaded library subject: {subject_name}")
        else:
            fugue_path: Path = output_dir / f"{name}.fugue"
            if fugue_path.exists():
                fugue = load_fugue_path(path=fugue_path)
                print(f"  Loaded cached fugue: {fugue_path.name}")
            else:
                mode, tonic_midi = _parse_key_string(key=key)
                triple = generate_fugue_triple(
                    mode=mode,
                    metre=metre_tuple,
                    seed=seed,
                    tonic_midi=tonic_midi,
                    verbose=True,
                )
                write_fugue_file(triple=triple, path=fugue_path)
                fugue = load_fugue_path(path=fugue_path)
                print(f"  Generated fugue: {fugue_path.name}")
        # Print summary
        print(f"  Subject: {len(fugue.subject.degrees)} notes, {fugue.subject.bars} bars, "
              f"leap {fugue.subject.leap_direction} {fugue.subject.leap_size}, "
              f"head: {fugue.subject.head_name}")
        print(f"  Answer: {fugue.answer.answer_type}, "
              f"{len(fugue.answer.mutation_points)} mutation(s)")
        print(f"  Countersubject: {len(fugue.countersubject.degrees)} notes")
    result, phrase_plans, home_key = generate(
        genre=genre,
        affect=affect,
        key=key,
        tempo_override=tempo,
        fugue=fugue,
        sections_override=sections_override,
        seed=seed,
    )
    note_path: Path = output_dir / f"{name}.note"
    midi_path: Path = output_dir / f"{name}.midi"
    xml_path: Path = output_dir / name
    write_note_file(
        comp=result,
        path=note_path,
        home_key=home_key,
        genre=genre,
        phrase_plans=phrase_plans,
    )
    tonic: str = home_key.tonic
    mode: str = home_key.mode
    write_midi_file(comp=result, path=midi_path, tonic=tonic, mode=mode)
    write_musicxml_file(comp=result, path=xml_path, tonic=tonic, mode=mode)
    return result


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
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

_log: logging.Logger = logging.getLogger(__name__)

from builder.compose import compose_phrases
from builder.config_loader import load_configs
from builder.io import write_midi_file, write_musicxml_file
from builder.note_writer import write_note_file
from builder.phrase_planner import build_phrase_plans
from builder.phrase_types import PhrasePlan
from builder.types import Composition, SchemaChain, TonalPlan
from motifs.catalogue import SubjectCatalogue
from motifs.fugue_loader import LoadedFugue, load_fugue_path
from scripts.generate_subjects import generate_fugue_triple, write_fugue_file
from planner.arc import load_named_curve
from planner.dramaturgy import get_suggested_key
from planner.imitative.subject_planner import plan_subject
from planner.metric.layer import layer_4_metric
from planner.plannertypes import TensionCurve
from planner.rhetorical import layer_1_rhetorical
from planner.schematic import layer_3_schematic
from planner.thematic import BeatRole, plan_thematic_roles
from planner.tonal import layer_2_tonal
from shared.constants import TONIC_TO_MIDI
from shared.key import Key
from shared.music_math import parse_metre
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
    return replace(genre_config, sections=sections_override)


def generate(
    genre: str,
    affect: str,
    key: str | None = None,
    tempo_override: int | None = None,
    fugue: LoadedFugue | None = None,
    sections_override: tuple[dict, ...] | None = None,
    seed: int = 42,
    trace_name: str | None = None,
) -> tuple[Composition, tuple[PhrasePlan, ...], Key]:
    """Generate composition from genre and affect, with optional key and tempo."""
    tracer = get_tracer()
    if key is None:
        key = _derive_key_from_affect(affect=affect)
    tracer.start(genre=genre, affect=affect, key=key, trace_name=trace_name)
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

    # Branch: imitative path (IMP-3: SubjectPlan → PhrasePlans, skip galant L3/L4/L5)
    if genre_config.composition_model == "imitative" and fugue is not None:
        from planner.imitative.entry_layout import build_imitative_plans

        # Load genre YAML for thematic config
        genre_yaml_path_imp: Path = Path(__file__).parent.parent / "data" / "genres" / f"{genre}.yaml"
        with open(genre_yaml_path_imp, encoding="utf-8") as f_imp:
            genre_yaml_imp: dict = yaml.safe_load(f_imp)
        thematic_cfg: dict | None = genre_yaml_imp.get("thematic")
        assert thematic_cfg is not None, (
            f"Genre '{genre}' has composition_model='imitative' but no 'thematic' section in YAML"
        )

        # Build home key from key string
        key_parts: list[str] = key.rsplit("_", maxsplit=1)
        tonic_cap: str = key_parts[0][0].upper() + key_parts[0][1:]
        home_key_imp: Key = Key(tonic=tonic_cap, mode=key_parts[1])

        # L3 imitative: Build SubjectPlan
        subject_plan = plan_subject(
            thematic_config=thematic_cfg,
            subject_bars=fugue.subject.bars,
            home_key=home_key_imp,
            metre=genre_config.metre,
            sections=genre_config.sections,
            stretto_offsets=fugue.stretto,
        )

        # Log SubjectPlan summary
        section_names: list[str] = [ba.section for ba in subject_plan.bars]
        unique_sections: list[str] = []
        prev_sec: str = ""
        for sn in section_names:
            if sn != prev_sec:
                unique_sections.append(sn)
                prev_sec = sn
        entry_count: int = len(thematic_cfg["entry_sequence"])
        tracer._line(
            f"L3 Imitative SubjectPlan: {subject_plan.total_bars} bars, "
            f"{entry_count} entries, sections: {' > '.join(unique_sections)}"
        )

        # L4/L5 imitative: Build PhrasePlans from SubjectPlan (skip galant layers)
        phrase_plans: tuple[PhrasePlan, ...] = build_imitative_plans(
            subject_plan=subject_plan,
            genre_config=genre_config,
            home_key=home_key_imp,
        )

        tracer.trace_L5(plans=phrase_plans)

        # Jump to composition (L6)
        comp: Composition = compose_phrases(
            phrase_plans=phrase_plans,
            home_key=home_key_imp,
            metre=genre_config.metre,
            tempo=tempo,
            upbeat=genre_config.upbeat,
            fugue=fugue,
        )

        return comp, phrase_plans, home_key_imp

    # Galant path: Layer 3: Schematic planning (graph-walk schema selection)
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

    # Layer 4b: Thematic planning (if genre has thematic: section)
    # Load raw genre YAML to check for thematic section
    genre_yaml_path: Path = Path(__file__).parent.parent / "data" / "genres" / f"{genre}.yaml"
    with open(genre_yaml_path, encoding="utf-8") as f:
        genre_yaml_data: dict = yaml.safe_load(f)

    thematic_config: dict | None = genre_yaml_data.get("thematic")

    thematic_plan: tuple[BeatRole, ...] | None = None
    if thematic_config is not None and fugue is not None:
        # Build subject catalogue
        catalogue: SubjectCatalogue = SubjectCatalogue(fugue=fugue)
        tracer._line(f"Subject catalogue: {catalogue.fragment_count()} fragments — "
                     f"{', '.join(catalogue.fragment_names()[:10])}"
                     f"{' ...' if catalogue.fragment_count() > 10 else ''}")

        # Plan thematic roles with entry_sequence
        assert len(anchors) > 0, "Cannot plan thematic roles with no anchors"
        home_key_plan: Key = anchors[0].local_key
        voice_count: int = thematic_config.get("voice_count", 2)
        subject_bars: int = fugue.subject.bars

        thematic_plan: tuple[BeatRole, ...] = plan_thematic_roles(
            total_bars=total_bars,
            metre=genre_config.metre,
            voice_count=voice_count,
            home_key=home_key_plan,
            schema_chain=schema_chain,
            schemas=schemas,
            genre_config=genre_config,
            thematic_config=thematic_config,
            subject_bars=subject_bars,
        )

        bar_length, beat_unit = parse_metre(metre=genre_config.metre)
        beats_per_bar: int = int(bar_length / beat_unit)
        total_beats: int = total_bars * beats_per_bar
        free_count: int = sum(1 for role in thematic_plan if role.role.value == "free")
        free_pct: float = (free_count / len(thematic_plan)) * 100 if thematic_plan else 0.0

        tracer._line(f"Thematic plan: {len(thematic_plan)} beat-roles "
                     f"({total_beats} beats x {voice_count} voices) — "
                     f"FREE: {free_count}/{len(thematic_plan)} ({free_pct:.1f}%)")

        # Trace thematic plan summary
        entry_count: int = len(thematic_config.get("entry_sequence", []))
        tracer.trace_thematic_plan(
            plan=thematic_plan,
            entry_count=entry_count,
            total_bars=total_bars,
            metre=genre_config.metre,
        )

        # Slice thematic plan into per-phrase ranges
        phrase_plans = _attach_thematic_roles(
            phrase_plans=phrase_plans,
            thematic_plan=thematic_plan,
            genre_config=genre_config,
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

    # Trace thematic coverage summary (only for thematic genres)
    if thematic_config is not None and thematic_plan is not None:
        bar_length, beat_unit = parse_metre(metre=genre_config.metre)
        beats_per_bar_coverage: int = int(bar_length / beat_unit)
        tracer.trace_thematic_coverage(
            plan=thematic_plan,
            total_bars=total_bars,
            beats_per_bar=beats_per_bar_coverage,
        )

    return comp, phrase_plans, home_key


def _attach_thematic_roles(
    phrase_plans: tuple[PhrasePlan, ...],
    thematic_plan: tuple[BeatRole, ...],
    genre_config: Any,
) -> tuple[PhrasePlan, ...]:
    """Slice thematic plan into per-phrase chunks and attach to PhrasePlans.

    Each PhrasePlan gets a slice of BeatRoles covering its bar range.
    """
    bar_length, beat_unit = parse_metre(metre=genre_config.metre)
    beats_per_bar: int = int(bar_length / beat_unit)

    # Build a map from (bar, beat, voice) -> BeatRole
    role_map: dict[tuple[int, int, int], BeatRole] = {}
    for role in thematic_plan:
        beat_idx: int = int(role.beat / beat_unit)
        role_map[(role.bar, beat_idx, role.voice)] = role

    # For each phrase plan, extract the roles covering its bar range
    enriched_plans: list[PhrasePlan] = []
    for plan in phrase_plans:
        start_bar: int = plan.start_bar
        end_bar: int = plan.start_bar + plan.bar_span - 1

        phrase_roles: list[BeatRole] = []
        for bar in range(start_bar, end_bar + 1):
            for beat_idx in range(beats_per_bar):
                for voice in range(2):  # FIXME: voice_count from config
                    key: tuple[int, int, int] = (bar, beat_idx, voice)
                    if key in role_map:
                        phrase_roles.append(role_map[key])

        enriched: PhrasePlan = replace(plan, thematic_roles=tuple(phrase_roles))
        enriched_plans.append(enriched)

    return tuple(enriched_plans)


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
    if genre == "invention" and fugue is None:
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
            _log.info("Loaded library subject: %s", subject_name)
        else:
            fugue_path: Path = output_dir / f"{name}.fugue"
            if fugue_path.exists():
                fugue = load_fugue_path(path=fugue_path)
                _log.info("Loaded cached fugue: %s", fugue_path.name)
            else:
                assert key is not None, (
                    f"Key required to generate fugue for '{genre}'. "
                    f"Provide explicit key or add 'subject' field to genre YAML."
                )
                mode, tonic_midi = _parse_key_string(key=key)
                triple = generate_fugue_triple(
                    mode=mode,
                    metre=metre_tuple,
                    seed=seed,
                    tonic_midi=tonic_midi,
                    verbose=True,
                    affect=affect,
                    genre=genre,
                )
                write_fugue_file(triple=triple, path=fugue_path)
                fugue = load_fugue_path(path=fugue_path)
                _log.info("Generated fugue: %s", fugue_path.name)
        # Log summary
        _log.info(
            "Subject: %d notes, %d bars, leap %s %s, head: %s",
            len(fugue.subject.degrees), fugue.subject.bars,
            fugue.subject.leap_direction, fugue.subject.leap_size,
            fugue.subject.head_name,
        )
        _log.info(
            "Answer: %s, %d mutation(s)",
            fugue.answer.answer_type, len(fugue.answer.mutation_points),
        )
        _log.info("Countersubject: %d notes", len(fugue.countersubject.degrees))
    result, phrase_plans, home_key = generate(
        genre=genre,
        affect=affect,
        key=key,
        tempo_override=tempo,
        fugue=fugue,
        sections_override=sections_override,
        seed=seed,
        trace_name=name,
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


"""Main planner orchestrating 7 layers + L6.5 Figuration.

generate() is the public entry point matching architecture.md.

The layers:
1. Rhetorical: Genre → Trajectory + rhythm + tempo
2. Tonal: Affect → Tonal plan + density + modality
3. Schematic: Tonal plan → Schema chain
4. Metric: Schema chain + tonal plan → Bar assignments + phrase anchors
5. Textural: Genre + bar assignments → Treatment assignments (voice roles per bar)
6. Rhythmic: Anchors + treatments + density → Active slots + durations per voice
6.5 Figuration: Anchors + schema profiles → Baroque figuration patterns (NEW)
7. Melodic: Active slots + anchors → Pitches (ORPHANED when figuration enabled)

Category B: Orchestrator that validates and delegates.
"""
from fractions import Fraction
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
from planner.schema_loader import get_schema_profiles
from planner.textural import layer_5_textural, treatments_to_rhythm_input
from planner.tonal import layer_2_tonal
from shared.key import Key


DEBUG: bool = True


def _expand_notes_to_slots(
    pitches: tuple[int, ...],
    durations: tuple[Fraction, ...],
    slot_pitches: list[int],
    slot_durations: list[Fraction],
    total_slots: int,
    slots_per_bar: int,
) -> None:
    """Expand note-indexed arrays to slot-indexed arrays.

    Converts sequential (pitch, duration) pairs into slot-based arrays
    where each slot represents 1/16th of a bar.

    Args:
        pitches: Note pitches (one per note)
        durations: Note durations (one per note, in whole notes)
        slot_pitches: Output list of pitches (one per slot)
        slot_durations: Output list of durations (one per slot)
        total_slots: Total number of slots needed
        slots_per_bar: Number of slots per bar (16 for 1/16th resolution)
    """
    current_slot: int = 0

    for pitch, duration in zip(pitches, durations):
        # Calculate how many slots this note occupies
        slots_for_note: int = max(1, int(duration * slots_per_bar))

        for _ in range(slots_for_note):
            if current_slot >= total_slots:
                break
            slot_pitches.append(pitch)
            slot_durations.append(duration)
            current_slot += 1

        if current_slot >= total_slots:
            break

    # Fill remaining slots with last pitch if needed
    last_pitch: int = slot_pitches[-1] if slot_pitches else 60
    last_duration: Fraction = Fraction(1, 16)

    while len(slot_pitches) < total_slots:
        slot_pitches.append(last_pitch)
        slot_durations.append(last_duration)


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

    # Simple anchor holds (figuration backed out)
    _debug(f"Generating held anchors (no figuration)")
    soprano_pitches: list[int] = []
    soprano_durations: list[Fraction] = []
    bass_pitches: list[int] = []
    bass_durations: list[Fraction] = []
    SLOTS_PER_BAR: int = 16
    for i, anchor in enumerate(arrivals):
        soprano_pitches.append(anchor.soprano_midi)
        bass_pitches.append(anchor.bass_midi)
        if i < len(arrivals) - 1:
            next_anchor = arrivals[i + 1]
            bar_a: int = int(anchor.bar_beat.split(".")[0])
            beat_a: float = float(anchor.bar_beat.split(".")[1]) if "." in anchor.bar_beat else 1.0
            bar_b: int = int(next_anchor.bar_beat.split(".")[0])
            beat_b: float = float(next_anchor.bar_beat.split(".")[1]) if "." in next_anchor.bar_beat else 1.0
            slot_a: int = (bar_a - 1) * SLOTS_PER_BAR + int((beat_a - 1) * 4)
            slot_b: int = (bar_b - 1) * SLOTS_PER_BAR + int((beat_b - 1) * 4)
            duration: Fraction = Fraction(slot_b - slot_a, SLOTS_PER_BAR)
            soprano_durations.append(duration)
            bass_durations.append(duration)
        else:
            soprano_durations.append(Fraction(1, 4))
            bass_durations.append(Fraction(1, 4))
    _debug(f"Anchors: {len(soprano_pitches)} notes per voice")
    total_slots: int = total_bars * SLOTS_PER_BAR
    soprano_slots: list[int] = []
    soprano_slot_durations: list[Fraction] = []
    _expand_notes_to_slots(tuple(soprano_pitches), tuple(soprano_durations), soprano_slots, soprano_slot_durations, total_slots, SLOTS_PER_BAR)
    bass_slots: list[int] = []
    bass_slot_durations: list[Fraction] = []
    _expand_notes_to_slots(tuple(bass_pitches), tuple(bass_durations), bass_slots, bass_slot_durations, total_slots, SLOTS_PER_BAR)
    solution: Solution = Solution(
        soprano_pitches=tuple(soprano_slots),
        bass_pitches=tuple(bass_slots),
        soprano_durations=tuple(soprano_slot_durations),
        bass_durations=tuple(bass_slot_durations),
        cost=0.0,
    )
    _debug(f"Solution: {len(solution.soprano_pitches)} slots per voice")

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

"""Main planner: orchestrates Brief -> Plan with full dramaturgical pipeline."""
from planner.frame import resolve_frame
from planner.material import acquire_material
from planner.structure import plan_structure
from planner.dramaturgy import (
    select_archetype, compute_rhetorical_structure, compute_tension_curve
)
from planner.harmony import plan_harmony
from planner.devices import assign_devices
from planner.coherence import plan_coherence
from planner.plannertypes import (
    Brief, Frame, Material, Motif, Plan, Structure,
    RhetoricalStructure, TensionCurve, HarmonicPlan, CoherencePlan
)
from planner.validator import validate
from shared.constraint_validator import validate_brief, validate_frame


def build_plan(brief: Brief, user_motif: Motif | None = None, seed: int | None = None) -> Plan:
    """Build complete plan from brief.

    This is the main entry point for the planner. It orchestrates:
    1. Frame resolution (key, mode, metre, tempo)
    2. Dramaturgical structure (archetype, rhetoric, tension)
    3. Material acquisition (affect-driven subject generation)
    4. Structural planning (sections, episodes, phrases)
    5. Harmonic architecture (key schemes, cadences)
    6. Device assignment (Figurenlehre)
    7. Coherence planning (callbacks, surprises)

    Args:
        brief: Brief with affect, genre, forces, bars
        user_motif: Optional user-provided motif (takes priority over generation)
        seed: Optional random seed for affect-driven generation

    Returns:
        Complete plan with full dramaturgical structure
    """
    # Validate brief
    valid, errors = validate_brief(brief.genre, brief.affect, brief.bars)
    assert valid, f"Brief validation failed: {errors}"

    # Resolve frame
    frame: Frame = resolve_frame(brief)
    valid, errors = validate_frame(
        genre=brief.genre,
        affect=brief.affect,
        key=frame.key,
        mode=frame.mode,
        metre=frame.metre,
        tempo=frame.tempo,
        voices=frame.voices,
        form=frame.form,
    )
    assert valid, f"Frame validation failed: {errors}"

    # Step 1: Compute dramaturgical structure
    archetype: str = select_archetype(brief.affect)
    rhetoric: RhetoricalStructure = compute_rhetorical_structure(archetype, brief.bars)
    tension_curve: TensionCurve = compute_tension_curve(archetype, brief.bars)

    # Step 2: Acquire material (affect-driven or user-provided)
    material: Material = acquire_material(
        frame=frame,
        user_motif=user_motif,
        genre=brief.genre,
        affect=brief.affect,
        seed=seed,
    )

    # Step 3: Plan structure
    structure: Structure = plan_structure(brief, frame, material)

    # Calculate actual bars
    actual_bars: int = sum(
        sum(phrase.bars for episode in section.episodes for phrase in episode.phrases)
        for section in structure.sections
    )

    # Step 4: Plan harmonic architecture
    harmonic_plan: HarmonicPlan = plan_harmony(
        rhetoric=rhetoric,
        tension_curve=tension_curve,
        mode=frame.mode,
        total_bars=actual_bars,
    )

    # Step 5: Assign devices (musical figures)
    structure = assign_devices(
        structure=structure,
        affect=brief.affect,
        tension_curve=tension_curve,
        rhetoric=rhetoric,
        total_bars=actual_bars,
    )

    # Step 6: Plan coherence (callbacks, surprises)
    coherence: CoherencePlan = plan_coherence(
        structure=structure,
        material=material,
        rhetoric=rhetoric,
        tension_curve=tension_curve,
        total_bars=actual_bars,
        affect=brief.affect,
    )

    # Build complete plan
    plan: Plan = Plan(
        brief=brief,
        frame=frame,
        material=material,
        structure=structure,
        actual_bars=actual_bars,
        tension_curve=tension_curve,
        rhetoric=rhetoric,
        harmonic_plan=harmonic_plan,
        coherence=coherence,
    )

    # Validate complete plan
    valid, errors = validate(plan)
    assert valid, f"Plan validation failed: {errors}"

    return plan

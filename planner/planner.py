"""Main planner: orchestrates Brief -> SchemaPlan via schema-first pipeline.

Schema-first planning (per planner_design.md):
1. Frame resolution (key, mode, metre, tempo)
2. Cadence planning (arrival points first)
3. Schema chain generation (harmonic DNA)
4. Subject handling (validation/derivation after schema)
5. Structure building (from schemas, not episodes)
"""
from dataclasses import dataclass

from planner.frame import resolve_frame
from planner.material import acquire_material
from planner.structure import build_structure_from_schemas
from planner.plannertypes import (
    Brief, Frame, Material, Motif, SchemaStructure,
    CadencePoint, SchemaSlot,
)
from planner.validator import validate_schema_plan
from planner.cadence_planner import plan_cadences
from planner.schema_generator import generate_schema_chain, compute_actual_bars
from planner.subject_validator import validate_subject
from planner.subject_deriver import derive_subject
from shared.constraint_validator import validate_brief, validate_frame


# =============================================================================
# Schema-First Planner (planner_design.md)
# =============================================================================


@dataclass
class SchemaPlan:
    """Schema-first plan output.

    Different from Plan in that:
    - structure is SchemaStructure (SectionSchema, not Section)
    - No macro_form, tension_curve, rhetoric, harmonic_plan, coherence
    - Schema chain is the "harmonic plan" - no separate harmony stage needed
    """
    brief: Brief
    frame: Frame
    material: Material
    structure: SchemaStructure
    cadence_plan: tuple[CadencePoint, ...]
    schema_chain: tuple[SchemaSlot, ...]
    actual_bars: int


def build_schema_plan(
    brief: Brief,
    user_motif: Motif | None = None,
    seed: int | None = None,
    user_frame: Frame | None = None,
    user_cs: Motif | None = None,
) -> SchemaPlan:
    """Build plan using schema-first approach.

    New pipeline (per planner_design.md):
    1. Frame resolution (unchanged)
    2. Cadence planning (NEW - arrival points first)
    3. Schema chain generation (NEW - harmonic DNA)
    4. Subject handling (NEW - validation/derivation after schema)
    5. Structure building (CHANGED - from schemas, not episodes)

    Args:
        brief: Brief with affect, genre, forces, bars
        user_motif: Optional user-provided motif
        seed: Optional random seed
        user_frame: Optional explicit frame
        user_cs: Optional user counter-subject (ignored in schema-first)

    Returns:
        SchemaPlan with schema-based structure
    """
    # Validate brief
    valid, errors = validate_brief(brief.genre, brief.affect, brief.bars)
    assert valid, f"Brief validation failed: {errors}"

    # Step 1: Resolve frame (unchanged)
    frame: Frame = user_frame if user_frame else resolve_frame(brief)
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

    # Step 2: Plan cadences (NEW)
    cadence_plan: tuple[CadencePoint, ...] = plan_cadences(
        frame=frame,
        genre=brief.genre,
        total_bars=brief.bars,
    )

    # Step 3: Generate schema chain (NEW)
    schema_chain: tuple[SchemaSlot, ...] = generate_schema_chain(
        cadence_plan=cadence_plan,
        genre=brief.genre,
        mode=frame.mode,
        total_bars=brief.bars,
        seed=seed,
    )

    # Step 4: Handle subject (NEW - after schema)
    opening_schema: str = schema_chain[0].type

    if user_motif is not None:
        # Validate user subject against opening schema
        validation = validate_subject(user_motif, opening_schema, frame.mode)
        assert validation.valid, f"Subject invalid: {validation.errors}"
        subject = user_motif
    else:
        # Derive subject from opening schema
        subject = derive_subject(opening_schema, frame, brief.genre)

    material: Material = Material(subject=subject, counter_subject=user_cs)

    # Step 5: Build structure from schemas (CHANGED)
    structure: SchemaStructure = build_structure_from_schemas(
        schema_chain=schema_chain,
        cadence_plan=cadence_plan,
    )

    # Calculate actual bars
    actual_bars: int = compute_actual_bars(schema_chain)

    # Build schema plan
    plan = SchemaPlan(
        brief=brief,
        frame=frame,
        material=material,
        structure=structure,
        cadence_plan=cadence_plan,
        schema_chain=schema_chain,
        actual_bars=actual_bars,
    )

    # Validate schema plan
    valid, errors = validate_schema_plan(plan)
    assert valid, f"Schema plan validation failed: {errors}"

    return plan

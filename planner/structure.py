"""Structure planner: builds SectionSchema hierarchy from schema chain.

Schema-first structure building: converts SchemaSlot chain into
SectionSchema hierarchy grouped by cadence points.
"""
from planner.plannertypes import (
    CadencePoint, SchemaSlot, SectionSchema, SchemaStructure,
)


# =============================================================================
# Schema-First Structure Building (planner_design.md)
# =============================================================================


def build_structure_from_schemas(
    schema_chain: tuple[SchemaSlot, ...],
    cadence_plan: tuple[CadencePoint, ...],
) -> SchemaStructure:
    """Build SchemaStructure from schema chain and cadence plan.

    Groups consecutive schemas into sections based on cadence points.
    Each section ends at a cadence (where SchemaSlot.cadence is not None).

    Args:
        schema_chain: Tuple of SchemaSlot from schema_generator
        cadence_plan: Tuple of CadencePoint from cadence_planner

    Returns:
        SchemaStructure with SectionSchema objects
    """
    assert schema_chain, "schema_chain cannot be empty"
    assert cadence_plan, "cadence_plan cannot be empty"

    sections: list[SectionSchema] = []
    current_section_schemas: list[SchemaSlot] = []
    current_section_cadences: list[CadencePoint] = []

    # Map cadence bars to cadence points
    cadence_by_bar: dict[int, CadencePoint] = {cp.bar: cp for cp in cadence_plan}

    # Track cumulative bars
    cumulative_bars = 0
    section_label_idx = 0
    section_labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    for slot in schema_chain:
        current_section_schemas.append(slot)
        cumulative_bars += slot.bars

        # Check if this slot ends on a cadence
        if slot.cadence is not None:
            # Find matching cadence point
            if cumulative_bars in cadence_by_bar:
                current_section_cadences.append(cadence_by_bar[cumulative_bars])

            # Determine key area for this section
            key_area = _determine_key_area(
                section_idx=section_label_idx,
                total_sections=len(cadence_plan),
                cadences=current_section_cadences,
            )

            # Create section
            section = SectionSchema(
                label=section_labels[section_label_idx % len(section_labels)],
                key_area=key_area,
                cadence_plan=tuple(current_section_cadences),
                schemas=tuple(current_section_schemas),
            )
            sections.append(section)

            # Reset for next section
            current_section_schemas = []
            current_section_cadences = []
            section_label_idx += 1

    # Handle any remaining schemas (shouldn't happen if cadence_plan is correct)
    if current_section_schemas:
        # Create final section without explicit cadence
        key_area = "I"  # Default to tonic
        section = SectionSchema(
            label=section_labels[section_label_idx % len(section_labels)],
            key_area=key_area,
            cadence_plan=tuple(current_section_cadences),
            schemas=tuple(current_section_schemas),
        )
        sections.append(section)

    return SchemaStructure(sections=tuple(sections))


def _determine_key_area(
    section_idx: int,
    total_sections: int,
    cadences: list[CadencePoint],
) -> str:
    """Determine key area for a section based on position and cadences.

    Rules:
    - First section: I (tonic)
    - Middle sections: V (dominant) or based on cadence targets
    - Final section: I (tonic)

    Args:
        section_idx: 0-indexed section number
        total_sections: Total number of sections
        cadences: Cadence points in this section

    Returns:
        Roman numeral key area
    """
    if section_idx == 0:
        return "I"

    if section_idx == total_sections - 1:
        return "I"

    # Middle sections: use cadence target or default to V
    if cadences:
        # Use the target of the last cadence in section
        return cadences[-1].target

    return "V"

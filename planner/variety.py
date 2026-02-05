"""Tonal variety rule validators.

Hard constraints for tonal planning per tonal_planning_upgrade.md.
Validators detect violations; generators must prevent them.
"""

# Opening schemas allowed only at section starts
OPENING_SCHEMAS: frozenset[str] = frozenset({
    "romanesca", "do_re_mi", "meyer", "sol_fa_mi",
})


def validate_no_adjacent_schema_repetition(schemas: tuple[str, ...]) -> None:
    """V-T001: No consecutive identical schemas."""
    for i in range(len(schemas) - 1):
        assert schemas[i] != schemas[i + 1], (
            f"V-T001: '{schemas[i]}' repeated at positions {i} and {i + 1}"
        )


def validate_opening_placement(
    schemas: tuple[str, ...],
    section_boundaries: tuple[int, ...],
) -> None:
    """V-T002: Opening schemas only at section starts."""
    boundary_set: set[int] = {0} | set(section_boundaries)
    for i, schema in enumerate(schemas):
        if schema in OPENING_SCHEMAS:
            assert i in boundary_set, (
                f"V-T002: opening schema '{schema}' at position {i}, "
                f"not at section boundary. Boundaries: {sorted(boundary_set)}"
            )


def validate_cadence_variety(cadences: tuple[str, ...]) -> None:
    """V-T003: Cadence variety rules."""
    if len(cadences) < 2:
        return
    interior: tuple[str, ...] = cadences[:-1]
    authentic_count: int = sum(1 for c in interior if c == "authentic")
    assert authentic_count <= 1, (
        f"V-T003: {authentic_count} interior authentic cadences (max 1)"
    )
    for i in range(len(cadences) - 1):
        assert not (cadences[i] == "half" and cadences[i + 1] == "half"), (
            f"V-T003: consecutive half cadences at sections {i} and {i + 1}"
        )


def validate_tonal_path_variety(key_areas: tuple[str, ...]) -> None:
    """V-T004: No consecutive identical non-tonic key areas."""
    for i in range(len(key_areas) - 1):
        if key_areas[i] != "I" and key_areas[i] == key_areas[i + 1]:
            assert False, (
                f"V-T004: consecutive non-tonic key '{key_areas[i]}' "
                f"at sections {i} and {i + 1}"
            )

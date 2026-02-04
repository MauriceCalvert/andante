"""Layer 3: Schematic.

Category A: Pure functions, no I/O, no validation.
Input: Tonal plan
Output: Schema chain

Enumerate all valid chains from rules.
"""
from builder.types import FormConfig, GenreConfig, SchemaChain, SchemaConfig


def layer_3_schematic(
    tonal_plan: dict[str, tuple[str, ...]],
    genre_config: GenreConfig,
    form_config: FormConfig,
    schemas: dict[str, SchemaConfig],
) -> SchemaChain:
    """Execute Layer 3.
    
    Returns:
        SchemaChain with schemas, key areas, free passage markers.
    """
    schema_sequence: list[str] = []
    key_areas: list[str] = []
    free_passages: set[tuple[int, int]] = set()
    for section in genre_config.sections:
        section_name: str = section["name"]
        section_schemas: list[str] = section.get("schema_sequence", [])
        section_key_areas: tuple[str, ...] = tonal_plan.get(section_name, ("I",))
        for i, schema_name in enumerate(section_schemas):
            if schema_name == "episode":
                if schema_sequence:
                    free_passages.add((len(schema_sequence) - 1, len(schema_sequence)))
                continue
            schema_sequence.append(schema_name)
            area_idx: int = min(i, len(section_key_areas) - 1)
            key_areas.append(section_key_areas[area_idx])
    for i in range(len(schema_sequence) - 1):
        if (i, i + 1) not in free_passages:
            current_schema: str = schema_sequence[i]
            next_schema: str = schema_sequence[i + 1]
            if current_schema in schemas and next_schema in schemas:
                if not _check_connection(exit_schema=schemas[current_schema], entry_schema=schemas[next_schema]):
                    free_passages.add((i, i + 1))
    return SchemaChain(
        schemas=tuple(schema_sequence),
        key_areas=tuple(key_areas),
        free_passages=frozenset(free_passages),
    )


def _check_connection(
    exit_schema: SchemaConfig,
    entry_schema: SchemaConfig,
) -> bool:
    """Check if two schemas can connect directly.
    
    Valid connections:
    1. Identity: exit.bass == entry.bass
    2. Step: |exit.bass - entry.bass| == 1
    3. Dominant: exit.bass == 5 and entry.bass == 1
    """
    exit_bass: int = exit_schema.exit_bass
    entry_bass: int = entry_schema.entry_bass
    if exit_bass == entry_bass:
        return True
    if abs(exit_bass - entry_bass) == 1:
        return True
    if exit_bass == 5 and entry_bass == 1:
        return True
    return False


def enumerate_valid_chains(
    tonal_plan: dict[str, tuple[str, ...]],
    schemas: dict[str, SchemaConfig],
    genre_config: GenreConfig,
) -> list[SchemaChain]:
    """Enumerate all valid schema chains for tonal plan.
    
    For minimal implementation, returns single chain based on
    genre section definitions.
    """
    chain: SchemaChain = layer_3_schematic(
        tonal_plan=tonal_plan,
        genre_config=genre_config,
        form_config=None,  # type: ignore
        schemas=schemas,
    )
    return [chain]

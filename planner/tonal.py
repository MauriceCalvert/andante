"""Layer 2: Tonal.

Category A: Pure functions, no I/O, no validation.
Input: Affect config
Output: Tonal plan + density + modality

Lookup table, expandable.
"""
from builder.types import AffectConfig


def layer_2_tonal(
    affect_config: AffectConfig,
) -> tuple[dict[str, tuple[str, ...]], str, str]:
    """Execute Layer 2.
    
    Returns:
        tonal_plan: Dict mapping section to key areas
        density: "high", "medium", or "low"
        modality: "diatonic" or "chromatic"
    """
    tonal_plan: dict[str, tuple[str, ...]] = dict(affect_config.tonal_path)
    density: str = affect_config.density
    modality: str = "diatonic"
    return tonal_plan, density, modality

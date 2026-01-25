"""Layer 1: Rhetorical.

Category A: Pure functions, no I/O, no validation.
Input: Genre config
Output: Trajectory + rhythmic vocabulary + tempo

Fixed per genre - no enumeration.
"""
from typing import Any

from builder.types import GenreConfig


def layer_1_rhetorical(
    genre_config: GenreConfig,
) -> tuple[list[str], dict[str, Any], int]:
    """Execute Layer 1.
    
    Returns:
        trajectory: List of section names
        rhythm_vocab: Dict of rhythmic parameters
        tempo: Base tempo in BPM
    """
    trajectory: list[str] = [s["name"] for s in genre_config.sections]
    rhythm_vocab: dict[str, Any] = {
        "primary_value": genre_config.primary_value,
        "characteristic_figures": genre_config.rhythmic_vocabulary.get(
            "characteristic_figures", []
        ),
    }
    tempo_range: list[int] = genre_config.rhythmic_vocabulary.get("tempo_range", [72, 88])
    tempo: int = (tempo_range[0] + tempo_range[1]) // 2
    return trajectory, rhythm_vocab, tempo

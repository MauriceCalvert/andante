"""Phrase-level rhythmic motif selection and development.

Loads motif vocabulary from YAML, selects motifs per phrase with
variety constraints, and applies development operations.
"""
import logging
import random
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from typing import Any
import yaml
from builder.types import RhythmicMotif, RhythmicProfile
from shared.constants import (
    VALID_DURATIONS,
    VALID_MOTIF_CHARACTERS,
    VALID_PHRASE_POSITIONS,
)

logger = logging.getLogger(__name__)

_DATA_DIR: Path = Path(__file__).resolve().parent.parent / "data" / "rhythm"
_VOCABULARY_FILE: str = "motif_vocabulary.yaml"
_VALID_DURATIONS_SET: frozenset[Fraction] = frozenset(VALID_DURATIONS)


# =============================================================================
# Vocabulary Loading
# =============================================================================


def _parse_fraction(s: str) -> Fraction:
    """Parse a string fraction like '3/8' into Fraction."""
    return Fraction(s)


def _load_motif_entry(
    name: str,
    entry: dict[str, Any],
    metre: str,
) -> RhythmicMotif:
    """Parse one motif entry from YAML into a RhythmicMotif."""
    assert "pattern" in entry, f"Motif '{name}': missing 'pattern'"
    assert "accent_pattern" in entry, f"Motif '{name}': missing 'accent_pattern'"
    assert "character" in entry, f"Motif '{name}': missing 'character'"
    assert "phrase_positions" in entry, f"Motif '{name}': missing 'phrase_positions'"
    assert "weight" in entry, f"Motif '{name}': missing 'weight'"
    pattern: tuple[Fraction, ...] = tuple(
        _parse_fraction(s=d) for d in entry["pattern"]
    )
    assert len(pattern) > 0, f"Motif '{name}': empty pattern"
    for dur in pattern:
        assert dur > 0, f"Motif '{name}': non-positive duration {dur}"
    accent_pattern: tuple[int, ...] = tuple(entry["accent_pattern"])
    assert len(accent_pattern) == len(pattern), (
        f"Motif '{name}': accent_pattern length {len(accent_pattern)} "
        f"!= pattern length {len(pattern)}"
    )
    character: str = entry["character"]
    assert character in VALID_MOTIF_CHARACTERS, (
        f"Motif '{name}': invalid character '{character}'"
    )
    positions: tuple[str, ...] = tuple(entry["phrase_positions"])
    for pos in positions:
        assert pos in VALID_PHRASE_POSITIONS, (
            f"Motif '{name}': invalid phrase_position '{pos}'"
        )
    compatible_metres: tuple[str, ...] = tuple(
        entry.get("compatible_metres", [metre])
    )
    weight: float = float(entry["weight"])
    assert weight > 0, f"Motif '{name}': weight must be positive, got {weight}"
    return RhythmicMotif(
        name=name,
        pattern=pattern,
        accent_pattern=accent_pattern,
        character=character,
        compatible_metres=compatible_metres,
        phrase_positions=positions,
        weight=weight,
    )


def load_motif_vocabulary(metre: str) -> list[RhythmicMotif]:
    """Load all motifs for a given metre from YAML."""
    path: Path = _DATA_DIR / _VOCABULARY_FILE
    assert path.exists(), f"Missing motif vocabulary: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)
    assert metre in data, (
        f"No motif vocabulary for metre '{metre}'. "
        f"Available: {list(data.keys())}"
    )
    metre_data: dict[str, dict[str, Any]] = data[metre]
    motifs: list[RhythmicMotif] = []
    for category_name, category in metre_data.items():
        assert isinstance(category, dict), (
            f"Metre '{metre}' category '{category_name}': expected dict, got {type(category)}"
        )
        for motif_name, entry in category.items():
            motif: RhythmicMotif = _load_motif_entry(
                name=motif_name,
                entry=entry,
                metre=metre,
            )
            motifs.append(motif)
    assert len(motifs) > 0, f"No motifs loaded for metre '{metre}'"
    return motifs


# =============================================================================
# Motif Selection
# =============================================================================


_DENSITY_WEIGHT_MAP: dict[str, dict[str, float]] = {
    "low": {"plain": 1.5, "expressive": 1.0, "energetic": 0.3, "ornate": 0.5, "bold": 0.3},
    "medium": {"plain": 1.0, "expressive": 1.2, "energetic": 0.8, "ornate": 1.0, "bold": 0.7},
    "high": {"plain": 0.5, "expressive": 0.8, "energetic": 1.5, "ornate": 1.0, "bold": 1.2},
}


def _density_weight(
    motif: RhythmicMotif,
    base_density: str,
) -> float:
    """Compute density-adjusted weight for a motif."""
    density_weights: dict[str, float] = _DENSITY_WEIGHT_MAP.get(
        base_density, _DENSITY_WEIGHT_MAP["medium"]
    )
    modifier: float = density_weights.get(motif.character, 1.0)
    return motif.weight * modifier


def select_motif(
    vocabulary: list[RhythmicMotif],
    phrase_position: str,
    profile: RhythmicProfile,
    previous_motif_name: str | None,
    seed: int,
) -> RhythmicMotif:
    """Select a motif for a phrase, respecting variety and density."""
    assert phrase_position in VALID_PHRASE_POSITIONS, (
        f"Invalid phrase_position: '{phrase_position}'"
    )
    candidates: list[RhythmicMotif] = [
        m for m in vocabulary
        if phrase_position in m.phrase_positions
    ]
    assert len(candidates) > 0, (
        f"No motifs available for position '{phrase_position}'"
    )
    # V-R001: no consecutive identical motifs
    if previous_motif_name is not None and len(candidates) > 1:
        candidates = [m for m in candidates if m.name != previous_motif_name]
    assert len(candidates) > 0, (
        f"No motifs remaining after V-R001 filter for position '{phrase_position}'"
    )
    weights: list[float] = [
        _density_weight(motif=m, base_density=profile.base_density)
        for m in candidates
    ]
    rng: random.Random = random.Random(seed)
    selected: list[RhythmicMotif] = rng.choices(
        population=candidates,
        weights=weights,
        k=1,
    )
    return selected[0]


# =============================================================================
# Motif Development Operations
# =============================================================================


def diminute(motif: RhythmicMotif) -> RhythmicMotif:
    """Double note count, halve durations."""
    new_pattern: list[Fraction] = []
    new_accents: list[int] = []
    for dur, acc in zip(motif.pattern, motif.accent_pattern):
        half_dur: Fraction = dur / 2
        new_pattern.append(half_dur)
        new_pattern.append(half_dur)
        new_accents.append(acc)
        new_accents.append(max(1, acc - 1))
    return replace(
        motif,
        pattern=tuple(new_pattern),
        accent_pattern=tuple(new_accents),
        name=f"{motif.name}_dim",
    )


def augment(motif: RhythmicMotif) -> RhythmicMotif:
    """Halve note count, double durations."""
    new_pattern: list[Fraction] = []
    new_accents: list[int] = []
    for i in range(0, len(motif.pattern), 2):
        combined: Fraction = motif.pattern[i]
        acc: int = motif.accent_pattern[i]
        if i + 1 < len(motif.pattern):
            combined += motif.pattern[i + 1]
            acc = max(acc, motif.accent_pattern[i + 1])
        new_pattern.append(combined)
        new_accents.append(acc)
    return replace(
        motif,
        pattern=tuple(new_pattern),
        accent_pattern=tuple(new_accents),
        name=f"{motif.name}_aug",
    )


def fragment(motif: RhythmicMotif) -> RhythmicMotif:
    """Take first half of motif."""
    half: int = max(1, len(motif.pattern) // 2)
    return replace(
        motif,
        pattern=motif.pattern[:half],
        accent_pattern=motif.accent_pattern[:half],
        name=f"{motif.name}_frag",
    )


def invert(motif: RhythmicMotif) -> RhythmicMotif:
    """Reverse duration order."""
    return replace(
        motif,
        pattern=tuple(reversed(motif.pattern)),
        accent_pattern=tuple(reversed(motif.accent_pattern)),
        name=f"{motif.name}_inv",
    )


def displace(
    motif: RhythmicMotif,
    offset: Fraction,
) -> RhythmicMotif:
    """Rotate pattern by offset for syncopation."""
    total: Fraction = sum(motif.pattern)
    assert total > 0, f"Motif '{motif.name}': zero-length pattern"
    offset_normalized: Fraction = offset % total
    cumulative: Fraction = Fraction(0)
    split_idx: int = 0
    for i, dur in enumerate(motif.pattern):
        cumulative += dur
        if cumulative >= offset_normalized:
            split_idx = i + 1
            break
    new_pattern: tuple[Fraction, ...] = (
        motif.pattern[split_idx:] + motif.pattern[:split_idx]
    )
    new_accents: tuple[int, ...] = (
        motif.accent_pattern[split_idx:] + motif.accent_pattern[:split_idx]
    )
    return replace(
        motif,
        pattern=new_pattern,
        accent_pattern=new_accents,
        name=f"{motif.name}_disp",
    )


def develop_motif(
    base: RhythmicMotif,
    phrase_idx: int,
    development_plan: str,
) -> RhythmicMotif:
    """Apply development operation based on phrase index and plan."""
    assert development_plan in {"intensifying", "relaxing", "contrasting"}, (
        f"Invalid development_plan: '{development_plan}'"
    )
    if phrase_idx == 0:
        return base
    if development_plan == "intensifying":
        if phrase_idx <= 2:
            return base
        if phrase_idx <= 4:
            return diminute(motif=base)
        return fragment(motif=base)
    if development_plan == "relaxing":
        if phrase_idx <= 2:
            return base
        return augment(motif=base)
    # contrasting
    if phrase_idx % 2 == 1:
        return invert(motif=base)
    return base

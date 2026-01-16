"""Dynamic treatment sequence generator.

Generates structurally-appropriate treatment sequences based on:
- phrase_count: number of phrases to fill
- climax_position: where the climax falls (0.0-1.0)
- genre: optional genre-specific constraints

Replaces static `treatments: [...]` arrays in arcs.yaml with
dynamically generated sequences that respect musical structure.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"

# Structural regions as fraction of piece
REGIONS = {
    "exposition": (0.0, 0.15),    # Opening statement
    "development_1": (0.15, 0.4), # First development phase
    "climax": (0.4, 0.7),         # Climax region (adjusted by climax_position)
    "development_2": (0.7, 0.85), # Return/recapitulation
    "close": (0.85, 1.0),         # Final statement and cadence
}

# Treatment pools by region
TREATMENT_POOLS: dict[str, list[str]] = {
    "exposition": ["statement"],
    "development_1": ["imitation", "sequence", "inversion", "dialogue"],
    "climax": ["stretto", "fragmentation", "augmentation", "diminution"],
    "development_2": ["sequence", "imitation", "inversion"],
    "close": ["statement"],
}

# Transition rules: what can follow what
# Format: treatment -> list of valid next treatments
TRANSITIONS: dict[str, list[str]] = {
    "statement": ["imitation", "sequence", "stretto", "inversion", "dialogue", "statement"],
    "imitation": ["sequence", "inversion", "statement", "stretto", "fragmentation"],
    "sequence": ["statement", "imitation", "inversion", "stretto", "fragmentation", "sequence"],
    "inversion": ["sequence", "statement", "imitation", "stretto"],
    "stretto": ["fragmentation", "sequence", "statement", "augmentation"],
    "fragmentation": ["sequence", "imitation", "statement", "stretto"],
    "augmentation": ["diminution", "sequence", "statement"],
    "diminution": ["sequence", "statement", "stretto"],
    "dialogue": ["imitation", "sequence", "statement", "inversion"],
}

# Treatments that should appear at most N times
MAX_OCCURRENCES: dict[str, int] = {
    "stretto": 2,
    "fragmentation": 2,
    "augmentation": 1,
    "diminution": 1,
}

# Koch's phrase type transitions (sections 34-37)
# I-phrase = caesura on tonic, V-phrase = caesura on dominant
# These guide tonal_target selection during structure generation
TONAL_TRANSITIONS: dict[str, list[str]] = {
    "I": ["V", "cadence"],      # I-phrase can go to V-phrase or cadence
    "V": ["cadence"],           # V-phrase should go to cadence (not I at start)
    "cadence": ["I", "V"],      # After cadence, new period can start either way
}


@dataclass
class TreatmentProfile:
    """Profile for treatment generation."""
    phrase_count: int
    climax_position: float = 0.7  # late climax by default
    must_include: list[str] | None = None
    must_avoid: list[str] | None = None
    start_with: str = "statement"
    end_with: str = "statement"
    second_phrase: str | None = None  # Force second phrase treatment (e.g., imitation for invention)


def get_region_for_position(position: float, climax_pos: float) -> str:
    """Determine structural region for a given position.

    Adjusts regions based on climax_position:
    - Early climax (0.3-0.5): shorter development_1, longer development_2
    - Late climax (0.7-0.9): longer development_1, shorter development_2
    """
    # Adjust climax region center based on climax_position
    climax_start = max(0.2, climax_pos - 0.15)
    climax_end = min(0.85, climax_pos + 0.15)

    if position < 0.15:
        return "exposition"
    elif position < climax_start:
        return "development_1"
    elif position < climax_end:
        return "climax"
    elif position < 0.9:
        return "development_2"
    else:
        return "close"


def filter_by_transitions(
    candidates: list[str],
    previous: str | None,
) -> list[str]:
    """Filter candidates by transition rules."""
    if previous is None:
        return candidates
    valid = TRANSITIONS.get(previous, candidates)
    filtered = [c for c in candidates if c in valid]
    return filtered if filtered else candidates[:1]


def filter_by_occurrences(
    candidates: list[str],
    history: list[str],
) -> list[str]:
    """Filter out treatments that have hit their max occurrences."""
    counts: dict[str, int] = {}
    for t in history:
        counts[t] = counts.get(t, 0) + 1

    filtered = []
    for c in candidates:
        max_occ = MAX_OCCURRENCES.get(c, 999)
        if counts.get(c, 0) < max_occ:
            filtered.append(c)

    return filtered if filtered else candidates[:1]


def filter_by_avoid(
    candidates: list[str],
    avoid: list[str] | None,
) -> list[str]:
    """Remove avoided treatments."""
    if not avoid:
        return candidates
    filtered = [c for c in candidates if c not in avoid]
    return filtered if filtered else candidates


def select_treatment(
    candidates: list[str],
    history: list[str],
    seed: int,
) -> str:
    """Select treatment from candidates with some variety bias."""
    if not candidates:
        return "statement"

    # Prefer treatments not recently used
    recent = set(history[-3:]) if len(history) >= 3 else set(history)
    preferred = [c for c in candidates if c not in recent]

    if preferred:
        # Simple deterministic selection based on seed and position
        return preferred[(seed + len(history)) % len(preferred)]

    return candidates[(seed + len(history)) % len(candidates)]


def generate_treatment_sequence(
    profile: TreatmentProfile,
    seed: int = 0,
) -> list[str]:
    """Generate a treatment sequence for the given profile.

    Args:
        profile: TreatmentProfile with phrase_count, climax_position, etc.
        seed: Random seed for deterministic generation

    Returns:
        List of treatment names, one per phrase
    """
    treatments: list[str] = []
    n = profile.phrase_count

    for i in range(n):
        position = i / max(1, n - 1) if n > 1 else 0.5

        # Force start and end treatments
        if i == 0:
            treatments.append(profile.start_with)
            continue
        if i == 1 and profile.second_phrase:
            treatments.append(profile.second_phrase)
            continue
        if i == n - 1:
            treatments.append(profile.end_with)
            continue

        # Get region and pool
        region = get_region_for_position(position, profile.climax_position)
        pool = TREATMENT_POOLS.get(region, ["statement"])

        # Apply filters
        candidates = list(pool)
        candidates = filter_by_transitions(candidates, treatments[-1] if treatments else None)
        candidates = filter_by_occurrences(candidates, treatments)
        candidates = filter_by_avoid(candidates, profile.must_avoid)

        # Add must_include if we're running out of opportunities
        remaining = n - i - 1  # phrases left (excluding this one)
        if profile.must_include:
            missing = [t for t in profile.must_include if t not in treatments]
            if missing and remaining <= len(missing):
                # Force a missing treatment
                for m in missing:
                    if m in TRANSITIONS.get(treatments[-1], [m]):
                        candidates = [m]
                        break

        # Select
        treatment = select_treatment(candidates, treatments, seed)
        treatments.append(treatment)

    return treatments


def load_genre_constraints(genre: str) -> dict:
    """Load genre-specific treatment constraints."""
    try:
        with open(DATA_DIR / "genres" / f"{genre}.yaml", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data.get("treatment_constraints", {})
    except FileNotFoundError:
        return {}


def generate_for_genre(
    genre: str,
    phrase_count: int,
    climax_position: float = 0.7,
    seed: int = 0,
) -> list[str]:
    """Generate treatment sequence with genre-specific constraints.

    Args:
        genre: Genre name (e.g., "invention", "fugue")
        phrase_count: Number of phrases
        climax_position: Where climax falls (0.0-1.0)
        seed: Random seed

    Returns:
        List of treatment names
    """
    constraints = load_genre_constraints(genre)

    profile = TreatmentProfile(
        phrase_count=phrase_count,
        climax_position=climax_position,
        must_include=constraints.get("must_include"),
        must_avoid=constraints.get("must_avoid"),
        start_with=constraints.get("start_with", "statement"),
        end_with=constraints.get("end_with", "statement"),
        second_phrase=constraints.get("second_phrase"),
    )

    return generate_treatment_sequence(profile, seed)

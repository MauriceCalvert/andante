"""Dynamic treatment sequence generator.

Generates structurally-appropriate treatment sequences based on:
- phrase_count: number of phrases to fill
- climax_position: where the climax falls (0.0-1.0)
- genre: optional genre-specific constraints from TreatmentsConfig

Replaces static `treatments: [...]` arrays in arcs.yaml with
dynamically generated sequences that respect musical structure.
"""
from dataclasses import dataclass

from builder.types import GenreConfig, TreatmentsConfig


# Structural regions as fraction of piece
REGIONS = {
    "exposition": (0.0, 0.15),    # Opening statement
    "development_1": (0.15, 0.4), # First development phase
    "climax": (0.4, 0.7),         # Climax region (adjusted by climax_position)
    "development_2": (0.7, 0.85), # Return/recapitulation
    "close": (0.85, 1.0),         # Final statement and cadence
}

# Treatment pools by region (used when genre has optional treatments)
TREATMENT_POOLS: dict[str, list[str]] = {
    "exposition": ["statement"],
    "development_1": ["imitation", "transposition", "inversion", "dialogue"],
    "climax": ["stretto", "fragmentation", "augmentation", "diminution"],
    "development_2": ["transposition", "imitation", "inversion"],
    "close": ["statement"],
}

# Transition rules: what can follow what
TRANSITIONS: dict[str, list[str]] = {
    "statement": ["imitation", "transposition", "stretto", "inversion", "dialogue", "statement"],
    "imitation": ["transposition", "inversion", "statement", "stretto", "fragmentation"],
    "transposition": ["statement", "imitation", "inversion", "stretto", "fragmentation", "transposition"],
    "inversion": ["transposition", "statement", "imitation", "stretto"],
    "stretto": ["fragmentation", "transposition", "statement", "augmentation"],
    "fragmentation": ["transposition", "imitation", "statement", "stretto"],
    "augmentation": ["diminution", "transposition", "statement"],
    "diminution": ["transposition", "statement", "stretto"],
    "dialogue": ["imitation", "transposition", "statement", "inversion"],
    "melody_accompaniment": ["melody_accompaniment"],
}

# Treatments that should appear at most N times
MAX_OCCURRENCES: dict[str, int] = {
    "stretto": 2,
    "fragmentation": 2,
    "augmentation": 1,
    "diminution": 1,
}


@dataclass
class TreatmentProfile:
    """Profile for treatment generation."""
    phrase_count: int
    climax_position: float = 0.7
    must_include: list[str] | None = None
    must_avoid: list[str] | None = None
    start_with: str = "statement"
    end_with: str = "statement"
    second_phrase: str | None = None
    available_pool: list[str] | None = None


def get_region_for_position(position: float, climax_pos: float) -> str:
    """Determine structural region for a given position."""
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
    recent = set(history[-3:]) if len(history) >= 3 else set(history)
    preferred = [c for c in candidates if c not in recent]
    if preferred:
        return preferred[(seed + len(history)) % len(preferred)]
    return candidates[(seed + len(history)) % len(candidates)]


def generate_treatment_sequence(
    profile: TreatmentProfile,
    seed: int = 0,
) -> list[str]:
    """Generate a treatment sequence for the given profile."""
    treatments: list[str] = []
    n = profile.phrase_count
    for i in range(n):
        position = i / max(1, n - 1) if n > 1 else 0.5
        if i == 0:
            treatments.append(profile.start_with)
            continue
        if i == 1 and profile.second_phrase:
            treatments.append(profile.second_phrase)
            continue
        if i == n - 1:
            treatments.append(profile.end_with)
            continue
        if profile.available_pool:
            candidates = list(profile.available_pool)
        else:
            region = get_region_for_position(position, profile.climax_position)
            candidates = list(TREATMENT_POOLS.get(region, ["statement"]))
        candidates = filter_by_transitions(candidates, treatments[-1] if treatments else None)
        candidates = filter_by_occurrences(candidates, treatments)
        candidates = filter_by_avoid(candidates, profile.must_avoid)
        remaining = n - i - 1
        if profile.must_include:
            missing = [t for t in profile.must_include if t not in treatments]
            if missing and remaining <= len(missing):
                for m in missing:
                    if m in TRANSITIONS.get(treatments[-1], [m]):
                        candidates = [m]
                        break
        treatment = select_treatment(candidates, treatments, seed)
        treatments.append(treatment)
    return treatments


def profile_from_genre(genre_config: GenreConfig) -> TreatmentProfile:
    """Create TreatmentProfile from genre's TreatmentsConfig."""
    tc: TreatmentsConfig = genre_config.treatments
    available: list[str] = list(tc.required) + list(tc.optional)
    return TreatmentProfile(
        phrase_count=0,
        must_include=list(tc.required),
        start_with=tc.opening,
        end_with=tc.opening,
        second_phrase=tc.answer if tc.answer != tc.opening else None,
        available_pool=available if available else None,
    )


def generate_for_genre(
    genre_config: GenreConfig,
    phrase_count: int,
    climax_position: float = 0.7,
    seed: int = 0,
) -> list[str]:
    """Generate treatment sequence using genre's TreatmentsConfig.

    Args:
        genre_config: Genre configuration with treatments
        phrase_count: Number of phrases
        climax_position: Where climax falls (0.0-1.0)
        seed: Random seed

    Returns:
        List of treatment names
    """
    profile = profile_from_genre(genre_config)
    profile = TreatmentProfile(
        phrase_count=phrase_count,
        climax_position=climax_position,
        must_include=profile.must_include,
        must_avoid=profile.must_avoid,
        start_with=profile.start_with,
        end_with=profile.end_with,
        second_phrase=profile.second_phrase,
        available_pool=profile.available_pool,
    )
    return generate_treatment_sequence(profile, seed)

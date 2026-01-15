"""Episode generator: constraint-based episode sequence generation."""
import random
from pathlib import Path

import yaml

from planner.plannertypes import EpisodeSpec, MacroSection

DATA_DIR = Path(__file__).parent.parent / "data"
_constraints: dict | None = None


def load_constraints() -> dict:
    """Load episode constraints from YAML."""
    global _constraints
    if _constraints is None:
        with open(DATA_DIR / "episode_constraints.yaml", encoding="utf-8") as f:
            _constraints = yaml.safe_load(f)
    return _constraints


def get_first_candidates(character: str) -> list[str]:
    """Get valid first episode types for a character."""
    constraints: dict = load_constraints()
    first_map: dict = constraints["first_episode"]
    return first_map.get(character, ["statement"])


def get_valid_transitions(episode_type: str) -> list[str]:
    """Get valid next episode types after given type."""
    constraints: dict = load_constraints()
    transitions: dict = constraints["transitions"]
    return transitions.get(episode_type, ["cadential"])


def get_energy_profile(episode_type: str) -> str:
    """Get energy profile for an episode type."""
    constraints: dict = load_constraints()
    profiles: dict = constraints["energy_profiles"]
    return profiles.get(episode_type, "stable")


def filter_by_repetition(candidates: list[str], history: list[EpisodeSpec]) -> list[str]:
    """Filter out episodes that violate repetition constraints."""
    if not candidates:
        return candidates
    result: list[str] = []
    type_counts: dict[str, int] = {}
    for ep in history:
        type_counts[ep.type] = type_counts.get(ep.type, 0) + 1
    last_type: str | None = history[-1].type if history else None
    for candidate in candidates:
        if type_counts.get(candidate, 0) >= 2:
            continue
        if candidate == last_type:
            continue
        result.append(candidate)
    return result if result else candidates[:1]


def filter_by_energy(
    candidates: list[str],
    history: list[EpisodeSpec],
    energy_arc: str,
    remaining_bars: int,
) -> list[str]:
    """Filter candidates by energy arc constraints."""
    if not candidates:
        return candidates
    constraints: dict = load_constraints()
    arc_rules: dict = constraints.get("energy_arc_rules", {})
    rule: dict = arc_rules.get(energy_arc, {})
    allowed: list[str] | None = rule.get("allowed")
    required_end: str | None = rule.get("required_end")
    must_contain: list[str] | None = rule.get("must_contain")
    result: list[str] = []
    for candidate in candidates:
        profile: str = get_energy_profile(candidate)
        if allowed and profile not in allowed:
            continue
        if remaining_bars <= 8 and required_end and profile != required_end:
            if candidate != "cadential":
                continue
        result.append(candidate)
    if must_contain and remaining_bars > 8:
        has_peak: bool = any(get_energy_profile(ep.type) == "peak" for ep in history)
        if not has_peak:
            peak_candidates: list[str] = [
                c for c in result if get_energy_profile(c) == "peak"
            ]
            if peak_candidates and remaining_bars <= 16:
                return peak_candidates
    return result if result else candidates


def weight_by_affinity(candidates: list[str], character: str) -> list[tuple[str, float]]:
    """Weight candidates by character affinity (soft constraint)."""
    constraints: dict = load_constraints()
    affinity: dict = constraints.get("character_affinity", {}).get(character, {})
    preferred: list[str] = affinity.get("preferred", [])
    avoided: list[str] = affinity.get("avoided", [])
    weighted: list[tuple[str, float]] = []
    for candidate in candidates:
        weight: float = 1.0
        if candidate in preferred:
            weight = 3.0
        elif candidate in avoided:
            weight = 0.3
        weighted.append((candidate, weight))
    return weighted


def select_episode(weighted: list[tuple[str, float]], rng: random.Random) -> str:
    """Select episode using weighted random choice."""
    if not weighted:
        return "cadential"
    total: float = sum(w for _, w in weighted)
    r: float = rng.random() * total
    cumulative: float = 0.0
    for episode_type, weight in weighted:
        cumulative += weight
        if r <= cumulative:
            return episode_type
    return weighted[-1][0]


def _get_peak_episode_types() -> list[str]:
    """Get episode types with peak energy profile."""
    constraints: dict = load_constraints()
    profiles: dict = constraints["energy_profiles"]
    return [ep_type for ep_type, profile in profiles.items() if profile == "peak"]


def _get_climax_characters() -> list[str]:
    """Get characters that require a peak-energy episode."""
    constraints: dict = load_constraints()
    return constraints.get("climax_characters", [])


def _ensure_climax_episode(
    episodes: list[EpisodeSpec], character: str
) -> list[EpisodeSpec]:
    """Ensure climax characters have a peak-energy episode."""
    climax_chars: list[str] = _get_climax_characters()
    if character not in climax_chars:
        return episodes
    peak_types: list[str] = _get_peak_episode_types()
    has_peak: bool = any(ep.type in peak_types for ep in episodes)
    if has_peak:
        return episodes
    # Find best episode to replace (not first, not cadential)
    best_idx: int = -1
    for i, ep in enumerate(episodes):
        if i == 0 or ep.type == "cadential":
            continue
        best_idx = i
        break
    if best_idx < 0 and len(episodes) > 1:
        best_idx = 1
    if best_idx >= 0:
        ep: EpisodeSpec = episodes[best_idx]
        replacement: str = character if character in peak_types else peak_types[0]
        episodes[best_idx] = EpisodeSpec(type=replacement, bars=ep.bars)
    return episodes


def generate_episodes(section: MacroSection, seed: int | None = None) -> tuple[EpisodeSpec, ...]:
    """Generate episode sequence satisfying all constraints."""
    rng: random.Random = random.Random(seed)
    target_bars: int = section.bars
    character: str = section.character
    energy_arc: str = section.energy_arc
    first_candidates: list[str] = get_first_candidates(character)
    episodes: list[EpisodeSpec] = []
    allocated: int = 0
    max_iterations: int = 100
    iteration: int = 0
    while allocated < target_bars and iteration < max_iterations:
        iteration += 1
        remaining: int = target_bars - allocated
        if remaining <= 4:
            episodes.append(EpisodeSpec(type="cadential", bars=remaining))
            allocated += remaining
            break
        if not episodes:
            candidates: list[str] = first_candidates
        else:
            candidates = get_valid_transitions(episodes[-1].type)
            if not candidates:
                episodes.append(EpisodeSpec(type="cadential", bars=remaining))
                allocated += remaining
                break
        candidates = filter_by_repetition(candidates, episodes)
        candidates = filter_by_energy(candidates, episodes, energy_arc, remaining)
        weighted: list[tuple[str, float]] = weight_by_affinity(candidates, character)
        selected: str = select_episode(weighted, rng)
        episodes.append(EpisodeSpec(type=selected, bars=4))
        allocated += 4
    if allocated < target_bars:
        diff: int = target_bars - allocated
        if episodes:
            last: EpisodeSpec = episodes[-1]
            episodes[-1] = EpisodeSpec(type=last.type, bars=last.bars + diff)
        else:
            episodes.append(EpisodeSpec(type="cadential", bars=diff))
    episodes = _ensure_climax_episode(episodes, character)
    return tuple(episodes)

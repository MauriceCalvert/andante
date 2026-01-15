"""Affect profile loader for Affektenlehre system.

Loads musical characteristics from affects.yaml and provides scoring
functions for subject generation.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class AffectProfile:
    """Musical characteristics for an affect."""
    name: str
    mode: str
    tempo: str
    interval_profile: str  # stepwise, leaps, mixed
    contour: str  # ascending, descending, arch, wave
    rhythm_density: str  # sparse, moderate, dense
    chromaticism: str  # none, light, heavy


_affects_cache: dict[str, AffectProfile] | None = None


def _load_affects() -> dict[str, AffectProfile]:
    """Load all affect profiles from YAML."""
    path = DATA_DIR / "affects.yaml"
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)

    profiles: dict[str, AffectProfile] = {}
    for name, defn in data.items():
        if not isinstance(defn, dict):
            continue
        profiles[name] = AffectProfile(
            name=name,
            mode=defn.get("mode", "major"),
            tempo=defn.get("tempo", "andante"),
            interval_profile=defn.get("interval_profile", "mixed"),
            contour=defn.get("contour", "wave"),
            rhythm_density=defn.get("rhythm_density", "moderate"),
            chromaticism=defn.get("chromaticism", "none"),
        )
    return profiles


def get_affect_profile(affect: str) -> Optional[AffectProfile]:
    """Get the musical profile for an affect."""
    global _affects_cache
    if _affects_cache is None:
        _affects_cache = _load_affects()
    return _affects_cache.get(affect)


def score_subject_affect(
    degrees: tuple[int, ...],
    durations: tuple[float, ...],
    profile: AffectProfile,
) -> float:
    """Score how well a subject matches an affect's musical profile.

    Args:
        degrees: Scale degree sequence (0-6)
        durations: Note durations
        profile: The affect profile to score against

    Returns:
        Score from 0.0 to 1.0 (higher = better match)
    """
    if not degrees or len(degrees) < 2:
        return 0.5

    score = 0.0
    max_score = 0.0

    # 1. Interval profile scoring
    max_score += 1.0
    intervals = [abs(degrees[i + 1] - degrees[i]) for i in range(len(degrees) - 1)]
    steps = sum(1 for iv in intervals if iv <= 1)
    leaps = sum(1 for iv in intervals if iv >= 3)
    step_ratio = steps / len(intervals) if intervals else 0.5

    if profile.interval_profile == "stepwise":
        score += step_ratio  # Higher = better for stepwise
    elif profile.interval_profile == "leaps":
        score += (1.0 - step_ratio)  # Higher = better for leaps
    else:  # mixed
        score += 0.5 + (0.5 - abs(0.5 - step_ratio))  # Balanced is best

    # 2. Contour scoring
    max_score += 1.0
    net_motion = degrees[-1] - degrees[0]

    if profile.contour == "ascending":
        score += min(1.0, max(0.0, net_motion / 4))  # Upward motion
    elif profile.contour == "descending":
        score += min(1.0, max(0.0, -net_motion / 4))  # Downward motion
    elif profile.contour == "arch":
        # Check for rise then fall
        mid = len(degrees) // 2
        if mid > 0:
            first_half = degrees[mid] - degrees[0]
            second_half = degrees[-1] - degrees[mid]
            if first_half > 0 and second_half < 0:
                score += 1.0
            elif first_half > 0 or second_half < 0:
                score += 0.5
    else:  # wave
        # Count direction changes
        changes = sum(
            1 for i in range(len(intervals) - 1)
            if (intervals[i] > 0) != (intervals[i + 1] > 0)
        ) if len(intervals) > 1 else 0
        score += min(1.0, changes / 3)  # More changes = more wave-like

    # 3. Rhythm density scoring
    max_score += 1.0
    avg_dur = sum(durations) / len(durations) if durations else 0.25

    if profile.rhythm_density == "sparse":
        score += min(1.0, avg_dur / 0.5)  # Longer notes = better
    elif profile.rhythm_density == "dense":
        score += min(1.0, 0.25 / avg_dur) if avg_dur > 0 else 0.5  # Shorter = better
    else:  # moderate
        # Penalize extremes
        if 0.125 <= avg_dur <= 0.375:
            score += 1.0
        elif 0.0625 <= avg_dur <= 0.5:
            score += 0.5
        else:
            score += 0.2

    return score / max_score if max_score > 0 else 0.5

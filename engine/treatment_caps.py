"""Treatment capability interdictions.

Treatments declare what they FORBID. Everything else is allowed by default.
"""
from functools import lru_cache
from pathlib import Path

import yaml

DATA_DIR: Path = Path(__file__).parent.parent / "data"
_TREATMENTS: dict = yaml.safe_load(open(DATA_DIR / "treatments.yaml", encoding="utf-8"))

# Known capabilities - add new ones here as features are added
KNOWN_CAPABILITIES: frozenset[str] = frozenset({
    "energy_shift",
    "climax_boost",
    "inner_voice_gen",
    "ornaments",
    "voice_crossing_penalty",
})

# Transforms that modify rhythm (not just pitch)
# If soprano uses these, bass must use the same to preserve CS consonance alignment
RHYTHM_TRANSFORMS: frozenset[str] = frozenset({"augment", "diminish"})


@lru_cache(maxsize=64)
def get_interdictions(treatment: str | None) -> frozenset[str]:
    """Return set of forbidden capabilities for treatment.

    Empty set means everything allowed (default).
    """
    if treatment is None:
        return frozenset()
    t_config = _TREATMENTS.get(treatment, {})
    return frozenset(t_config.get("interdictions", []))


def allows(treatment: str | None, capability: str) -> bool:
    """Check if treatment allows a capability."""
    return capability not in get_interdictions(treatment)


def validate_treatments() -> list[str]:
    """Return list of errors for treatment configuration.

    Call at startup to catch typos and inconsistencies in treatments.yaml.
    """
    errors: list[str] = []
    for name, config in _TREATMENTS.items():
        # Check for unknown interdictions
        for cap in config.get("interdictions", []):
            if cap not in KNOWN_CAPABILITIES:
                errors.append(f"{name}: unknown interdiction '{cap}'")

        bass_source = config.get("bass_source", "counter_subject")  # default is CS
        bass_delay = config.get("bass_delay")

        # bass_delay is forbidden with counter_subject - CS was generated for delay=0
        # Any delay breaks the consonance alignment CP-SAT verified
        if bass_delay is not None and bass_source == "counter_subject":
            errors.append(
                f"{name}: bass_delay={bass_delay} forbidden with bass_source='counter_subject'. "
                f"CS consonance alignment requires delay=0."
            )

        # Check rhythm transform consistency: if soprano rhythm changes, bass must match
        # ONLY when bass uses counter_subject (CS alignment depends on matching rhythms)
        # Other bass sources (sustained, accompaniment) don't have this constraint
        soprano_transform = config.get("soprano_transform", "none")
        bass_transform = config.get("bass_transform", "none")
        if soprano_transform in RHYTHM_TRANSFORMS and bass_source == "counter_subject":
            if bass_transform != soprano_transform:
                errors.append(
                    f"{name}: soprano_transform='{soprano_transform}' modifies rhythm, "
                    f"but bass_transform='{bass_transform}' does not match. "
                    f"CS consonance alignment will be broken."
                )
    return errors


def validate_or_raise() -> None:
    """Validate treatments and raise if any errors found."""
    errors = validate_treatments()
    if errors:
        raise ValueError(f"Invalid treatment interdictions:\n  " + "\n  ".join(errors))

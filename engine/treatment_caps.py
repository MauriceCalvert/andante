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
    """Return list of errors for unknown interdictions.

    Call at startup to catch typos in treatments.yaml.
    """
    errors: list[str] = []
    for name, config in _TREATMENTS.items():
        for cap in config.get("interdictions", []):
            if cap not in KNOWN_CAPABILITIES:
                errors.append(f"{name}: unknown interdiction '{cap}'")
    return errors


def validate_or_raise() -> None:
    """Validate treatments and raise if any errors found."""
    errors = validate_treatments()
    if errors:
        raise ValueError(f"Invalid treatment interdictions:\n  " + "\n  ".join(errors))

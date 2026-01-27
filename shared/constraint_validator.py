"""Validate semantic constraints on Brief and Frame.

Ensures musically valid combinations before planning begins.
"""
from pathlib import Path
from typing import Any

import yaml

from builder.config_loader import load_genre_raw


DATA_DIR: Path = Path(__file__).parent.parent / "data"
_constraints_cache: dict[str, Any] | None = None


def load_constraints() -> dict[str, Any]:
    """Load constraints.yaml with caching."""
    global _constraints_cache
    if _constraints_cache is None:
        with open(DATA_DIR / "rules" / "constraints.yaml") as f:
            _constraints_cache = yaml.safe_load(f)
    return _constraints_cache


def get_genre_metre(genre: str) -> str | None:
    """Get metre from genre definition."""
    data: dict[str, Any] = load_genre_raw(genre)
    return data.get("metre")


def get_genre_voices(genre: str) -> int | None:
    """Get voice count from genre definition."""
    data: dict[str, Any] = load_genre_raw(genre)
    return data.get("voices")


def get_genre_form(genre: str) -> str | None:
    """Get form from genre definition."""
    data: dict[str, Any] = load_genre_raw(genre)
    return data.get("form")


def check_rule(
    rule: dict[str, Any],
    context: dict[str, Any],
) -> str | None:
    """Check a single constraint rule. Returns error message or None."""
    when: dict[str, Any] | None = rule.get("when")
    if when:
        for field, expected in when.items():
            actual: Any = context.get(field)
            if actual != expected:
                return None
    require: dict[str, list[Any]] | None = rule.get("require")
    if require:
        for field, allowed in require.items():
            actual = context.get(field)
            if actual is not None and actual not in allowed:
                return rule.get("message", f"{field}={actual} not in {allowed}")
    forbid: dict[str, list[Any]] | None = rule.get("forbid")
    if forbid:
        for field, forbidden in forbid.items():
            actual = context.get(field)
            if actual in forbidden:
                return rule.get("message", f"{field}={actual} is forbidden")
    return None


def validate_brief(
    genre: str,
    affect: str,
    bars: int,
) -> tuple[bool, list[str]]:
    """Validate Brief parameters. Returns (valid, errors)."""
    constraints: dict[str, Any] = load_constraints()
    errors: list[str] = []
    genre_def: dict[str, Any] = load_genre_raw(genre)
    metre: str | None = genre_def.get("metre")
    voices: int | None = genre_def.get("voices")
    form: str | None = genre_def.get("form")
    context: dict[str, Any] = {
        "genre": genre,
        "affect": affect,
        "bars": bars,
        "metre": metre,
        "voices": voices,
        "form": form,
    }
    for category in ["genre", "affect"]:
        rules: dict[str, Any] = constraints.get(category, {})
        for rule_name, rule in rules.items():
            error: str | None = check_rule(rule, context)
            if error:
                errors.append(error)
    struct_rules: dict[str, Any] = constraints.get("structure", {})
    if "minimum_bars" in struct_rules:
        min_bars: int = struct_rules["minimum_bars"]["require"]["min_bars"]
        if bars < min_bars:
            errors.append(struct_rules["minimum_bars"]["message"])
    return len(errors) == 0, errors


def validate_frame(
    genre: str,
    affect: str,
    tonic: str,
    mode: str,
    metre: str,
    tempo: str,
    voices: int,
    form: str,
) -> tuple[bool, list[str]]:
    """Validate Frame parameters against constraints. Returns (valid, errors)."""
    constraints: dict[str, Any] = load_constraints()
    errors: list[str] = []
    context: dict[str, Any] = {
        "genre": genre,
        "affect": affect,
        "tonic": tonic,
        "mode": mode,
        "metre": metre,
        "tempo": tempo,
        "voices": voices,
        "form": form,
    }
    for category in ["genre", "affect", "arc"]:
        rules: dict[str, Any] = constraints.get(category, {})
        for rule_name, rule in rules.items():
            error: str | None = check_rule(rule, context)
            if error:
                errors.append(error)
    return len(errors) == 0, errors


def validate_plan_structure(
    sections: list[dict[str, Any]],
    form: str,
    bars_per_phrase: int,
    total_bars: int,
) -> tuple[bool, list[str]]:
    """Validate planned structure. Returns (valid, errors)."""
    constraints: dict[str, Any] = load_constraints()
    errors: list[str] = []
    form_rules: dict[str, Any] = constraints.get("form", {})
    context: dict[str, Any] = {
        "form": form,
        "section_count": len(sections),
    }
    for rule_name, rule in form_rules.items():
        error: str | None = check_rule(rule, context)
        if error:
            errors.append(error)
    struct_rules: dict[str, Any] = constraints.get("structure", {})
    if sections:
        last_cadence: str | None = sections[-1].get("final_cadence")
        if "last_cadence_authentic" in struct_rules:
            allowed: list[str] = struct_rules["last_cadence_authentic"]["require"]["last_section_cadence"]
            if last_cadence not in allowed:
                errors.append(struct_rules["last_cadence_authentic"]["message"])
    if "bars_divisible_by_phrase" in struct_rules and bars_per_phrase > 0:
        if total_bars % bars_per_phrase != 0:
            errors.append(struct_rules["bars_divisible_by_phrase"]["message"])
    return len(errors) == 0, errors


if __name__ == "__main__":
    print("Testing constraint validation...")
    valid, errors = validate_brief("minuet", "maestoso", 16)
    print(f"minuet/maestoso/16: valid={valid}, errors={errors}")
    valid, errors = validate_frame(
        genre="minuet",
        affect="maestoso",
        tonic="C",
        mode="major",
        metre="3/4",
        tempo="allegro",
        voices=2,
        form="binary",
    )
    print(f"Valid minuet frame: valid={valid}, errors={errors}")
    valid, errors = validate_frame(
        genre="minuet",
        affect="maestoso",
        tonic="C",
        mode="major",
        metre="4/4",
        tempo="allegro",
        voices=2,
        form="binary",
    )
    print(f"Invalid minuet (4/4): valid={valid}, errors={errors}")

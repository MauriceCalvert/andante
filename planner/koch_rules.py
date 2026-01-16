"""Koch's mechanical rules for melodic structure.

Source: Heinrich Christoph Koch, Versuch einer Anleitung zur Composition (1782-1793)

This module validates phrase sequences and period structure according to Koch's rules:
- Phrase sequence constraints (I->I forbidden, V->V in same key forbidden, etc.)
- Period structure recommendations (16-bar standard)
- Modulation rules for first cadence
"""
from dataclasses import dataclass
from pathlib import Path

import yaml

from planner.plannertypes import Plan, Phrase

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class KochViolation:
    """A violation of Koch's rules."""

    rule_id: str
    severity: str  # "blocker" | "warning"
    message: str
    phrase_index: int | None = None


def load_koch_config() -> dict:
    """Load Koch rules configuration."""
    with open(DATA_DIR / "koch_rules.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def classify_phrase(phrase: Phrase, mode: str) -> str:
    """Classify phrase as I-phrase, V-phrase, or cadence.

    Koch distinguishes:
    - I-phrase (Grundabsatz): Caesura on tonic triad
    - V-phrase (Quintabsatz): Caesura on dominant triad
    - Closing phrase (Schlußsatz): Contains formal cadence
    """
    # A phrase with authentic cadence is a closing phrase
    if phrase.cadence == "authentic":
        return "cadence"

    target = phrase.tonal_target.upper()

    # I-phrase: tonal target is tonic
    if target == "I":
        return "I-phrase"

    # V-phrase: tonal target is dominant
    if target == "V":
        return "V-phrase"

    # Minor mode: lowercase 'i' also counts as I-phrase
    if mode == "minor" and phrase.tonal_target.lower() == "i":
        return "I-phrase"

    # Minor mode: 'v' counts as V-phrase
    if mode == "minor" and phrase.tonal_target.lower() == "v":
        return "V-phrase"

    # Other targets (III, iv, vi, etc.)
    return "other"


def check_phrase_sequence(phrases: list[Phrase], mode: str) -> list[KochViolation]:
    """Check phrase sequence rules (Koch sections 34-37).

    Rules:
    - Koch's rule 35: Two I-phrases in succession produce unpleasant effect
    - Koch's rule 36: Two V-phrases prohibited in same key (allowed in different keys)
    - Koch's rule 37: Opening V-phrase should NOT be followed by I-phrase

    Explicitly allowed transitions:
    - I → V (tonic to dominant): natural progression
    - I → CAD: tonic phrase to cadence
    - V → CAD: dominant phrase to cadence
    - V → V in different keys: modulating sequence
    """
    violations: list[KochViolation] = []
    config = load_koch_config()
    seq_config = config.get("phrase_sequence", {})

    # Define explicitly allowed transitions
    ALLOWED_TRANSITIONS: set[tuple[str, str]] = {
        ("I-phrase", "V-phrase"),    # I → V: natural progression
        ("I-phrase", "cadence"),     # I → CAD: tonic to cadence
        ("V-phrase", "cadence"),     # V → CAD: dominant to cadence
        ("V-phrase", "I-phrase"),    # V → I: allowed except at composition start
        ("cadence", "I-phrase"),     # After cadence, new I-phrase is fine
        ("cadence", "V-phrase"),     # After cadence, new V-phrase is fine
        ("other", "I-phrase"),       # Transitional → I
        ("other", "V-phrase"),       # Transitional → V
        ("other", "cadence"),        # Transitional → cadence
        ("I-phrase", "other"),       # I → transitional
        ("V-phrase", "other"),       # V → transitional
    }

    for i in range(1, len(phrases)):
        prev_class = classify_phrase(phrases[i - 1], mode)
        curr_class = classify_phrase(phrases[i], mode)
        transition = (prev_class, curr_class)

        # Koch's rule 35: Two I-phrases in succession forbidden
        if seq_config.get("i_i_forbidden", True):
            if prev_class == "I-phrase" and curr_class == "I-phrase":
                violations.append(
                    KochViolation(
                        rule_id="koch_ii",
                        severity="blocker",
                        message=f"Koch's rule 35: Two I-phrases in succession (phrases {i - 1}, {i})",
                        phrase_index=i,
                    )
                )

        # Koch's rule 36: Two V-phrases forbidden in same key
        if seq_config.get("v_v_same_key_forbidden", True):
            if prev_class == "V-phrase" and curr_class == "V-phrase":
                # Check if same key - "different_key_only" exception
                prev_target = phrases[i - 1].tonal_target.upper()
                curr_target = phrases[i].tonal_target.upper()
                if prev_target == curr_target:
                    violations.append(
                        KochViolation(
                            rule_id="koch_vv",
                            severity="blocker",
                            message=f"Koch's rule 36: Two V-phrases in same key (phrases {i - 1}, {i})",
                            phrase_index=i,
                        )
                    )
                # V → V in different keys is allowed (modulating sequence)

        # Koch's rule 37: V→I forbidden at composition start
        if seq_config.get("vi_start_forbidden", True):
            if i == 1 and prev_class == "V-phrase" and curr_class == "I-phrase":
                violations.append(
                    KochViolation(
                        rule_id="koch_vi_start",
                        severity="blocker",
                        message="Koch's rule 37: V-phrase followed by I-phrase at start",
                        phrase_index=i,
                    )
                )

    return violations


def validate_caesura(phrase: Phrase, mode: str) -> list[KochViolation]:
    """Validate caesura placement according to Koch's rules.

    Koch's caesura rules:
    1. Caesura (phrase ending) must fall on a strong beat
    2. Bass note at caesura should be root position (not 6th chord)
       - Exception: incises (incomplete phrases) may use 6th chord
    3. Caesura chord must match phrase type:
       - I-phrase: tonic chord
       - V-phrase: dominant chord

    Args:
        phrase: The phrase to validate
        mode: "major" or "minor"

    Returns:
        List of violations found
    """
    violations: list[KochViolation] = []

    # Check if phrase has a cadence (caesura indicator)
    if phrase.cadence is None:
        return violations  # No caesura to validate

    phrase_class = classify_phrase(phrase, mode)
    target = phrase.tonal_target.upper()

    # Rule 3: Caesura chord must match phrase type
    if phrase_class == "I-phrase" and target != "I":
        # I-phrase should end on tonic
        if phrase.cadence != "authentic":  # Authentic cadence is always on tonic
            violations.append(
                KochViolation(
                    rule_id="koch_caesura_mismatch",
                    severity="warning",
                    message=f"I-phrase caesura should be on tonic, got {target}",
                    phrase_index=phrase.index,
                )
            )

    if phrase_class == "V-phrase" and target != "V":
        # V-phrase should end on dominant
        if phrase.cadence not in ("half", "authentic"):
            violations.append(
                KochViolation(
                    rule_id="koch_caesura_mismatch",
                    severity="warning",
                    message=f"V-phrase caesura should be on dominant, got {target}",
                    phrase_index=phrase.index,
                )
            )

    return violations


def check_all_caesurae(phrases: list[Phrase], mode: str) -> list[KochViolation]:
    """Check all phrase caesurae in a sequence."""
    violations: list[KochViolation] = []
    for phrase in phrases:
        violations.extend(validate_caesura(phrase, mode))
    return violations


def check_period_structure(plan: Plan) -> list[KochViolation]:
    """Check period structure rules (Koch sections 22-30).

    Koch's rule 22: Shortest compositions usually 16 measures (4 four-measure phrases).
    This is a soft constraint (warning only).
    """
    violations: list[KochViolation] = []
    config = load_koch_config()
    period_config = config.get("period_structure", {})

    total_bars = sum(
        p.bars for s in plan.structure.sections for e in s.episodes for p in e.phrases
    )

    standard_bars = period_config.get("standard_bars", [8, 16, 24, 32])
    if total_bars not in standard_bars:
        violations.append(
            KochViolation(
                rule_id="koch_period_length",
                severity="warning",
                message=f"Koch's rule 22: Non-standard period length ({total_bars} bars, prefer {standard_bars})",
                phrase_index=None,
            )
        )

    return violations


def check_modulation_rules(plan: Plan) -> list[KochViolation]:
    """Check modulation rules (Koch section 30).

    Koch's rule 30:
    - Major mode first period: Cadence in V (dominant)
    - Minor mode first period: Cadence in v (minor dominant) OR III (relative major)
    """
    violations: list[KochViolation] = []
    config = load_koch_config()
    mod_config = config.get("modulation", {})

    mode = plan.frame.mode

    # Find first cadence
    for section in plan.structure.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                if phrase.cadence in ("authentic", "half"):
                    target = phrase.tonal_target

                    # Major mode check
                    if mode == "major":
                        allowed = mod_config.get("major_first_cadence", ["I", "V"])
                        if target.upper() not in [a.upper() for a in allowed]:
                            violations.append(
                                KochViolation(
                                    rule_id="koch_modulation_major",
                                    severity="warning",
                                    message=f"Koch's rule 30: First cadence in major should be {allowed}, got {target}",
                                    phrase_index=phrase.index,
                                )
                            )

                    # Minor mode check
                    if mode == "minor":
                        allowed = mod_config.get("minor_first_cadence", ["i", "v", "III"])
                        normalized_target = target.lower() if target.islower() else target
                        normalized_allowed = [a.lower() if a.islower() else a for a in allowed]
                        if normalized_target not in normalized_allowed:
                            violations.append(
                                KochViolation(
                                    rule_id="koch_modulation_minor",
                                    severity="warning",
                                    message=f"Koch's rule 30: First cadence in minor should be {allowed}, got {target}",
                                    phrase_index=phrase.index,
                                )
                            )

                    # Only check first cadence
                    return violations

    return violations


def check_phrase_length(plan: Plan) -> list[KochViolation]:
    """Check phrase length preferences (Koch sections 86-95).

    Koch's rule 87: Four-measure phrases most common, useful, and pleasing.
    This is a soft constraint (warning only).
    """
    violations: list[KochViolation] = []
    config = load_koch_config()
    length_config = config.get("phrase_length", {})

    preferred = length_config.get("preferred", 4)
    allowed = length_config.get("allowed", [4, 5, 6, 7])

    for section in plan.structure.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                if phrase.bars not in allowed:
                    violations.append(
                        KochViolation(
                            rule_id="koch_phrase_length",
                            severity="warning",
                            message=f"Koch's rule 89: Unusual phrase length {phrase.bars} bars (allowed: {allowed})",
                            phrase_index=phrase.index,
                        )
                    )
                elif phrase.bars != preferred:
                    # Non-preferred but allowed length - very minor warning
                    pass  # Don't report, too noisy

    return violations


def validate_koch(plan: Plan) -> tuple[bool, list[KochViolation]]:
    """Run all Koch rule checks.

    Returns:
        (valid, violations) where valid is True if no blockers found.
    """
    all_phrases: list[Phrase] = [
        p for s in plan.structure.sections for e in s.episodes for p in e.phrases
    ]

    violations: list[KochViolation] = []
    violations.extend(check_phrase_sequence(all_phrases, plan.frame.mode))
    violations.extend(check_all_caesurae(all_phrases, plan.frame.mode))
    violations.extend(check_period_structure(plan))
    violations.extend(check_modulation_rules(plan))
    violations.extend(check_phrase_length(plan))

    blockers = [v for v in violations if v.severity == "blocker"]
    return (len(blockers) == 0, violations)

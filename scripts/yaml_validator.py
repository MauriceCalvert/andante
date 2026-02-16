"""Validate YAML data files for the Andante pipeline.

Comprehensive field-level, structural, and cross-reference validation.
Catches configuration errors early with actionable error messages.

Usage:
    python -m scripts.yaml_validator          # validate all
    python -m scripts.yaml_validator --force   # ignore timestamp cache
"""
import re
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from shared.constants import (
    VALID_BASS_MODES,
    VALID_BASS_TREATMENTS,
    VALID_HARMONIC_RHYTHMS,
    VALID_MOTIF_CHARACTERS,
    VALID_PHRASE_POSITIONS,
    VALID_TEXTURES,
)


# =============================================================================
# Paths
# =============================================================================

PROJECT_DIR: Path = Path(__file__).parent.parent
DATA_DIR: Path = PROJECT_DIR / "data"
OUTPUT_DIR: Path = PROJECT_DIR / "output"
TIMESTAMP_FILE: Path = DATA_DIR / ".yaml_last_validated"


# =============================================================================
# Result type
# =============================================================================

class ValidationResult(NamedTuple):
    valid: bool
    errors: list[str]
    warnings: list[str]
    usages: dict[str, list[str]]
    orphaned: list[Path]


# =============================================================================
# Enum sets for validators
# =============================================================================

VALID_SCHEMA_POSITIONS: frozenset[str] = frozenset({
    "opening", "riposte", "continuation",
    "pre_cadential", "cadential", "post_cadential",
})

VALID_FIGURATION_METRICS: frozenset[str] = frozenset({
    "strong", "weak", "across", "any",
})

VALID_FIGURATION_FUNCTIONS: frozenset[str] = frozenset({
    "ornament", "diminution", "cadential", "sequential",
})

VALID_ENERGY_LEVELS: frozenset[str] = frozenset({
    "low", "medium", "high",
})

VALID_DIMINUTION_CHARACTERS: frozenset[str] = frozenset({
    "plain", "energetic", "sustained",
})

VALID_DIMINUTION_DIRECTIONS: frozenset[str] = frozenset({
    "ascending", "descending", "static",
})

VALID_AFFECT_MODES: frozenset[str] = frozenset({"major", "minor"})

VALID_AFFECT_DENSITIES: frozenset[str] = frozenset({"low", "medium", "high"})

VALID_RHYTHM_CELL_CHARACTERS: frozenset[str] = frozenset({
    "plain", "dotted", "flowing", "energetic", "cadential",
})

VALID_RHYTHM_TEMPLATE_CHARACTERS: frozenset[str] = frozenset({
    "plain", "expressive", "energetic", "ornate", "bold",
})

VALID_RHYTHM_TEMPLATE_POSITIONS: frozenset[str] = frozenset({
    "passing", "cadential", "schema_arrival",
})

VALID_TREATMENT_SOURCES: frozenset[str] = frozenset({
    "subject", "counter_subject", "sustained", "pedal",
    "schema", "accompaniment",
})

VALID_TREATMENT_TRANSFORMS: frozenset[str] = frozenset({
    "none", "invert", "retrograde", "head", "tail", "augment", "diminish",
})

# =============================================================================
# YAML load cache
# =============================================================================

_yaml_cache: dict[Path, Any] = {}


def _load(path: Path) -> Any:
    """Load YAML with caching. Returns empty dict if file missing."""
    if path in _yaml_cache:
        return _yaml_cache[path]
    if not path.exists():
        _yaml_cache[path] = {}
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _yaml_cache[path] = data
    return data


def _clear_cache() -> None:
    _yaml_cache.clear()


# =============================================================================
# Timestamp caching
# =============================================================================

def yaml_changed() -> bool:
    """Return True if any YAML file has changed since last validation."""
    if not TIMESTAMP_FILE.exists():
        return True
    stamp_mtime: float = TIMESTAMP_FILE.stat().st_mtime
    for directory in [DATA_DIR, PROJECT_DIR / "briefs"]:
        if not directory.exists():
            continue
        for yaml_file in directory.rglob("*.yaml"):
            if yaml_file.stat().st_mtime > stamp_mtime:
                return True
    return False


def touch_timestamp() -> None:
    """Write current timestamp to cache file."""
    TIMESTAMP_FILE.write_text(str(time.time()), encoding="utf-8")


# =============================================================================
# Helper: relative path for error messages
# =============================================================================

def _rel(path: Path) -> str:
    return str(path.relative_to(PROJECT_DIR)).replace("\\", "/")


# =============================================================================
# Helper: signed degree parsing
# =============================================================================

_SIGNED_DEGREE_RE: re.Pattern[str] = re.compile(r'^[+-]?[1-7]$')


def _is_valid_signed_degree(raw: Any) -> bool:
    """Check if value is a valid signed scale degree."""
    s = str(raw).strip()
    return bool(_SIGNED_DEGREE_RE.match(s))


# =============================================================================
# Collect helpers for files
# =============================================================================

def _genre_files() -> list[Path]:
    genres_dir = DATA_DIR / "genres"
    if not genres_dir.exists():
        return []
    return sorted(
        p for p in genres_dir.glob("*.yaml")
        if not p.name.startswith("_")
    )


def _form_stems() -> set[str]:
    forms_dir = DATA_DIR / "forms"
    if not forms_dir.exists():
        return set()
    return {p.stem for p in forms_dir.glob("*.yaml")}


# =============================================================================
# 0. Syntax validation
# =============================================================================

def validate_yaml_syntax() -> list[str]:
    """Validate all YAML files parse without errors."""
    errors: list[str] = []
    for directory in [DATA_DIR, PROJECT_DIR / "briefs", PROJECT_DIR / "motifs"]:
        if not directory.exists():
            continue
        for yaml_file in directory.rglob("*.yaml"):
            try:
                _load(path=yaml_file)
            except yaml.YAMLError as e:
                errors.append(f"{_rel(yaml_file)}: YAML syntax error -- fix syntax: {e}")
    return errors


# =============================================================================
# 1. Genre field types
# =============================================================================

def validate_genre_field_types() -> list[str]:
    errors: list[str] = []
    schemas_data = _load(path=DATA_DIR / "schemas" / "schemas.yaml")
    bass_patterns_data = _load(path=DATA_DIR / "figuration" / "bass_patterns.yaml")
    form_stems = _form_stems()

    for gf in _genre_files():
        rel = _rel(gf)
        data = _load(path=gf)
        name = data.get("name", gf.stem)

        # voices: int or list of dicts with id+role
        voices = data.get("voices")
        if voices is not None:
            if isinstance(voices, list):
                for i, v in enumerate(voices):
                    if not isinstance(v, dict):
                        errors.append(f"{rel}: genre '{name}' voices[{i}] must be dict with 'id' and 'role', got {type(v).__name__} -- use {{id: x, role: y}}")
                    elif "id" not in v or "role" not in v:
                        errors.append(f"{rel}: genre '{name}' voices[{i}] missing 'id' or 'role' -- add both fields")
            elif not isinstance(voices, int):
                errors.append(f"{rel}: genre '{name}' 'voices' must be int or list of voice defs, got {type(voices).__name__}")

        # form
        form_val = data.get("form")
        if form_val is not None and form_val not in form_stems:
            errors.append(f"{rel}: genre '{name}' form '{form_val}' not found -- available: {sorted(form_stems)}")

        # metre
        metre = data.get("metre")
        if metre is not None and not re.match(r'^\d+/\d+$', str(metre)):
            errors.append(f"{rel}: genre '{name}' metre '{metre}' -- expected 'N/N' format like '3/4'")

        # rhythmic_unit
        ru = data.get("rhythmic_unit")
        if ru is not None and not re.match(r'^\d+(/\d+)?$', str(ru)):
            errors.append(f"{rel}: genre '{name}' rhythmic_unit '{ru}' -- expected fraction like '1/8'")

        # tempo
        tempo = data.get("tempo")
        if tempo is not None:
            if not isinstance(tempo, int) or not (30 <= tempo <= 300):
                errors.append(f"{rel}: genre '{name}' tempo {tempo} -- expected int 30-300")

        # bass_treatment
        bt = data.get("bass_treatment")
        if bt is not None and bt not in VALID_BASS_TREATMENTS:
            errors.append(f"{rel}: genre '{name}' bass_treatment '{bt}' -- expected one of {sorted(VALID_BASS_TREATMENTS)}")

        # bass_mode
        bm = data.get("bass_mode")
        if bm is not None and bm not in VALID_BASS_MODES:
            errors.append(f"{rel}: genre '{name}' bass_mode '{bm}' -- expected one of {sorted(VALID_BASS_MODES)}")

        # bass_pattern cross-ref
        bp = data.get("bass_pattern")
        if bp is not None and bp not in bass_patterns_data:
            errors.append(f"{rel}: genre '{name}' bass_pattern '{bp}' not found in bass_patterns.yaml -- available: {sorted(bass_patterns_data.keys())}")

        # upbeat
        upbeat = data.get("upbeat")
        if upbeat is not None:
            if upbeat != 0:
                try:
                    Fraction(str(upbeat))
                except (ValueError, ZeroDivisionError):
                    errors.append(f"{rel}: genre '{name}' upbeat '{upbeat}' -- expected 0 or valid fraction string")

        # sections
        sections = data.get("sections", [])
        if isinstance(sections, list):
            for i, sec in enumerate(sections):
                sec_name = sec.get("name", f"section_{i}")

                # lead_voice
                lv = sec.get("lead_voice")
                if lv is not None and not isinstance(lv, int):
                    errors.append(f"{rel}: genre '{name}' section '{sec_name}' lead_voice must be int, got {type(lv).__name__}")

                # accompany_texture
                at = sec.get("accompany_texture")
                if at is not None and not isinstance(at, str):
                    errors.append(f"{rel}: genre '{name}' section '{sec_name}' accompany_texture must be string, got {type(at).__name__}")

                # schema_sequence cross-ref
                ss = sec.get("schema_sequence", [])
                for schema_name in ss:
                    if schema_name not in schemas_data:
                        errors.append(f"{rel}: genre '{name}' section '{sec_name}' references unknown schema '{schema_name}' -- check data/schemas/schemas.yaml")
            # Final section's last schema must be in a final-eligible cadence type
            cadences_data = _load(path=DATA_DIR / "cadences" / "cadences.yaml")
            cadence_types = cadences_data.get("types", {})
            final_schemas: set[str] = set()
            for ct in cadence_types.values():
                if isinstance(ct, dict) and ct.get("final", False):
                    for s in ct.get("schemas", []):
                        final_schemas.add(s)
            if sections:
                last_sec = sections[-1]
                last_ss = last_sec.get("schema_sequence", [])
                last_sec_name = last_sec.get("name", "last")
                if last_ss:
                    final_schema: str = last_ss[-1]
                    if final_schema not in final_schemas:
                        errors.append(
                            f"{rel}: genre '{name}' section '{last_sec_name}' "
                            f"ends with '{final_schema}' which is not final-eligible "
                            f"-- use one of {sorted(final_schemas)}"
                        )

    return errors


# =============================================================================
# 2. Schemas validation
# =============================================================================

def validate_schemas() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "schemas" / "schemas.yaml"
    data = _load(path=path)
    rel = _rel(path)
    profiles_data = _load(path=DATA_DIR / "figuration" / "figuration_profiles.yaml")

    for name, schema in data.items():
        if not isinstance(schema, dict):
            continue

        # position
        pos = schema.get("position")
        if pos is not None and pos not in VALID_SCHEMA_POSITIONS:
            errors.append(f"{rel}: schema '{name}' position '{pos}' -- expected one of {sorted(VALID_SCHEMA_POSITIONS)}")

        # cadence_type cross-ref against cadences.yaml types
        ct = schema.get("cadence_type")
        if ct is not None:
            cadences_data = _load(path=DATA_DIR / "cadences" / "cadences.yaml")
            valid_cadence_types = set(cadences_data.get("types", {}).keys())
            if ct not in valid_cadence_types:
                errors.append(f"{rel}: schema '{name}' cadence_type '{ct}' not in cadences.yaml types -- available: {sorted(valid_cadence_types)}")

        # figuration_profile cross-ref
        fp = schema.get("figuration_profile")
        if fp is not None and fp not in profiles_data:
            errors.append(f"{rel}: schema '{name}' figuration_profile '{fp}' not in figuration_profiles.yaml -- available: {sorted(profiles_data.keys())}")

        # sequential schemas have segment sub-structure
        if schema.get("sequential"):
            segments = schema.get("segments")
            if segments is not None:
                if isinstance(segments, int):
                    assert segments > 0, f"{rel}: schema '{name}' segments must be > 0"
                elif isinstance(segments, list):
                    for s in segments:
                        if not isinstance(s, int) or s <= 0:
                            errors.append(f"{rel}: schema '{name}' segments list contains non-positive value {s} -- all must be int > 0")
                else:
                    errors.append(f"{rel}: schema '{name}' segments must be int > 0 or list[int > 0], got {type(segments).__name__}")

            # segment soprano/bass degrees
            seg = schema.get("segment", {})
            seg_sop = seg.get("soprano_degrees", [])
            seg_bass = seg.get("bass_degrees", [])
            for deg in seg_sop:
                if not _is_valid_signed_degree(deg):
                    errors.append(f"{rel}: schema '{name}' segment soprano_degree '{deg}' -- expected signed degree 1-7")
            for deg in seg_bass:
                if not _is_valid_signed_degree(deg):
                    errors.append(f"{rel}: schema '{name}' segment bass_degree '{deg}' -- expected signed degree 1-7")
        else:
            # non-sequential: soprano_degrees and bass_degrees at top level
            sop = schema.get("soprano_degrees", [])
            bass = schema.get("bass_degrees", [])
            for deg in sop:
                if not _is_valid_signed_degree(deg):
                    errors.append(f"{rel}: schema '{name}' soprano_degree '{deg}' -- expected signed degree 1-7")
            for deg in bass:
                if not _is_valid_signed_degree(deg):
                    errors.append(f"{rel}: schema '{name}' bass_degree '{deg}' -- expected signed degree 1-7")

            # lengths must match for non-sequential
            if sop and bass and len(sop) != len(bass):
                errors.append(f"{rel}: schema '{name}' soprano_degrees ({len(sop)}) != bass_degrees ({len(bass)}) -- lengths must match")

        # bars
        bars = schema.get("bars")
        if bars is not None:
            if isinstance(bars, int):
                if bars <= 0:
                    errors.append(f"{rel}: schema '{name}' bars must be > 0")
            elif isinstance(bars, list):
                if len(bars) != 2:
                    errors.append(f"{rel}: schema '{name}' bars must be [min, max] -- got list of length {len(bars)}")
                elif bars[0] <= 0 or bars[0] > bars[1]:
                    errors.append(f"{rel}: schema '{name}' bars [{bars[0]}, {bars[1]}] -- need 0 < min <= max")
            else:
                errors.append(f"{rel}: schema '{name}' bars must be int > 0 or [min, max]")

    return errors


# =============================================================================
# 3. Figuration profiles
# =============================================================================

def validate_figuration_profiles() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "figuration_profiles.yaml"
    data = _load(path=path)
    rel = _rel(path)
    figurations = _load(path=DATA_DIR / "figuration" / "figurations.yaml")

    for name, profile in data.items():
        if not isinstance(profile, dict):
            continue

        for section in ("interior", "cadential"):
            patterns = profile.get(section)
            if patterns is None:
                errors.append(f"{rel}: profile '{name}' missing '{section}' list -- add it")
                continue
            if not isinstance(patterns, list):
                errors.append(f"{rel}: profile '{name}' '{section}' must be a list")
                continue
            for pat_name in patterns:
                if pat_name not in figurations:
                    errors.append(f"{rel}: profile '{name}' {section} references '{pat_name}' not in figurations.yaml -- check spelling")

    return errors


# =============================================================================
# 4. Figurations
# =============================================================================

def validate_figurations() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "figurations.yaml"
    data = _load(path=path)
    rel = _rel(path)

    required_fields = ("description", "offset_from_target", "notes_per_beat", "metric", "function", "approach", "energy")

    for name, fig in data.items():
        if not isinstance(fig, dict):
            continue

        for field in required_fields:
            if field not in fig:
                errors.append(f"{rel}: figuration '{name}' missing required field '{field}' -- add it")

        # metric
        metric = fig.get("metric")
        if metric is not None and metric not in VALID_FIGURATION_METRICS:
            errors.append(f"{rel}: figuration '{name}' metric '{metric}' -- expected one of {sorted(VALID_FIGURATION_METRICS)}")

        # function
        func = fig.get("function")
        if func is not None and func not in VALID_FIGURATION_FUNCTIONS:
            errors.append(f"{rel}: figuration '{name}' function '{func}' -- expected one of {sorted(VALID_FIGURATION_FUNCTIONS)}")

        # energy
        energy = fig.get("energy")
        if energy is not None and energy not in VALID_ENERGY_LEVELS:
            errors.append(f"{rel}: figuration '{name}' energy '{energy}' -- expected one of {sorted(VALID_ENERGY_LEVELS)}")

        # offset_from_target: list of ints
        # last must be 0 for cadential/sequential (arrival-oriented) patterns
        ot = fig.get("offset_from_target")
        if ot is not None:
            if not isinstance(ot, list) or not all(isinstance(x, int) for x in ot):
                errors.append(f"{rel}: figuration '{name}' offset_from_target must be list of ints")
            elif ot and ot[-1] != 0 and func in ("cadential", "sequential"):
                errors.append(f"{rel}: figuration '{name}' offset_from_target last element must be 0, got {ot[-1]} -- target arrival required for {func} figures")

    return errors


# =============================================================================
# 5. Bass patterns
# =============================================================================

def validate_bass_patterns() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "bass_patterns.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for name, pattern in data.items():
        if not isinstance(pattern, dict):
            continue

        # texture
        texture = pattern.get("texture")
        if texture is None:
            errors.append(f"{rel}: bass_pattern '{name}' missing 'texture' -- add it")
        elif texture not in VALID_TEXTURES:
            errors.append(f"{rel}: bass_pattern '{name}' texture '{texture}' -- expected one of {sorted(VALID_TEXTURES)}")

        # harmonic_rhythm
        hr = pattern.get("harmonic_rhythm")
        if hr is None:
            errors.append(f"{rel}: bass_pattern '{name}' missing 'harmonic_rhythm' -- add it")
        elif hr not in VALID_HARMONIC_RHYTHMS:
            errors.append(f"{rel}: bass_pattern '{name}' harmonic_rhythm '{hr}' -- expected one of {sorted(VALID_HARMONIC_RHYTHMS)}")

        # beats
        beats = pattern.get("beats")
        if beats is None:
            errors.append(f"{rel}: bass_pattern '{name}' missing 'beats' -- add it")
        elif not isinstance(beats, list):
            errors.append(f"{rel}: bass_pattern '{name}' beats must be a list")
        else:
            for i, b in enumerate(beats):
                if not isinstance(b, dict):
                    errors.append(f"{rel}: bass_pattern '{name}' beats[{i}] must be dict with 'beat' and 'duration'")
                    continue
                if "beat" not in b:
                    errors.append(f"{rel}: bass_pattern '{name}' beats[{i}] missing 'beat' -- add it")
                if "duration" not in b:
                    errors.append(f"{rel}: bass_pattern '{name}' beats[{i}] missing 'duration' -- add it")

    return errors


# =============================================================================
# 6. Bass diminutions
# =============================================================================

def validate_bass_diminutions() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "bass_diminutions.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for interval_group, patterns in data.items():
        if not isinstance(patterns, list):
            continue
        for i, pat in enumerate(patterns):
            if not isinstance(pat, dict):
                errors.append(f"{rel}: {interval_group}[{i}] must be a dict")
                continue

            pat_name = pat.get("name", f"{interval_group}[{i}]")

            for field in ("name", "degrees", "durations", "character", "direction"):
                if field not in pat:
                    errors.append(f"{rel}: {interval_group} pattern '{pat_name}' missing '{field}' -- add it")

            char = pat.get("character")
            if char is not None and char not in VALID_DIMINUTION_CHARACTERS:
                errors.append(f"{rel}: {interval_group} pattern '{pat_name}' character '{char}' -- expected one of {sorted(VALID_DIMINUTION_CHARACTERS)}")

            direction = pat.get("direction")
            if direction is not None and direction not in VALID_DIMINUTION_DIRECTIONS:
                errors.append(f"{rel}: {interval_group} pattern '{pat_name}' direction '{direction}' -- expected one of {sorted(VALID_DIMINUTION_DIRECTIONS)}")

            # degrees and durations must be same length
            degrees = pat.get("degrees", [])
            durations = pat.get("durations", [])
            if degrees and durations and len(degrees) != len(durations):
                errors.append(f"{rel}: {interval_group} pattern '{pat_name}' degrees ({len(degrees)}) != durations ({len(durations)}) -- lengths must match")

    return errors


# =============================================================================
# 7. Cadential figures
# =============================================================================

def validate_cadential_figures() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "cadential.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for required_target in ("target_1", "target_5"):
        if required_target not in data:
            errors.append(f"{rel}: missing required section '{required_target}' -- add it")
            continue
        target = data[required_target]
        if not isinstance(target, dict):
            errors.append(f"{rel}: '{required_target}' must be a dict of approach intervals")
            continue
        for approach_name, figures in target.items():
            if not isinstance(figures, list) or len(figures) == 0:
                errors.append(f"{rel}: {required_target}.{approach_name} must be a non-empty list")
                continue
            for i, fig in enumerate(figures):
                if not isinstance(fig, dict):
                    errors.append(f"{rel}: {required_target}.{approach_name}[{i}] must be a dict")
                    continue
                for field in ("name", "degrees", "contour"):
                    if field not in fig:
                        errors.append(f"{rel}: {required_target}.{approach_name}[{i}] missing '{field}' -- add it")

    return errors


# =============================================================================
# 8. Rhythm templates
# =============================================================================

def validate_rhythm_templates() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "figuration" / "rhythm_templates.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for metre_key, note_counts in data.items():
        if metre_key == "hemiola":
            continue  # special section, skip
        if not isinstance(note_counts, dict):
            continue
        for nc_str, templates in note_counts.items():
            note_count = int(nc_str)
            if not isinstance(templates, list):
                continue
            for i, tmpl in enumerate(templates):
                if not isinstance(tmpl, dict):
                    continue
                tmpl_name = tmpl.get("name", f"{metre_key}/{nc_str}[{i}]")

                if "name" not in tmpl:
                    errors.append(f"{rel}: {metre_key}/{nc_str}[{i}] missing 'name' -- add it")
                if "durations" not in tmpl:
                    errors.append(f"{rel}: template '{tmpl_name}' missing 'durations' -- add it")
                    continue

                durations = tmpl["durations"]
                if not isinstance(durations, list):
                    errors.append(f"{rel}: template '{tmpl_name}' durations must be a list")
                    continue
                if len(durations) != note_count:
                    errors.append(f"{rel}: template '{tmpl_name}' has {len(durations)} durations but note_count is {note_count} -- must match")

                # characters validation
                chars = tmpl.get("characters", [])
                for c in chars:
                    if c not in VALID_RHYTHM_TEMPLATE_CHARACTERS:
                        errors.append(f"{rel}: template '{tmpl_name}' character '{c}' -- expected one of {sorted(VALID_RHYTHM_TEMPLATE_CHARACTERS)}")

                # positions validation
                positions = tmpl.get("positions", [])
                for p in positions:
                    if p not in VALID_RHYTHM_TEMPLATE_POSITIONS:
                        errors.append(f"{rel}: template '{tmpl_name}' position '{p}' -- expected one of {sorted(VALID_RHYTHM_TEMPLATE_POSITIONS)}")

                # weight must be > 0
                weight = tmpl.get("weight")
                if weight is not None and (not isinstance(weight, (int, float)) or weight <= 0):
                    errors.append(f"{rel}: template '{tmpl_name}' weight must be > 0, got {weight}")

    return errors


# =============================================================================
# 9. Affects
# =============================================================================

def validate_affects() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhetoric" / "affects.yaml"
    data = _load(path=path)
    rel = _rel(path)

    affects = data.get("affects")
    if affects is None:
        errors.append(f"{rel}: missing 'affects' section -- add it")
        return errors

    if "default" not in affects:
        errors.append(f"{rel}: missing 'default' entry under 'affects' -- add it")

    for name, affect in affects.items():
        if not isinstance(affect, dict):
            continue

        mode = affect.get("mode")
        if mode is not None and mode not in VALID_AFFECT_MODES:
            errors.append(f"{rel}: affect '{name}' mode '{mode}' -- expected one of {sorted(VALID_AFFECT_MODES)}")

        density = affect.get("density")
        if density is not None and density not in VALID_AFFECT_DENSITIES:
            errors.append(f"{rel}: affect '{name}' density '{density}' -- expected one of {sorted(VALID_AFFECT_DENSITIES)}")

    return errors


# =============================================================================
# 10. Archetypes
# =============================================================================

def validate_archetypes() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhetoric" / "archetypes.yaml"
    data = _load(path=path)
    rel = _rel(path)

    # Get valid affect names
    affects_data = _load(path=DATA_DIR / "rhetoric" / "affects.yaml")
    valid_affects = set(affects_data.get("affects", {}).keys())

    for name, archetype in data.items():
        if not isinstance(archetype, dict):
            continue

        # compatible_affects
        ca = archetype.get("compatible_affects", [])
        for aff in ca:
            if aff not in valid_affects:
                errors.append(f"{rel}: archetype '{name}' compatible_affect '{aff}' not in affects.yaml -- available: {sorted(valid_affects)}")

        # tension_curve: list of [float, float]
        tc = archetype.get("tension_curve")
        if tc is not None:
            if not isinstance(tc, list):
                errors.append(f"{rel}: archetype '{name}' tension_curve must be a list of [position, level] pairs")
            else:
                for i, point in enumerate(tc):
                    if not isinstance(point, list) or len(point) != 2:
                        errors.append(f"{rel}: archetype '{name}' tension_curve[{i}] must be [position, level] pair")
                    else:
                        for j, val in enumerate(point):
                            if not isinstance(val, (int, float)):
                                errors.append(f"{rel}: archetype '{name}' tension_curve[{i}][{j}] must be numeric, got {type(val).__name__}")

        # climax_position
        cp = archetype.get("climax_position")
        if cp is not None:
            if not isinstance(cp, (int, float)) or cp < 0 or cp > 1:
                errors.append(f"{rel}: archetype '{name}' climax_position must be float 0-1, got {cp}")

    return errors


# =============================================================================
# 11. Episodes
# =============================================================================

def validate_episodes() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhetoric" / "episodes.yaml"
    data = _load(path=path)
    rel = _rel(path)

    treatments_data = _load(path=DATA_DIR / "treatments" / "treatments.yaml")
    valid_treatments = set(treatments_data.keys())

    # Get valid energy levels from affects.yaml
    affects_data = _load(path=DATA_DIR / "rhetoric" / "affects.yaml")
    valid_energy_profiles = set(affects_data.get("energy_levels", {}).keys())

    episodes = data.get("episodes", {})
    for name, ep in episodes.items():
        if not isinstance(ep, dict):
            continue

        treatment = ep.get("treatment")
        if treatment is not None and treatment not in valid_treatments:
            errors.append(f"{rel}: episode '{name}' treatment '{treatment}' not in treatments.yaml -- available: {sorted(valid_treatments)}")

        energy_profile = ep.get("energy_profile")
        if energy_profile is not None and valid_energy_profiles and energy_profile not in valid_energy_profiles:
            errors.append(f"{rel}: episode '{name}' energy_profile '{energy_profile}' not in energy_levels -- available: {sorted(valid_energy_profiles)}")

    return errors


# =============================================================================
# 12. Treatments
# =============================================================================

def validate_treatments() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "treatments" / "treatments.yaml"
    data = _load(path=path)
    rel = _rel(path)

    if "_default" not in data:
        errors.append(f"{rel}: missing '_default' entry -- add it as base treatment")

    for name, treatment in data.items():
        if not isinstance(treatment, dict):
            continue
        if name == "bar_treatments":
            continue  # separate section

        for voice in ("soprano", "bass"):
            source_key = f"{voice}_source"
            transform_key = f"{voice}_transform"

            source = treatment.get(source_key)
            if source is not None and source not in VALID_TREATMENT_SOURCES:
                errors.append(f"{rel}: treatment '{name}' {source_key} '{source}' -- expected one of {sorted(VALID_TREATMENT_SOURCES)}")

            transform = treatment.get(transform_key)
            if transform is not None and transform not in VALID_TREATMENT_TRANSFORMS:
                errors.append(f"{rel}: treatment '{name}' {transform_key} '{transform}' -- expected one of {sorted(VALID_TREATMENT_TRANSFORMS)}")

    return errors


# =============================================================================
# 13. Cadences
# =============================================================================

def validate_cadences() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "cadences" / "cadences.yaml"
    data = _load(path=path)
    rel = _rel(path)
    schemas_data = _load(path=DATA_DIR / "schemas" / "schemas.yaml")
    for section in ("types", "internal", "final"):
        if section not in data:
            errors.append(f"{rel}: missing required section '{section}' -- add it")
    # Validate types section
    types = data.get("types", {})
    for type_name, type_def in types.items():
        if not isinstance(type_def, dict):
            continue
        if "final" not in type_def:
            errors.append(f"{rel}: type '{type_name}' missing 'final' field -- add it")
        for schema_name in type_def.get("schemas", []):
            if schema_name not in schemas_data:
                errors.append(f"{rel}: type '{type_name}' references unknown schema '{schema_name}' -- check schemas.yaml")
    return errors


# =============================================================================
# 14. Cadence templates
# =============================================================================

def validate_cadence_templates() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "cadence_templates" / "templates.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for schema_name, metres in data.items():
        if not isinstance(metres, dict):
            continue
        for metre, tmpl in metres.items():
            if not isinstance(tmpl, dict):
                continue

            soprano = tmpl.get("soprano", {})
            bass = tmpl.get("bass", {})

            sop_deg = soprano.get("degrees", [])
            sop_dur = soprano.get("durations", [])
            bass_deg = bass.get("degrees", [])
            bass_dur = bass.get("durations", [])

            if sop_deg and sop_dur and len(sop_deg) != len(sop_dur):
                errors.append(f"{rel}: {schema_name}/{metre} soprano degrees ({len(sop_deg)}) != durations ({len(sop_dur)}) -- must match")

            if bass_deg and bass_dur and len(bass_deg) != len(bass_dur):
                errors.append(f"{rel}: {schema_name}/{metre} bass degrees ({len(bass_deg)}) != durations ({len(bass_dur)}) -- must match")

    return errors


# =============================================================================
# 15. Instruments
# =============================================================================

def validate_instruments() -> list[str]:
    errors: list[str] = []
    instruments_dir = DATA_DIR / "instruments"
    if not instruments_dir.exists():
        return errors

    for inst_file in sorted(instruments_dir.glob("*.yaml")):
        rel = _rel(inst_file)
        data = _load(path=inst_file)

        if "name" not in data:
            errors.append(f"{rel}: missing 'name' field -- add it")

        actuators = data.get("actuators")
        if actuators is None:
            errors.append(f"{rel}: missing 'actuators' list -- add it")
            continue
        if not isinstance(actuators, list):
            errors.append(f"{rel}: 'actuators' must be a list")
            continue

        for i, act in enumerate(actuators):
            if not isinstance(act, dict):
                errors.append(f"{rel}: actuators[{i}] must be a dict")
                continue
            act_name = act.get("name", f"actuator_{i}")

            if "name" not in act:
                errors.append(f"{rel}: actuators[{i}] missing 'name' -- add it")

            rng = act.get("range")
            if rng is None:
                errors.append(f"{rel}: actuator '{act_name}' missing 'range' -- add [low, high] MIDI values")
            elif not isinstance(rng, list) or len(rng) != 2:
                errors.append(f"{rel}: actuator '{act_name}' range must be [low, high] -- got {rng}")
            else:
                low, high = rng
                if not isinstance(low, int) or not isinstance(high, int):
                    errors.append(f"{rel}: actuator '{act_name}' range values must be ints")
                elif not (0 <= low < high <= 127):
                    errors.append(f"{rel}: actuator '{act_name}' range [{low}, {high}] -- need 0 <= low < high <= 127")

    return errors


# =============================================================================
# 16. Rhythm cells
# =============================================================================

def validate_rhythm_cells() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhythm_cells" / "cells.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for name, cell in data.items():
        if not isinstance(cell, dict):
            continue

        metre = cell.get("metre")
        if metre is not None and not re.match(r'^\d+/\d+$', str(metre)):
            errors.append(f"{rel}: cell '{name}' metre '{metre}' -- expected 'N/N' format")

        durations = cell.get("durations")
        if durations is None:
            errors.append(f"{rel}: cell '{name}' missing 'durations' -- add it")
        elif not isinstance(durations, list):
            errors.append(f"{rel}: cell '{name}' durations must be a list")

        char = cell.get("character")
        if char is not None and char not in VALID_RHYTHM_CELL_CHARACTERS:
            errors.append(f"{rel}: cell '{name}' character '{char}' -- expected one of {sorted(VALID_RHYTHM_CELL_CHARACTERS)}")

    return errors


# =============================================================================
# 17. Rhythm affect profiles
# =============================================================================

def validate_rhythm_affect_profiles() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhythm" / "affect_profiles.yaml"
    data = _load(path=path)
    rel = _rel(path)

    # Cross-check affect names
    affects_data = _load(path=DATA_DIR / "rhetoric" / "affects.yaml")
    valid_affects = set(affects_data.get("affects", {}).keys())

    profiles = data.get("affect_profiles", {})
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        if name != "default" and name not in valid_affects:
            errors.append(f"{rel}: affect_profile '{name}' not in affects.yaml -- available: {sorted(valid_affects)}")

        char = profile.get("character")
        if char is not None and char not in VALID_MOTIF_CHARACTERS:
            errors.append(f"{rel}: affect_profile '{name}' character '{char}' -- expected one of {sorted(VALID_MOTIF_CHARACTERS)}")

    return errors


# =============================================================================
# 18. Motif vocabulary
# =============================================================================

def validate_motif_vocabulary() -> list[str]:
    errors: list[str] = []
    path = DATA_DIR / "rhythm" / "motif_vocabulary.yaml"
    data = _load(path=path)
    rel = _rel(path)

    for metre_key, categories in data.items():
        if not isinstance(categories, dict):
            continue
        for cat_name, motifs in categories.items():
            if not isinstance(motifs, dict):
                continue
            for motif_name, motif in motifs.items():
                if not isinstance(motif, dict):
                    continue

                char = motif.get("character")
                if char is not None and char not in VALID_MOTIF_CHARACTERS:
                    errors.append(f"{rel}: {metre_key}/{cat_name}/{motif_name} character '{char}' -- expected one of {sorted(VALID_MOTIF_CHARACTERS)}")

                positions = motif.get("phrase_positions", [])
                for pos in positions:
                    if pos not in VALID_PHRASE_POSITIONS:
                        errors.append(f"{rel}: {metre_key}/{cat_name}/{motif_name} phrase_position '{pos}' -- expected one of {sorted(VALID_PHRASE_POSITIONS)}")

    return errors


# =============================================================================
# 19. Humanisation
# =============================================================================

def validate_humanisation() -> list[str]:
    errors: list[str] = []

    # metric_weights.yaml
    mw_path = DATA_DIR / "humanisation" / "metric_weights.yaml"
    mw_data = _load(path=mw_path)
    mw_rel = _rel(mw_path)

    for metre_key, entry in mw_data.items():
        if not isinstance(entry, dict):
            continue
        if not re.match(r'^\d+/\d+$', str(metre_key)):
            errors.append(f"{mw_rel}: key '{metre_key}' -- expected valid metre like 'N/N'")

        bd = entry.get("bar_duration")
        if bd is not None and not isinstance(bd, (int, float)):
            errors.append(f"{mw_rel}: {metre_key} bar_duration must be numeric, got {type(bd).__name__}")

        beats = entry.get("beats", {})
        if isinstance(beats, dict):
            for beat_pos, weight in beats.items():
                if not isinstance(weight, (int, float)):
                    errors.append(f"{mw_rel}: {metre_key} beats[{beat_pos}] weight must be numeric, got {type(weight).__name__}")

    # Performance files
    perf_dir = DATA_DIR / "humanisation" / "performance"
    if perf_dir.exists():
        for pf in sorted(perf_dir.glob("*.yaml")):
            rel = _rel(pf)
            data = _load(path=pf)
            for section in ("timing", "dynamics"):
                if section not in data:
                    errors.append(f"{rel}: missing required section '{section}' -- add it")
                elif isinstance(data[section], dict):
                    for key, val in data[section].items():
                        if not isinstance(val, (int, float)):
                            errors.append(f"{rel}: {section}.{key} must be numeric, got {type(val).__name__} ('{val}')")

    # Style files
    styles_dir = DATA_DIR / "humanisation" / "styles"
    if styles_dir.exists():
        for sf in sorted(styles_dir.glob("*.yaml")):
            rel = _rel(sf)
            data = _load(path=sf)
            for section in ("timing", "dynamics"):
                if section not in data:
                    errors.append(f"{rel}: missing required section '{section}' -- add it")
                elif isinstance(data[section], dict):
                    for key, val in data[section].items():
                        if not isinstance(val, (int, float)):
                            errors.append(f"{rel}: {section}.{key} must be numeric, got {type(val).__name__} ('{val}')")

    return errors


# =============================================================================
# 20. Rules
# =============================================================================

def validate_rules() -> list[str]:
    errors: list[str] = []

    # constraints.yaml
    con_path = DATA_DIR / "rules" / "constraints.yaml"
    con_data = _load(path=con_path)
    con_rel = _rel(con_path)

    # Check genre constraints reference valid genres
    genre_names = {gf.stem for gf in _genre_files()}
    genre_constraints = con_data.get("genre", {})
    if isinstance(genre_constraints, dict):
        for rule_name, rule in genre_constraints.items():
            if not isinstance(rule, dict):
                continue
            when = rule.get("when", {})
            genre_ref = when.get("genre")
            if genre_ref is not None and genre_ref not in genre_names:
                errors.append(f"{con_rel}: genre constraint '{rule_name}' references genre '{genre_ref}' not in data/genres/ -- available: {sorted(genre_names)}")

    # Check affect constraints reference valid affects
    affects_data = _load(path=DATA_DIR / "rhetoric" / "affects.yaml")
    valid_affects = set(affects_data.get("affects", {}).keys())
    affect_constraints = con_data.get("affect", {})
    if isinstance(affect_constraints, dict):
        for rule_name, rule in affect_constraints.items():
            if not isinstance(rule, dict):
                continue
            when = rule.get("when", {})
            affect_ref = when.get("affect")
            if affect_ref is not None and affect_ref not in valid_affects:
                errors.append(f"{con_rel}: affect constraint '{rule_name}' references affect '{affect_ref}' not in affects.yaml -- available: {sorted(valid_affects)}")

    # counterpoint_rules.yaml - check required sections
    cp_path = DATA_DIR / "rules" / "counterpoint_rules.yaml"
    cp_data = _load(path=cp_path)
    cp_rel = _rel(cp_path)

    for section in ("intervals", "hard_constraints", "soft_constraints"):
        if section not in cp_data:
            errors.append(f"{cp_rel}: missing required section '{section}' -- add it")

    return errors


# =============================================================================
# 21. Thematic entry_sequence (invention genres)
# =============================================================================

def validate_thematic_entry_sequence() -> list[str]:
    """Validate entry_sequence within thematic sections of genre files."""
    errors: list[str] = []
    valid_materials: frozenset[str] = frozenset({"subject", "answer", "cs", "stretto"})
    valid_key_labels: frozenset[str] = frozenset({"I", "V", "IV", "vi", "iii", "ii", "III", "VI"})

    for gf in _genre_files():
        rel = _rel(gf)
        data = _load(path=gf)
        name = data.get("name", gf.stem)

        thematic = data.get("thematic")
        if thematic is None or not isinstance(thematic, dict):
            continue

        entry_sequence = thematic.get("entry_sequence")
        if entry_sequence is None:
            continue

        if not isinstance(entry_sequence, list):
            errors.append(f"{rel}: genre '{name}' thematic.entry_sequence must be a list -- got {type(entry_sequence).__name__}")
            continue

        for i, entry in enumerate(entry_sequence):
            # Entry is either "cadence" (string), episode dict, or regular dict with upper/lower
            if entry == "cadence":
                # Valid cadence marker
                continue

            if not isinstance(entry, dict):
                errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] must be 'cadence' or dict -- got {type(entry).__name__}")
                continue

            # Episode entry
            if entry.get("type") == "episode":
                # Validate episode-specific fields
                if "bars" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] episode missing 'bars' field -- add it")
                if "lead_voice" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] episode missing 'lead_voice' field -- add it")
                elif entry["lead_voice"] not in ("upper", "lower"):
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] episode lead_voice must be 'upper' or 'lower', got '{entry['lead_voice']}'")
                if "fragment" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] episode missing 'fragment' field -- add it")
                elif entry["fragment"] != "head":
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] episode fragment must be 'head' (IMP-4), got '{entry['fragment']}'")
                continue

            # Pedal entry
            if entry.get("type") == "pedal":
                # Validate pedal-specific fields
                if "degree" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] pedal missing 'degree' field -- add it")
                elif not isinstance(entry["degree"], int) or not (1 <= entry["degree"] <= 7):
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] pedal degree must be int 1-7, got {entry.get('degree')}")
                if "bars" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] pedal missing 'bars' field -- add it")
                elif not isinstance(entry["bars"], int) or entry["bars"] <= 0:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] pedal bars must be int > 0, got {entry.get('bars')}")
                continue

            # Stretto entry
            if entry.get("type") == "stretto":
                # Validate stretto-specific fields
                if "key" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] stretto missing 'key' field -- add it")
                elif not isinstance(entry["key"], str):
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] stretto key must be string, got {type(entry.get('key')).__name__}")
                if "delay" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] stretto missing 'delay' field -- add it")
                elif not isinstance(entry["delay"], int) or entry["delay"] <= 0:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] stretto delay must be int > 0, got {entry.get('delay')}")
                continue

            # Hold-exchange entry
            if entry.get("type") == "hold_exchange":
                # Validate hold_exchange-specific fields
                if "key" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] hold_exchange missing 'key' field -- add it")
                elif not isinstance(entry["key"], str):
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] hold_exchange key must be string, got {type(entry.get('key')).__name__}")
                if "bars" not in entry:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] hold_exchange missing 'bars' field -- add it")
                elif not isinstance(entry["bars"], int) or entry["bars"] < 2:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] hold_exchange bars must be int >= 2, got {entry.get('bars')}")
                continue

            # Regular entry: check for upper and lower keys
            if "upper" not in entry:
                errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] missing 'upper' key -- add it")
            if "lower" not in entry:
                errors.append(f"{rel}: genre '{name}' entry_sequence[{i}] missing 'lower' key -- add it")

            # Validate voice slots
            for voice_slot in ("upper", "lower"):
                if voice_slot not in entry:
                    continue

                slot_value = entry[voice_slot]

                # Slot is either "none" or [material, key_label]
                if slot_value == "none":
                    continue

                if not isinstance(slot_value, list):
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}].{voice_slot} must be 'none' or [material, key_label] -- got {type(slot_value).__name__}")
                    continue

                if len(slot_value) != 2:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}].{voice_slot} must be [material, key_label] with 2 elements -- got {len(slot_value)}")
                    continue

                material, key_label = slot_value

                # Validate material
                if material not in valid_materials:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}].{voice_slot} material '{material}' -- expected one of {sorted(valid_materials)}")

                # Validate key_label
                if key_label not in valid_key_labels:
                    errors.append(f"{rel}: genre '{name}' entry_sequence[{i}].{voice_slot} key_label '{key_label}' -- expected one of {sorted(valid_key_labels)}")

    return errors


# =============================================================================
# Legacy: required fields, unknown keys, genre sections, brief files
# =============================================================================

VALID_GENRE_KEYS: frozenset[str] = frozenset({
    "name", "voices", "form", "metre", "rhythmic_unit", "tempo",
    "bass_treatment", "bass_mode", "bass_pattern", "sections", "upbeat",
    "instruments", "scoring", "tracks", "affect", "tension", "subject",
    "thematic", "composition_model",
})
VALID_GENRE_SECTION_KEYS: frozenset[str] = frozenset({
    "name", "schema_sequence", "lead_voice", "lead_material",
    "accompany_material", "accompany_texture", "tonal_path", "final_cadence",
    "character", "min_non_cadential",
})
VALID_BRIEF_KEYS: frozenset[str] = frozenset({
    "brief", "frame", "material", "sections", "structure",
})
VALID_BRIEF_SECTION_KEYS: frozenset[str] = frozenset({
    "name", "tonal_path", "final_cadence", "phrases",
    "lead_voice", "accompany_texture",
})
VALID_BRIEF_PHRASE_KEYS: frozenset[str] = frozenset({
    "schema", "treatment", "bars", "tonal_target", "cadence",
})


def validate_required_fields() -> list[str]:
    """Validate required fields in genre and form files."""
    errors: list[str] = []
    required_genre_fields = ["name", "voices", "form", "metre"]
    for gf in _genre_files():
        data = _load(path=gf)
        rel = _rel(gf)
        for field in required_genre_fields:
            if field not in data:
                errors.append(f"{rel}: missing required field '{field}' -- add it")

    forms_dir = DATA_DIR / "forms"
    if forms_dir.exists():
        for form_file in forms_dir.glob("*.yaml"):
            data = _load(path=form_file)
            if "name" not in data:
                errors.append(f"{_rel(form_file)}: missing required field 'name' -- add it")
    return errors


def validate_unknown_keys() -> list[str]:
    """Check for unknown keys in genres and briefs."""
    errors: list[str] = []
    for gf in _genre_files():
        rel = _rel(gf)
        data = _load(path=gf)
        for key in data.keys():
            if key not in VALID_GENRE_KEYS:
                errors.append(f"{rel}: unknown key '{key}' -- remove it or add to VALID_GENRE_KEYS")
        for i, section in enumerate(data.get("sections", [])):
            sec_name = section.get("name", f"section_{i}")
            for key in section.keys():
                if key not in VALID_GENRE_SECTION_KEYS:
                    errors.append(f"{rel}: section '{sec_name}' has unknown key '{key}' -- remove it or add to VALID_GENRE_SECTION_KEYS")

    briefs_dir = PROJECT_DIR / "briefs"
    if briefs_dir.exists():
        for brief_file in briefs_dir.rglob("*.brief"):
            rel = _rel(brief_file)
            data = _load(path=brief_file)
            for key in data.keys():
                if key not in VALID_BRIEF_KEYS:
                    errors.append(f"{rel}: unknown top-level key '{key}' -- remove or update VALID_BRIEF_KEYS")
            for i, section in enumerate(data.get("sections", [])):
                sec_name = section.get("name", section.get("label", f"section_{i}"))
                for key in section.keys():
                    if key not in VALID_BRIEF_SECTION_KEYS:
                        errors.append(f"{rel}: section '{sec_name}' has unknown key '{key}'")
                for j, phrase in enumerate(section.get("phrases", [])):
                    for key in phrase.keys():
                        if key not in VALID_BRIEF_PHRASE_KEYS:
                            errors.append(f"{rel}: section '{sec_name}' phrase {j+1} has unknown key '{key}'")
    return errors


def validate_brief_files() -> list[str]:
    """Validate brief files don't have 'bars' field."""
    errors: list[str] = []
    briefs_dir = PROJECT_DIR / "briefs"
    if not briefs_dir.exists():
        return errors
    for brief_file in briefs_dir.rglob("*.brief"):
        rel = _rel(brief_file)
        data = _load(path=brief_file)
        brief_section = data.get("brief", {})
        if "bars" in brief_section:
            errors.append(f"{rel}: brief has 'bars' field -- remove it (bar count derived from schema_sequence)")
    return errors


# =============================================================================
# Cross-reference validation (yaml_types.yaml based)
# =============================================================================

def get_nested(data: dict[str, Any], path: str) -> set[str]:
    """Extract values at dotted path. * = wildcard, keys = dict keys."""
    if not path or data is None:
        return set()
    parts: list[str] = path.replace("[*]", ".*").split(".")
    return _get_nested_recursive(data=data, parts=parts)


def _get_nested_recursive(data: Any, parts: list[str]) -> set[str]:
    if not parts:
        if isinstance(data, str):
            return {data}
        if isinstance(data, list):
            return {x for x in data if isinstance(x, str)}
        return set()
    part = parts[0]
    rest = parts[1:]
    if part == "*":
        if isinstance(data, dict):
            result: set[str] = set()
            for v in data.values():
                result |= _get_nested_recursive(data=v, parts=rest)
            return result
        if isinstance(data, list):
            result = set()
            for v in data:
                result |= _get_nested_recursive(data=v, parts=rest)
            return result
        return set()
    if part == "keys":
        if isinstance(data, dict):
            return set(data.keys())
        return set()
    if isinstance(data, dict) and part in data:
        return _get_nested_recursive(data=data[part], parts=rest)
    return set()


def collect_definitions(type_spec: dict[str, Any]) -> dict[str, set[str]]:
    """Collect all type definitions from data files per yaml_types.yaml."""
    definitions: dict[str, set[str]] = {}
    for file_key, file_schema in type_spec.items():
        if "defines" not in file_schema:
            continue
        type_name: str = file_schema["defines"]
        path_str: str = file_schema.get("path", "keys")

        if file_key == "genres":
            values: set[str] = set()
            genres_dir = DATA_DIR / "genres"
            if genres_dir.exists():
                for genre_file in genres_dir.glob("*.yaml"):
                    if genre_file.name.startswith("_"):
                        continue
                    data = _load(path=genre_file)
                    values |= get_nested(data=data, path=path_str)
        elif file_key == "cadences":
            data = _load(path=DATA_DIR / "cadences" / "cadences.yaml")
            values = get_nested(data=data, path="internal.keys") | get_nested(data=data, path="final.keys")
        else:
            yaml_path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = _load(path=yaml_path)
            values = get_nested(data=data, path=path_str)
        definitions[type_name] = values
    return definitions


def get_valid_values(type_spec_str: str, definitions: dict[str, set[str]]) -> set[str]:
    valid: set[str] = set()
    for type_name in type_spec_str.split("|"):
        valid |= definitions.get(type_name.strip(), set())
    return valid


def validate_cross_references() -> list[str]:
    """Validate cross-references per yaml_types.yaml."""
    errors: list[str] = []
    type_spec_path = DATA_DIR / "yaml_types.yaml"
    if not type_spec_path.exists():
        errors.append("data/yaml_types.yaml not found -- cannot validate cross-references")
        return errors

    type_spec = _load(path=type_spec_path)
    definitions = collect_definitions(type_spec=type_spec)

    for file_key, file_schema in type_spec.items():
        refs: dict[str, str] = file_schema.get("references", {})
        if not refs:
            continue

        if file_key == "genres":
            genres_dir = DATA_DIR / "genres"
            if genres_dir.exists():
                for genre_file in genres_dir.glob("*.yaml"):
                    if genre_file.name.startswith("_"):
                        continue
                    data = _load(path=genre_file)
                    for ref_path, type_spec_str in refs.items():
                        values = get_nested(data=data, path=ref_path)
                        valid = get_valid_values(type_spec_str=type_spec_str, definitions=definitions)
                        for v in values:
                            if v and v not in valid:
                                errors.append(
                                    f"{_rel(genre_file)}: {ref_path}={v!r} not in {type_spec_str} -- check value or add to source"
                                )
        else:
            yaml_path = DATA_DIR / f"{file_key}.yaml"
            if not yaml_path.exists():
                continue
            data = _load(path=yaml_path)
            for ref_path, type_spec_str in refs.items():
                values = get_nested(data=data, path=ref_path)
                valid = get_valid_values(type_spec_str=type_spec_str, definitions=definitions)
                for v in values:
                    if v and v not in valid:
                        errors.append(
                            f"{file_key}.yaml: {ref_path}={v!r} not in {type_spec_str} -- check value or add to source"
                        )
    return errors


# =============================================================================
# Usages / orphaned files
# =============================================================================

def get_all_yaml_files() -> list[Path]:
    yaml_files: list[Path] = []
    for directory in [DATA_DIR, PROJECT_DIR / "briefs", PROJECT_DIR / "motifs"]:
        if directory.exists():
            yaml_files.extend(directory.rglob("*.yaml"))
    return sorted(yaml_files)


def get_all_python_files() -> list[Path]:
    python_files: list[Path] = []
    for directory in [PROJECT_DIR / "builder", PROJECT_DIR / "planner",
                      PROJECT_DIR / "shared", PROJECT_DIR / "scripts",
                      PROJECT_DIR / "motifs"]:
        if directory.exists():
            python_files.extend(directory.rglob("*.py"))
    return sorted(python_files)


def extract_yaml_references_from_python(py_file: Path) -> set[str]:
    """Extract YAML file references from Python source."""
    references: set[str] = set()
    try:
        content = py_file.read_text(encoding="utf-8")
    except Exception:
        return references

    yaml_pattern = re.compile(r'["\']([^"\']*\.yaml)["\']')
    for match in yaml_pattern.finditer(content):
        references.add(match.group(1))

    path_pattern = re.compile(r'(?:DATA_DIR|PROJECT_DIR)\s*/\s*["\']([^"\']+)["\'](?:\s*/\s*["\']([^"\']+)["\'])*')
    for match in path_pattern.finditer(content):
        groups = [g for g in match.groups() if g]
        if groups:
            full_path = "/".join(groups)
            if full_path.endswith(".yaml") or any(g.endswith(".yaml") for g in groups):
                references.add(full_path)

    fstring_pattern = re.compile(r'f["\'][^"\']*\.yaml[^"\']*["\']')
    for match in fstring_pattern.finditer(content):
        references.add("<dynamic>.yaml")

    return references


def build_yaml_usages() -> dict[str, list[str]]:
    usages: dict[str, list[str]] = {}
    for py_file in get_all_python_files():
        refs = extract_yaml_references_from_python(py_file=py_file)
        module_name = str(py_file.relative_to(PROJECT_DIR)).replace("\\", "/").replace(".py", "")
        for ref in refs:
            if ref not in usages:
                usages[ref] = []
            usages[ref].append(module_name)
    for key in usages:
        usages[key] = sorted(usages[key])
    return dict(sorted(usages.items()))


def find_orphaned_yaml_files(usages: dict[str, list[str]]) -> list[Path]:
    all_yaml = get_all_yaml_files()
    referenced: set[str] = set()
    for ref in usages.keys():
        if ref == "<dynamic>.yaml":
            continue
        normalized = ref.replace("\\", "/").lstrip("/")
        referenced.add(normalized)
        referenced.add(Path(normalized).name)
        if "/" in normalized:
            referenced.add(normalized.split("/", 1)[-1] if not normalized.startswith("data/") else normalized)

    has_dynamic_refs = any("{" in ref for ref in usages.keys())
    orphaned: list[Path] = []
    for yaml_file in all_yaml:
        rel_path = str(yaml_file.relative_to(PROJECT_DIR)).replace("\\", "/")
        filename = yaml_file.name
        if filename.startswith("_"):
            continue
        if "briefs" in rel_path:
            continue
        if has_dynamic_refs and rel_path.startswith("data/"):
            data_subdir = rel_path.split("/")[1] if "/" in rel_path else ""
            if data_subdir in ("forms", "genres"):
                continue
        is_referenced = (
            filename in referenced or
            rel_path in referenced or
            rel_path.replace("data/", "") in referenced
        )
        if not is_referenced:
            orphaned.append(yaml_file)
    return orphaned


def write_yaml_usages(usages: dict[str, list[str]], orphaned: list[Path]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "yaml_usages.yaml"
    report: dict[str, Any] = {
        "_meta": {
            "description": "YAML file usage report",
            "generated_by": "scripts/yaml_validator.py",
        },
        "usages": usages,
        "orphaned_files": [str(p.relative_to(PROJECT_DIR)) for p in orphaned],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return output_path


# =============================================================================
# Main validate_all
# =============================================================================

_cached_valid_result: ValidationResult | None = None


def validate_all(force: bool = False) -> ValidationResult:
    """Run all validations. Uses timestamp caching unless force=True."""
    global _cached_valid_result

    if not force and not yaml_changed() and _cached_valid_result is not None:
        return _cached_valid_result

    _clear_cache()
    errors: list[str] = []
    warnings: list[str] = []

    # Phase 1: Syntax (must pass before field-level checks)
    errors.extend(validate_yaml_syntax())

    # Phase 2: Required fields and structure
    errors.extend(validate_required_fields())
    errors.extend(validate_unknown_keys())
    errors.extend(validate_brief_files())

    # Phase 3: Field-level type validation
    errors.extend(validate_genre_field_types())
    errors.extend(validate_schemas())
    errors.extend(validate_figuration_profiles())
    errors.extend(validate_figurations())
    errors.extend(validate_bass_patterns())
    errors.extend(validate_bass_diminutions())
    errors.extend(validate_cadential_figures())
    errors.extend(validate_rhythm_templates())
    errors.extend(validate_affects())
    errors.extend(validate_archetypes())
    errors.extend(validate_episodes())
    errors.extend(validate_treatments())
    errors.extend(validate_cadences())
    errors.extend(validate_cadence_templates())
    errors.extend(validate_instruments())
    errors.extend(validate_rhythm_cells())
    errors.extend(validate_rhythm_affect_profiles())
    errors.extend(validate_motif_vocabulary())
    errors.extend(validate_humanisation())
    errors.extend(validate_rules())

    # Phase 4: Thematic entry_sequence validation
    errors.extend(validate_thematic_entry_sequence())

    # Phase 5: Cross-references
    errors.extend(validate_cross_references())

    # Build usages and orphaned
    usages = build_yaml_usages()
    orphaned = find_orphaned_yaml_files(usages=usages)

    result = ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        usages=usages,
        orphaned=orphaned,
    )

    if result.valid:
        touch_timestamp()
        _cached_valid_result = result

    return result


# =============================================================================
# CLI entry point
# =============================================================================

def main() -> None:
    """Run validation and generate report."""
    import sys

    force = "--force" in sys.argv

    print("Validating YAML files...")
    print()

    result = validate_all(force=force)

    report_path = write_yaml_usages(usages=result.usages, orphaned=result.orphaned)
    print(f"Generated: {report_path.relative_to(PROJECT_DIR)}")
    print()

    if result.errors:
        print(f"ERRORS ({len(result.errors)}):")
        for e in result.errors:
            print(f"  - {e}")
        print()

    if result.orphaned:
        print(f"ORPHANED YAML FILES ({len(result.orphaned)}):")
        for p in result.orphaned:
            print(f"  - {p.relative_to(PROJECT_DIR)}")
        print()

    print(f"YAML files checked: {len(get_all_yaml_files())}")
    print(f"Python modules scanned: {len(get_all_python_files())}")
    print(f"Cross-reference usages tracked: {len(result.usages)}")
    print()

    if result.valid and not result.orphaned:
        print("Validation PASSED")
    elif result.valid:
        print("Validation PASSED (with orphaned files)")
    else:
        print("Validation FAILED")
        exit(1)


if __name__ == "__main__":
    main()

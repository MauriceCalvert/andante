"""Dramaturgy module: rhetorical structure and tension curves.

Maps affects to dramaturgical archetypes and computes:
- Rhetorical structure (exordium, narratio, confutatio, confirmatio, peroratio)
- Tension curves (per-bar tension levels)
- Climax positioning

Phase 10 (baroque_plan.md item 10.1):
- Expression and affect parameter selection
- Map affect → (tempo, mode, key suggestions)
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

from planner.plannertypes import (
    RhetoricalSection, RhetoricalStructure, TensionPoint, TensionCurve
)


DATA_DIR: Path = Path(__file__).parent.parent / "data"

# Rhetorical function descriptions
RHETORICAL_FUNCTIONS: Dict[str, str] = {
    "exordium": "Opening - captures attention, establishes affect",
    "narratio": "Exposition - presents main thematic material",
    "confutatio": "Development - confronts, contrasts, develops",
    "confirmatio": "Proof - confirms, resolves, builds to climax",
    "peroratio": "Conclusion - summarizes, brings closure",
}

# Default archetype for unknown affects
DEFAULT_ARCHETYPE = "assertion_confirmation"


def load_archetypes() -> Dict[str, dict]:
    """Load archetype definitions from YAML."""
    path = DATA_DIR / "archetypes.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_affects() -> Dict[str, dict]:
    """Load affect definitions from YAML."""
    path = DATA_DIR / "affects.yaml"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def select_archetype(affect: str) -> str:
    """Select appropriate archetype for the given affect.

    Uses the archetype mapping in affects.yaml, falling back to
    compatible_affects in archetypes.yaml, then to default.
    """
    affects = load_affects()
    archetypes = load_archetypes()

    # Check if affect has explicit archetype mapping
    if affect in affects:
        affect_data = affects[affect]
        if "archetype" in affect_data:
            archetype = affect_data["archetype"]
            if archetype in archetypes:
                return archetype

    # Fall back to compatible_affects search
    for arch_name, arch_data in archetypes.items():
        compatible = arch_data.get("compatible_affects", [])
        if affect in compatible:
            return arch_name

    return DEFAULT_ARCHETYPE


def compute_rhetorical_structure(
    archetype: str,
    total_bars: int,
) -> RhetoricalStructure:
    """Compute rhetorical section boundaries for the piece.

    Args:
        archetype: Name of the dramaturgical archetype
        total_bars: Total number of bars in the piece

    Returns:
        RhetoricalStructure with section boundaries
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes[archetype]
    proportions = arch_data.get("rhetorical_sections", {})
    climax_pos = arch_data.get("climax_position", 0.7)

    # Default proportions if not specified
    default_props = {
        "exordium": 0.12,
        "narratio": 0.23,
        "confutatio": 0.30,
        "confirmatio": 0.20,
        "peroratio": 0.15,
    }

    # Merge with defaults
    for key in default_props:
        if key not in proportions:
            proportions[key] = default_props[key]

    # Normalize proportions
    total_prop = sum(proportions.values())
    proportions = {k: v / total_prop for k, v in proportions.items()}

    # Compute bar boundaries
    sections: List[RhetoricalSection] = []
    current_bar = 1
    section_order = ["exordium", "narratio", "confutatio", "confirmatio", "peroratio"]

    for section_name in section_order:
        prop = proportions.get(section_name, 0.2)
        section_bars = max(1, round(total_bars * prop))

        # Adjust last section to fill remaining bars
        if section_name == "peroratio":
            section_bars = total_bars - current_bar + 1

        end_bar = min(current_bar + section_bars - 1, total_bars)

        sections.append(RhetoricalSection(
            name=section_name,
            start_bar=current_bar,
            end_bar=end_bar,
            function=RHETORICAL_FUNCTIONS.get(section_name, ""),
            proportion=prop,
        ))

        current_bar = end_bar + 1
        if current_bar > total_bars:
            break

    # Compute climax bar
    climax_bar = max(1, min(total_bars, round(total_bars * climax_pos)))

    return RhetoricalStructure(
        archetype=archetype,
        sections=tuple(sections),
        climax_position=climax_pos,
        climax_bar=climax_bar,
    )


def compute_tension_curve(
    archetype: str,
    total_bars: int,
) -> TensionCurve:
    """Compute tension curve for the piece.

    Interpolates between control points defined in the archetype.

    Args:
        archetype: Name of the dramaturgical archetype
        total_bars: Total number of bars in the piece

    Returns:
        TensionCurve with interpolated per-bar tension values
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes.get(archetype, {})
    raw_curve = arch_data.get("tension_curve", [
        [0.0, 0.3],
        [0.5, 0.7],
        [0.8, 0.9],
        [1.0, 0.4],
    ])
    climax_pos = arch_data.get("climax_position", 0.7)

    # Convert to TensionPoints
    control_points: List[Tuple[float, float]] = [
        (float(p[0]), float(p[1])) for p in raw_curve
    ]

    # Ensure we have start and end points
    if control_points[0][0] > 0:
        control_points.insert(0, (0.0, control_points[0][1]))
    if control_points[-1][0] < 1.0:
        control_points.append((1.0, control_points[-1][1]))

    # Interpolate to get per-bar values
    points: List[TensionPoint] = []
    max_tension = 0.0
    max_position = 0.0

    for bar in range(1, total_bars + 1):
        position = bar / total_bars
        tension = _interpolate_tension(position, control_points)

        points.append(TensionPoint(position=position, level=tension))

        if tension > max_tension:
            max_tension = tension
            max_position = position

    return TensionCurve(
        points=tuple(points),
        climax_position=max_position,
        climax_level=max_tension,
    )


def _interpolate_tension(
    position: float,
    control_points: List[Tuple[float, float]],
) -> float:
    """Linear interpolation between control points."""
    # Find surrounding control points
    for i in range(len(control_points) - 1):
        p1_pos, p1_level = control_points[i]
        p2_pos, p2_level = control_points[i + 1]

        if p1_pos <= position <= p2_pos:
            # Linear interpolation
            if p2_pos == p1_pos:
                return p1_level
            t = (position - p1_pos) / (p2_pos - p1_pos)
            return p1_level + t * (p2_level - p1_level)

    # If position is beyond control points, use nearest
    if position <= control_points[0][0]:
        return control_points[0][1]
    return control_points[-1][1]


def get_tension_at_bar(
    tension_curve: TensionCurve,
    bar: int,
    total_bars: int,
) -> float:
    """Get tension level at a specific bar."""
    position = bar / total_bars
    return _get_tension_at_position(tension_curve, position)


def _get_tension_at_position(
    tension_curve: TensionCurve,
    position: float,
) -> float:
    """Get tension level at a specific position (0.0 to 1.0)."""
    # Find nearest point
    best_dist = float("inf")
    best_level = 0.5

    for point in tension_curve.points:
        dist = abs(point.position - position)
        if dist < best_dist:
            best_dist = dist
            best_level = point.level

    return best_level


def get_section_at_bar(
    rhetoric: RhetoricalStructure,
    bar: int,
) -> RhetoricalSection | None:
    """Get the rhetorical section containing a specific bar."""
    for section in rhetoric.sections:
        if section.start_bar <= bar <= section.end_bar:
            return section
    return None


def get_key_scheme(
    archetype: str,
    mode: str,
) -> Dict[str, str]:
    """Get the key scheme for an archetype and mode.

    Args:
        archetype: Name of the archetype
        mode: "major" or "minor"

    Returns:
        Dict mapping rhetorical section names to key areas (Roman numerals)
    """
    archetypes = load_archetypes()

    if archetype not in archetypes:
        archetype = DEFAULT_ARCHETYPE

    arch_data = archetypes.get(archetype, {})

    scheme_key = f"key_scheme_{mode}"
    if scheme_key not in arch_data:
        scheme_key = "key_scheme_major" if mode == "major" else "key_scheme_minor"

    scheme = arch_data.get(scheme_key, {})

    # Default scheme if not specified
    if not scheme:
        if mode == "minor":
            scheme = {
                "exordium": "i",
                "narratio": "III",
                "confutatio": "iv",
                "confirmatio": "V",
                "peroratio": "i",
            }
        else:
            scheme = {
                "exordium": "I",
                "narratio": "V",
                "confutatio": "IV",
                "confirmatio": "V",
                "peroratio": "I",
            }

    return scheme


# =============================================================================
# Phase 10: Expression and Affect (baroque_plan.md item 10.1)
# =============================================================================

@dataclass(frozen=True)
class CompositionParams:
    """Parameters for composition derived from affect.

    Provides all the high-level decisions that follow from the chosen affect:
    tempo, mode, key suggestions, and musical characteristics.
    """
    affect: str
    mode: str  # "major" or "minor"
    tempo: str  # Tempo marking (adagio, andante, allegro, presto)
    tempo_bpm_range: Tuple[int, int]  # BPM range
    key_suggestions: Tuple[str, ...]  # Suggested keys (pitch classes)
    key_character: str  # "bright" or "dark"
    interval_profile: str  # "stepwise", "leaps", "mixed"
    contour: str  # "ascending", "descending", "arch", "wave"
    rhythm_density: str  # "sparse", "moderate", "dense"
    chromaticism: str  # "none", "light", "heavy"
    archetype: str  # Dramaturgical archetype


# Tempo to BPM mappings (baroque conventions)
TEMPO_BPM_RANGES: Dict[str, Tuple[int, int]] = {
    "grave": (25, 45),
    "largo": (40, 60),
    "lento": (45, 60),
    "adagio": (55, 75),
    "andante": (73, 100),
    "moderato": (86, 108),
    "allegretto": (100, 128),
    "allegro": (120, 156),
    "vivace": (140, 176),
    "presto": (168, 200),
    "prestissimo": (188, 220),
}


# Mattheson Key Characteristics (baroque_theory.md section 8.1)
# Maps key to its baroque character per Mattheson's Der vollkommene Capellmeister
MATTHESON_KEYS: Dict[str, str] = {
    "C": "pure_innocent",
    "D": "sharp_martial",
    "E": "piercing_sorrowful",
    "F": "tender_calm",
    "G": "persuading_brilliant",
    "A": "affecting_radiant",
    "Bb": "magnificent",
    "Eb": "serious",
    "c": "sweet_sad",
    "d": "devout_grand",
    "e": "pensive_profound",
    "g": "serious_magnificent",
    "a": "tender_plaintive",
    "f": "obscure_plaintive",
    "b": "harsh_plaintive",
}

# Affect to Mattheson key mapping (baroque_theory.md section 8.1 Affektenlehre)
# Maps each affect to its appropriate keys based on Mattheson's key character theory
# Both German baroque names and English equivalents are supported
AFFECT_TO_KEYS: Dict[str, Tuple[str, ...]] = {
    # Major affects (German)
    "Freudigkeit": ("G", "A", "D"),       # Joy → brilliant, radiant, sharp
    "Majestaet": ("D", "Bb", "Eb"),       # Majesty → martial, magnificent, serious
    "Zaertlichkeit": ("F", "C", "A"),     # Tenderness → tender, pure, radiant
    "Verwunderung": ("A", "G", "E"),      # Wonder → radiant, brilliant, piercing
    "Entschlossenheit": ("D", "G", "C"),  # Resolution → martial, brilliant, pure
    # Minor affects (German)
    "Sehnsucht": ("e", "a", "d"),         # Yearning → pensive, plaintive, devout
    "Klage": ("a", "c", "g"),             # Lament → plaintive, sad, serious
    "Zorn": ("g", "d", "c"),              # Anger → serious, grand, sad
    "Dolore": ("a", "c", "e"),            # Pain → plaintive, sad, pensive
    # English equivalents (map to same keys as German counterparts)
    "joyful": ("G", "A", "D"),            # = Freudigkeit
    "majestic": ("D", "Bb", "Eb"),        # = Majestaet
    "tender": ("F", "C", "A"),            # = Zaertlichkeit
    "default": ("D", "G", "C"),           # Default affect (based on Entschlossenheit)
    "resolute": ("D", "G", "C"),          # = Entschlossenheit
    "wondering": ("A", "G", "E"),         # = Verwunderung
    "yearning": ("e", "a", "d"),          # = Sehnsucht
    "lamenting": ("a", "c", "g"),         # = Klage
    "angry": ("g", "d", "c"),             # = Zorn
    "sorrowful": ("a", "c", "e"),         # = Dolore
}

# Legacy key suggestions by affect character (for backwards compatibility)
# Deprecated: Use AFFECT_TO_KEYS directly for Mattheson compliance
KEY_SUGGESTIONS: Dict[str, Tuple[str, ...]] = {
    "bright_major": ("G", "A", "D"),      # Brilliant, radiant
    "dark_major": ("Eb", "Bb", "E"),      # Serious, magnificent
    "bright_minor": ("e", "a", "d"),      # Pensive, plaintive
    "dark_minor": ("c", "g", "f"),        # Sad, serious
}


def select_parameters(affect: str) -> CompositionParams:
    """Select composition parameters based on affect.

    baroque_plan.md item 10.1: Map affect → (tempo, mode, key suggestions)

    Uses affects.yaml data to derive all composition parameters
    that follow from the chosen affect.

    Args:
        affect: Name of the affect (e.g., "Sehnsucht", "Freudigkeit")

    Returns:
        CompositionParams with all derived parameters
    """
    affects = load_affects()

    # Get affect data with defaults
    if affect in affects:
        affect_data = affects[affect]
    else:
        # Default to a neutral affect
        affect_data = {
            "mode": "major",
            "tempo": "andante",
            "key_character": "bright",
            "archetype": DEFAULT_ARCHETYPE,
            "interval_profile": "mixed",
            "contour": "arch",
            "rhythm_density": "moderate",
            "chromaticism": "none",
        }

    # Extract parameters
    mode = affect_data.get("mode", "major")
    tempo = affect_data.get("tempo", "andante")
    key_character = affect_data.get("key_character", "bright")
    archetype = affect_data.get("archetype", DEFAULT_ARCHETYPE)
    interval_profile = affect_data.get("interval_profile", "mixed")
    contour = affect_data.get("contour", "arch")
    rhythm_density = affect_data.get("rhythm_density", "moderate")
    chromaticism = affect_data.get("chromaticism", "none")

    # Get tempo BPM range
    tempo_bpm_range = TEMPO_BPM_RANGES.get(tempo, (80, 120))

    # Select appropriate keys based on mode and character
    key_category = f"{key_character}_{mode}"
    key_suggestions = KEY_SUGGESTIONS.get(key_category, ("C", "G", "F"))

    return CompositionParams(
        affect=affect,
        mode=mode,
        tempo=tempo,
        tempo_bpm_range=tempo_bpm_range,
        key_suggestions=key_suggestions,
        key_character=key_character,
        interval_profile=interval_profile,
        contour=contour,
        rhythm_density=rhythm_density,
        chromaticism=chromaticism,
        archetype=archetype,
    )


def get_affect_characteristics(affect: str) -> Dict[str, str]:
    """Get musical characteristics for an affect.

    Returns a dict with:
    - interval_profile: "stepwise", "leaps", or "mixed"
    - contour: "ascending", "descending", "arch", or "wave"
    - rhythm_density: "sparse", "moderate", or "dense"
    - chromaticism: "none", "light", or "heavy"

    These inform melodic generation to match the affect.
    """
    params = select_parameters(affect)
    return {
        "interval_profile": params.interval_profile,
        "contour": params.contour,
        "rhythm_density": params.rhythm_density,
        "chromaticism": params.chromaticism,
    }


def get_suggested_key(affect: str, preference: int = 0) -> str:
    """Get a suggested key for the affect per Mattheson's Affektenlehre.

    Uses baroque_theory.md section 8.1 key-character mappings to select
    historically appropriate keys for the given affect.

    Args:
        affect: Name of the affect (e.g., "Freudigkeit", "Sehnsucht")
        preference: Index into key suggestions (0 = first choice)

    Returns:
        Key as pitch class string (e.g., "G", "a" for minor)
        Lowercase indicates minor mode.
    """
    # Direct Mattheson mapping takes priority
    if affect in AFFECT_TO_KEYS:
        suggestions = AFFECT_TO_KEYS[affect]
        if preference < len(suggestions):
            return suggestions[preference]
        return suggestions[0]

    # Fall back to legacy mode+character mapping
    params = select_parameters(affect)
    key_character = params.key_character
    mode = params.mode
    key_category = f"{key_character}_{mode}"
    suggestions = KEY_SUGGESTIONS.get(key_category, ("C",))

    if preference < len(suggestions):
        return suggestions[preference]
    return suggestions[0] if suggestions else "C"


def get_tempo_marking(affect: str) -> str:
    """Get the appropriate tempo marking for an affect."""
    params = select_parameters(affect)
    return params.tempo


def get_tempo_bpm(affect: str, variation: float = 0.0) -> int:
    """Get a BPM value for an affect.

    Args:
        affect: Name of the affect
        variation: Value from -1.0 to 1.0 to vary within the tempo range
                   (-1.0 = min, 0.0 = middle, 1.0 = max)

    Returns:
        Integer BPM value
    """
    params = select_parameters(affect)
    min_bpm, max_bpm = params.tempo_bpm_range

    # Calculate BPM from variation
    mid_bpm = (min_bpm + max_bpm) / 2
    range_half = (max_bpm - min_bpm) / 2

    bpm = mid_bpm + (variation * range_half)
    return int(round(max(min_bpm, min(max_bpm, bpm))))

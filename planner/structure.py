"""Structure planner: builds sections and episodes from arc."""
from pathlib import Path

import yaml

from planner.arc import build_tension_curve, get_energy_for_bar
from planner.macro_form import build_macro_form, uses_macro_form
from planner.phrase_harmony import generate_phrase_harmony
from planner.section_planner import plan_all_sections
from planner.treatment_generator import generate_for_genre
from planner.plannertypes import (
    Brief, Episode, Frame, MacroForm, Material, Phrase, Section,
    SectionPlan, Structure, TensionCurve,
)

DATA_DIR = Path(__file__).parent.parent / "data"
EPISODES_DATA: dict = yaml.safe_load(open(DATA_DIR / "episodes.yaml", encoding="utf-8"))


def load_yaml(name: str) -> dict:
    """Load YAML file from data directory."""
    with open(DATA_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def phrase_at_position(position: float, phrase_count: int) -> int:
    """Calculate phrase index from position ratio."""
    return int(position * phrase_count)


def get_episode_treatment(episode_type: str) -> str:
    """Get treatment for an episode type."""
    if episode_type in EPISODES_DATA:
        return EPISODES_DATA[episode_type].get("treatment", "statement")
    return "statement"


def plan_structure_from_macro(
    brief: Brief, frame: Frame, macro_form: MacroForm
) -> Structure:
    """Build Structure from macro-form and section plans."""
    section_plans: tuple[SectionPlan, ...] = plan_all_sections(macro_form)
    tension_curve: TensionCurve = build_tension_curve(brief)
    total_bars: int = sum(sp.total_bars for sp in section_plans)
    sections: list[Section] = []
    phrase_idx: int = 0
    current_bar: int = 0
    climax_section: str = macro_form.climax_section
    prev_end_chord: str = "I"
    for sp_idx, sp in enumerate(section_plans):
        episodes: list[Episode] = []
        tonal_targets: list[str] = []
        for ep_idx, ep_spec in enumerate(sp.episodes):
            treatment: str = get_episode_treatment(ep_spec.type)
            is_last_episode: bool = ep_idx == len(sp.episodes) - 1
            is_last_section: bool = sp_idx == len(section_plans) - 1
            cadence: str | None = None
            if is_last_episode and is_last_section:
                cadence = "authentic"
            elif is_last_episode:
                cadence = "half"
            is_climax: bool = sp.label == climax_section and ep_spec.type in ("climax", "triumphant")
            energy: str = get_energy_for_bar(tension_curve, current_bar, total_bars)
            harmony: tuple[str, ...] = generate_phrase_harmony(
                ep_spec.bars, sp.key_area, cadence, prev_end_chord
            )
            phrase: Phrase = Phrase(
                index=phrase_idx,
                bars=ep_spec.bars,
                tonal_target=sp.key_area,
                cadence=cadence,
                treatment=treatment,
                surprise=None,
                is_climax=is_climax,
                energy=energy,
                harmony=harmony,
            )
            episode: Episode = Episode(
                type=ep_spec.type,
                bars=ep_spec.bars,
                texture=sp.texture,
                phrases=(phrase,),
                is_transition=ep_spec.is_transition,
            )
            episodes.append(episode)
            tonal_targets.append(sp.key_area)
            prev_end_chord = harmony[-1] if harmony else sp.key_area
            phrase_idx += 1
            current_bar += ep_spec.bars
        final_cadence: str = "authentic" if sp_idx == len(section_plans) - 1 else "half"
        section: Section = Section(
            label=sp.label,
            tonal_path=tuple(tonal_targets),
            final_cadence=final_cadence,
            episodes=tuple(episodes),
        )
        sections.append(section)
    arc_name: str = load_yaml("arc_selection.yaml")[brief.genre][brief.affect]
    return Structure(sections=tuple(sections), arc=arc_name)


def get_section_phrase_count(section_def: dict) -> int:
    """Get phrase count from section: episodes list or tonal_path length."""
    if "episodes" in section_def:
        return len(section_def["episodes"])
    return len(section_def["tonal_path"])


def plan_structure(brief: Brief, frame: Frame, material: Material) -> Structure:
    """Plan structure from brief, frame, and material."""
    if uses_macro_form(brief):
        macro_form: MacroForm = build_macro_form(brief, frame)
        return plan_structure_from_macro(brief, frame, macro_form)
    arcs: dict = load_yaml("arcs.yaml")
    positions: dict = load_yaml("positions.yaml")
    genre_data: dict = load_yaml(f"genres/{brief.genre}.yaml")
    arc_name: str = genre_data["arc"]
    arc_def: dict = arcs[arc_name]
    static_treatments: list[str] = arc_def.get("treatments", [])
    climax_pos: str | None = arc_def.get("climax")
    surprise_pos: str | None = arc_def.get("surprise")
    surprise_type: str | None = arc_def.get("surprise_type")
    section_defs: list[dict] = genre_data["sections"]
    total_phrases: int = sum(get_section_phrase_count(s) for s in section_defs)
    # Use dynamic treatment generation if static list is empty or explicitly dynamic
    use_dynamic: bool = not static_treatments or arc_def.get("dynamic_treatments", False)
    if use_dynamic:
        climax_position: float = {"early": 0.4, "mid": 0.5, "late": 0.7}.get(climax_pos or "late", 0.7)
        arc_treatments: list[str] = generate_for_genre(
            brief.genre, total_phrases, climax_position, seed=hash(brief.affect) % 1000
        )
    else:
        arc_treatments = static_treatments
    climax_idx: int | None = None
    if climax_pos:
        climax_idx = phrase_at_position(positions[climax_pos], total_phrases)
    surprise_idx: int | None = None
    if surprise_pos:
        surprise_idx = phrase_at_position(positions[surprise_pos], total_phrases)
    tension_curve: TensionCurve = build_tension_curve(brief)
    total_bars: int = sum(s["bars_per_phrase"] * get_section_phrase_count(s) for s in section_defs)
    sections: list[Section] = []
    phrase_idx: int = 0
    current_bar: int = 0
    prev_end_chord: str = "I"
    for section_def in section_defs:
        bars_per_phrase: int = section_def["bars_per_phrase"]
        texture: str = section_def.get("texture", "polyphonic")
        key_area: str = section_def.get("key_area", "I")
        episode_types: list[str] = section_def.get("episodes", [])
        tonal_path_legacy: list[str] = section_def.get("tonal_path", [])
        phrase_count: int = len(episode_types) if episode_types else len(tonal_path_legacy)
        episodes: list[Episode] = []
        for i in range(phrase_count):
            is_last_in_section: bool = i == phrase_count - 1
            if episode_types:
                episode_type: str = episode_types[i]
                treatment: str = get_episode_treatment(episode_type)
                tonal_target: str = key_area
            else:
                tonal_target = tonal_path_legacy[i]
                treatment = arc_treatments[phrase_idx % len(arc_treatments)]
                episode_type = "statement" if treatment == "statement" else "continuation"
            surprise: str | None = None
            if phrase_idx == surprise_idx and phrase_idx > 0 and not is_last_in_section:
                surprise = surprise_type
            cadence: str | None = None
            if is_last_in_section:
                cadence = section_def["final_cadence"]
            elif surprise == "evaded_cadence":
                cadence = "deceptive"
            is_climax: bool = phrase_idx == climax_idx
            energy: str = get_energy_for_bar(tension_curve, current_bar, total_bars)
            harmony: tuple[str, ...] = generate_phrase_harmony(
                bars_per_phrase, tonal_target, cadence, prev_end_chord
            )
            phrase: Phrase = Phrase(
                index=phrase_idx,
                bars=bars_per_phrase,
                tonal_target=tonal_target,
                cadence=cadence,
                treatment=treatment,
                surprise=surprise,
                is_climax=is_climax,
                energy=energy,
                harmony=harmony,
            )
            episode: Episode = Episode(
                type=episode_type,
                bars=bars_per_phrase,
                texture=texture,
                phrases=(phrase,),
            )
            episodes.append(episode)
            prev_end_chord = harmony[-1] if harmony else tonal_target
            phrase_idx += 1
            current_bar += bars_per_phrase
        tonal_path_out: tuple[str, ...] = tuple([key_area] * phrase_count) if episode_types else tuple(tonal_path_legacy)
        section: Section = Section(
            label=section_def["label"],
            tonal_path=tonal_path_out,
            final_cadence=section_def["final_cadence"],
            episodes=tuple(episodes),
        )
        sections.append(section)
    return Structure(sections=tuple(sections), arc=arc_name)


# =============================================================================
# Phase 4: Period Structure Generation (baroque_plan.md item 4.4)
# =============================================================================

def generate_period(
    mode: str,
    bars_per_phrase: int = 4,
    first_half_modulation: str | None = None,
) -> Structure:
    """Generate a standard 8+8 bar period structure.

    Koch's rule 22: Standard periods are 16 measures organized as:
    - First half (8 bars): 2 phrases, modulates to dominant (major) or relative (minor)
    - Second half (8 bars): 2 phrases, returns to tonic

    Args:
        mode: "major" or "minor"
        bars_per_phrase: Bars per phrase (default 4)
        first_half_modulation: Override modulation target for first half

    Returns:
        Structure with 8+8 bar period organization
    """
    # Determine modulation targets
    if first_half_modulation:
        half1_target = first_half_modulation
    elif mode == "major":
        half1_target = "V"  # Dominant
    else:
        half1_target = "III"  # Relative major (or "v" for minor dominant)

    # First half: I-phrase/V-phrase + Cadence in modulation target
    harmony_1 = generate_phrase_harmony(bars_per_phrase, "I", None, "I")
    phrase_1 = Phrase(
        index=0,
        bars=bars_per_phrase,
        tonal_target="I",
        cadence=None,  # No cadence yet
        treatment="statement",
        surprise=None,
        is_climax=False,
        energy="low",
        harmony=harmony_1,
    )
    harmony_2 = generate_phrase_harmony(bars_per_phrase, half1_target, "half", harmony_1[-1])
    phrase_2 = Phrase(
        index=1,
        bars=bars_per_phrase,
        tonal_target=half1_target,
        cadence="half",  # Half cadence in new key
        treatment="continuation",
        surprise=None,
        is_climax=False,
        energy="medium",
        harmony=harmony_2,
    )

    # Second half: Development/modulation + Cadence in tonic
    harmony_3 = generate_phrase_harmony(bars_per_phrase, half1_target, None, harmony_2[-1])
    phrase_3 = Phrase(
        index=2,
        bars=bars_per_phrase,
        tonal_target=half1_target,  # Continue in secondary key
        cadence=None,
        treatment="development",
        surprise=None,
        is_climax=True,  # Climax typically in development
        energy="high",
        harmony=harmony_3,
    )
    harmony_4 = generate_phrase_harmony(bars_per_phrase, "I", "authentic", harmony_3[-1])
    phrase_4 = Phrase(
        index=3,
        bars=bars_per_phrase,
        tonal_target="I",  # Return to tonic
        cadence="authentic",  # Final authentic cadence
        treatment="closing",
        surprise=None,
        is_climax=False,
        energy="medium",
        harmony=harmony_4,
    )

    # Create episodes for each phrase
    episode_1 = Episode(
        type="opening",
        bars=bars_per_phrase,
        texture="polyphonic",
        phrases=(phrase_1,),
    )
    episode_2 = Episode(
        type="modulating",
        bars=bars_per_phrase,
        texture="polyphonic",
        phrases=(phrase_2,),
    )
    episode_3 = Episode(
        type="development",
        bars=bars_per_phrase,
        texture="polyphonic",
        phrases=(phrase_3,),
    )
    episode_4 = Episode(
        type="closing",
        bars=bars_per_phrase,
        texture="polyphonic",
        phrases=(phrase_4,),
    )

    # Create sections for each half
    first_half = Section(
        label="antecedent",
        tonal_path=("I", half1_target),
        final_cadence="half",
        episodes=(episode_1, episode_2),
    )
    second_half = Section(
        label="consequent",
        tonal_path=(half1_target, "I"),
        final_cadence="authentic",
        episodes=(episode_3, episode_4),
    )

    return Structure(
        sections=(first_half, second_half),
        arc="period",
    )


def generate_sentence(
    mode: str,
    bars: int = 8,
) -> Structure:
    """Generate a sentence structure (presentation + continuation).

    Alternative to period: the sentence has:
    - Presentation (4 bars): statement + response (often sequential)
    - Continuation (4 bars): fragmentation + cadence

    Args:
        mode: "major" or "minor"
        bars: Total bars (default 8)

    Returns:
        Structure with sentence organization
    """
    half_bars = bars // 2
    quarter_bars = bars // 4

    # Presentation: statement + response
    harmony_stmt = generate_phrase_harmony(quarter_bars, "I", None, "I")
    statement = Phrase(
        index=0,
        bars=quarter_bars,
        tonal_target="I",
        cadence=None,
        treatment="statement",
        surprise=None,
        is_climax=False,
        energy="low",
        harmony=harmony_stmt,
    )
    harmony_resp = generate_phrase_harmony(quarter_bars, "I", None, harmony_stmt[-1])
    response = Phrase(
        index=1,
        bars=quarter_bars,
        tonal_target="I",
        cadence=None,
        treatment="response",  # Often sequential repetition
        surprise=None,
        is_climax=False,
        energy="low",
        harmony=harmony_resp,
    )

    # Continuation: fragmentation + cadence
    harmony_frag = generate_phrase_harmony(quarter_bars, "V", None, harmony_resp[-1])
    fragmentation = Phrase(
        index=2,
        bars=quarter_bars,
        tonal_target="V",
        cadence=None,
        treatment="fragmentation",
        surprise=None,
        is_climax=True,
        energy="high",
        harmony=harmony_frag,
    )
    harmony_cad = generate_phrase_harmony(quarter_bars, "I", "authentic", harmony_frag[-1])
    cadential = Phrase(
        index=3,
        bars=quarter_bars,
        tonal_target="I",
        cadence="authentic",
        treatment="closing",
        surprise=None,
        is_climax=False,
        energy="medium",
        harmony=harmony_cad,
    )

    presentation = Episode(
        type="presentation",
        bars=half_bars,
        texture="polyphonic",
        phrases=(statement, response),
    )
    continuation = Episode(
        type="continuation",
        bars=half_bars,
        texture="polyphonic",
        phrases=(fragmentation, cadential),
    )

    section = Section(
        label="sentence",
        tonal_path=("I", "I", "V", "I"),
        final_cadence="authentic",
        episodes=(presentation, continuation),
    )

    return Structure(
        sections=(section,),
        arc="sentence",
    )

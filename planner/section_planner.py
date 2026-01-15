"""Section planner: MacroSection -> SectionPlan with episodes."""
from planner.episode_generator import generate_episodes
from planner.transition import generate_transition, needs_transition
from planner.plannertypes import EpisodeSpec, MacroForm, MacroSection, SectionPlan

# Global seed counter for reproducible variety across sections
_seed_counter: int = 0


def get_next_seed() -> int:
    """Get next seed for episode generation."""
    global _seed_counter
    seed: int = _seed_counter
    _seed_counter += 1
    return seed


def reset_seed_counter(base_seed: int = 0) -> None:
    """Reset seed counter for reproducibility."""
    global _seed_counter
    _seed_counter = base_seed


def plan_section(macro_section: MacroSection) -> SectionPlan:
    """Break a macro-section into episodes using constraint-based generation."""
    seed: int = get_next_seed()
    episodes: tuple[EpisodeSpec, ...] = generate_episodes(macro_section, seed)
    actual_bars: int = sum(ep.bars for ep in episodes)
    return SectionPlan(
        label=macro_section.label,
        character=macro_section.character,
        texture=macro_section.texture,
        key_area=macro_section.key_area,
        episodes=episodes,
        total_bars=actual_bars,
    )


def plan_all_sections(macro_form: MacroForm) -> tuple[SectionPlan, ...]:
    """Plan all sections in a macro-form, inserting transitions as needed."""
    sections: list[MacroSection] = list(macro_form.sections)
    plans: list[SectionPlan] = []
    for i, sec in enumerate(sections):
        if i > 0 and needs_transition(sections[i - 1], sec):
            trans: EpisodeSpec = generate_transition(sections[i - 1], sec)
            prev_plan: SectionPlan = plans[-1]
            extended: tuple[EpisodeSpec, ...] = prev_plan.episodes + (trans,)
            new_bars: int = prev_plan.total_bars + trans.bars
            plans[-1] = SectionPlan(
                label=prev_plan.label,
                character=prev_plan.character,
                texture=prev_plan.texture,
                key_area=prev_plan.key_area,
                episodes=extended,
                total_bars=new_bars,
            )
        plans.append(plan_section(sec))
    return tuple(plans)

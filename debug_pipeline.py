"""Debug actual pipeline to find where filter is bypassed."""
from fractions import Fraction
from builder.figuration.selector import (
    get_figures_for_interval,
    filter_by_direction,
    filter_by_tension,
    filter_by_character,
    filter_by_density,
    filter_by_minor_safety,
    filter_by_compensation,
    filter_cadential_safe,
    filter_by_max_leap,
    filter_by_note_count,
)
from builder.figuration.selection import apply_misbehaviour, select_figure, sort_by_weight
from builder.figuration.rhythm_calc import compute_rhythmic_distribution

def trace_select_figure_with_filters(
    interval: str,
    ascending: bool,
    harmonic_tension: str,
    character: str,
    density: str,
    is_minor: bool,
    prev_leaped: bool,
    leap_direction: str | None,
    near_cadence: bool,
    seed: int,
    required_count: int | None = None,
):
    """Traced version of _select_figure_with_filters."""
    print(f"\n=== trace_select_figure_with_filters ===")
    print(f"  interval={interval}, ascending={ascending}")
    print(f"  harmonic_tension={harmonic_tension}, character={character}")
    print(f"  density={density}, is_minor={is_minor}")
    print(f"  required_count={required_count}")
    
    all_figures = get_figures_for_interval(interval)
    if not all_figures:
        print("  -> No figures for interval!")
        return None
    
    candidates = list(all_figures)
    print(f"  Initial: {[f.name for f in candidates]}")
    
    candidates = filter_by_direction(candidates, ascending)
    print(f"  After direction: {[f.name for f in candidates]}")
    
    candidates = filter_by_tension(candidates, harmonic_tension)
    print(f"  After tension: {[f.name for f in candidates]}")
    
    candidates = filter_by_character(candidates, character)
    print(f"  After character: {[f.name for f in candidates]}")
    
    candidates = filter_by_density(candidates, density)
    print(f"  After density: {[f.name for f in candidates]}")
    
    candidates = filter_by_minor_safety(candidates, is_minor)
    print(f"  After minor_safety: {[f.name for f in candidates]}")
    
    candidates = filter_by_compensation(candidates, prev_leaped, leap_direction)
    print(f"  After compensation: {[f.name for f in candidates]}")
    
    candidates = filter_cadential_safe(candidates, near_cadence)
    print(f"  After cadential_safe: {[f.name for f in candidates]}")
    
    candidates = filter_by_max_leap(candidates)
    print(f"  After max_leap: {[f.name for f in candidates]}")
    
    if required_count is not None:
        candidates = filter_by_note_count(candidates, required_count)
        print(f"  After note_count(required={required_count}): {[f.name for f in candidates]}")
    else:
        print("  NOTE: required_count is None, skipping note_count filter!")
    
    candidates = apply_misbehaviour(candidates, all_figures, seed)
    print(f"  After misbehaviour: {[f.name for f in candidates]}")
    
    candidates = sort_by_weight(candidates)
    selected = select_figure(candidates, seed)
    print(f"  -> Selected: {selected.name if selected else None}")
    return selected


# Test case 1: Simulate Prinner section with high density
print("=" * 60)
print("TEST 1: Prinner schema, step_down, high density, 3/4 bar")
print("=" * 60)

gap = Fraction(3, 4)
density = 'high'
required_count, unit = compute_rhythmic_distribution(gap, density)
print(f"Gap={gap}, density={density} -> required_count={required_count}, unit={unit}")

trace_select_figure_with_filters(
    interval='step_down',
    ascending=False,
    harmonic_tension='low',  # as in _apply_schema_figuration
    character='expressive',  # from stepwise_descent profile
    density=density,
    is_minor=False,
    prev_leaped=False,
    leap_direction=None,
    near_cadence=False,
    seed=42,
    required_count=required_count,
)

# Test case 2: What if density is medium?
print("\n" + "=" * 60)
print("TEST 2: Same but density='medium'")
print("=" * 60)

density = 'medium'
required_count, unit = compute_rhythmic_distribution(gap, density)
print(f"Gap={gap}, density={density} -> required_count={required_count}, unit={unit}")

trace_select_figure_with_filters(
    interval='step_down',
    ascending=False,
    harmonic_tension='low',
    character='expressive',
    density=density,
    is_minor=False,
    prev_leaped=False,
    leap_direction=None,
    near_cadence=False,
    seed=42,
    required_count=required_count,
)

# Test case 3: What if density is low?
print("\n" + "=" * 60)
print("TEST 3: Same but density='low'")
print("=" * 60)

density = 'low'
required_count, unit = compute_rhythmic_distribution(gap, density)
print(f"Gap={gap}, density={density} -> required_count={required_count}, unit={unit}")

trace_select_figure_with_filters(
    interval='step_down',
    ascending=False,
    harmonic_tension='low',
    character='expressive',
    density=density,
    is_minor=False,
    prev_leaped=False,
    leap_direction=None,
    near_cadence=False,
    seed=42,
    required_count=required_count,
)

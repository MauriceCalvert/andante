"""Debug full filter pipeline."""
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
from builder.figuration.rhythm_calc import compute_rhythmic_distribution

# Simulate Prinner bar 16: step_down, high density, 3/4 bar
gap = Fraction(3, 4)
density = 'high'
required_count, unit = compute_rhythmic_distribution(gap, density)
print(f'Gap={gap}, density={density} -> required_count={required_count}')

# Parameters matching _apply_schema_figuration for Prinner
interval = 'step_down'
ascending = False  # 6->5 is descending
harmonic_tension = 'low'
character = 'expressive'  # from stepwise_descent profile
is_minor = False
prev_leaped = False
leap_direction = None
near_cadence = False

# Get figures
figs = get_figures_for_interval(interval)
print(f'\nInitial: {len(figs)} figures')

# Apply each filter in order
figs = filter_by_direction(figs, ascending)
print(f'After direction: {[f.name for f in figs]}')

figs = filter_by_tension(figs, harmonic_tension)
print(f'After tension: {[f.name for f in figs]}')

figs = filter_by_character(figs, character)
print(f'After character: {[f.name for f in figs]}')

figs = filter_by_density(figs, density)
print(f'After density: {[f.name for f in figs]}')

figs = filter_by_minor_safety(figs, is_minor)
print(f'After minor_safety: {[f.name for f in figs]}')

figs = filter_by_compensation(figs, prev_leaped, leap_direction)
print(f'After compensation: {[f.name for f in figs]}')

figs = filter_cadential_safe(figs, near_cadence)
print(f'After cadential_safe: {[f.name for f in figs]}')

figs = filter_by_max_leap(figs)
print(f'After max_leap: {[f.name for f in figs]}')

figs = filter_by_note_count(figs, required_count)
print(f'After note_count: {[f.name for f in figs]}')

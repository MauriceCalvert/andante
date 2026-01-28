"""Quick test for schema loading with signed degrees."""
from builder.config_loader import load_all_schemas

schemas = load_all_schemas()
print(f"Loaded {len(schemas)} schemas")

# Test do_re_mi
drm = schemas["do_re_mi"]
print(f"\ndo_re_mi:")
print(f"  soprano_degrees={drm.soprano_degrees}")
print(f"  soprano_directions={drm.soprano_directions}")
print(f"  bass_degrees={drm.bass_degrees}")
print(f"  bass_directions={drm.bass_directions}")
print(f"  entry=({drm.entry_soprano}, {drm.entry_bass})")
print(f"  exit=({drm.exit_soprano}, {drm.exit_bass})")

# Test monte (sequential)
monte = schemas["monte"]
print(f"\nmonte:")
print(f"  soprano_degrees={monte.soprano_degrees}")
print(f"  soprano_directions={monte.soprano_directions}")
print(f"  bass_degrees={monte.bass_degrees}")
print(f"  bass_directions={monte.bass_directions}")
print(f"  segment_direction={monte.segment_direction}")

# Verify bass direction for do_re_mi
# Expected: 1 -> 7 (down), 7 -> 1 (up)
print(f"\nVerification:")
print(f"  do_re_mi bass: 1 -> 7 should be 'down': {drm.bass_directions[1]}")
print(f"  do_re_mi bass: 7 -> 1 should be 'up': {drm.bass_directions[2]}")

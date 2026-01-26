"""Regenerate bach_minuet and check output."""
from planner.planner import generate_to_files
from pathlib import Path

output_dir = Path("output")
result = generate_to_files("minuet", "Zierlich", output_dir, "bach_minuet", "g_major")
print(f"Generated {len(result.soprano)} soprano notes, {len(result.bass)} bass notes")
print(f"Metre: {result.metre}, Tempo: {result.tempo}")

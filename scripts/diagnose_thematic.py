"""Diagnostic: print thematic plan assignments."""
import yaml
from pathlib import Path
from fractions import Fraction

from planner.thematic import plan_thematic_roles
from shared.key import Key

# Load genre YAML
genre_path = Path(__file__).parent.parent / 'data/genres/invention.yaml'
with open(genre_path, 'r', encoding='utf-8') as f:
    genre_data = yaml.safe_load(f)

thematic_config = genre_data['thematic']
entry_seq = thematic_config['entry_sequence']

# Create minimal thematic plan
home_key = Key(tonic="C", mode="major")
plan = plan_thematic_roles(
    total_bars=26,
    metre="4/4",
    voice_count=2,
    home_key=home_key,
    thematic_config=thematic_config,
    subject_bars=2,
)

print(f"Total roles: {len(plan)}")
print()
print("Entry sequence:")
for i, entry in enumerate(entry_seq):
    print(f"  {i+1}. {entry}")
print()

# Print bar-by-bar assignments for first 14 bars
print("Bar-by-bar thematic assignments (first 14 bars):")
print(f"{'Bar':<4} {'Beat':<6} {'Voice':<6} {'Role':<10} {'Material':<15} {'Key':<10}")
print("-" * 70)

for role in plan:
    if role.bar > 14:
        break
    if role.beat == Fraction(0):  # Only show downbeats
        voice_name = "upper" if role.voice == 0 else "lower"
        print(f"{role.bar:<4} {float(role.beat)+1:<6.1f} {voice_name:<6} {role.role.value:<10} {role.material or 'None':<15} {role.material_key.tonic} {role.material_key.mode}")

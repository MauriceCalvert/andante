"""Full pipeline: Brief -> MIDI using split packages.

Usage:
    python -m scripts.run_pipeline <brief.yaml> <output_path>

This demonstrates the complete split architecture:
    Brief YAML -> planner -> Plan YAML
    Plan YAML -> engine -> MIDI/MusicXML
"""
import sys
from pathlib import Path

import yaml

from engine.pipeline import execute_and_export
from planner.planner import build_plan
from planner.serializer import serialize_plan
from planner.plannertypes import Brief, Motif
from planner.motif_loader import load_motif


def main() -> None:
    """Run full pipeline."""
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.run_pipeline <brief.yaml> <output_path>", file=sys.stderr)
        sys.exit(1)
    brief_path: Path = Path(sys.argv[1])
    output_path: str = sys.argv[2]
    if not brief_path.exists():
        print(f"Error: File not found: {brief_path}", file=sys.stderr)
        sys.exit(1)
    with open(brief_path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    brief_data: dict = data.get("brief", data)
    motif_source: str | None = brief_data.get("motif_source")
    brief: Brief = Brief(
        affect=brief_data["affect"],
        genre=brief_data["genre"],
        forces=brief_data["forces"],
        bars=brief_data["bars"],
        virtuosic=brief_data.get("virtuosic", False),
        motif_source=motif_source,
    )
    # Load user motif if specified
    user_motif: Motif | None = None
    if motif_source:
        print(f"Loading motif from {motif_source}...")
        user_motif = load_motif(motif_source)
        print(f"  Degrees: {user_motif.degrees}")
        print(f"  Durations: {[str(d) for d in user_motif.durations]}")
    print(f"Building plan from {brief_path}...")
    plan = build_plan(brief, user_motif=user_motif)
    plan_yaml: str = serialize_plan(plan)
    plan_out: Path = Path(output_path).with_suffix(".plan.yaml")
    with open(plan_out, "w", encoding="utf-8") as f:
        f.write(plan_yaml)
    print(f"  Plan written to {plan_out}")
    print("Executing plan...")
    notes = execute_and_export(plan_yaml, output_path)
    print(f"  Wrote {len(notes)} notes to {output_path}.*")
    print("Done!")


if __name__ == "__main__":
    main()

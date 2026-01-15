"""Plan validator: structural and semantic checks."""
from fractions import Fraction

from planner.material import bar_duration
from planner.plannertypes import Plan


def validate(plan: Plan) -> tuple[bool, list[str]]:
    """Validate plan. Returns (valid, errors)."""
    errors: list[str] = []
    if not plan.structure.sections:
        errors.append("Structure must have at least one section")
    seen_labels: set[str] = set()
    for section in plan.structure.sections:
        if section.label in seen_labels:
            errors.append(f"Duplicate section label: {section.label}")
        seen_labels.add(section.label)
        if not section.episodes:
            errors.append(f"Section {section.label} must have at least one episode")
        if not section.tonal_path:
            errors.append(f"Section {section.label} must have non-empty tonal_path")
        phrase_count: int = sum(len(ep.phrases) for ep in section.episodes)
        if phrase_count != len(section.tonal_path):
            errors.append(f"Section {section.label}: phrase count must equal tonal_path length")
    last_section = plan.structure.sections[-1] if plan.structure.sections else None
    if last_section and last_section.final_cadence != "authentic":
        errors.append("Last section must have authentic final_cadence")
    motif = plan.material.subject
    if len(motif.degrees) != len(motif.durations):
        errors.append("Motif degrees and durations must have same length")
    bar_dur: Fraction = bar_duration(plan.frame.metre)
    expected_dur: Fraction = bar_dur * motif.bars
    actual_dur: Fraction = sum(motif.durations, Fraction(0))
    if actual_dur != expected_dur:
        errors.append(f"Motif duration {actual_dur} != expected {expected_dur}")
    indices: list[int] = []
    for section in plan.structure.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                indices.append(phrase.index)
    expected_indices: list[int] = list(range(len(indices)))
    if indices != expected_indices:
        errors.append(f"Phrase indices must be sequential from 0: got {indices}")
    return (len(errors) == 0, errors)

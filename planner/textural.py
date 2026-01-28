"""Layer 5: Textural.

Category A: Pure functions, no I/O, no validation.
Input: Genre + bar assignments
Output: Treatment assignments with bar ranges and voice assignments

Determines which voice carries thematic material per bar range.
Must run BEFORE rhythm and pitch generation (L6, L7).
"""
from builder.types import GenreConfig, TreatmentAssignment


def layer_5_textural(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[TreatmentAssignment]:
    """Execute Layer 5.

    Args:
        genre_config: Genre configuration with treatment_sequence
        bar_assignments: Section name -> (start_bar, end_bar) mapping

    Returns:
        List of TreatmentAssignment with bar ranges and voice assignments.
    """
    if genre_config.treatment_sequence:
        return _sequence_texture(genre_config, bar_assignments)
    return _default_texture(genre_config, bar_assignments)


def _default_texture(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[TreatmentAssignment]:
    """Default texture: statement treatment for all sections."""
    assignments: list[TreatmentAssignment] = []
    for section_name, (start_bar, end_bar) in bar_assignments.items():
        assignments.append(TreatmentAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            treatment="statement",
            subject_voice=None,
        ))
    return assignments


def _sequence_texture(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[TreatmentAssignment]:
    """Generate texture from treatment_sequence in YAML.

    Each entry in treatment_sequence specifies:
      - treatment: str (subject, answer, episode, development, cadential, statement)
      - subject_voice: int|null (0=soprano, 1=bass, null=both)

    Maps entries to sections by index order.
    """
    assignments: list[TreatmentAssignment] = []
    treatment_seq: list[dict] = list(genre_config.treatment_sequence)
    sections: list[tuple[str, int, int]] = [
        (section["name"], *bar_assignments[section["name"]])
        for section in genre_config.sections
    ]
    section_idx: int = 0
    for entry in treatment_seq:
        if section_idx >= len(sections):
            break
        section_name, start_bar, end_bar = sections[section_idx]
        treatment: str = entry.get("treatment", "statement")
        subject_voice_raw = entry.get("subject_voice")
        subject_voice: int | None = None if subject_voice_raw is None else int(subject_voice_raw)
        assignments.append(TreatmentAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            treatment=treatment,
            subject_voice=subject_voice,
        ))
        section_idx += 1
    while section_idx < len(sections):
        section_name, start_bar, end_bar = sections[section_idx]
        assignments.append(TreatmentAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            treatment="statement",
            subject_voice=None,
        ))
        section_idx += 1
    return assignments


def treatments_to_rhythm_input(
    assignments: list[TreatmentAssignment],
) -> list[dict]:
    """Convert TreatmentAssignment list to rhythm planning input format.

    Args:
        assignments: List of TreatmentAssignment from L5

    Returns:
        List of dicts with {bars: [start, end], subject_voice: 0|1|None}
    """
    return [
        {
            "bars": [a.start_bar, a.end_bar],
            "subject_voice": a.subject_voice,
        }
        for a in assignments
    ]

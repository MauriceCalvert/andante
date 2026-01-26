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
    if genre_config.name == "invention":
        return _invention_texture(genre_config, bar_assignments)
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


def _invention_texture(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[TreatmentAssignment]:
    """Generate texture sequence for invention.

    Sequence: S → A → episode₁ → S'/A' → episode₂ → S'' → coda
    Maps treatment_sequence entries to bar ranges from sections.
    """
    assignments: list[TreatmentAssignment] = []
    treatment_seq: list[dict] = list(genre_config.treatment_sequence)
    sections: list[tuple[str, int, int]] = [
        (section["name"], *bar_assignments[section["name"]])
        for section in genre_config.sections
    ]

    # Match treatments to sections
    section_idx: int = 0
    for treatment in treatment_seq:
        if section_idx >= len(sections):
            break

        symbol: str = treatment.get("symbol", "schematic")
        section_name, start_bar, end_bar = sections[section_idx]

        if symbol == "S":
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="subject",
                subject_voice=0,  # soprano
            ))
        elif symbol == "A":
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="answer",
                subject_voice=1,  # bass
            ))
        elif symbol.startswith("episode"):
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="episode",
                subject_voice=None,
            ))
        elif symbol == "development":
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="development",
                subject_voice=None,
            ))
        elif symbol == "return":
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="subject",
                subject_voice=0,
            ))
        elif symbol == "coda":
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="cadential",
                subject_voice=None,
            ))
        else:
            assignments.append(TreatmentAssignment(
                start_bar=start_bar,
                end_bar=end_bar,
                treatment="statement",
                subject_voice=None,
            ))

        section_idx += 1

    # Handle remaining sections not covered by treatment_seq
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

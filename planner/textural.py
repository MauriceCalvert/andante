"""Layer 5: Textural.

Category A: Pure functions, no I/O, no validation.
Input: Genre + bar assignments
Output: Passage assignments with bar ranges and lead voice

Determines which voice carries thematic material per bar range.
Must run BEFORE rhythm and pitch generation (L6, L7).

Per vocabulary.md:
- PassageAssignment binds a bar range to a passage function (subject, answer, etc.)
- function field holds the passage function name
- lead_voice indicates which voice leads (0=upper, 1=lower, None=equal)
"""
from builder.types import GenreConfig, PassageAssignment


def layer_5_textural(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[PassageAssignment]:
    """Execute Layer 5.

    Args:
        genre_config: Genre configuration with passage_sequence
        bar_assignments: Section name -> (start_bar, end_bar) mapping

    Returns:
        List of PassageAssignment with bar ranges and lead voice.
    """
    if genre_config.passage_sequence:
        return _sequence_texture(genre_config, bar_assignments)
    return _default_texture(genre_config, bar_assignments)


def _default_texture(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[PassageAssignment]:
    """Default texture: subject function for all sections."""
    assignments: list[PassageAssignment] = []
    for section_name, (start_bar, end_bar) in bar_assignments.items():
        assignments.append(PassageAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            function="subject",
            lead_voice=None,
        ))
    return assignments


def _sequence_texture(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[PassageAssignment]:
    """Generate texture from passage_sequence in YAML.

    Each entry in passage_sequence specifies:
      - function: str (subject, answer, episode, development, cadential)
      - lead_voice: int|null (0=upper, 1=lower, null=equal)

    Also accepts legacy field names during transition:
      - treatment -> function
      - subject_voice -> lead_voice

    Maps entries to sections by index order.
    """
    assignments: list[PassageAssignment] = []
    passage_seq: list[dict] = list(genre_config.passage_sequence)
    sections: list[tuple[str, int, int]] = [
        (section["name"], *bar_assignments[section["name"]])
        for section in genre_config.sections
    ]
    section_idx: int = 0
    for entry in passage_seq:
        if section_idx >= len(sections):
            break
        section_name, start_bar, end_bar = sections[section_idx]
        # Accept both new and legacy field names
        function: str = entry.get("function", entry.get("treatment", "subject"))
        lead_voice_raw = entry.get("lead_voice", entry.get("subject_voice"))
        lead_voice: int | None = None if lead_voice_raw is None else int(lead_voice_raw)
        assignments.append(PassageAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            function=function,
            lead_voice=lead_voice,
        ))
        section_idx += 1
    while section_idx < len(sections):
        section_name, start_bar, end_bar = sections[section_idx]
        assignments.append(PassageAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            function="subject",
            lead_voice=None,
        ))
        section_idx += 1
    return assignments


def passages_to_rhythm_input(
    assignments: list[PassageAssignment],
) -> list[dict]:
    """Convert PassageAssignment list to rhythm planning input format.

    Args:
        assignments: List of PassageAssignment from L5

    Returns:
        List of dicts with {bars: [start, end], lead_voice: 0|1|None}
    """
    return [
        {
            "bars": [a.start_bar, a.end_bar],
            "lead_voice": a.lead_voice,
        }
        for a in assignments
    ]

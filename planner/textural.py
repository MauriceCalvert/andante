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
from fractions import Fraction

from builder.types import GenreConfig, PassageAssignment


def layer_5_textural(
    genre_config: GenreConfig,
    bar_assignments: dict[str, tuple[int, int]],
) -> list[PassageAssignment]:
    """Execute Layer 5.

    Args:
        genre_config: Genre configuration with sections
        bar_assignments: Section name -> (start_bar, end_bar) mapping

    Returns:
        List of PassageAssignment with bar ranges and lead voice.
    """
    assignments: list[PassageAssignment] = []
    for section in genre_config.sections:
        section_name: str = section["name"]
        if section_name not in bar_assignments:
            continue
        start_bar, end_bar = bar_assignments[section_name]
        function: str = section.get("function", "subject")
        lead_voice: int | None = section.get("lead_voice")
        accompany_texture: str | None = section.get("accompany_texture")
        follow_voice: int | None = section.get("follow_voice")
        raw_delay: str | None = section.get("follow_delay")
        follow_delay: Fraction | None = None
        follow_interval: int | None = section.get("follow_interval")
        if follow_voice is not None:
            assert raw_delay is not None, (
                f"Section '{section_name}': follow_voice requires follow_delay"
            )
            assert follow_interval is not None, (
                f"Section '{section_name}': follow_voice requires follow_interval"
            )
            follow_delay = Fraction(raw_delay)
            assert follow_delay > 0, (
                f"Section '{section_name}': follow_delay must be positive, "
                f"got {follow_delay}"
            )
        assignments.append(PassageAssignment(
            start_bar=start_bar,
            end_bar=end_bar,
            function=function,
            lead_voice=lead_voice,
            accompany_texture=accompany_texture,
            follow_voice=follow_voice,
            follow_delay=follow_delay,
            follow_interval=follow_interval,
        ))
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

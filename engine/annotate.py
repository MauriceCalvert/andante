"""Extract annotations from piece structure for labeling output."""
from fractions import Fraction

from engine.engine_types import Annotation, PieceAST


def extract_annotations(
    piece: PieceAST,
    granularity: str = "phrase",
) -> tuple[Annotation, ...]:
    """Extract annotations from piece at specified granularity.

    Args:
        piece: Parsed piece AST with section/episode/phrase hierarchy.
        granularity: "none", "section", "episode", or "phrase".

    Returns:
        Tuple of Annotation objects sorted by offset.
    """
    if granularity == "none":
        return ()
    num_str, den_str = piece.metre.split("/")
    bar_dur: Fraction = Fraction(int(num_str), int(den_str))
    annotations: list[Annotation] = []
    offset: Fraction = Fraction(0)
    for section in piece.sections:
        section_start: Fraction = offset
        if granularity in ("section", "episode", "phrase"):
            tonal: str = section.tonal_path[0] if section.tonal_path else "I"
            text: str = f"{section.label}: {tonal}"
            annotations.append(Annotation(offset=section_start, text=text, level="section"))
        for episode in section.episodes:
            episode_start: Fraction = offset
            if granularity in ("episode", "phrase"):
                text = f"{episode.type}"
                annotations.append(Annotation(offset=episode_start, text=text, level="episode"))
            for phrase in episode.phrases:
                phrase_start: Fraction = offset
                if granularity == "phrase":
                    text = f"{phrase.treatment}"
                    annotations.append(Annotation(offset=phrase_start, text=text, level="phrase"))
                offset += bar_dur * phrase.bars
    return tuple(sorted(annotations, key=lambda a: (a.offset, _level_order(a.level))))


def _level_order(level: str) -> int:
    """Sort order for annotation levels (section first, then episode, then phrase)."""
    return {"section": 0, "episode": 1, "phrase": 2}.get(level, 3)

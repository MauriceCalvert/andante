"""Subject selection — delegates to plan-driven selector (SUB-2).

Legacy flat-enumeration code removed. The plan-driven selector
(planned_selector.py) handles per-segment density contrast.
"""

from motifs.subject_gen.models import GeneratedSubject
from motifs.subject_gen.planned_selector import select_planned_subjects


def select_diverse_subjects(
    n: int = 6,
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    fixed_midi: tuple[int, ...] | None = None,
    verbose: bool = False,
) -> list[GeneratedSubject]:
    """Select n subjects maximising pairwise feature distance."""
    assert pitch_contour is None, (
        "pitch_contour filter not supported by plan-driven selector; "
        "use planned_selector directly or remove --contour flag"
    )
    assert fixed_midi is None, (
        "fixed_midi not supported by plan-driven selector; "
        "remove --pitches flag"
    )
    return select_planned_subjects(
        n=n,
        mode=mode,
        metre=metre,
        tonic_midi=tonic_midi,
        target_bars=target_bars,
        note_counts=note_counts,
        verbose=verbose,
    )


def select_subject(
    mode: str = "major",
    metre: tuple[int, int] = (4, 4),
    tonic_midi: int = 60,
    target_bars: int | None = None,
    pitch_contour: str | None = None,
    rhythm_contour: str | None = None,
    note_counts: tuple[int, ...] | None = None,
    fixed_midi: tuple[int, ...] | None = None,
    seed: int = 0,
    verbose: bool = False,
) -> GeneratedSubject:
    """Select a single subject (seed indexes into a diverse set)."""
    subjects = select_diverse_subjects(
        n=6,
        mode=mode,
        metre=metre,
        tonic_midi=tonic_midi,
        target_bars=target_bars,
        pitch_contour=pitch_contour,
        note_counts=note_counts,
        fixed_midi=fixed_midi,
        verbose=verbose,
    )
    return subjects[seed % len(subjects)]

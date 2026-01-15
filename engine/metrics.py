"""Piece metrics calculation."""
from fractions import Fraction

from engine.engine_types import ExpandedPhrase, PieceMetrics

SUBJECT_TREATMENTS: set[str] = {
    "statement", "imitation", "inversion", "retrograde", "augmentation", "stretto", "sequence", "repose"
}
DERIVED_TREATMENTS: set[str] = {"head_sequence", "tail_development", "fragmentation", "diminution"}
EPISODE_TYPES: set[str] = {"scalar", "arpeggiated", "cadenza", "turbulent"}
BASS_LEAD_EPISODES: set[str] = {"bass_statement", "bass_sequence", "bass_development"}


def compute_metrics(phrases: list[ExpandedPhrase], bar_duration: Fraction) -> PieceMetrics:
    """Compute proportion metrics from expanded phrases.

    Categories:
    - subject_bars: Treatments using full subject (statement, imitation, etc.)
    - derived_bars: Treatments using derived motifs (head_sequence, tail_development)
    - episode_bars: Scalar/arpeggiated episodes based on intervals
    - free_bars: Transitions, cadences, accompaniment-heavy textures
    """
    total_bars: int = 0
    subject_bars: int = 0
    derived_bars: int = 0
    episode_bars: int = 0
    free_bars: int = 0
    for phrase in phrases:
        phrase_bars: int = phrase.bars if hasattr(phrase, 'bars') else int(
            sum(phrase.soprano_durations, Fraction(0)) / bar_duration
        )
        total_bars += phrase_bars
        treatment: str = phrase.treatment if hasattr(phrase, 'treatment') else "statement"
        episode: str | None = phrase.episode_type
        if episode in EPISODE_TYPES:
            episode_bars += phrase_bars
        elif treatment in DERIVED_TREATMENTS:
            derived_bars += phrase_bars
        elif treatment in SUBJECT_TREATMENTS:
            subject_bars += phrase_bars
        else:
            free_bars += phrase_bars
    return PieceMetrics(
        total_bars=total_bars,
        subject_bars=subject_bars,
        derived_bars=derived_bars,
        episode_bars=episode_bars,
        free_bars=free_bars,
    )

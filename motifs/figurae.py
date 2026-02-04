"""Figurenlehre - Baroque rhetorical musical figures.

This module provides:
1. Loading and validation of figurae definitions
2. Selection of appropriate figurae based on affect and context
3. Constraint checking for motif compliance with figurae
4. Application of figurae patterns to melodic generation
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml


DATA_DIR: Path = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class FiguraConstraints:
    """Constraints that define a figura's musical characteristics."""
    min_notes: int | None = None
    direction: str | None = None  # ascending, descending, None
    motion: str | None = None  # stepwise, None
    chromatic: bool = False
    returns_to_start: bool = False
    max_duration_per_note: float | None = None
    interval_type: tuple[str, ...] | None = None
    interval: str | None = None  # e.g., "minor_sixth_up"
    phrase_end: bool = False
    accent_off_beat: bool = False
    early_arrival: bool = False
    suspension: bool = False
    dotted: bool = False
    pattern: str | None = None  # e.g., "short_long"
    imitation: bool = False
    voices: int | None = None
    homophonic: bool = False
    parallel_motion: bool = False
    contrast: bool = False
    neighbor: bool = False
    oscillation: bool = False
    on_cadence: bool = False
    dissonant_approach: bool = False
    resolves_stepwise: bool = False
    follows_main_note: bool = False
    rest: bool = False
    unexpected: bool = False
    short_rests: bool = False
    between_phrases: bool = False
    break_in_line: bool = False
    exact_repeat: bool = False
    immediate: bool = False


@dataclass(frozen=True)
class Figura:
    """A baroque rhetorical musical figure."""
    name: str
    category: str  # melodic, rhythmic, textural, ornamental, structural
    description: str
    affects: tuple[str, ...]
    rhetoric_positions: tuple[str, ...]
    tension_range: tuple[float, float]
    constraints: FiguraConstraints


class Figurae:
    """Manager for baroque musical figures."""

    def __init__(self) -> None:
        """Load figurae from YAML."""
        self._figurae: dict[str, Figura] = {}
        self._by_category: dict[str, list[str]] = {}
        self._by_affect: dict[str, list[str]] = {}
        self._load()

    def _load(self) -> None:
        """Load and parse figurae.yaml."""
        path = DATA_DIR / "rhetoric" / "figurae.yaml"
        if not path.exists():
            return

        with open(path, encoding="utf-8") as f:
            data: dict = yaml.safe_load(f)

        for category, figures in data.items():
            if not isinstance(figures, dict):
                continue
            self._by_category.setdefault(category, [])
            for name, defn in figures.items():
                if not isinstance(defn, dict):
                    continue
                # Parse constraints
                raw_constraints = defn.get("constraints", {})
                interval_type = raw_constraints.get("interval_type")
                if interval_type:
                    interval_type = tuple(interval_type)

                constraints = FiguraConstraints(
                    min_notes=raw_constraints.get("min_notes"),
                    direction=raw_constraints.get("direction"),
                    motion=raw_constraints.get("motion"),
                    chromatic=raw_constraints.get("chromatic", False),
                    returns_to_start=raw_constraints.get("returns_to_start", False),
                    max_duration_per_note=raw_constraints.get("max_duration_per_note"),
                    interval_type=interval_type,
                    interval=raw_constraints.get("interval"),
                    phrase_end=raw_constraints.get("phrase_end", False),
                    accent_off_beat=raw_constraints.get("accent_off_beat", False),
                    early_arrival=raw_constraints.get("early_arrival", False),
                    suspension=raw_constraints.get("suspension", False),
                    dotted=raw_constraints.get("dotted", False),
                    pattern=raw_constraints.get("pattern"),
                    imitation=raw_constraints.get("imitation", False),
                    voices=raw_constraints.get("voices"),
                    homophonic=raw_constraints.get("homophonic", False),
                    parallel_motion=raw_constraints.get("parallel_motion", False),
                    contrast=raw_constraints.get("contrast", False),
                    neighbor=raw_constraints.get("neighbor", False),
                    oscillation=raw_constraints.get("oscillation", False),
                    on_cadence=raw_constraints.get("on_cadence", False),
                    dissonant_approach=raw_constraints.get("dissonant_approach", False),
                    resolves_stepwise=raw_constraints.get("resolves_stepwise", False),
                    follows_main_note=raw_constraints.get("follows_main_note", False),
                    rest=raw_constraints.get("rest", False),
                    unexpected=raw_constraints.get("unexpected", False),
                    short_rests=raw_constraints.get("short_rests", False),
                    between_phrases=raw_constraints.get("between_phrases", False),
                    break_in_line=raw_constraints.get("break_in_line", False),
                    exact_repeat=raw_constraints.get("exact_repeat", False),
                    immediate=raw_constraints.get("immediate", False),
                )

                affects = tuple(defn.get("affects", []))
                positions = tuple(defn.get("rhetoric_positions", []))
                tension = defn.get("tension_range", [0.0, 1.0])

                figura = Figura(
                    name=name,
                    category=category,
                    description=defn.get("description", ""),
                    affects=affects,
                    rhetoric_positions=positions,
                    tension_range=(tension[0], tension[1]),
                    constraints=constraints,
                )

                self._figurae[name] = figura
                self._by_category[category].append(name)

                # Index by affect
                for affect in affects:
                    self._by_affect.setdefault(affect, []).append(name)

    def get(self, name: str) -> Optional[Figura]:
        """Get a figura by name."""
        return self._figurae.get(name)

    def all_names(self) -> list[str]:
        """Get all figura names."""
        return list(self._figurae.keys())

    def by_category(self, category: str) -> list[Figura]:
        """Get all figurae in a category."""
        names = self._by_category.get(category, [])
        return [self._figurae[n] for n in names]

    def by_affect(self, affect: str) -> list[Figura]:
        """Get all figurae appropriate for an affect."""
        names = self._by_affect.get(affect, [])
        return [self._figurae[n] for n in names]

    def melodic_figurae(self) -> list[Figura]:
        """Get melodic figurae (most relevant for motif generation)."""
        return self.by_category(category="melodic")

    def select_for_motif(
        self,
        affect: str,
        tension: float = 0.5,
        rhetoric_position: str | None = None,
    ) -> list[Figura]:
        """Select figurae appropriate for motif generation context.

        Args:
            affect: The affect (Freudigkeit, Klage, etc.)
            tension: Current tension level (0.0-1.0)
            rhetoric_position: Position in piece (exordium, narratio, etc.)

        Returns:
            List of applicable figurae, sorted by relevance
        """
        candidates: list[tuple[Figura, float]] = []

        # Only melodic figurae apply to motif generation
        for fig in self.melodic_figurae():
            score = 0.0

            # Must match affect
            if affect not in fig.affects:
                continue
            score += 1.0

            # Tension within range
            if fig.tension_range[0] <= tension <= fig.tension_range[1]:
                score += 0.5
            elif abs(tension - (fig.tension_range[0] + fig.tension_range[1]) / 2) < 0.3:
                score += 0.2  # Close enough

            # Rhetoric position match
            if rhetoric_position and rhetoric_position in fig.rhetoric_positions:
                score += 0.3

            candidates.append((fig, score))

        # Sort by score descending
        candidates.sort(key=lambda x: x[1], reverse=True)
        return [fig for fig, _ in candidates]


def check_motif_figura(
    indices: list[int],
    durations: list[float],
    figura: Figura,
) -> tuple[bool, str]:
    """Check if a motif satisfies a figura's constraints.

    Args:
        indices: Scale degree indices (0-6)
        durations: Note durations in whole notes
        figura: The figura to check against

    Returns:
        (passes, reason) tuple
    """
    c = figura.constraints

    # Check min_notes
    if c.min_notes and len(indices) < c.min_notes:
        return False, f"too_few_notes({len(indices)}<{c.min_notes})"

    # Check direction
    if c.direction:
        net_motion = indices[-1] - indices[0]
        if c.direction == "ascending" and net_motion <= 0:
            return False, f"not_ascending({net_motion})"
        if c.direction == "descending" and net_motion >= 0:
            return False, f"not_descending({net_motion})"

    # Check motion type
    if c.motion == "stepwise":
        intervals = [abs(indices[i+1] - indices[i]) for i in range(len(indices)-1)]
        non_steps = sum(1 for iv in intervals if iv > 1)
        if non_steps > 1:  # Allow one non-step for variety
            return False, f"not_stepwise({non_steps}_leaps)"

    # Check returns_to_start (circulatio)
    if c.returns_to_start:
        if abs(indices[-1] - indices[0]) > 1:
            return False, f"does_not_return({indices[-1]} vs {indices[0]})"

    # Check max_duration_per_note (tirata = fast)
    if c.max_duration_per_note:
        if any(d > c.max_duration_per_note for d in durations):
            return False, f"note_too_long(>{c.max_duration_per_note})"

    # Check dotted rhythm
    if c.dotted:
        has_dotted = any(
            i < len(durations) - 1 and
            abs(durations[i] / durations[i+1] - 3.0) < 0.5
            for i in range(len(durations) - 1)
        )
        if not has_dotted:
            return False, "no_dotted_rhythm"

    return True, "ok"


def score_motif_figurae(
    indices: list[int],
    durations: list[float],
    figurae: list[Figura],
) -> tuple[float, list[str]]:
    """Score how well a motif embodies applicable figurae.

    Args:
        indices: Scale degree indices
        durations: Note durations
        figurae: List of applicable figurae to check

    Returns:
        (score 0.0-1.0, list of satisfied figura names)
    """
    if not figurae:
        return 0.5, []  # Neutral if no figurae specified

    satisfied: list[str] = []
    for fig in figurae:
        passes, _ = check_motif_figura(indices=indices, durations=durations, figura=fig)
        if passes:
            satisfied.append(fig.name)

    # Score based on how many figurae are satisfied
    score = len(satisfied) / len(figurae) if figurae else 0.5
    return score, satisfied


# Global instance
_figurae: Figurae | None = None


def get_figurae() -> Figurae:
    """Get the global Figurae manager."""
    global _figurae
    if _figurae is None:
        _figurae = Figurae()
    return _figurae

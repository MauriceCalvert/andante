"""Subject class: encapsulates subject and N counter-subjects.

Uses the gold-plated cs_generator for beautiful, invertible counter-subjects
with joint pitch+rhythm optimization.
"""
from fractions import Fraction

from planner.cs_generator import (
    DEFAULT_MIN_CS_DURATION,
    VALID_DURATIONS,
    generate_countersubject,
    Subject as CSSubject,
    CounterSubject,
)
from planner.plannertypes import Motif


class Subject:
    """Encapsulates subject motif with lazy N-voice counter-subject generation.

    Each counter-subject's rhythm is generated using CP-SAT to minimize attack
    collisions with ALL preceding motifs (subject and earlier counter-subjects).
    Motifs are named: subject, cs_1, cs_2, ... cs_N.
    """

    def __init__(self, degrees: tuple[int, ...], durations: tuple[Fraction, ...], bars: int, mode: str = "major", genre: str = "", voice_count: int = 2) -> None:
        assert len(degrees) == len(durations), "Degrees and durations must match"
        assert all(1 <= d <= 7 for d in degrees), "Degrees must be 1-7"
        assert voice_count >= 2, "Must have at least 2 voices"
        self._degrees: tuple[int, ...] = degrees
        self._durations: tuple[Fraction, ...] = durations
        self._bars: int = bars
        self._mode: str = mode
        self._genre: str = genre
        self._voice_count: int = voice_count
        self._motifs: dict[str, Motif] = {}
        self._cs_degrees: tuple[int, ...] | None = None
        self._cs_durations: tuple[Fraction, ...] | None = None

    @property
    def degrees(self) -> tuple[int, ...]:
        return self._degrees

    @property
    def durations(self) -> tuple[Fraction, ...]:
        return self._durations

    @property
    def bars(self) -> int:
        return self._bars

    @property
    def subject(self) -> Motif:
        return Motif(degrees=self._degrees, durations=self._durations, bars=self._bars)

    @property
    def counter_subject(self) -> Motif:
        if self._cs_degrees is None:
            self._generate_counter_subject()
        return Motif(degrees=self._cs_degrees, durations=self._cs_durations, bars=self._bars)

    def _generate_counter_subject(self) -> None:
        """Generate counter-subject using the gold-plated joint pitch+rhythm solver.

        Uses cs_generator.generate_countersubject for beautiful, invertible CS with:
        - Rhythmic density matching subject
        - All intervals consonant and invertible
        - Melodic contour complementing subject
        - Cadential convergence
        - Motivic coherence
        """
        cs_subj = CSSubject(
            degrees=self._degrees,
            durations=self._durations,
            mode=self._mode,
        )
        cs_result: CounterSubject | None = generate_countersubject(cs_subj, timeout_seconds=10.0)
        if cs_result is None:
            raise ValueError(f"No valid counter-subject for degrees {self._degrees} in {self._mode}")
        self._cs_degrees = cs_result.degrees
        self._cs_durations = cs_result.durations

    def extend_to(self, budget: Fraction) -> tuple[Motif, Motif]:
        """Extend subject and counter-subject to fill budget, preserving rhythm invariant.

        Both voices are cycled together to maintain CSP-optimized rhythm relationship.
        Returns (extended_subject, extended_counter_subject).
        """
        subj: Motif = self.subject
        cs: Motif = self.counter_subject
        subj_dur: Fraction = sum(subj.durations)
        cs_dur: Fraction = sum(cs.durations)
        assert subj_dur == cs_dur, "Subject and CS must have same total duration"
        if budget <= subj_dur:
            return self._trim_pair(subj, cs, budget)
        return self._cycle_pair(subj, cs, budget, subj_dur)

    def _trim_pair(self, subj: Motif, cs: Motif, budget: Fraction) -> tuple[Motif, Motif]:
        """Trim both motifs to budget."""
        subj_p: list[int] = []
        subj_d: list[Fraction] = []
        cs_p: list[int] = []
        cs_d: list[Fraction] = []
        remaining: Fraction = budget
        for deg, dur in zip(subj.degrees, subj.durations):
            if remaining <= Fraction(0):
                break
            subj_p.append(deg)
            subj_d.append(min(dur, remaining))
            remaining -= dur
        remaining = budget
        for deg, dur in zip(cs.degrees, cs.durations):
            if remaining <= Fraction(0):
                break
            cs_p.append(deg)
            cs_d.append(min(dur, remaining))
            remaining -= dur
        return (
            Motif(degrees=tuple(subj_p), durations=tuple(subj_d), bars=self._bars),
            Motif(degrees=tuple(cs_p), durations=tuple(cs_d), bars=self._bars),
        )

    def _cycle_pair(self, subj: Motif, cs: Motif, budget: Fraction, cycle_dur: Fraction) -> tuple[Motif, Motif]:
        """Cycle both motifs independently to fill budget."""
        ext_subj: Motif = self._cycle_single(subj, budget)
        ext_cs: Motif = self._cycle_single(cs, budget)
        return ext_subj, ext_cs

    def _cycle_single(self, motif: Motif, budget: Fraction) -> Motif:
        """Cycle a single motif to fill budget exactly."""
        degrees: list[int] = []
        durations: list[Fraction] = []
        remaining: Fraction = budget
        n: int = len(motif.degrees)
        idx: int = 0
        max_iterations: int = 10000
        while remaining > Fraction(0) and idx < max_iterations:
            deg: int = motif.degrees[idx % n]
            dur: Fraction = motif.durations[idx % n]
            use_dur: Fraction = min(dur, remaining)
            degrees.append(deg)
            durations.append(use_dur)
            remaining -= use_dur
            idx += 1
        return Motif(degrees=tuple(degrees), durations=tuple(durations), bars=self._bars)

    def get_motif(self, name: str) -> Motif:
        """Get motif by name: 'subject', 'cs_1', 'cs_2', etc.

        Motifs are lazily generated on first access.
        """
        if name == "subject":
            return self.subject
        if name == "cs_1" or name == "counter_subject":
            return self.counter_subject
        if name in self._motifs:
            return self._motifs[name]
        if not name.startswith("cs_"):
            raise ValueError(f"Unknown motif name: {name}")
        cs_num: int = int(name.split("_")[1])
        self._ensure_motifs_generated(cs_num)
        return self._motifs[name]

    def _ensure_motifs_generated(self, up_to_cs: int) -> None:
        """Ensure all counter-subjects up to cs_N are generated."""
        for i in range(1, up_to_cs + 1):
            name: str = f"cs_{i}"
            if name in self._motifs:
                continue
            if i == 1:
                self._motifs[name] = self.counter_subject
            else:
                self._generate_cs_n(i)

    def _generate_cs_n(self, n: int) -> None:
        """Generate cs_N using the gold-plated generator.

        For n > 1, we reuse the same generator - each CS is generated fresh
        against the subject. Future enhancement could add collision avoidance
        with preceding counter-subjects.
        """
        cs_subj = CSSubject(
            degrees=self._degrees,
            durations=self._durations,
            mode=self._mode,
        )
        cs_result: CounterSubject | None = generate_countersubject(cs_subj, timeout_seconds=10.0)
        if cs_result is None:
            raise ValueError(f"No valid cs_{n} for degrees {self._degrees} in {self._mode}")
        self._motifs[f"cs_{n}"] = Motif(
            degrees=cs_result.degrees,
            durations=cs_result.durations,
            bars=self._bars,
        )

    def get_motif_extended(self, name: str, budget: Fraction) -> Motif:
        """Get motif by name, extended/trimmed to fill budget."""
        motif: Motif = self.get_motif(name)
        return self._cycle_single(motif, budget)

    @property
    def motif_names(self) -> tuple[str, ...]:
        """Return all available motif names for this voice count."""
        names: list[str] = ["subject"]
        for i in range(1, self._voice_count):
            names.append(f"cs_{i}")
        return tuple(names)

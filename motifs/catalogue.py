"""Subject catalogue: extracts and stores fragment library from fugue triple.

Builds the complete fragment library from a LoadedFugue, including:
- Primary material (subject, answer, countersubject)
- Head and tail extractions
- Melodic transforms (inversion, augmentation, diminution)

All fragments stored in relative form (signed diatonic intervals + durations).
"""
from dataclasses import dataclass
from fractions import Fraction

from motifs.fugue_loader import LoadedFugue

@dataclass(frozen=True)
class Fragment:
    """A fragment of thematic material, stored in relative form.

    Intervals are signed diatonic steps between consecutive notes.
    Durations are Fraction objects (whole-note fractions).
    """
    name: str
    intervals: tuple[int, ...]
    durations: tuple[Fraction, ...]
    total_duration: Fraction
    source: str  # "subject", "countersubject", "derived"

@dataclass(frozen=True)
class InvertiblePair:
    """A subject+CS pair that can be inverted (voices swapped)."""
    subject: Fragment
    countersubject: Fragment

def _degrees_to_intervals(degrees: tuple[int, ...]) -> tuple[int, ...]:
    """Convert absolute degrees to signed diatonic intervals.

    Example: [4, 2, 0, 1] → [-2, -2, +1]
    (degree 4 to 2 is -2 steps, 2 to 0 is -2 steps, 0 to 1 is +1 step)
    """
    if len(degrees) < 2:
        return ()
    return tuple(degrees[i + 1] - degrees[i] for i in range(len(degrees) - 1))

def _floats_to_fractions(durations: tuple[float, ...]) -> tuple[Fraction, ...]:
    """Convert float durations to Fraction objects."""
    return tuple(Fraction(d).limit_denominator(128) for d in durations)

def _negate_intervals(intervals: tuple[int, ...]) -> tuple[int, ...]:
    """Negate all intervals (inversion transform)."""
    return tuple(-i for i in intervals)

def _double_durations(durations: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    """Double all durations (augmentation transform)."""
    return tuple(d * 2 for d in durations)

def _halve_durations(durations: tuple[Fraction, ...]) -> tuple[Fraction, ...]:
    """Halve all durations (diminution transform)."""
    return tuple(d / 2 for d in durations)

class SubjectCatalogue:
    """Repository of all fragments derived from a fugue triple.

    Frozen after construction. Provides query methods for fragment lookup.
    """

    def __init__(self, fugue: LoadedFugue):
        """Build catalogue from LoadedFugue."""
        self._fragments: dict[str, Fragment] = {}
        self._invertible_pair: InvertiblePair | None = None
        self._build_catalogue(fugue=fugue)

    def _build_catalogue(self, fugue: LoadedFugue) -> None:
        """Extract all fragments from the fugue triple."""
        # Convert subject
        subj_intervals: tuple[int, ...] = _degrees_to_intervals(degrees=fugue.subject.degrees)
        subj_durations: tuple[Fraction, ...] = _floats_to_fractions(durations=fugue.subject.durations)
        subj_total: Fraction = sum(subj_durations, start=Fraction(0))

        subject_frag: Fragment = Fragment(
            name="subject",
            intervals=subj_intervals,
            durations=subj_durations,
            total_duration=subj_total,
            source="subject",
        )
        self._fragments["subject"] = subject_frag

        # Convert answer
        ans_intervals: tuple[int, ...] = _degrees_to_intervals(degrees=fugue.answer.degrees)
        ans_durations: tuple[Fraction, ...] = _floats_to_fractions(durations=fugue.answer.durations)
        ans_total: Fraction = sum(ans_durations, start=Fraction(0))

        answer_frag: Fragment = Fragment(
            name="answer",
            intervals=ans_intervals,
            durations=ans_durations,
            total_duration=ans_total,
            source="subject",
        )
        self._fragments["answer"] = answer_frag

        # Convert countersubject
        cs_intervals: tuple[int, ...] = _degrees_to_intervals(degrees=fugue.countersubject.degrees)
        cs_durations: tuple[Fraction, ...] = _floats_to_fractions(durations=fugue.countersubject.durations)
        cs_total: Fraction = sum(cs_durations, start=Fraction(0))

        cs_frag: Fragment = Fragment(
            name="countersubject",
            intervals=cs_intervals,
            durations=cs_durations,
            total_duration=cs_total,
            source="countersubject",
        )
        self._fragments["countersubject"] = cs_frag

        # Store invertible pair
        self._invertible_pair = InvertiblePair(subject=subject_frag, countersubject=cs_frag)

        # Generate head fragments for subject
        self._generate_heads(base_name="head", intervals=subj_intervals, durations=subj_durations, source="subject")

        # Generate tail fragments for subject
        self._generate_tails(base_name="tail", intervals=subj_intervals, durations=subj_durations, source="subject")

        # Generate head fragments for countersubject
        self._generate_heads(base_name="cs_head", intervals=cs_intervals, durations=cs_durations, source="countersubject")

        # Generate tail fragments for countersubject
        self._generate_tails(base_name="cs_tail", intervals=cs_intervals, durations=cs_durations, source="countersubject")

        # Generate transforms of subject
        self._generate_inversion(base_frag=subject_frag, name="inversion")
        self._generate_augmentation(base_frag=subject_frag, name="augmentation")
        self._generate_diminution(base_frag=subject_frag, name="diminution")

        # Generate inverted heads
        inv_intervals: tuple[int, ...] = _negate_intervals(intervals=subj_intervals)
        inv_durations: tuple[Fraction, ...] = subj_durations
        self._generate_heads(base_name="head_inv", intervals=inv_intervals, durations=inv_durations, source="derived")

        # Generate augmented heads
        aug_durations: tuple[Fraction, ...] = _double_durations(durations=subj_durations)
        self._generate_heads(base_name="head_aug", intervals=subj_intervals, durations=aug_durations, source="derived")

        # Generate diminished heads
        dim_durations: tuple[Fraction, ...] = _halve_durations(durations=subj_durations)
        self._generate_heads(base_name="head_dim", intervals=subj_intervals, durations=dim_durations, source="derived")

    def _generate_heads(
        self,
        base_name: str,
        intervals: tuple[int, ...],
        durations: tuple[Fraction, ...],
        source: str,
    ) -> None:
        """Generate head(n) fragments for n = 1 beat to len-1 beats."""
        assert len(intervals) + 1 == len(durations), (
            f"Interval count {len(intervals)} must be len(durations) - 1, got {len(durations)} durations"
        )

        # Accumulate durations to find beat boundaries
        cumulative: Fraction = Fraction(0)
        beat_count: int = 0

        for i, dur in enumerate(durations):
            cumulative += dur
            # Each whole beat represents a head fragment opportunity
            while cumulative >= beat_count + 1:
                beat_count += 1
                # Head of beat_count beats: take first i+1 notes
                if i + 1 < len(durations):  # Don't generate full-length head
                    head_intervals: tuple[int, ...] = intervals[:i]
                    head_durations: tuple[Fraction, ...] = durations[:i + 1]
                    head_total: Fraction = sum(head_durations, start=Fraction(0))

                    head_frag: Fragment = Fragment(
                        name=f"{base_name}_{beat_count}",
                        intervals=head_intervals,
                        durations=head_durations,
                        total_duration=head_total,
                        source=source,
                    )
                    self._fragments[head_frag.name] = head_frag

    def _generate_tails(
        self,
        base_name: str,
        intervals: tuple[int, ...],
        durations: tuple[Fraction, ...],
        source: str,
    ) -> None:
        """Generate tail(n) fragments for n = 1 beat to len-1 beats."""
        assert len(intervals) + 1 == len(durations), (
            f"Interval count {len(intervals)} must be len(durations) - 1, got {len(durations)} durations"
        )

        total_duration: Fraction = sum(durations, start=Fraction(0))

        # Accumulate from end backwards
        cumulative: Fraction = Fraction(0)
        beat_count: int = 0

        for i in range(len(durations) - 1, -1, -1):
            cumulative += durations[i]
            # Each whole beat represents a tail fragment opportunity
            while cumulative >= beat_count + 1:
                beat_count += 1
                # Tail of beat_count beats: take last notes from index i onward
                if i > 0:  # Don't generate full-length tail
                    tail_intervals: tuple[int, ...] = intervals[i - 1:]
                    tail_durations: tuple[Fraction, ...] = durations[i:]
                    tail_total: Fraction = sum(tail_durations, start=Fraction(0))

                    tail_frag: Fragment = Fragment(
                        name=f"{base_name}_{beat_count}",
                        intervals=tail_intervals,
                        durations=tail_durations,
                        total_duration=tail_total,
                        source=source,
                    )
                    self._fragments[tail_frag.name] = tail_frag

    def _generate_inversion(self, base_frag: Fragment, name: str) -> None:
        """Generate inverted fragment (intervals negated)."""
        inv_intervals: tuple[int, ...] = _negate_intervals(intervals=base_frag.intervals)
        inv_frag: Fragment = Fragment(
            name=name,
            intervals=inv_intervals,
            durations=base_frag.durations,
            total_duration=base_frag.total_duration,
            source="derived",
        )
        self._fragments[name] = inv_frag

    def _generate_augmentation(self, base_frag: Fragment, name: str) -> None:
        """Generate augmented fragment (durations doubled)."""
        aug_durations: tuple[Fraction, ...] = _double_durations(durations=base_frag.durations)
        aug_total: Fraction = sum(aug_durations, start=Fraction(0))
        aug_frag: Fragment = Fragment(
            name=name,
            intervals=base_frag.intervals,
            durations=aug_durations,
            total_duration=aug_total,
            source="derived",
        )
        self._fragments[name] = aug_frag

    def _generate_diminution(self, base_frag: Fragment, name: str) -> None:
        """Generate diminished fragment (durations halved)."""
        dim_durations: tuple[Fraction, ...] = _halve_durations(durations=base_frag.durations)
        dim_total: Fraction = sum(dim_durations, start=Fraction(0))
        dim_frag: Fragment = Fragment(
            name=name,
            intervals=base_frag.intervals,
            durations=dim_durations,
            total_duration=dim_total,
            source="derived",
        )
        self._fragments[name] = dim_frag

    def get(self, name: str) -> Fragment:
        """Get fragment by name. Raises KeyError if not found."""
        assert name in self._fragments, (
            f"Fragment '{name}' not found in catalogue. "
            f"Available: {sorted(self._fragments.keys())}"
        )
        return self._fragments[name]

    def list_by_duration(self, max_duration: Fraction) -> tuple[Fragment, ...]:
        """Return all fragments with total_duration <= max_duration."""
        return tuple(
            frag for frag in self._fragments.values()
            if frag.total_duration <= max_duration
        )

    def get_invertible_pair(self) -> InvertiblePair:
        """Get the subject+CS invertible pair."""
        assert self._invertible_pair is not None, "Invertible pair not built"
        return self._invertible_pair

    def fragment_names(self) -> tuple[str, ...]:
        """Return all fragment names in the catalogue."""
        return tuple(sorted(self._fragments.keys()))

    def fragment_count(self) -> int:
        """Return total number of fragments in the catalogue."""
        return len(self._fragments)

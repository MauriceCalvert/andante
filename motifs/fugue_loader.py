"""Fugue file loader.

Loads .fugue YAML files containing pre-composed subject, answer, and countersubject.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from motifs.thematic_transform import CellCatalogue, IntervalPattern, VerticalGenome

from motifs.head_generator import degrees_to_midi
from shared.music_math import parse_metre
from shared.pitch import build_pitch_class_set, diatonic_step_count

LIBRARY_DIR = Path(__file__).parent / "library"

@dataclass(frozen=True)
class LoadedSubject:
    """Subject loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    mode: str
    bars: int
    head_name: str
    leap_size: int
    leap_direction: str

@dataclass(frozen=True)
class LoadedAnswer:
    """Answer loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    answer_type: str
    mutation_points: tuple[int, ...]

@dataclass(frozen=True)
class LoadedCountersubject:
    """Countersubject loaded from .fugue file."""
    degrees: tuple[int, ...]
    durations: tuple[float, ...]
    vertical_intervals: tuple[int, ...]

@dataclass(frozen=True)
class LoadedStretto:
    """One viable stretto offset from .fugue file."""
    offset_slots: int
    quality: float


@dataclass(frozen=True)
class ThematicBias:
    """Bundled thematic bias data extracted from a LoadedFugue (M001)."""
    degree_affinity: tuple[float, ...] | None
    subject_interval_affinity: dict[int, float] | None
    cs_interval_affinity: dict[int, float] | None
    subject_pattern: IntervalPattern | None
    cs_pattern: IntervalPattern | None
    cell_catalogue: CellCatalogue | None
    vertical_genome: VerticalGenome | None


@dataclass(frozen=True)
class LoadedFugue:
    """Complete fugue triple loaded from file."""
    subject: LoadedSubject
    answer: LoadedAnswer
    countersubject: LoadedCountersubject
    metre: tuple[int, int]
    tonic: str
    tonic_midi: int
    seed: int
    stretto: tuple[LoadedStretto, ...]

    def subject_midi(self, tonic_midi: int | None = None, mode: str | None = None) -> tuple[int, ...]:
        """Get subject as MIDI pitches.

        Args:
            tonic_midi: MIDI pitch of tonic (default: self.tonic_midi)
            mode: "major" or "minor" (default: self.subject.mode)
        """
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        effective_mode = mode if mode is not None else self.subject.mode
        return degrees_to_midi(
            degrees=self.subject.degrees,
            tonic_midi=midi,
            mode=effective_mode,
        )

    def answer_midi(self, tonic_midi: int | None = None) -> tuple[int, ...]:
        """Get answer as MIDI pitches (in dominant key)."""
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        dominant_midi = midi + 7
        return degrees_to_midi(
            degrees=self.answer.degrees,
            tonic_midi=dominant_midi,
            mode=self.subject.mode,
        )

    def countersubject_midi(self, tonic_midi: int | None = None, mode: str | None = None) -> tuple[int, ...]:
        """Get countersubject as MIDI pitches.

        Args:
            tonic_midi: MIDI pitch of tonic (default: self.tonic_midi)
            mode: "major" or "minor" (default: self.subject.mode)
        """
        midi = tonic_midi if tonic_midi is not None else self.tonic_midi
        effective_mode = mode if mode is not None else self.subject.mode
        return degrees_to_midi(
            degrees=self.countersubject.degrees,
            tonic_midi=midi,
            mode=effective_mode,
        )

    def degree_affinity(self) -> tuple[float, ...]:
        """Compute 7-element degree affinity profile from the subject.

        Returns normalised weights (sum=1.0) for degrees 1-7, indexed 0-6.
        Each degree's weight = sum of (duration * metric_weight) for every
        subject note on that degree.

        Metric weight: 2.0 for notes starting on a strong beat (beat 1 or
        the half-bar), 1.0 otherwise. Strong beats are offsets 0 and
        half the bar length.
        """
        metre_str: str = f"{self.metre[0]}/{self.metre[1]}"
        bar_length: Fraction
        bar_length, _ = parse_metre(metre_str)
        strong_offsets: frozenset[Fraction] = frozenset({Fraction(0), bar_length / 2})
        weights: list[float] = [0.0] * 7
        offset: Fraction = Fraction(0)
        for degree, duration in zip(self.subject.degrees, self.subject.durations):
            degree_index: int = (degree - 1) % 7
            beat_pos: Fraction = offset % bar_length
            metric_weight: float = 2.0 if beat_pos in strong_offsets else 1.0
            frac_dur: Fraction = Fraction(duration).limit_denominator(1024)
            weights[degree_index] += float(frac_dur) * metric_weight
            offset += frac_dur
        total: float = sum(weights)
        if total == 0.0:
            return tuple(1.0 / 7 for _ in range(7))
        return tuple(w / total for w in weights)

    def subject_interval_affinity(self) -> dict[int, float]:
        """Compute subject interval vocabulary as a normalised frequency table.

        Returns dict mapping signed diatonic interval to weight (values sum to 1.0).
        Positive = ascending, negative = descending; distance in diatonic steps.
        Returns empty dict if fewer than 2 notes.
        """
        midi_pitches: tuple[int, ...] = self.subject_midi()
        if len(midi_pitches) < 2:
            return {}
        tonic_pc: int = self.tonic_midi % 12
        pcs: frozenset[int] = build_pitch_class_set(tonic_pc=tonic_pc, mode=self.subject.mode)
        counts: dict[int, int] = {}
        for i in range(len(midi_pitches) - 1):
            a: int = midi_pitches[i]
            b: int = midi_pitches[i + 1]
            direction: int = 1 if b > a else (-1 if b < a else 0)
            step_count: int = diatonic_step_count(pitch_a=a, pitch_b=b, pitch_class_set=pcs)
            signed_interval: int = direction * step_count
            counts[signed_interval] = counts.get(signed_interval, 0) + 1
        total: int = sum(counts.values())
        return {interval: count / total for interval, count in counts.items()}

    def cs_interval_affinity(self) -> dict[int, float]:
        """Compute countersubject interval vocabulary as a normalised frequency table.

        Same algorithm as subject_interval_affinity applied to the countersubject.
        CS uses the same key (tonic and mode) as the subject.
        Returns empty dict if fewer than 2 notes.
        """
        midi_pitches: tuple[int, ...] = self.countersubject_midi()
        if len(midi_pitches) < 2:
            return {}
        tonic_pc: int = self.tonic_midi % 12
        pcs: frozenset[int] = build_pitch_class_set(tonic_pc=tonic_pc, mode=self.subject.mode)
        counts: dict[int, int] = {}
        for i in range(len(midi_pitches) - 1):
            a: int = midi_pitches[i]
            b: int = midi_pitches[i + 1]
            direction: int = 1 if b > a else (-1 if b < a else 0)
            step_count: int = diatonic_step_count(pitch_a=a, pitch_b=b, pitch_class_set=pcs)
            signed_interval: int = direction * step_count
            counts[signed_interval] = counts.get(signed_interval, 0) + 1
        total: int = sum(counts.values())
        return {interval: count / total for interval, count in counts.items()}

    def cs_interval_pattern(self) -> IntervalPattern:
        """Extract ordered interval pattern from the countersubject."""
        from motifs.thematic_transform import extract_interval_pattern
        return extract_interval_pattern(
            degrees=self.countersubject.degrees,
            durations=self.countersubject.durations,
            tonic_midi=self.tonic_midi,
            mode=self.subject.mode,
        )

    def subject_interval_pattern(self) -> IntervalPattern:
        """Extract ordered interval pattern from the subject."""
        from motifs.thematic_transform import extract_interval_pattern
        return extract_interval_pattern(
            degrees=self.subject.degrees,
            durations=self.subject.durations,
            tonic_midi=self.tonic_midi,
            mode=self.subject.mode,
        )

    def vertical_genome(self) -> "VerticalGenome":
        """Extract vertical interval profile from subject+CS overlap (TB-5a).

        Samples diatonic intervals between the two voices at every note onset
        within the overlap of subject and CS durations.  Returns a VerticalGenome
        with entries normalised to [0.0, 1.0].  Returns empty genome when either
        voice has fewer than 2 notes.
        """
        from motifs.thematic_transform import VerticalGenome
        from shared.constants import exact_fraction

        subject_midi: tuple[int, ...] = self.subject_midi()
        cs_midi: tuple[int, ...] = self.countersubject_midi()

        if len(subject_midi) < 2 or len(cs_midi) < 2:
            return VerticalGenome(entries=())

        tonic_pc: int = self.tonic_midi % 12
        pcs: frozenset[int] = build_pitch_class_set(tonic_pc=tonic_pc, mode=self.subject.mode)

        # Convert float durations to exact Fractions
        subj_frac_durs: tuple[Fraction, ...] = tuple(
            exact_fraction(value=d, label=f"subject_duration[{i}]")
            for i, d in enumerate(self.subject.durations)
        )
        cs_frac_durs: tuple[Fraction, ...] = tuple(
            exact_fraction(value=d, label=f"cs_duration[{i}]")
            for i, d in enumerate(self.countersubject.durations)
        )

        # Build (onset, pitch) step functions for each voice
        subj_onsets: list[Fraction] = []
        subj_pitches: list[int] = []
        offset: Fraction = Fraction(0)
        for pitch, dur in zip(subject_midi, subj_frac_durs):
            subj_onsets.append(offset)
            subj_pitches.append(pitch)
            offset += dur
        subj_total: Fraction = offset

        cs_onsets: list[Fraction] = []
        cs_pitches: list[int] = []
        offset = Fraction(0)
        for pitch, dur in zip(cs_midi, cs_frac_durs):
            cs_onsets.append(offset)
            cs_pitches.append(pitch)
            offset += dur
        cs_total: Fraction = offset

        overlap: Fraction = min(subj_total, cs_total)
        if overlap <= Fraction(0):
            return VerticalGenome(entries=())

        # Collect all note onsets from both voices within [0, overlap)
        all_onsets: list[Fraction] = sorted(set(
            o for o in subj_onsets + cs_onsets
            if Fraction(0) <= o < overlap
        ))

        entries: list[tuple[float, int]] = []
        for onset in all_onsets:
            # Most recent subject onset ≤ this offset
            subj_idx: int = 0
            for i, so in enumerate(subj_onsets):
                if so <= onset:
                    subj_idx = i
                else:
                    break
            # Most recent CS onset ≤ this offset
            cs_idx: int = 0
            for i, co in enumerate(cs_onsets):
                if co <= onset:
                    cs_idx = i
                else:
                    break
            pitch_a: int = subj_pitches[subj_idx]
            pitch_b: int = cs_pitches[cs_idx]
            interval: int = diatonic_step_count(
                pitch_a=pitch_a, pitch_b=pitch_b, pitch_class_set=pcs
            )
            norm_pos: float = float(onset / overlap)
            entries.append((norm_pos, interval))

        return VerticalGenome(entries=tuple(entries))

    def thematic_bias(self) -> ThematicBias:
        """Extract all thematic bias data in one call (M005)."""
        from motifs.fragen import build_chains, extract_cells
        from motifs.thematic_transform import build_cell_catalogue
        bar_length: Fraction = parse_metre(metre=f"{self.metre[0]}/{self.metre[1]}")[0]
        cells = extract_cells(fugue=self, bar_length=bar_length)
        chains = build_chains(cells=cells, bar_length=bar_length)
        catalogue = build_cell_catalogue(cells=chains, bar_length=bar_length)
        return ThematicBias(
            degree_affinity=self.degree_affinity(),
            subject_interval_affinity=self.subject_interval_affinity(),
            cs_interval_affinity=self.cs_interval_affinity(),
            subject_pattern=self.subject_interval_pattern(),
            cs_pattern=self.cs_interval_pattern(),
            cell_catalogue=catalogue,
            vertical_genome=self.vertical_genome(),
        )


def _parse_fugue_data(data: dict) -> LoadedFugue:
    """Parse fugue YAML data dict into a LoadedFugue."""
    subj_data: dict = data["subject"]
    ans_data: dict = data["answer"]
    cs_data: dict = data["countersubject"]
    meta: dict = data["metadata"]
    subject: LoadedSubject = LoadedSubject(
        degrees=tuple(subj_data["degrees"]),
        durations=tuple(subj_data["durations"]),
        mode=subj_data["mode"],
        bars=subj_data["bars"],
        head_name=subj_data["head_name"],
        leap_size=subj_data["leap_size"],
        leap_direction=subj_data["leap_direction"],
    )
    answer: LoadedAnswer = LoadedAnswer(
        degrees=tuple(ans_data["degrees"]),
        durations=tuple(ans_data["durations"]),
        answer_type=ans_data["type"],
        mutation_points=tuple(ans_data["mutation_points"]),
    )
    countersubject: LoadedCountersubject = LoadedCountersubject(
        degrees=tuple(cs_data["degrees"]),
        durations=tuple(cs_data["durations"]),
        vertical_intervals=tuple(cs_data["vertical_intervals"]),
    )
    stretto_entries: list[LoadedStretto] = []
    for s in data.get("stretto", []):
        stretto_entries.append(LoadedStretto(
            offset_slots=s["offset_slots"],
            quality=s["quality"],
        ))
    return LoadedFugue(
        subject=subject,
        answer=answer,
        countersubject=countersubject,
        metre=tuple(meta["metre"]),
        tonic=meta["tonic"],
        tonic_midi=meta["tonic_midi"],
        seed=meta["seed"],
        stretto=tuple(stretto_entries),
    )

def load_fugue(name: str) -> LoadedFugue:
    """Load a fugue triple from the library by name."""
    if name.endswith(".fugue"):
        name = name[:-6]
    path: Path = LIBRARY_DIR / f"{name}.fugue"
    assert path.exists(), f"Fugue file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    return _parse_fugue_data(data=data)

def load_fugue_path(path: Path) -> LoadedFugue:
    """Load a fugue triple from an explicit file path."""
    assert path.exists(), f"Fugue file not found: {path}"
    with open(path, encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    return _parse_fugue_data(data=data)

def list_fugues() -> list[str]:
    """List available fugue names in the library."""
    return [p.stem for p in LIBRARY_DIR.glob("*.fugue")]

"""Figured bass realisation for soprano voice generation."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from engine.key import Key
from shared.pitch import FloatingNote, MidiPitch, Pitch
from shared.timed_material import TimedMaterial

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class FigureIntervals:
    """Intervals above bass for a figured bass symbol."""
    symbol: str
    intervals: tuple[int, ...]
    suspension: bool = False
    altered: bool = False


def load_figures() -> dict[str, FigureIntervals]:
    """Load figured bass definitions from YAML."""
    with open(DATA_DIR / "figures.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, FigureIntervals] = {}
    for symbol, defn in data.items():
        intervals: tuple[int, ...] = tuple(defn["intervals"])
        suspension: bool = defn.get("suspension", False)
        altered: bool = defn.get("altered", False)
        fig: FigureIntervals = FigureIntervals(
            symbol=symbol, intervals=intervals,
            suspension=suspension, altered=altered,
        )
        result[symbol] = fig
    return result


FIGURES: dict[str, FigureIntervals] = load_figures()


def realise_figure(
    bass_pitch: int,
    figure: str,
    prev_soprano: int | None,
    soprano_range: tuple[int, int] = (60, 84),
) -> int:
    """Select soprano pitch from figured bass symbol.

    Args:
        bass_pitch: MIDI pitch of bass note
        figure: Figured bass symbol (e.g., "", "6", "6/4")
        prev_soprano: Previous soprano MIDI pitch for voice-leading
        soprano_range: (min, max) MIDI pitch range for soprano

    Returns:
        MIDI pitch for soprano note
    """
    assert figure in FIGURES, f"Unknown figure: {figure}"
    intervals: tuple[int, ...] = FIGURES[figure].intervals
    candidates: list[int] = []
    for interval in intervals:
        base: int = bass_pitch + interval
        while base < soprano_range[0]:
            base += 12
        while base > soprano_range[1]:
            base -= 12
        if soprano_range[0] <= base <= soprano_range[1]:
            candidates.append(base)
    assert candidates, f"No valid candidates for figure {figure} above bass {bass_pitch}"
    if prev_soprano is not None:
        candidates.sort(key=lambda p: abs(p - prev_soprano))
    return candidates[0]


def realise_suspension(
    bass_pitch: int,
    figure: str,
    prev_soprano: int | None,
    duration: Fraction,
    soprano_range: tuple[int, int] = (60, 84),
) -> tuple[tuple[int, ...], tuple[Fraction, ...]]:
    """Realise suspension figure producing two soprano notes.

    Args:
        bass_pitch: MIDI pitch of bass note
        figure: Suspension figure (e.g., "4-3", "7-6")
        prev_soprano: Previous soprano MIDI pitch
        duration: Total duration for suspension and resolution
        soprano_range: (min, max) MIDI pitch range for soprano

    Returns:
        Tuple of (pitches, durations) for suspension and resolution
    """
    assert figure in FIGURES, f"Unknown figure: {figure}"
    assert FIGURES[figure].suspension, f"Figure {figure} is not a suspension"
    intervals: tuple[int, ...] = FIGURES[figure].intervals
    sus_interval: int = intervals[0]
    res_interval: int = intervals[1]
    sus_pitch: int = bass_pitch + sus_interval
    res_pitch: int = bass_pitch + res_interval
    while sus_pitch < soprano_range[0]:
        sus_pitch += 12
        res_pitch += 12
    while sus_pitch > soprano_range[1]:
        sus_pitch -= 12
        res_pitch -= 12
    sus_dur: Fraction = duration * Fraction(2, 3)
    res_dur: Fraction = duration - sus_dur
    return (sus_pitch, res_pitch), (sus_dur, res_dur)


def realise_figured_bass(
    bass_pitches: tuple[Pitch, ...],
    bass_durations: tuple[Fraction, ...],
    figures: tuple[str, ...],
    key: Key,
    budget: Fraction,
    soprano_range: tuple[int, int] = (60, 84),
    bass_octave: int = 3,
) -> TimedMaterial:
    """Realise complete figured bass line to soprano voice.

    Args:
        bass_pitches: Bass line degrees
        bass_durations: Bass note durations
        figures: Figured bass symbols for each bass note
        key: Key for pitch resolution
        budget: Total duration budget
        soprano_range: (min, max) MIDI pitch range for soprano
        bass_octave: Octave for bass pitch resolution

    Returns:
        TimedMaterial with soprano degrees (FloatingNote) and durations
    """
    assert len(bass_pitches) == len(bass_durations) == len(figures)
    soprano_pitches: list[Pitch] = []
    soprano_durations: list[Fraction] = []
    prev_soprano_midi: int | None = None
    bass_target: int = 12 * (bass_octave + 1)
    for i, (bp, dur, fig) in enumerate(zip(bass_pitches, bass_durations, figures)):
        assert isinstance(bp, FloatingNote), f"Expected FloatingNote, got {type(bp)}"
        bass_midi: int = key.floating_to_midi(bp, bass_target, bass_target)
        if FIGURES[fig].suspension:
            midi_pitches, midi_durs = realise_suspension(
                bass_midi, fig, prev_soprano_midi, dur, soprano_range
            )
            for mp, md in zip(midi_pitches, midi_durs):
                # Convert MIDI back to scale degree for diatonic pipeline
                soprano_pitches.append(key.midi_to_floating(mp))
                soprano_durations.append(md)
            prev_soprano_midi = midi_pitches[-1]
        else:
            sop_midi: int = realise_figure(bass_midi, fig, prev_soprano_midi, soprano_range)
            # Convert MIDI back to scale degree for diatonic pipeline
            soprano_pitches.append(key.midi_to_floating(sop_midi))
            soprano_durations.append(dur)
            prev_soprano_midi = sop_midi
    return TimedMaterial(
        pitches=tuple(soprano_pitches),
        durations=tuple(soprano_durations),
        budget=budget,
    )


def generate_figures_for_bass(
    bass_pitches: tuple[Pitch, ...],
    style: str = "varied",
) -> tuple[str, ...]:
    """Generate figured bass symbols based on bass motion and style.

    Creates varied inversions for voice exchange and stepwise soprano motion.
    Root position ("") on strong beats, first inversion ("6") for passing motion.

    Args:
        bass_pitches: Bass line degrees
        style: "varied" for mixed inversions, "simple" for mostly root position

    Returns:
        Tuple of figure symbols for each bass note
    """
    if style == "simple" or len(bass_pitches) < 2:
        return tuple("" for _ in bass_pitches)
    figures: list[str] = []
    for i, bp in enumerate(bass_pitches):
        assert isinstance(bp, FloatingNote)
        deg: int = bp.degree
        is_first: bool = i == 0
        is_last: bool = i == len(bass_pitches) - 1
        prev_deg: int | None = bass_pitches[i - 1].degree if i > 0 and isinstance(bass_pitches[i - 1], FloatingNote) else None
        next_deg: int | None = bass_pitches[i + 1].degree if i < len(bass_pitches) - 1 and isinstance(bass_pitches[i + 1], FloatingNote) else None
        if is_first or is_last:
            figures.append("")
        elif prev_deg is not None and next_deg is not None:
            step_up: bool = (deg - prev_deg) % 7 == 1
            step_down: bool = (prev_deg - deg) % 7 == 1
            if step_up or step_down:
                figures.append("6")
            elif deg in (2, 4, 7):
                figures.append("6")
            elif deg == 5 and i % 2 == 1:
                figures.append("6/4")
            else:
                figures.append("")
        else:
            figures.append("")
    return tuple(figures)

"""Dissonance detection for generated music.

Detects harsh intervals (minor 2nd, major 7th) between simultaneously
sounding notes and reports them with bar/beat location.
"""
from fractions import Fraction
from typing import NamedTuple

from builder.types import CollectedNote
from shared.constants import DISSONANT_INTERVALS


class Dissonance(NamedTuple):
    """A detected dissonance."""

    bar: int
    beat: float
    interval: int
    midi_low: int
    midi_high: int
    voice_low: str
    voice_high: str


def _interval_name(semitones: int) -> str:
    """Return human-readable interval name."""
    names: dict[int, str] = {
        1: "minor 2nd",
        2: "major 2nd",
        6: "tritone",
        11: "major 7th",
    }
    return names.get(semitones, f"{semitones} semitones")


def _midi_to_note_name(midi: int) -> str:
    """Convert MIDI pitch to note name."""
    names: tuple[str, ...] = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    octave: int = (midi // 12) - 1
    note: str = names[midi % 12]
    return f"{note}{octave}"


def _diatonic_to_midi(diatonic: int, key_offset: int = 0) -> int:
    """Convert diatonic pitch to MIDI.

    Diatonic pitch: octave * 7 + scale_degree (0-6)
    Example: diatonic 28 = octave 4, degree 0 = C4 = MIDI 60
    """
    octave: int = diatonic // 7
    degree: int = diatonic % 7
    # Major scale intervals from root
    scale: tuple[int, ...] = (0, 2, 4, 5, 7, 9, 11)
    midi: int = (octave + 1) * 12 + scale[degree] + key_offset
    return midi


def detect_dissonances(
    notes: list[CollectedNote],
    key_offset: int = 0,
    beats_per_bar: int = 4,
) -> list[Dissonance]:
    """Detect dissonances in a list of notes.

    Args:
        notes: List of CollectedNote. Offset and duration are in whole notes.
        key_offset: Semitone offset for key (added to diatonic pitches).
        beats_per_bar: Beats per bar for calculating beat position.

    Returns:
        List of Dissonance objects describing each detected dissonance.
    """
    assert isinstance(notes, list), f"Expected list, got {type(notes)}"

    if len(notes) < 2:
        return []

    # Build list of sounding intervals: (start, end, voice, midi)
    sounding: list[tuple[Fraction, Fraction, str, int]] = []
    for note in notes:
        assert note.duration > 0, f"Invalid duration {note.duration} for note at offset {note.offset}"
        # Convert diatonic to MIDI: diatonic 28 = C4 = MIDI 60
        midi: int = _diatonic_to_midi(note.diatonic, key_offset)
        sounding.append((note.offset, note.offset + note.duration, note.role, midi))

    # Sort by start time
    sounding.sort(key=lambda x: (x[0], x[3]))

    # Collect all unique time points
    time_points: set[Fraction] = set()
    for start, end, _, _ in sounding:
        time_points.add(start)

    dissonances: list[Dissonance] = []
    seen: set[tuple[int, int, int, int]] = set()  # (bar, beat_int, low, high)

    for t in sorted(time_points):
        # Find all notes sounding at time t
        active: list[tuple[str, int]] = []
        for start, end, voice, midi in sounding:
            if start <= t < end:
                active.append((voice, midi))

        if len(active) < 2:
            continue

        # Check all pairs for dissonances
        for i in range(len(active)):
            for j in range(i + 1, len(active)):
                v1, m1 = active[i]
                v2, m2 = active[j]
                low, high = (m1, m2) if m1 <= m2 else (m2, m1)
                v_low, v_high = (v1, v2) if m1 <= m2 else (v2, v1)

                interval: int = (high - low) % 12

                if interval in DISSONANT_INTERVALS:
                    bar: int = int(t) + 1
                    beat: float = float((t - int(t)) * beats_per_bar) + 1

                    # Deduplicate by bar/beat/pitches
                    key: tuple[int, int, int, int] = (bar, int(beat * 100), low, high)
                    if key in seen:
                        continue
                    seen.add(key)

                    dissonances.append(Dissonance(
                        bar=bar,
                        beat=beat,
                        interval=interval,
                        midi_low=low,
                        midi_high=high,
                        voice_low=v_low,
                        voice_high=v_high,
                    ))

    return dissonances


def format_dissonance(d: Dissonance) -> str:
    """Format a dissonance as a human-readable string."""
    low_name: str = _midi_to_note_name(d.midi_low)
    high_name: str = _midi_to_note_name(d.midi_high)
    interval_name: str = _interval_name(d.interval)
    return f"Bar {d.bar} beat {d.beat:.1f}: {interval_name} ({low_name}-{high_name}) between {d.voice_low}/{d.voice_high}"


def warn_dissonances(
    notes: list[CollectedNote],
    key_offset: int = 0,
    beats_per_bar: int = 4,
) -> int:
    """Detect and print warnings for dissonances.

    Args:
        notes: List of CollectedNote.
        key_offset: Semitone offset for key.
        beats_per_bar: Beats per bar for calculating beat position.

    Returns:
        Number of dissonances found.
    """
    dissonances: list[Dissonance] = detect_dissonances(
        notes, key_offset=key_offset, beats_per_bar=beats_per_bar
    )

    if dissonances:
        print(f"  WARNING: {len(dissonances)} dissonance(s) detected:")
        for d in dissonances:
            print(f"    {format_dissonance(d)}")

    return len(dissonances)

"""Key representation and scale degree operations.

Single source of truth for Key class across all andante packages.
"""
from dataclasses import dataclass
from typing import Tuple

from shared.constants import (
    FLAT_KEYS_MAJOR,
    FLAT_KEYS_MINOR,
    MAJOR_SCALE,
    MODULATION_TARGETS,
    NATURAL_MINOR_SCALE,
    NOTE_NAME_MAP,
    NOTE_NAMES_FLAT,
    NOTE_NAMES_SHARP,
)
from shared.diatonic_pitch import DiatonicPitch
from shared.pitch import FloatingNote


@dataclass(frozen=True)
class Key:
    """Immutable key representation with MIDI conversion."""
    tonic: str
    mode: str

    def __post_init__(self) -> None:
        assert self.tonic in NOTE_NAME_MAP, f"Invalid tonic: {self.tonic}"
        assert self.mode in ("major", "minor"), f"Invalid mode: {self.mode}"

    @property
    def tonic_pc(self) -> int:
        """Return pitch class of tonic (0-11)."""
        return NOTE_NAME_MAP[self.tonic]

    @property
    def scale(self) -> Tuple[int, ...]:
        """Return scale intervals from tonic (natural minor for minor mode)."""
        return MAJOR_SCALE if self.mode == "major" else NATURAL_MINOR_SCALE

    @property
    def pitch_class_set(self) -> frozenset[int]:
        """Return pitch classes of the diatonic scale."""
        return frozenset((self.tonic_pc + interval) % 12 for interval in self.scale)

    @property
    def bridge_pitch_set(self) -> frozenset[int]:
        """Return pentatonic subset for bridges (omits 4th and 7th degrees)."""
        pentatonic_intervals: Tuple[int, ...] = (0, 2, 4, 7, 9) if self.mode == "major" else (0, 3, 5, 7, 10)
        return frozenset((self.tonic_pc + interval) % 12 for interval in pentatonic_intervals)

    def get_scale_for_context(self, tonal_target: str | None) -> Tuple[int, ...]:
        """Return scale appropriate for harmonic context."""
        if self.mode == "major":
            return MAJOR_SCALE
        return NATURAL_MINOR_SCALE

    def uses_flats(self) -> bool:
        """Determine if this key uses flat spelling."""
        if self.mode == "minor":
            return self.tonic in FLAT_KEYS_MINOR
        return self.tonic in FLAT_KEYS_MAJOR

    def modulate_to(self, target: str) -> "Key":
        """Return new Key for modulation target (Roman numeral)."""
        targets: dict[str, tuple[int, str]] = MODULATION_TARGETS.get(self.mode, {})
        if target not in targets:
            raise ValueError(f"Unknown modulation target '{target}' for {self.mode}")
        semitones, new_mode = targets[target]
        new_pc: int = (self.tonic_pc + semitones) % 12
        names: Tuple[str, ...] = NOTE_NAMES_FLAT if self.uses_flats() else NOTE_NAMES_SHARP
        new_tonic: str = names[new_pc]
        return Key(tonic=new_tonic, mode=new_mode)

    def degree_to_midi(self, degree: int, octave: int = 4) -> int:
        """Convert scale degree to MIDI pitch."""
        semitones: int = self.scale[degree - 1]
        return self.tonic_pc + (octave + 1) * 12 + semitones

    def floating_to_midi(
        self,
        note: FloatingNote,
        prev_midi: int,
        median: int,
        voice_range: tuple[int, int] | None = None,
    ) -> int:
        """Convert FloatingNote to MIDI using voice-leading heuristics.

        Chooses octave by minimizing distance to prev_midi with bias toward median.
        If voice_range is provided, strongly penalizes pitches outside the range.

        Args:
            note: FloatingNote to convert
            prev_midi: Previous MIDI pitch (for voice leading)
            median: Voice tessitura median (gravity center)
            voice_range: Optional (min, max) MIDI range for voice
        """
        semitones: int = self.scale[note.degree - 1]
        pc: int = (self.tonic_pc + semitones) % 12
        candidates: list[int] = [pc + (oct * 12) for oct in range(0, 10)]

        def score(m: int) -> float:
            base_score = abs(m - prev_midi) + abs(m - median) * 0.5
            # Strongly penalize out-of-range pitches
            if voice_range is not None:
                if m < voice_range[0]:
                    base_score += (voice_range[0] - m) * 10  # Heavy penalty per semitone below
                elif m > voice_range[1]:
                    base_score += (m - voice_range[1]) * 10  # Heavy penalty per semitone above
            return base_score

        return min(candidates, key=score)

    def diatonic_step(self, midi: int, steps: int) -> int:
        """Move MIDI pitch by diatonic steps within scale."""
        pc: int = (midi - self.tonic_pc) % 12
        octave: int = (midi - self.tonic_pc) // 12
        try:
            scale_idx: int = list(self.scale).index(pc)
        except ValueError:
            scale_idx = min(range(7), key=lambda i: abs(self.scale[i] - pc))
        new_idx: int = scale_idx + steps
        new_octave: int = octave + (new_idx // 7)
        new_idx = new_idx % 7
        return self.tonic_pc + new_octave * 12 + self.scale[new_idx]

    def diatonic_to_midi(self, dp: DiatonicPitch) -> int:
        """Convert DiatonicPitch to MIDI pitch number."""
        degree_idx: int = dp.step % 7
        diatonic_octave: int = dp.step // 7
        return self.tonic_pc + diatonic_octave * 12 + self.scale[degree_idx]

    def midi_to_diatonic(self, midi: int) -> DiatonicPitch:
        """Find nearest DiatonicPitch for a MIDI pitch."""
        adjusted: int = midi - self.tonic_pc
        diatonic_octave: int = adjusted // 12
        remainder: int = adjusted % 12
        best_idx: int = 0
        best_dist: int = 12
        for i, semitones in enumerate(self.scale):
            dist: int = abs(remainder - semitones)
            if dist < best_dist:
                best_dist = dist
                best_idx = i
        return DiatonicPitch(step=diatonic_octave * 7 + best_idx)

    def midi_to_degree(self, midi: int) -> int:
        """Convert MIDI pitch to scale degree (1-7).

        FOR EXTERNAL MIDI INPUT ONLY (e.g., figured bass, MIDI file import).
        Internal solvers should work in degree space directly.

        Finds the closest diatonic scale degree for the given MIDI pitch.
        Chromatic pitches are mapped to the nearest diatonic degree.
        """
        pc: int = (midi - self.tonic_pc) % 12

        # Exact match in scale
        for i, semitones in enumerate(self.scale):
            if pc == semitones:
                return i + 1  # 1-indexed

        # Chromatic note - find nearest diatonic
        best_degree: int = 1
        best_dist: int = 12
        for i, semitones in enumerate(self.scale):
            dist: int = min(abs(pc - semitones), 12 - abs(pc - semitones))
            if dist < best_dist:
                best_dist = dist
                best_degree = i + 1
        return best_degree

    def midi_to_floating(self, midi: int) -> FloatingNote:
        """Convert MIDI pitch to FloatingNote.

        FOR EXTERNAL MIDI INPUT ONLY (e.g., figured bass, MIDI file import).
        Internal solvers should work in degree space directly.
        """
        return FloatingNote(self.midi_to_degree(midi))

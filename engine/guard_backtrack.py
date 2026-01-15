"""Guard-based backtracking: realise candidates and check guards during expansion.

Single source of truth: guards define correctness in MIDI space.
No degree-level variety tracking - everything delegated to guards.

v6: Uses immutable AccumulatedMidi for N-voice support.
Handles all pitch types (MidiPitch, Note, FloatingNote).
"""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

from engine.key import Key
from shared.pitch import FloatingNote, Pitch, is_rest
from engine.engine_types import RealisedNote
from engine.voice_checks import check_sequence_duplication, Violation
from engine.voice_realiser import realise_voice

_DATA_DIR = Path(__file__).parent.parent / "data"
with open(_DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _PREDICATES: dict = yaml.safe_load(_f)
_REGISTERS: dict = _PREDICATES["registers"]


@dataclass(frozen=True)
class AccumulatedMidi:
    """MIDI history for all voices, used in guard checking. Immutable."""
    voices: list[list[tuple[Fraction, int]]]

    @staticmethod
    def empty(voice_count: int) -> "AccumulatedMidi":
        return AccumulatedMidi(voices=[[] for _ in range(voice_count)])

    def add_voice_notes(
        self,
        voice_index: int,
        notes: list[tuple[Fraction, int]],
    ) -> "AccumulatedMidi":
        """Return new AccumulatedMidi with notes added to voice."""
        new_voices: list[list[tuple[Fraction, int]]] = [list(v) for v in self.voices]
        new_voices[voice_index].extend(notes)
        return AccumulatedMidi(voices=new_voices)

    def get_voice(self, index: int) -> list[tuple[Fraction, int]]:
        return self.voices[index]

    @property
    def voice_count(self) -> int:
        return len(self.voices)


# Module-level accumulated state (for backward compatibility)
_accumulated: AccumulatedMidi = AccumulatedMidi.empty(2)


def reset_accumulated_midi(voice_count: int = 2) -> None:
    """Clear accumulated MIDI. Call at start of piece expansion."""
    global _accumulated
    _accumulated = AccumulatedMidi.empty(voice_count)


def _realise_for_guards(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    key: Key,
    start_offset: Fraction,
    median: int,
    voice_name: str,
    skip_exempt: bool = False,
) -> list[tuple[Fraction, int]]:
    """Realise pitches to MIDI for guard checking using the actual realiser.

    Uses realise_voice to ensure guards check the same MIDI values that
    will be rendered in the final output.

    When skip_exempt=True, filters out notes from exempt pitches after realisation.
    """
    # Track which indices are exempt (before realisation)
    exempt_offsets: set[Fraction] = set()
    if skip_exempt:
        offset: Fraction = start_offset
        for pitch, dur in zip(pitches, durations):
            if isinstance(pitch, FloatingNote) and pitch.exempt:
                exempt_offsets.add(offset)
            offset += dur
    # Use actual realiser
    realised: tuple[RealisedNote, ...] = realise_voice(
        pitches, durations, key, median, voice_name, start_offset
    )
    # Convert to guard format, filtering exempt if requested
    notes: list[tuple[Fraction, int]] = []
    for note in realised:
        if skip_exempt and note.offset in exempt_offsets:
            continue
        notes.append((note.offset, note.pitch))
    return notes


def _count_new_violations(
    accumulated: list[tuple[Fraction, int]],
    candidate: list[tuple[Fraction, int]],
) -> int:
    """Count only NEW violations introduced by candidate, not pre-existing ones."""
    existing_violations: int = len(check_sequence_duplication(accumulated))
    combined: list[tuple[Fraction, int]] = accumulated + candidate
    total_violations: int = len(check_sequence_duplication(combined))
    return max(0, total_violations - existing_violations)


def check_candidate_guards(
    soprano_pitches: tuple[Pitch, ...],
    soprano_durations: tuple[Fraction, ...],
    bass_pitches: tuple[Pitch, ...],
    bass_durations: tuple[Fraction, ...],
    key: Key,
    phrase_offset: Fraction,
) -> list[Violation]:
    """Check candidate against guards using accumulated MIDI context.

    Realises candidate to MIDI, combines with accumulated MIDI, runs var_002 guard.
    Returns only NEW violations introduced by candidate (not pre-existing ones).

    Notes marked with exempt=True are skipped in duplication checks
    (subject material is expected to repeat in inventions).
    """
    sop_notes: list[tuple[Fraction, int]] = _realise_for_guards(
        soprano_pitches, soprano_durations, key, phrase_offset, _REGISTERS["soprano"],
        "soprano", skip_exempt=True,
    )
    bass_notes: list[tuple[Fraction, int]] = _realise_for_guards(
        bass_pitches, bass_durations, key, phrase_offset, _REGISTERS["bass"],
        "bass", skip_exempt=True,
    )
    new_sop_violations: int = _count_new_violations(_accumulated.get_voice(0), sop_notes)
    new_bass_violations: int = _count_new_violations(_accumulated.get_voice(1), bass_notes)
    violations: list[Violation] = []
    for _ in range(new_sop_violations + new_bass_violations):
        violations.append(Violation(
            type="sequence_duplication",
            offset=phrase_offset,
            soprano_pitch=0,
            bass_pitch=0,
        ))
    return violations


def accept_candidate(
    soprano_pitches: tuple[Pitch, ...],
    soprano_durations: tuple[Fraction, ...],
    bass_pitches: tuple[Pitch, ...],
    bass_durations: tuple[Fraction, ...],
    key: Key,
    phrase_offset: Fraction,
) -> None:
    """Accept candidate: add its MIDI to accumulated context."""
    global _accumulated
    sop_notes: list[tuple[Fraction, int]] = _realise_for_guards(
        soprano_pitches, soprano_durations, key, phrase_offset, _REGISTERS["soprano"],
        "soprano", skip_exempt=False,
    )
    bass_notes: list[tuple[Fraction, int]] = _realise_for_guards(
        bass_pitches, bass_durations, key, phrase_offset, _REGISTERS["bass"],
        "bass", skip_exempt=False,
    )
    _accumulated = _accumulated.add_voice_notes(0, sop_notes)
    _accumulated = _accumulated.add_voice_notes(1, bass_notes)

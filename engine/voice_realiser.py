"""Voice realisation: convert pitches to MIDI."""
from fractions import Fraction

from shared.pitch import FloatingNote, MidiPitch, Pitch, is_rest
from engine.key import Key
from engine.octave import best_octave, best_octave_against, best_octave_contrapuntal, best_octave_interleaved, CONSONANCES, OCTAVE
from shared.tracer import get_tracer
from engine.engine_types import RealisedNote


def realise_voice(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    key: Key,
    median: int,
    voice_name: str,
    start_offset: Fraction,
    tonal_target: str | None = None,
    voice_range: tuple[int, int] | None = None,
) -> tuple[RealisedNote, ...]:
    """Realise a voice to concrete notes.

    Handles two pitch types:
    - MidiPitch: pass through directly (already resolved)
    - FloatingNote: heuristic (degree -> MIDI via best_octave)

    Args:
        voice_range: Optional (min, max) MIDI range for voice. If provided,
            strongly penalizes out-of-range pitches during octave selection.
    """
    tracer = get_tracer()
    notes: list[RealisedNote] = []
    offset: Fraction = start_offset
    prev_midi: int = median
    for pitch, duration in zip(pitches, durations, strict=True):
        if is_rest(pitch):
            offset += duration
            continue
        if isinstance(pitch, MidiPitch):
            midi = pitch.midi
        elif isinstance(pitch, FloatingNote):
            midi = key.floating_to_midi(pitch, prev_midi, median, voice_range)
            midi = best_octave(midi, prev_midi, median, OCTAVE, voice_range)
        else:
            raise TypeError(f"Unknown pitch type: {type(pitch)}")
        interval: int = midi - prev_midi
        tracer.trace("REALISE", f"{voice_name}/note", f"pitch={pitch}",
                     offset=offset, prev=prev_midi, midi=midi, interval=interval)
        notes.append(RealisedNote(offset=offset, pitch=midi, duration=duration, voice=voice_name))
        offset += duration
        prev_midi = midi
    return tuple(notes)


def realise_bass_contrapuntal(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    key: Key,
    median: int,
    start_offset: Fraction,
    soprano_notes: tuple[RealisedNote, ...],
    tonal_target: str | None = None,
) -> tuple[RealisedNote, ...]:
    """Realise bass voice ensuring consonance with soprano.

    For two-voice counterpoint, bass octave selection considers soprano pitch
    at each onset to ensure consonant intervals.
    """
    tracer = get_tracer()
    sop_by_offset: dict[Fraction, int] = {}
    for sn in soprano_notes:
        end: Fraction = sn.offset + sn.duration
        pos: Fraction = sn.offset
        step: Fraction = Fraction(1, 16)
        while pos < end:
            sop_by_offset[pos] = sn.pitch
            pos += step
    notes: list[RealisedNote] = []
    offset: Fraction = start_offset
    prev_midi: int = median
    voice_name: str = "bass"
    for pitch, duration in zip(pitches, durations, strict=True):
        if is_rest(pitch):
            offset += duration
            continue
        soprano_midi: int | None = sop_by_offset.get(offset)
        if isinstance(pitch, MidiPitch):
            midi = pitch.midi
        elif isinstance(pitch, FloatingNote):
            midi = key.floating_to_midi(pitch, prev_midi, median)
            midi = best_octave_contrapuntal(midi, prev_midi, median, OCTAVE, soprano_midi, CONSONANCES)
        else:
            raise TypeError(f"Unknown pitch type: {type(pitch)}")
        interval: int = midi - prev_midi
        tracer.trace("REALISE", f"{voice_name}/note", f"pitch={pitch}",
                     offset=offset, prev=prev_midi, midi=midi, interval=interval,
                     soprano=soprano_midi, consonant=soprano_midi is None or (abs(midi - soprano_midi) % 12) in CONSONANCES)
        notes.append(RealisedNote(offset=offset, pitch=midi, duration=duration, voice=voice_name))
        offset += duration
        prev_midi = midi
    return tuple(notes)


def realise_voice_against(
    pitches: tuple[Pitch, ...],
    durations: tuple[Fraction, ...],
    key: Key,
    median: int,
    voice_name: str,
    start_offset: Fraction,
    reference_voices: list[tuple[RealisedNote, ...]],
    tonal_target: str | None = None,
    voice_range: tuple[int, int] | None = None,
    skip_parallels: bool = False,
) -> tuple[RealisedNote, ...]:
    """Realise voice avoiding parallels with all reference voices.

    For N-voice counterpoint, octave selection considers all previously
    realised voices to avoid parallel fifths and octaves.

    Args:
        voice_range: Optional (min, max) MIDI range for voice. If provided,
            strongly penalizes out-of-range pitches during octave selection.
        skip_parallels: If True, don't penalize parallel motion (for imitative textures
            like baroque_invention where parallel motion is expected in stretto).
    """
    tracer = get_tracer()
    step: Fraction = Fraction(1, 16)
    ref_by_offset: list[dict[Fraction, int]] = []
    for ref_notes in reference_voices:
        by_offset: dict[Fraction, int] = {}
        for rn in ref_notes:
            end: Fraction = rn.offset + rn.duration
            pos: Fraction = rn.offset
            while pos < end:
                by_offset[pos] = rn.pitch
                pos += step
        ref_by_offset.append(by_offset)
    prev_ref: list[int | None] = [None] * len(reference_voices)
    notes: list[RealisedNote] = []
    offset: Fraction = start_offset
    prev_midi: int = median
    for pitch, duration in zip(pitches, durations, strict=True):
        if is_rest(pitch):
            offset += duration
            continue
        curr_ref: list[int | None] = [by_off.get(offset) for by_off in ref_by_offset]
        ref_pairs: list[tuple[int | None, int | None]] = list(zip(prev_ref, curr_ref))
        if isinstance(pitch, MidiPitch):
            midi = pitch.midi
        elif isinstance(pitch, FloatingNote):
            midi = key.floating_to_midi(pitch, prev_midi, median, voice_range)
            midi = best_octave_against(midi, prev_midi, median, OCTAVE, ref_pairs, CONSONANCES, voice_range, skip_parallels)
        else:
            raise TypeError(f"Unknown pitch type: {type(pitch)}")
        interval: int = midi - prev_midi
        tracer.trace("REALISE", f"{voice_name}/note", f"pitch={pitch}",
                     offset=offset, prev=prev_midi, midi=midi, interval=interval)
        notes.append(RealisedNote(offset=offset, pitch=midi, duration=duration, voice=voice_name))
        prev_ref = curr_ref
        offset += duration
        prev_midi = midi
    return tuple(notes)


def realise_interleaved_voices(
    voice1_pitches: tuple[Pitch, ...],
    voice1_durations: tuple[Fraction, ...],
    voice2_pitches: tuple[Pitch, ...],
    voice2_durations: tuple[Fraction, ...],
    key: Key,
    voice1_median: int,
    start_offset: Fraction,
    tonal_target: str | None = None,
    voice2_median: int | None = None,
    voice1_range: tuple[int, int] | None = None,
    voice2_range: tuple[int, int] | None = None,
) -> tuple[tuple[RealisedNote, ...], tuple[RealisedNote, ...]]:
    """Realise two interleaved voices with separate home registers.

    Baroque invertible counterpoint with ~octave voice separation:
    - V1 centered around voice1_median (high register, ~C5)
    - V2 centered around voice2_median (low register, ~C4)
    - Voice crossing allowed but voices return to home registers
    - Creates audible separation while permitting Goldberg-style crossings

    Args:
        voice1_median: Home pitch for voice 1 (upper voice)
        voice2_median: Home pitch for voice 2 (lower voice), defaults to voice1_median - 12
        voice1_range: Optional MIDI range (min, max) for voice 1
        voice2_range: Optional MIDI range (min, max) for voice 2
    """
    tracer = get_tracer()
    step: Fraction = Fraction(1, 16)

    # Default voice 2 median to one octave below voice 1 if not specified
    if voice2_median is None:
        voice2_median = voice1_median - 12

    # Build offset maps for both voices
    def build_onset_map(
        pitches: tuple[Pitch, ...], durations: tuple[Fraction, ...]
    ) -> list[tuple[Fraction, Pitch, Fraction]]:
        """Return (offset, pitch, duration) for each non-rest note."""
        result: list[tuple[Fraction, Pitch, Fraction]] = []
        offset: Fraction = start_offset
        for p, d in zip(pitches, durations, strict=True):
            if not is_rest(p):
                result.append((offset, p, d))
            offset += d
        return result

    voice1_onsets = build_onset_map(voice1_pitches, voice1_durations)
    voice2_onsets = build_onset_map(voice2_pitches, voice2_durations)

    # Create lookup tables for what's sounding at each time step
    voice1_by_offset: dict[Fraction, int] = {}
    voice2_by_offset: dict[Fraction, int] = {}

    # Realise voice 1 in upper register
    notes1: list[RealisedNote] = []
    prev_midi1: int = voice1_median

    for offset, pitch, duration in voice1_onsets:
        if isinstance(pitch, MidiPitch):
            midi = pitch.midi
        elif isinstance(pitch, FloatingNote):
            midi = key.floating_to_midi(pitch, prev_midi1, voice1_median, voice1_range)
            midi = best_octave(midi, prev_midi1, voice1_median, OCTAVE, voice1_range)
        else:
            raise TypeError(f"Unknown pitch type: {type(pitch)}")

        tracer.trace("REALISE", "voice_1/note", f"pitch={pitch}",
                     offset=offset, prev=prev_midi1, midi=midi)
        notes1.append(RealisedNote(offset=offset, pitch=midi, duration=duration, voice="voice_1"))

        # Update lookup table for consonance checking
        pos: Fraction = offset
        end: Fraction = offset + duration
        while pos < end:
            voice1_by_offset[pos] = midi
            pos += step

        prev_midi1 = midi

    # Realise voice 2 in lower register
    notes2: list[RealisedNote] = []
    prev_midi2 = voice2_median

    for offset, pitch, duration in voice2_onsets:
        if isinstance(pitch, MidiPitch):
            midi = pitch.midi
        elif isinstance(pitch, FloatingNote):
            midi = key.floating_to_midi(pitch, prev_midi2, voice2_median, voice2_range)
            midi = best_octave(midi, prev_midi2, voice2_median, OCTAVE, voice2_range)
        else:
            raise TypeError(f"Unknown pitch type: {type(pitch)}")

        tracer.trace("REALISE", "voice_2/note", f"pitch={pitch}",
                     offset=offset, prev=prev_midi2, midi=midi)
        notes2.append(RealisedNote(offset=offset, pitch=midi, duration=duration, voice="voice_2"))

        # Update lookup table
        pos = offset
        end = offset + duration
        while pos < end:
            voice2_by_offset[pos] = midi
            pos += step

        prev_midi2 = midi

    return tuple(notes1), tuple(notes2)

"""Realiser passes - modular post-processing for realised phrases.

Each pass is a function that takes realised notes and returns modified notes.
Passes are applied conditionally based on phrase metadata.
"""
from fractions import Fraction
from pathlib import Path
from typing import Callable

import yaml

from engine.key import Key
from shared.tracer import get_tracer
from engine.engine_types import RealisedNote
from engine.voice_checks import check_voice_leading, Violation

DATA_DIR: Path = Path(__file__).parent.parent / "data"
with open(DATA_DIR / "predicates.yaml", encoding="utf-8") as _f:
    _P: dict = yaml.safe_load(_f)
_I: dict = _P["intervals"]
_S: dict = _P["spacing"]
_CONS: dict = _P["consonance"]
CONSONANT: set[int] = set(_CONS["perfect"] + _CONS["imperfect"])


def is_consonant(soprano_midi: int, bass_midi: int) -> bool:
    """Check if interval is consonant."""
    interval: int = abs(soprano_midi - bass_midi) % 12
    return interval in CONSONANT


def _is_leading_tone(midi: int, key: Key) -> bool:
    """Check if pitch is leading tone."""
    pc: int = midi % 12
    leading_tone_pc: int = (key.tonic_pc + 11) % 12
    return pc == leading_tone_pc


def _is_degree_6_minor(midi: int, key: Key) -> bool:
    """Check if pitch is degree 6 in minor key."""
    if key.mode != "minor":
        return False
    pc: int = midi % 12
    degree_6_pc: int = (key.tonic_pc + 8) % 12
    return pc == degree_6_pc


# Pass: Fix downbeat dissonances
def fix_downbeat_dissonance(
    soprano: tuple[RealisedNote, ...],
    bass: tuple[RealisedNote, ...],
    bar_dur: Fraction,
    phrase_idx: int,
    key: Key,
) -> tuple[RealisedNote, ...]:
    """Adjust bass to ensure consonance on beats.

    No range constraints (L003). Candidates filtered by consonance and voice leading only.
    """
    tracer = get_tracer()
    octave: int = _I["octave"]
    max_gap: int = _S["max_gap"]
    bass_notes: list[RealisedNote] = list(bass)
    sop_by_offset: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
    quarter: Fraction = bar_dur / 4
    for i, note in enumerate(bass_notes):
        bar_pos: Fraction = note.offset % bar_dur
        if bar_pos % quarter != 0:
            continue
        sop_pitch: int | None = sop_by_offset.get(note.offset)
        if sop_pitch is None:
            continue
        if is_consonant(sop_pitch, note.pitch) and abs(sop_pitch - note.pitch) <= max_gap:
            continue
        base: int = note.pitch
        candidates: list[int] = [
            base, base + octave, base - octave,
            key.diatonic_step(base, 1), key.diatonic_step(base, -1),
            key.diatonic_step(base, 2), key.diatonic_step(base, -2),
        ]
        valid: list[int] = [
            p for p in candidates
            if not _is_leading_tone(p, key)
            and not _is_degree_6_minor(p, key)
        ]
        best: int | None = None
        best_score: float = float("inf")
        for p in valid:
            if not is_consonant(sop_pitch, p):
                continue
            if abs(sop_pitch - p) > max_gap:
                continue
            score: float = abs(p - note.pitch)
            if score < best_score:
                best, best_score = p, score
        if best is not None and best != note.pitch:
            tracer.fix(f"phrase_{phrase_idx}", "downbeat dissonance",
                       offset=note.offset, old_pitch=note.pitch, new_pitch=best)
            bass_notes[i] = RealisedNote(note.offset, best, note.duration, note.voice)
    return tuple(bass_notes)


# Pass: Fix parallel fifths/octaves
def fix_parallel_violations(
    soprano: tuple[RealisedNote, ...],
    bass: tuple[RealisedNote, ...],
    key: Key,
    phrase_idx: int,
    preserve_final: bool = False,
) -> tuple[RealisedNote, ...]:
    """Fix parallel fifths and octaves by adjusting bass.

    Only accepts adjustments that maintain consonance with soprano.
    """
    tracer = get_tracer()
    sop_by_offset: dict[Fraction, int] = {n.offset: n.pitch for n in soprano}
    sop_list: list[tuple[Fraction, int]] = [(n.offset, n.pitch) for n in soprano]
    bass_list: list[tuple[Fraction, int]] = [(n.offset, n.pitch) for n in bass]
    bass_notes: list[RealisedNote] = list(bass)
    final_offset: Fraction = bass[-1].offset if bass else Fraction(-1)
    max_iterations: int = 50
    iterations: int = 0
    while iterations < max_iterations:
        iterations += 1
        violations: list[Violation] = check_voice_leading(sop_list, bass_list)
        if not violations:
            break
        v: Violation = violations[0]
        if preserve_final and v.offset == final_offset:
            break
        fixed: bool = False
        for i, note in enumerate(bass_notes):
            if note.offset == v.offset and note.pitch == v.bass_pitch:
                sop_pitch: int | None = sop_by_offset.get(note.offset)
                for step in (-1, 1, -2, 2):
                    candidate: int = key.diatonic_step(note.pitch, step)
                    if sop_pitch is not None and not is_consonant(sop_pitch, candidate):
                        continue
                    tracer.fix(f"phrase_{phrase_idx}", f"parallel {v.type}",
                               offset=v.offset, old_pitch=note.pitch, new_pitch=candidate)
                    bass_notes[i] = RealisedNote(note.offset, candidate, note.duration, note.voice)
                    bass_list[i] = (note.offset, candidate)
                    fixed = True
                    break
                break
        if not fixed:
            break
    return tuple(bass_notes)


# Pass configuration
PassConfig = dict[str, bool]


def should_apply_dissonance_fix(
    episode_type: str | None,
    texture: str,
    has_cadence: bool,
    voice_count: int = 2,
) -> bool:
    """Determine if dissonance fix should be applied.

    Two-voice: consonance handled at generation time (realise_bass_contrapuntal).
    Multi-voice: skip for imitative statement episodes.
    """
    if voice_count == 2:
        return False
    is_imitative: bool = episode_type == "statement" and texture == "polyphonic"
    return not is_imitative


def should_apply_parallel_fix(
    has_cadence: bool,
    texture: str = "",
) -> bool:
    """Determine if parallel fix should be applied.

    Skip for baroque_invention texture - parallel motion is expected
    in imitative entries (stretto, canon-like passages).
    """
    if texture == "baroque_invention":
        return False
    return True


def apply_bass_passes(
    soprano: tuple[RealisedNote, ...],
    bass: tuple[RealisedNote, ...],
    bar_dur: Fraction,
    phrase_idx: int,
    key: Key,
    episode_type: str | None,
    texture: str,
    has_cadence: bool,
    voice_count: int = 2,
) -> tuple[RealisedNote, ...]:
    """Apply all applicable passes to bass voice."""
    result: tuple[RealisedNote, ...] = bass
    if should_apply_dissonance_fix(episode_type, texture, has_cadence, voice_count):
        result = fix_downbeat_dissonance(soprano, result, bar_dur, phrase_idx, key)
    if should_apply_parallel_fix(has_cadence, texture):
        result = fix_parallel_violations(soprano, result, key, phrase_idx, has_cadence)
    return result

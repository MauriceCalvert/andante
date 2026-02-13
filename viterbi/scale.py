"""Diatonic scale operations and interval classification."""
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Key representation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeyInfo:
    """Minimal key representation for the viterbi solver."""
    pitch_class_set: frozenset[int]   # e.g. {0,2,4,5,7,9,11} for C major
    tonic_pc: int                      # e.g. 0 for C


# ---------------------------------------------------------------------------
# C major scale — the only scale in this prototype
# ---------------------------------------------------------------------------

# Semitone offsets within one octave for C major (deprecated: use KeyInfo)
CMAJ_OFFSETS = [0, 2, 4, 5, 7, 9, 11]  # C D E F G A B

# Default key for all operations
CMAJ = KeyInfo(pitch_class_set=frozenset({0, 2, 4, 5, 7, 9, 11}), tonic_pc=0)

# Consonant intervals in semitones (absolute, mod 12)
# Unison, minor 3rd, major 3rd, perfect 4th (treated as consonant in
# upper voices), perfect 5th, minor 6th, major 6th, octave
CONSONANT_INTERVALS = {0, 3, 4, 5, 7, 8, 9}

# Perfect consonances (unison, 5th, octave) — for parallel motion checks
PERFECT_CONSONANCES = {0, 7}


def build_pitch_set(
    low_midi: int,
    high_midi: int,
    key: KeyInfo = CMAJ,
) -> list[int]:
    """All diatonic pitches from low_midi to high_midi inclusive."""
    pitches = []
    for midi in range(low_midi, high_midi + 1):
        if (midi % 12) in key.pitch_class_set:
            pitches.append(midi)
    return pitches


def is_consonant(interval_semitones: int) -> bool:
    """True if the interval (in semitones, absolute) is consonant."""
    return (abs(interval_semitones) % 12) in CONSONANT_INTERVALS


def is_perfect(interval_semitones: int) -> bool:
    """True if the interval is a perfect consonance (unison, 5th, octave)."""
    return (abs(interval_semitones) % 12) in PERFECT_CONSONANCES


def interval_name(semitones: int) -> str:
    """Human-readable interval name from semitone count."""
    simple = abs(semitones) % 12
    compound = abs(semitones)
    names = {
        0: "unison", 1: "m2", 2: "M2", 3: "m3", 4: "M3",
        5: "P4", 6: "tritone", 7: "P5", 8: "m6", 9: "M6",
        10: "m7", 11: "M7",
    }
    base = names.get(simple, f"{simple}st")
    if compound >= 12:
        octaves = compound // 12
        if simple == 0:
            return f"{'8ve' if octaves == 1 else f'{octaves} 8ves'}"
        return f"{base}+{octaves}oct"
    return base


def scale_degree_distance(pitch_a: int, pitch_b: int, key: KeyInfo = CMAJ) -> int:
    """Distance in diatonic scale steps (not semitones).

    E.g. C4 to D4 = 1 step, C4 to E4 = 2 steps. Always positive.
    """
    if pitch_a == pitch_b:
        return 0
    low, high = min(pitch_a, pitch_b), max(pitch_a, pitch_b)
    count = 0
    for midi in range(low + 1, high + 1):
        if (midi % 12) in key.pitch_class_set:
            count += 1
    return count


def triad_pcs(
    bass_midi: int,
    key: KeyInfo = CMAJ,
) -> frozenset[int]:
    """Pitch classes of the diatonic triad built above bass_midi.

    Stacks two diatonic thirds above the bass. Root-position assumption.
    """
    pcs = sorted(key.pitch_class_set)
    bass_pc: int = bass_midi % 12
    assert bass_pc in key.pitch_class_set, (
        f"bass pitch class {bass_pc} not in key {key.pitch_class_set}"
    )
    idx: int = pcs.index(bass_pc)
    n: int = len(pcs)
    third_pc: int = pcs[(idx + 2) % n]
    fifth_pc: int = pcs[(idx + 4) % n]
    return frozenset({bass_pc, third_pc, fifth_pc})


def is_diatonic(midi: int, key: KeyInfo = CMAJ) -> bool:
    """True if midi pitch is diatonic in the given key."""
    return (midi % 12) in key.pitch_class_set

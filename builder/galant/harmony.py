"""Harmonic grid infrastructure for schema-annotated chord progressions.

Converts Roman numeral annotations to chord labels and provides block-style
harmonic rhythm lookup for voice generation.
"""
from dataclasses import dataclass
from fractions import Fraction

from builder.phrase_types import PhrasePlan, phrase_degree_offset
from shared.key import Key
from shared.music_math import parse_metre


@dataclass(frozen=True)
class ChordLabel:
    """Parsed Roman numeral chord annotation."""
    root: int                    # scale degree 1-7
    quality: str                 # "major" | "minor" | "diminished" | "augmented"
    members: tuple[int, ...]     # scale degrees in chord (root, third, fifth, [seventh])
    has_seventh: bool            # True for V7, viio7, etc.
    numeral: str                 # original Roman numeral string for display


def parse_roman(numeral: str) -> ChordLabel:
    """Parse Roman numeral string to ChordLabel.

    Vocabulary (curated, not extensible):
    - I, ii, iii, IV, V, V7, vi, viio (major keys)
    - i, III (minor keys)

    Syntax:
    - Case: uppercase = major, lowercase = minor
    - Suffix "7": adds diatonic seventh
    - Suffix "o": diminished quality

    Members are scale-degree positions (1-7), not pitch classes.
    Pitch-class conversion happens at query time via the Key.
    """
    original: str = numeral
    text: str = numeral.strip()

    # Parse has_seventh
    has_seventh: bool = text.endswith("7")
    if has_seventh:
        text = text[:-1]

    # Parse quality from suffix
    quality: str | None = None
    if text.endswith("o"):
        quality = "diminished"
        text = text[:-1]
    elif text.endswith("+"):
        quality = "augmented"
        text = text[:-1]

    # Parse root from Roman numeral base
    roman_map: dict[str, int] = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
        "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
    }
    assert text in roman_map, (
        f"Unknown Roman numeral base: '{text}' (from '{original}'). "
        f"Valid: {sorted(set(roman_map.keys()))}"
    )
    root: int = roman_map[text]

    # Derive quality from case if not already set
    if quality is None:
        quality = "major" if text.isupper() else "minor"

    # Build members by stacking thirds in scale-degree arithmetic
    # Members are always (root, root+2, root+4) wrapping at 7
    # For 7th chords, add root+6
    third: int = ((root - 1) + 2) % 7 + 1
    fifth: int = ((root - 1) + 4) % 7 + 1
    members: tuple[int, ...]
    if has_seventh:
        seventh: int = ((root - 1) + 6) % 7 + 1
        members = (root, third, fifth, seventh)
    else:
        members = (root, third, fifth)

    return ChordLabel(
        root=root,
        quality=quality,
        members=members,
        has_seventh=has_seventh,
        numeral=original,
    )


def chord_pcs(label: ChordLabel, key: Key) -> frozenset[int]:
    """Convert ChordLabel to pitch classes in the given key.

    Uses the key's natural scale, then adjusts intervals to match the
    annotated quality. This ensures V in A minor produces {E, G#, B}
    (major triad), not {E, G, B} (natural minor scale).
    """
    # Get pitch classes from natural scale
    pcs: list[int] = []
    for degree in label.members:
        midi: int = key.degree_to_midi(degree=degree, octave=4)
        pcs.append(midi % 12)

    root_pc: int = pcs[0]
    third_pc: int = pcs[1]
    fifth_pc: int = pcs[2]

    # Adjust third to match quality
    root_to_third: int = (third_pc - root_pc) % 12
    if label.quality == "major" and root_to_third == 3:
        # Minor third from scale, but chord is major → raise third by 1
        third_pc = (third_pc + 1) % 12
    elif label.quality == "minor" and root_to_third == 4:
        # Major third from scale, but chord is minor → lower third by 1
        third_pc = (third_pc - 1) % 12
    elif label.quality == "diminished":
        # Ensure root-to-third is 3 (minor third)
        if root_to_third != 3:
            third_pc = (root_pc + 3) % 12
        # Ensure third-to-fifth is 3 (diminished fifth from root)
        third_to_fifth: int = (fifth_pc - third_pc) % 12
        if third_to_fifth != 3:
            fifth_pc = (root_pc + 6) % 12  # diminished fifth = 6 semitones from root

    # Build result set
    result: set[int] = {root_pc, third_pc, fifth_pc}
    if label.has_seventh:
        seventh_pc: int = pcs[3]
        # V7 gets minor 7th (dominant 7th) — verify and adjust if needed
        # For other 7th chords, use the natural scale degree
        # The task says "For 7th chords: the 7th degree is also taken from the natural scale.
        # V7 gets a minor 7th above root (dominant 7th) — verify and adjust."
        if label.root == 5 and label.quality == "major":
            # Dominant 7th: ensure minor 7th (10 semitones above root)
            expected_seventh: int = (root_pc + 10) % 12
            if seventh_pc != expected_seventh:
                seventh_pc = expected_seventh
        result.add(seventh_pc)

    return frozenset(result)


@dataclass(frozen=True)
class HarmonicGrid:
    """Block-style harmonic rhythm lookup.

    Entries are sorted by offset. Each chord holds from its offset until
    the next entry (or indefinitely if it's the last). Before the first
    entry, the default tonic chord is returned.
    """
    entries: tuple[tuple[Fraction, ChordLabel], ...]
    key: Key

    def chord_at(self, offset: Fraction) -> ChordLabel:
        """Return chord active at the given offset.

        Binary search or linear scan for latest entry <= offset.
        Before first entry, return tonic chord (I or i).
        """
        if len(self.entries) == 0:
            # No entries — return tonic
            return _make_tonic_chord(key=self.key)

        # Find latest entry at or before offset
        latest: ChordLabel | None = None
        for entry_offset, chord in self.entries:
            if entry_offset <= offset:
                latest = chord
            else:
                break

        if latest is None:
            # Before first entry — return tonic
            return _make_tonic_chord(key=self.key)

        return latest

    def chord_pcs_at(self, offset: Fraction) -> frozenset[int]:
        """Return pitch classes of chord tones at the given offset."""
        chord: ChordLabel = self.chord_at(offset=offset)
        return chord_pcs(label=chord, key=self.key)

    def to_beat_list(self, beat_grid: list[float]) -> list[frozenset[int]]:
        """Convert to parallel list of pitch-class sets for Viterbi solver.

        One frozenset per beat position in beat_grid.
        beat_grid values are absolute offsets as floats, not bar.beat notation.
        """
        result: list[frozenset[int]] = []
        for beat_float in beat_grid:
            offset: Fraction = Fraction(beat_float).limit_denominator(64)
            result.append(self.chord_pcs_at(offset=offset))
        return result


def build_harmonic_grid(
    plan: PhrasePlan,
    schema_harmony: tuple[str, ...],
) -> HarmonicGrid:
    """Build harmonic grid from phrase plan and schema harmony annotations.

    For each degree position in the plan:
    1. Compute absolute offset from phrase_degree_offset
    2. Parse Roman numeral at that position
    3. Emit (offset, ChordLabel) entry

    For sequential schemas, the harmony pattern tiles across all segments.
    E.g., fonte with harmony=["V", "i"] and 2 segments → ["V", "i", "V", "i"]

    Returns HarmonicGrid sorted by offset.
    """
    bar_length, beat_unit = parse_metre(metre=plan.metre)
    entries: list[tuple[Fraction, ChordLabel]] = []

    # Tile harmony pattern to match degree_positions count (for sequential schemas)
    num_positions: int = len(plan.degree_positions)
    pattern_len: int = len(schema_harmony)

    for i, pos in enumerate(plan.degree_positions):
        # Tile the harmony pattern by using modulo
        numeral: str = schema_harmony[i % pattern_len]
        offset: Fraction = phrase_degree_offset(
            plan=plan,
            pos=pos,
            bar_length=bar_length,
            beat_unit=beat_unit,
        )
        chord: ChordLabel = parse_roman(numeral=numeral)
        entries.append((offset, chord))

    # Sort by offset (should already be sorted, but ensure)
    entries_sorted: list[tuple[Fraction, ChordLabel]] = sorted(entries, key=lambda e: e[0])

    return HarmonicGrid(
        entries=tuple(entries_sorted),
        key=plan.local_key,
    )


def _make_tonic_chord(key: Key) -> ChordLabel:
    """Create tonic chord (I or i) for the given key."""
    if key.mode == "major":
        return parse_roman(numeral="I")
    return parse_roman(numeral="i")

"""Harmonic grid infrastructure for schema-annotated chord progressions.

Converts Roman numeral annotations to chord labels and provides block-style
harmonic rhythm lookup for voice generation.
"""
import dataclasses
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
    inversion: int = 0           # 0=root position, 1=first inversion (6/3), 2=second (6/4)
    secondary_target: int | None = None  # target degree for V/X (5 for V/V, 6 for V/vi); None for diatonic


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

    # HRL-6: Secondary dominants (V/X) — early return
    if "/" in text:
        parts: list[str] = text.split("/")
        assert len(parts) == 2, (
            f"Multiple slashes in Roman numeral: '{original}'. "
            f"Only V/X notation supported."
        )
        function_str: str = parts[0].strip()
        target_str: str = parts[1].strip()
        assert function_str == "V", (
            f"Only V/X secondary dominants supported, got '{function_str}/...' "
            f"in '{original}'."
        )
        roman_map_sec: dict[str, int] = {
            "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
            "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
        }
        assert target_str in roman_map_sec, (
            f"Unknown target numeral '{target_str}' in '{original}'. "
            f"Valid: {sorted(set(roman_map_sec.keys()))}"
        )
        target_degree: int = roman_map_sec[target_str]
        # Dominant of target: root is a diatonic 5th above the target (4 steps up mod 7)
        sec_root: int = ((target_degree - 1) + 4) % 7 + 1
        sec_third: int = ((sec_root - 1) + 2) % 7 + 1
        sec_fifth: int = ((sec_root - 1) + 4) % 7 + 1
        return ChordLabel(
            root=sec_root,
            quality="major",
            members=(sec_root, sec_third, sec_fifth),
            has_seventh=False,
            numeral=original,
            secondary_target=target_degree,
        )

    # Parse inversion BEFORE quality/seventh (HRL-5)
    # "64" must be checked before "6" to avoid partial match
    inversion: int = 0
    if text.endswith("64"):
        inversion = 2
        text = text[:-2]
    elif text.endswith("6"):
        inversion = 1
        text = text[:-1]

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
        inversion=inversion,
    )


def chord_pcs(label: ChordLabel, key: Key) -> frozenset[int]:
    """Convert ChordLabel to pitch classes in the given key.

    Uses the key's natural scale, then adjusts intervals to match the
    annotated quality. This ensures V in A minor produces {E, G#, B}
    (major triad), not {E, G, B} (natural minor scale).
    """
    # HRL-6: Secondary dominants — compute chromatically from target
    if label.secondary_target is not None:
        target_pc: int = key.degree_to_pc(degree=label.secondary_target)
        dom_root_pc: int = (target_pc + 7) % 12
        major_third_pc: int = (dom_root_pc + 4) % 12
        perfect_fifth_pc: int = (dom_root_pc + 7) % 12
        return frozenset({dom_root_pc, major_third_pc, perfect_fifth_pc})

    # Get pitch classes from natural scale
    pcs: list[int] = []
    for degree in label.members:
        pcs.append(key.degree_to_pc(degree=degree))

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


def bass_degree(label: ChordLabel) -> int:
    """Return the scale degree that belongs in the bass for the given inversion.

    inversion=0 → root (members[0])
    inversion=1 → third (members[1])
    inversion=2 → fifth (members[2])
    """
    assert 0 <= label.inversion <= 2, (
        f"Inversion must be 0, 1, or 2; got {label.inversion} for '{label.numeral}'"
    )
    return label.members[label.inversion]


_INVERSION_SUFFIX: dict[int, str] = {0: "", 1: "6", 2: "64"}


def chord_display_label(label: ChordLabel) -> str:
    """Figured bass display string: numeral + inversion suffix."""
    suffix: str = _INVERSION_SUFFIX[label.inversion]
    if suffix and not label.numeral.endswith(suffix):
        return label.numeral + suffix
    return label.numeral


def bass_pc(label: ChordLabel, key: Key) -> int:
    """Return the pitch class of the bass note for the given inversion and key.

    Calls chord_pcs to get quality-adjusted pitch classes, then matches the
    natural bass degree PC against that set (handles raised 3rds in V, etc.).
    """
    degree: int = bass_degree(label)
    natural_pc: int = key.degree_to_pc(degree=degree)
    pcs: frozenset[int] = chord_pcs(label=label, key=key)
    if natural_pc in pcs:
        return natural_pc
    # Natural PC was adjusted (e.g. raised leading tone in V) — find nearest
    return min(pcs, key=lambda pc: min(abs(pc - natural_pc), 12 - abs(pc - natural_pc)))


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

    def to_bass_beat_list(self, beat_grid: list[float]) -> list[frozenset[int]]:
        """Like to_beat_list, but returns singleton frozensets for inverted chords.

        At inverted chord positions, the bass Viterbi sees only the inversion
        bass note as a chord tone — exploiting chord_tone_cost to steer the
        bass to the passing note and produce stepwise motion.

        inversion != 0 → singleton {bass_pc}
        inversion == 0 → full triad/seventh chord PCs
        """
        result: list[frozenset[int]] = []
        for beat_float in beat_grid:
            offset: Fraction = Fraction(beat_float).limit_denominator(64)
            chord: ChordLabel = self.chord_at(offset=offset)
            if chord.inversion != 0:
                result.append(frozenset({bass_pc(label=chord, key=self.key)}))
            else:
                result.append(chord_pcs(label=chord, key=self.key))
        return result


# Diatonic triad numerals by root degree for each mode (HRL-5 passing chords)
_DIATONIC_NUMERALS_MAJOR: dict[int, str] = {
    1: "I", 2: "ii", 3: "iii", 4: "IV", 5: "V", 6: "vi", 7: "viio",
}
_DIATONIC_NUMERALS_MINOR: dict[int, str] = {
    1: "i", 2: "iio", 3: "III", 4: "iv", 5: "v", 6: "VI", 7: "VII",
}


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


def build_stock_harmonic_grid(
    key: Key,
    bar_count: int,
    bar_length: Fraction,
    start_offset: Fraction,
) -> HarmonicGrid:
    """Build a stock I→(IV/iv)→V harmonic grid for FREE Viterbi fills.

    Assigns one chord per bar. Dominant is always V (major triad even in minor
    — raised leading tone, correct baroque practice). Subdominant uses iv in
    minor to avoid the diminished fifth of iio root position.

    bar_count == 1: [tonic]
    bar_count == 2: [tonic, V]
    bar_count == 3: [tonic, subdominant, V]
    bar_count >= 4: [tonic, alternating subdominant/tonic, subdominant, V]
    """
    assert bar_count >= 1, f"bar_count must be >= 1, got {bar_count}"

    tonic: str = "I" if key.mode == "major" else "i"
    subdominant: str = "IV" if key.mode == "major" else "iv"

    numerals: list[str]
    if bar_count == 1:
        numerals = [tonic]
    elif bar_count == 2:
        numerals = [tonic, "V"]
    elif bar_count == 3:
        numerals = [tonic, subdominant, "V"]
    else:
        # bar 1 = tonic
        # bars 2..bar_count-2: alternating subdominant / tonic (first = subdominant)
        # bar bar_count-1 = subdominant
        # bar bar_count = V
        middle: list[str] = [subdominant if i % 2 == 0 else tonic for i in range(bar_count - 3)]
        numerals = [tonic] + middle + [subdominant, "V"]

    # HRL-6b: V/vi → vi colour in the middle of longer runs
    if bar_count >= 5:
        numerals[1] = "V/vi" if key.mode == "major" else "V/VI"
        numerals[2] = "vi" if key.mode == "major" else "VI"

    entries: list[tuple[Fraction, ChordLabel]] = [
        (start_offset + i * bar_length, parse_roman(numeral=numeral))
        for i, numeral in enumerate(numerals)
    ]
    # HRL-4 + HRL-6c: Cadential acceleration — split the final V bar into
    # V/V (first half) + V (second half) for runs of 3+ bars.
    # V/V replaces the old ii/iv pre-dominant, adding chromatic colour
    # (e.g. F# in C major) that intensifies the cadential drive.
    half_bar: Fraction = bar_length / 2
    if bar_count >= 3:
        last_offset: Fraction = entries[-1][0]
        entries[-1] = (last_offset, parse_roman(numeral="V/V"))
        entries.append((last_offset + half_bar, parse_roman(numeral="V")))

    # HRL-5: Insert passing 6/3 chords between root-position entries.
    # Each consecutive pair separated by >= one bar gets a passing chord
    # at half-bar position, steering the bass toward stepwise motion.
    numerals_map: dict[int, str] = (
        _DIATONIC_NUMERALS_MAJOR if key.mode == "major"
        else _DIATONIC_NUMERALS_MINOR
    )
    insertions: list[tuple[Fraction, ChordLabel]] = []
    for i in range(len(entries) - 1):
        offset_a, entry_a = entries[i]
        offset_b, entry_b = entries[i + 1]
        if offset_b - offset_a < bar_length:
            continue  # cadential half-bar split — already dense, skip
        # Diatonic root distance (shortest circular path, 1–3 steps)
        raw_d: int = (entry_b.root - entry_a.root) % 7
        d: int = raw_d if raw_d <= 3 else 7 - raw_d
        if d <= 1:
            continue  # roots identical or one diatonic step — no passing chord
        # Direction: ascending when shortest path goes up from entry_a to entry_b
        ascending: bool = raw_d <= 3
        # Passing degree P: one step before entry_b root in direction of travel
        if ascending:
            P: int = ((entry_b.root - 2) % 7) + 1   # one step below next root
        else:
            P = (entry_b.root % 7) + 1               # one step above next root
        # Triad whose third = P → its root is two scale degrees below P
        triad_root: int = ((P - 3) % 7) + 1
        assert triad_root in numerals_map, (
            f"Triad root {triad_root} missing from numerals_map for mode '{key.mode}'"
        )
        base_chord: ChordLabel = parse_roman(numeral=numerals_map[triad_root])
        passing_chord: ChordLabel = dataclasses.replace(base_chord, inversion=1)
        insertions.append((offset_a + half_bar, passing_chord))

    entries = sorted(entries + insertions, key=lambda e: e[0])
    return HarmonicGrid(entries=tuple(entries), key=key)


def _make_tonic_chord(key: Key) -> ChordLabel:
    """Create tonic chord (I or i) for the given key."""
    if key.mode == "major":
        return parse_roman(numeral="I")
    return parse_roman(numeral="i")

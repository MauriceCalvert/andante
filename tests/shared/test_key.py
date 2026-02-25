"""Unit tests for shared/key.py — Key class scale degree operations."""
import pytest

from shared.constants import MAJOR_SCALE, NATURAL_MINOR_SCALE
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key


# =========================================================================
# Construction and properties
# =========================================================================


def test_key_construction_major() -> None:
    """C major key has correct tonic and scale."""
    k: Key = Key(tonic="C", mode="major")
    assert k.tonic_pc == 0
    assert k.scale == MAJOR_SCALE


def test_key_construction_minor() -> None:
    """A minor key has correct tonic and scale."""
    k: Key = Key(tonic="A", mode="minor")
    assert k.tonic_pc == 9
    assert k.scale == NATURAL_MINOR_SCALE


def test_key_invalid_tonic() -> None:
    """Invalid tonic raises."""
    with pytest.raises(AssertionError, match="Invalid tonic"):
        Key(tonic="H", mode="major")


def test_key_invalid_mode() -> None:
    """Invalid mode raises."""
    with pytest.raises(AssertionError, match="Invalid mode"):
        Key(tonic="C", mode="dorian")


def test_pitch_class_set_c_major() -> None:
    """C major pitch class set is {0,2,4,5,7,9,11}."""
    k: Key = Key(tonic="C", mode="major")
    assert k.pitch_class_set == frozenset({0, 2, 4, 5, 7, 9, 11})


def test_pitch_class_set_a_minor() -> None:
    """A minor pitch class set is {9,11,0,2,4,5,7}."""
    k: Key = Key(tonic="A", mode="minor")
    assert k.pitch_class_set == frozenset({9, 11, 0, 2, 4, 5, 7})


# =========================================================================
# degree_to_midi
# =========================================================================


@pytest.mark.parametrize("tonic, mode, degree, octave, expected_midi", [
    # C major: degree 1 octave 4 = C5 = 60
    ("C", "major", 1, 4, 60),
    # C major: degree 3 octave 4 = E5 = 64
    ("C", "major", 3, 4, 64),
    # C major: degree 5 octave 4 = G5 = 67
    ("C", "major", 5, 4, 67),
    # C major: degree 1 octave 3 = C4 = 48
    ("C", "major", 1, 3, 48),
    # A minor: degree 1 octave 4 = A5 = 69
    ("A", "minor", 1, 4, 69),
    # D major: degree 1 octave 4 = D5 = 62
    ("D", "major", 1, 4, 62),
    # D major: degree 5 octave 4 = A5 = 69
    ("D", "major", 5, 4, 69),
])
def test_degree_to_midi(
    tonic: str,
    mode: str,
    degree: int,
    octave: int,
    expected_midi: int,
) -> None:
    """Scale degree to MIDI conversion."""
    k: Key = Key(tonic=tonic, mode=mode)
    assert k.degree_to_midi(degree=degree, octave=octave) == expected_midi


# =========================================================================
# midi_to_degree
# =========================================================================


@pytest.mark.parametrize("tonic, mode, midi, expected_degree", [
    # C major: C4=60 → degree 1
    ("C", "major", 60, 1),
    # C major: D4=62 → degree 2
    ("C", "major", 62, 2),
    # C major: E4=64 → degree 3
    ("C", "major", 64, 3),
    # C major: F4=65 → degree 4
    ("C", "major", 65, 4),
    # C major: G4=67 → degree 5
    ("C", "major", 67, 5),
    # C major: A4=69 → degree 6
    ("C", "major", 69, 6),
    # C major: B4=71 → degree 7
    ("C", "major", 71, 7),
    # C major: C5=72 → degree 1 (octave higher)
    ("C", "major", 72, 1),
    # A minor: A4=69 → degree 1
    ("A", "minor", 69, 1),
    # A minor: B4=71 → degree 2
    ("A", "minor", 71, 2),
    # Chromatic: C#=61 in C major → nearest is C(1) or D(2), distance 1 each
    # Implementation picks degree 1 (first found with equal distance)
    ("C", "major", 61, 1),
])
def test_midi_to_degree(
    tonic: str,
    mode: str,
    midi: int,
    expected_degree: int,
) -> None:
    """MIDI to scale degree conversion."""
    k: Key = Key(tonic=tonic, mode=mode)
    assert k.midi_to_degree(midi=midi) == expected_degree


def test_midi_to_degree_roundtrip() -> None:
    """degree_to_midi then midi_to_degree returns original degree."""
    k: Key = Key(tonic="C", mode="major")
    for degree in range(1, 8):
        midi: int = k.degree_to_midi(degree=degree, octave=4)
        assert k.midi_to_degree(midi=midi) == degree


# =========================================================================
# diatonic_step
# =========================================================================


@pytest.mark.parametrize("start_midi, steps, expected_midi", [
    # C4=60, +1 step → D4=62
    (60, 1, 62),
    # C4=60, +2 steps → E4=64
    (60, 2, 64),
    # C4=60, -1 step → B3=59
    (60, -1, 59),
    # C4=60, +7 steps → C5=72
    (60, 7, 72),
    # G4=67, +1 step → A4=69
    (67, 1, 69),
    # E4=64, -2 steps → C4=60
    (64, -2, 60),
    # C4=60, 0 steps → C4=60
    (60, 0, 60),
])
def test_diatonic_step_c_major(
    start_midi: int,
    steps: int,
    expected_midi: int,
) -> None:
    """Diatonic step movement in C major."""
    k: Key = Key(tonic="C", mode="major")
    assert k.diatonic_step(midi=start_midi, steps=steps) == expected_midi


@pytest.mark.parametrize("start_midi, steps, expected_midi", [
    # A4=69, +1 step → B4=71 (natural minor: 0,2,3,5,7,8,10)
    (69, 1, 71),
    # A4=69, +2 steps → C5=72
    (69, 2, 72),
    # A4=69, -1 step → G4=67
    (69, -1, 67),
])
def test_diatonic_step_a_minor(
    start_midi: int,
    steps: int,
    expected_midi: int,
) -> None:
    """Diatonic step movement in A minor."""
    k: Key = Key(tonic="A", mode="minor")
    assert k.diatonic_step(midi=start_midi, steps=steps) == expected_midi


# =========================================================================
# diatonic_to_midi / midi_to_diatonic roundtrip
# =========================================================================


def test_diatonic_roundtrip_c_major() -> None:
    """midi_to_diatonic then diatonic_to_midi returns original for scale tones."""
    k: Key = Key(tonic="C", mode="major")
    for midi in [60, 62, 64, 65, 67, 69, 71, 72]:
        dp: DiatonicPitch = k.midi_to_diatonic(midi=midi)
        assert k.diatonic_to_midi(dp=dp) == midi


def test_diatonic_roundtrip_d_major() -> None:
    """Roundtrip in D major."""
    k: Key = Key(tonic="D", mode="major")
    # D4=62, E4=64, F#4=66, G4=67, A4=69, B4=71, C#5=73, D5=74
    d_major_midi: list[int] = [62, 64, 66, 67, 69, 71, 73, 74]
    for midi in d_major_midi:
        dp: DiatonicPitch = k.midi_to_diatonic(midi=midi)
        assert k.diatonic_to_midi(dp=dp) == midi


# =========================================================================
# modulate_to
# =========================================================================


def test_modulate_to_dominant() -> None:
    """C major → V = G major."""
    k: Key = Key(tonic="C", mode="major")
    v: Key = k.modulate_to(target="V")
    assert v.tonic == "G"
    assert v.mode == "major"


def test_modulate_to_relative_minor() -> None:
    """C major → vi = A minor."""
    k: Key = Key(tonic="C", mode="major")
    vi: Key = k.modulate_to(target="vi")
    assert vi.tonic == "A"
    assert vi.mode == "minor"


def test_modulate_to_invalid_target() -> None:
    """Unknown modulation target raises."""
    k: Key = Key(tonic="C", mode="major")
    with pytest.raises(ValueError, match="Unknown modulation target"):
        k.modulate_to(target="VII")


# =========================================================================
# uses_flats
# =========================================================================


@pytest.mark.parametrize("tonic, mode, expected", [
    ("C", "major", False),
    ("F", "major", True),
    ("Bb", "major", True),
    ("G", "major", False),
    ("D", "minor", True),
    ("A", "minor", False),
])
def test_uses_flats(tonic: str, mode: str, expected: bool) -> None:
    """Flat/sharp spelling heuristic."""
    k: Key = Key(tonic=tonic, mode=mode)
    assert k.uses_flats() is expected


# =========================================================================
# cadential_pitch_class_set
# =========================================================================


def test_cadential_pcs_major_same_as_natural() -> None:
    """Major key cadential set == natural set (no alteration needed)."""
    k: Key = Key(tonic="C", mode="major")
    assert k.cadential_pitch_class_set == k.pitch_class_set


def test_cadential_pcs_minor_has_raised_seventh() -> None:
    """A minor cadential set includes G# (pc 8) instead of G (pc 7)."""
    k: Key = Key(tonic="A", mode="minor")
    natural: frozenset[int] = k.pitch_class_set
    cadential: frozenset[int] = k.cadential_pitch_class_set
    assert 7 in natural       # G natural
    assert 8 not in natural   # No G#
    assert 8 in cadential     # G# in cadential
    assert 7 not in cadential # G natural removed


def test_cadential_pcs_d_minor() -> None:
    """D minor cadential set includes C# (pc 1) instead of C (pc 0)."""
    k: Key = Key(tonic="D", mode="minor")
    cadential: frozenset[int] = k.cadential_pitch_class_set
    assert 1 in cadential  # C#
    assert 0 not in cadential  # C natural removed


# =========================================================================
# bridge_pitch_set
# =========================================================================


def test_bridge_pcs_c_major() -> None:
    """C major pentatonic: C D E G A."""
    k: Key = Key(tonic="C", mode="major")
    assert k.bridge_pitch_set == frozenset({0, 2, 4, 7, 9})


def test_bridge_pcs_a_minor() -> None:
    """A minor pentatonic: A C D E G."""
    k: Key = Key(tonic="A", mode="minor")
    assert k.bridge_pitch_set == frozenset({9, 0, 2, 4, 7})


def test_bridge_pcs_is_subset_of_natural() -> None:
    """Bridge set is always a subset of natural pitch class set."""
    for tonic in ["C", "D", "G", "F"]:
        for mode in ["major", "minor"]:
            k: Key = Key(tonic=tonic, mode=mode)
            assert k.bridge_pitch_set.issubset(k.pitch_class_set)


def test_bridge_pcs_has_five_elements() -> None:
    """Pentatonic always has 5 pitch classes."""
    k: Key = Key(tonic="C", mode="major")
    assert len(k.bridge_pitch_set) == 5


# =========================================================================
# midi_to_diatonic / diatonic_to_midi — chromatic input
# =========================================================================


def test_midi_to_diatonic_chromatic_rounds() -> None:
    """Chromatic pitch maps to nearest diatonic."""
    k: Key = Key(tonic="C", mode="major")
    # C#4 = 61 should map to either C(step=28) or D(step=29)
    dp = k.midi_to_diatonic(midi=61)
    result_midi: int = k.diatonic_to_midi(dp=dp)
    # Result should be either 60 (C) or 62 (D)
    assert result_midi in (60, 62)


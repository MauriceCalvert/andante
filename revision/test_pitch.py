"""Property tests for DiatonicPitch and Key pitch conversion.

Tests the mathematical contract, not individual values:
1. Round-trip: diatonic_to_midi then midi_to_diatonic recovers original step
2. Monotonicity: higher step always produces higher MIDI
3. Octave consistency: step and step+7 differ by exactly 12 semitones
4. Degree cycling: DiatonicPitch.degree cycles through 1-7
5. Interval arithmetic: dp.interval_to(dp.transpose(n)) == n
6. Worked examples from phase5_design.md
"""
import pytest

from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALL_MAJOR_KEYS: list[Key] = [
    Key(tonic=t, mode="major")
    for t in ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
]
ALL_MINOR_KEYS: list[Key] = [
    Key(tonic=t, mode="minor")
    for t in ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
]
ALL_KEYS: list[Key] = ALL_MAJOR_KEYS + ALL_MINOR_KEYS

# Playable range: steps 14 (octave 2) through 56 (octave 8)
# covers MIDI ~24-96, well beyond any voice or instrument
STEP_LOW: int = 14
STEP_HIGH: int = 56


# ---------------------------------------------------------------------------
# 1. Round-trip: diatonic_to_midi → midi_to_diatonic recovers step
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ALL_KEYS, ids=lambda k: f"{k.tonic}_{k.mode}")
def test_round_trip(key: Key) -> None:
    """For every diatonic step, converting to MIDI and back recovers the step."""
    for step in range(STEP_LOW, STEP_HIGH + 1):
        dp: DiatonicPitch = DiatonicPitch(step=step)
        midi: int = key.diatonic_to_midi(dp)
        recovered: DiatonicPitch = key.midi_to_diatonic(midi)
        assert recovered.step == step, (
            f"{key.tonic} {key.mode}: step {step} → MIDI {midi} → step {recovered.step}"
        )


# ---------------------------------------------------------------------------
# 2. Monotonicity: higher step → higher MIDI (strictly)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ALL_KEYS, ids=lambda k: f"{k.tonic}_{k.mode}")
def test_monotonicity(key: Key) -> None:
    """diatonic_to_midi is strictly monotonic: higher step → higher MIDI."""
    prev_midi: int = key.diatonic_to_midi(DiatonicPitch(step=STEP_LOW))
    for step in range(STEP_LOW + 1, STEP_HIGH + 1):
        midi: int = key.diatonic_to_midi(DiatonicPitch(step=step))
        assert midi > prev_midi, (
            f"{key.tonic} {key.mode}: step {step} MIDI {midi} <= step {step - 1} MIDI {prev_midi}"
        )
        prev_midi = midi


# ---------------------------------------------------------------------------
# 3. Octave consistency: step and step+7 differ by exactly 12 semitones
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ALL_KEYS, ids=lambda k: f"{k.tonic}_{k.mode}")
def test_octave_consistency(key: Key) -> None:
    """Moving 7 diatonic steps always equals 12 semitones (one octave)."""
    for step in range(STEP_LOW, STEP_HIGH - 6):
        midi_lo: int = key.diatonic_to_midi(DiatonicPitch(step=step))
        midi_hi: int = key.diatonic_to_midi(DiatonicPitch(step=step + 7))
        assert midi_hi - midi_lo == 12, (
            f"{key.tonic} {key.mode}: step {step} MIDI {midi_lo}, "
            f"step {step + 7} MIDI {midi_hi}, diff {midi_hi - midi_lo}"
        )


# ---------------------------------------------------------------------------
# 4. Degree cycling: DiatonicPitch.degree cycles 1-7
# ---------------------------------------------------------------------------

def test_degree_cycles() -> None:
    """degree property cycles through 1-7 for consecutive steps."""
    for start in range(0, 21):
        for offset in range(7):
            dp: DiatonicPitch = DiatonicPitch(step=start + offset)
            expected: int = (offset % 7) + 1
            # degree depends on absolute step, not offset from start
            assert 1 <= dp.degree <= 7
    # Verify full cycle from step 0
    degrees: list[int] = [DiatonicPitch(step=s).degree for s in range(14)]
    assert degrees == [1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7]


def test_octave_property() -> None:
    """octave property increments every 7 steps."""
    for step in range(0, 49):
        dp: DiatonicPitch = DiatonicPitch(step=step)
        assert dp.octave == step // 7


# ---------------------------------------------------------------------------
# 5. Interval arithmetic
# ---------------------------------------------------------------------------

def test_interval_to_is_signed_difference() -> None:
    """interval_to returns target.step - source.step."""
    a: DiatonicPitch = DiatonicPitch(step=35)
    b: DiatonicPitch = DiatonicPitch(step=40)
    assert a.interval_to(b) == 5
    assert b.interval_to(a) == -5


def test_transpose_round_trip() -> None:
    """Transposing by n then by -n returns to start."""
    for step in range(STEP_LOW, STEP_HIGH + 1):
        dp: DiatonicPitch = DiatonicPitch(step=step)
        for n in range(-14, 15):
            result: DiatonicPitch = dp.transpose(n).transpose(-n)
            assert result.step == step


def test_interval_to_transpose_consistency() -> None:
    """dp.interval_to(dp.transpose(n)) == n for all n."""
    dp: DiatonicPitch = DiatonicPitch(step=35)
    for n in range(-21, 22):
        assert dp.interval_to(dp.transpose(n)) == n


# ---------------------------------------------------------------------------
# 6. Worked examples from phase5_design.md (C major)
# ---------------------------------------------------------------------------

C_MAJOR: Key = Key(tonic="C", mode="major")

DESIGN_DOC_EXAMPLES: list[tuple[int, int, int, str, int]] = [
    # (step, expected_degree, expected_octave, expected_note, expected_midi)
    (28, 1, 4, "C3", 48),
    (29, 2, 4, "D3", 50),
    (35, 1, 5, "C4", 60),
    (36, 2, 5, "D4", 62),
    (37, 3, 5, "E4", 64),
    (40, 6, 5, "A4", 69),
    (41, 7, 5, "B4", 71),
    (42, 1, 6, "C5", 72),
]


@pytest.mark.parametrize(
    "step,degree,octave,note,midi",
    DESIGN_DOC_EXAMPLES,
    ids=[f"step_{s}" for s, _, _, _, _ in DESIGN_DOC_EXAMPLES],
)
def test_design_doc_c_major(
    step: int,
    degree: int,
    octave: int,
    note: str,
    midi: int,
) -> None:
    """Verify worked examples from phase5_design.md."""
    dp: DiatonicPitch = DiatonicPitch(step=step)
    assert dp.degree == degree, f"step {step}: degree {dp.degree} != {degree}"
    assert dp.octave == octave, f"step {step}: octave {dp.octave} != {octave}"
    assert C_MAJOR.diatonic_to_midi(dp) == midi, (
        f"step {step}: MIDI {C_MAJOR.diatonic_to_midi(dp)} != {midi}"
    )


# ---------------------------------------------------------------------------
# 7. Key-relativity: same step, different keys → different MIDI
# ---------------------------------------------------------------------------

def test_key_relativity() -> None:
    """Same step in different keys produces different MIDI (design doc table)."""
    dp: DiatonicPitch = DiatonicPitch(step=35)
    c_maj: Key = Key(tonic="C", mode="major")
    g_maj: Key = Key(tonic="G", mode="major")
    a_maj: Key = Key(tonic="A", mode="major")
    assert c_maj.diatonic_to_midi(dp) == 60  # C4
    assert g_maj.diatonic_to_midi(dp) == 67  # G4
    assert a_maj.diatonic_to_midi(dp) == 69  # A4


# ---------------------------------------------------------------------------
# 8. Cross-check: diatonic_to_midi agrees with degree_to_midi
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ALL_KEYS, ids=lambda k: f"{k.tonic}_{k.mode}")
def test_agrees_with_degree_to_midi(key: Key) -> None:
    """New diatonic_to_midi matches existing degree_to_midi for all degrees."""
    for octave in range(2, 8):
        for degree_1based in range(1, 8):
            step: int = (octave + 1) * 7 + (degree_1based - 1)
            dp: DiatonicPitch = DiatonicPitch(step=step)
            new_midi: int = key.diatonic_to_midi(dp)
            old_midi: int = key.degree_to_midi(degree_1based, octave)
            assert new_midi == old_midi, (
                f"{key.tonic} {key.mode}: degree {degree_1based} octave {octave}: "
                f"new {new_midi} != old {old_midi}"
            )


# ---------------------------------------------------------------------------
# 9. Negative steps (below reference octave)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ALL_MAJOR_KEYS[:4], ids=lambda k: f"{k.tonic}_{k.mode}")
def test_negative_steps(key: Key) -> None:
    """Negative steps produce valid MIDI and maintain monotonicity."""
    prev_midi: int = key.diatonic_to_midi(DiatonicPitch(step=-7))
    for step in range(-6, 1):
        midi: int = key.diatonic_to_midi(DiatonicPitch(step=step))
        assert midi > prev_midi, f"step {step}: MIDI {midi} not > prev {prev_midi}"
        prev_midi = midi


# ---------------------------------------------------------------------------
# 10. Chromatic interval correctness (tritone detection)
# ---------------------------------------------------------------------------

def test_tritone_detection() -> None:
    """B-F in C major is 6 semitones (tritone), not 7 (perfect 5th)."""
    b4: DiatonicPitch = DiatonicPitch(step=41)  # B4, degree 7
    f4: DiatonicPitch = DiatonicPitch(step=38)  # F4, degree 4
    b_midi: int = C_MAJOR.diatonic_to_midi(b4)
    f_midi: int = C_MAJOR.diatonic_to_midi(f4)
    assert b_midi - f_midi == 6, f"B4-F4 = {b_midi - f_midi} semitones, expected 6"
    # Diatonic interval is 3 steps (both are correct)
    assert b4.interval_to(f4) == -3
    assert f4.interval_to(b4) == 3


def test_perfect_fifth_detection() -> None:
    """C-G in C major is 7 semitones (perfect 5th)."""
    c4: DiatonicPitch = DiatonicPitch(step=35)  # C4
    g4: DiatonicPitch = DiatonicPitch(step=39)  # G4
    c_midi: int = C_MAJOR.diatonic_to_midi(c4)
    g_midi: int = C_MAJOR.diatonic_to_midi(g4)
    assert g_midi - c_midi == 7, f"C4-G4 = {g_midi - c_midi} semitones, expected 7"
    # Same diatonic interval (4 steps) as B-F, different chromatic result
    assert c4.interval_to(g4) == 4

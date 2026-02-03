"""Property tests for DiatonicPitch and Key pitch conversion.

Tests the mathematical foundation that all pitch derivation depends on.
See phase5_design.md for specification.
"""
import pytest
from shared.diatonic_pitch import DiatonicPitch
from shared.key import Key


# -----------------------------------------------------------------------------
# DiatonicPitch property tests
# -----------------------------------------------------------------------------

class TestDiatonicPitchProperties:
    """Property-based tests for DiatonicPitch arithmetic."""

    def test_degree_range(self) -> None:
        """Degree is always 1-7 regardless of step."""
        for step in range(-100, 100):
            dp = DiatonicPitch(step=step)
            assert 1 <= dp.degree <= 7, f"step={step} gave degree={dp.degree}"

    def test_octave_monotonic(self) -> None:
        """Octave increases with step (floor division)."""
        for step in range(-50, 50):
            dp = DiatonicPitch(step=step)
            expected_octave: int = step // 7
            assert dp.octave == expected_octave, f"step={step}"

    def test_degree_cycle(self) -> None:
        """Degree cycles 1-7 as step increases."""
        expected_degrees: list[int] = [1, 2, 3, 4, 5, 6, 7]
        for base in [-14, 0, 7, 14]:
            for i in range(7):
                dp = DiatonicPitch(step=base + i)
                assert dp.degree == expected_degrees[i], f"step={base + i}"

    def test_interval_symmetric(self) -> None:
        """interval_to is antisymmetric: a.interval_to(b) == -b.interval_to(a)."""
        for step_a in range(-20, 20):
            for step_b in range(-20, 20):
                a = DiatonicPitch(step=step_a)
                b = DiatonicPitch(step=step_b)
                assert a.interval_to(b) == -b.interval_to(a)

    def test_interval_equals_step_difference(self) -> None:
        """interval_to equals step difference."""
        for step_a in range(-20, 20):
            for step_b in range(-20, 20):
                a = DiatonicPitch(step=step_a)
                b = DiatonicPitch(step=step_b)
                assert a.interval_to(b) == step_b - step_a

    def test_transpose_round_trip(self) -> None:
        """transpose(n).transpose(-n) returns original."""
        for step in range(-50, 50):
            for delta in range(-20, 20):
                dp = DiatonicPitch(step=step)
                result = dp.transpose(delta).transpose(-delta)
                assert result.step == step

    def test_transpose_additive(self) -> None:
        """transpose(a).transpose(b) == transpose(a + b)."""
        for step in range(-20, 20):
            for delta_a in range(-10, 10):
                for delta_b in range(-10, 10):
                    dp = DiatonicPitch(step=step)
                    via_chain = dp.transpose(delta_a).transpose(delta_b)
                    via_sum = dp.transpose(delta_a + delta_b)
                    assert via_chain.step == via_sum.step


# -----------------------------------------------------------------------------
# Key.diatonic_to_midi tests
# -----------------------------------------------------------------------------

class TestDiatonicToMidi:
    """Tests for Key.diatonic_to_midi conversion."""

    def test_monotonic_in_step(self) -> None:
        """MIDI increases monotonically with step."""
        key = Key(tonic="C", mode="major")
        prev_midi: int = key.diatonic_to_midi(DiatonicPitch(step=-50))
        for step in range(-49, 100):
            dp = DiatonicPitch(step=step)
            midi: int = key.diatonic_to_midi(dp)
            assert midi > prev_midi, f"step={step} not > prev"
            prev_midi = midi

    def test_octave_adds_12_semitones(self) -> None:
        """Moving up 7 diatonic steps adds 12 semitones."""
        for tonic in ["C", "G", "D", "F", "Bb"]:
            for mode in ["major", "minor"]:
                key = Key(tonic=tonic, mode=mode)
                for base_step in range(0, 50):
                    low = DiatonicPitch(step=base_step)
                    high = DiatonicPitch(step=base_step + 7)
                    midi_low: int = key.diatonic_to_midi(low)
                    midi_high: int = key.diatonic_to_midi(high)
                    assert midi_high - midi_low == 12, f"{tonic} {mode} step={base_step}"

    def test_c_major_reference_values(self) -> None:
        """Cross-check against known C major MIDI values from design doc."""
        key = Key(tonic="C", mode="major")
        # From phase5_design.md table
        cases: list[tuple[int, int]] = [
            (28, 48),  # C3
            (29, 50),  # D3
            (35, 60),  # C4
            (36, 62),  # D4
            (37, 64),  # E4
            (40, 69),  # A4
            (41, 71),  # B4
            (42, 72),  # C5
        ]
        for step, expected_midi in cases:
            dp = DiatonicPitch(step=step)
            actual: int = key.diatonic_to_midi(dp)
            assert actual == expected_midi, f"step={step}: expected {expected_midi}, got {actual}"

    def test_cross_check_degree_to_midi(self) -> None:
        """diatonic_to_midi agrees with degree_to_midi for same degree+octave."""
        for tonic in ["C", "G", "D", "A", "F", "Bb", "Eb"]:
            for mode in ["major", "minor"]:
                key = Key(tonic=tonic, mode=mode)
                for step in range(0, 70):
                    dp = DiatonicPitch(step=step)
                    via_diatonic: int = key.diatonic_to_midi(dp)
                    # degree_to_midi uses octave differently: octave=4 means C4 region
                    # DiatonicPitch octave is step // 7
                    # degree_to_midi formula: tonic_pc + (octave + 1) * 12 + scale[degree - 1]
                    # diatonic_to_midi formula: tonic_pc + (step // 7) * 12 + scale[step % 7]
                    # To match: degree_to_midi octave = (step // 7) - 1
                    deg: int = dp.degree
                    oct: int = dp.octave - 1
                    via_legacy: int = key.degree_to_midi(deg, oct)
                    assert via_diatonic == via_legacy, (
                        f"{tonic} {mode} step={step}: "
                        f"diatonic_to_midi={via_diatonic}, degree_to_midi({deg}, {oct})={via_legacy}"
                    )

    def test_tonic_pitch_class_correct(self) -> None:
        """Degree 1 at any octave has correct pitch class."""
        cases: list[tuple[str, int]] = [
            ("C", 0), ("D", 2), ("E", 4), ("F", 5),
            ("G", 7), ("A", 9), ("B", 11),
            ("Bb", 10), ("Eb", 3), ("Ab", 8),
        ]
        for tonic, expected_pc in cases:
            key = Key(tonic=tonic, mode="major")
            for oct in range(2, 7):
                step: int = oct * 7  # degree 1 at given diatonic octave
                dp = DiatonicPitch(step=step)
                midi: int = key.diatonic_to_midi(dp)
                actual_pc: int = midi % 12
                assert actual_pc == expected_pc, f"{tonic} oct={oct}: expected pc={expected_pc}, got {actual_pc}"


# -----------------------------------------------------------------------------
# Key.midi_to_diatonic tests
# -----------------------------------------------------------------------------

class TestMidiToDiatonic:
    """Tests for Key.midi_to_diatonic conversion."""

    def test_round_trip_exact(self) -> None:
        """Round-trip diatonic -> MIDI -> diatonic recovers original step."""
        for tonic in ["C", "G", "F", "D", "Bb"]:
            for mode in ["major", "minor"]:
                key = Key(tonic=tonic, mode=mode)
                for step in range(0, 70):
                    dp = DiatonicPitch(step=step)
                    midi: int = key.diatonic_to_midi(dp)
                    recovered: DiatonicPitch = key.midi_to_diatonic(midi)
                    assert recovered.step == step, (
                        f"{tonic} {mode} step={step}: recovered {recovered.step}"
                    )

    def test_chromatic_maps_to_nearest(self) -> None:
        """Chromatic (non-diatonic) MIDI maps to nearest diatonic step."""
        key = Key(tonic="C", mode="major")
        # C major scale: C D E F G A B = 0 2 4 5 7 9 11
        # Chromatic 1 (C#/Db) should map to C or D (distance 1 each, implementation picks lower)
        # Chromatic 6 (F#/Gb) should map to F or G (distance 1 each)
        # Just check it returns a valid DiatonicPitch without error
        for midi in range(24, 84):
            dp: DiatonicPitch = key.midi_to_diatonic(midi)
            assert isinstance(dp, DiatonicPitch)
            # The round-trip of the recovered pitch should give the nearest diatonic MIDI
            recovered_midi: int = key.diatonic_to_midi(dp)
            # The difference should be at most 1 semitone (nearest diatonic)
            diff: int = abs(recovered_midi - midi)
            assert diff <= 1, f"midi={midi}: recovered={recovered_midi}, diff={diff}"


# -----------------------------------------------------------------------------
# Cross-key consistency tests
# -----------------------------------------------------------------------------

class TestCrossKeyConsistency:
    """Same step means same scale position across keys."""

    def test_step_35_across_keys(self) -> None:
        """Step 35 produces different MIDI in different keys (same scale position)."""
        # From phase5_design.md: step 35 = degree 1, octave 5
        dp = DiatonicPitch(step=35)
        results: dict[str, int] = {}
        for tonic in ["C", "G", "A", "D", "F"]:
            key = Key(tonic=tonic, mode="major")
            results[tonic] = key.diatonic_to_midi(dp)
        # All should differ (different tonics)
        midi_values: list[int] = list(results.values())
        assert len(set(midi_values)) == len(midi_values), f"duplicates in {results}"
        # But pitch class should equal tonic pitch class
        for tonic, midi in results.items():
            key = Key(tonic=tonic, mode="major")
            assert midi % 12 == key.tonic_pc, f"{tonic}: midi={midi}, tonic_pc={key.tonic_pc}"


# -----------------------------------------------------------------------------
# Run tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

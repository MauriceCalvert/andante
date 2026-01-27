"""Tests for planner.metric package."""
from planner.metric.distribution import distribute_arrivals
from shared.key import Key
from shared.pitch import select_octave


class TestSelectOctave:
    """Tests for select_octave canonical pitch placement."""

    def test_c_major_degree_1_bass_median_48_initial(self) -> None:
        """C in C major with bass median 48, initial placement -> C3 (48)."""
        key = Key(tonic="C", mode="major")
        result = select_octave(key, 1, median=48)
        assert result == 48  # C3

    def test_c_major_degree_1_soprano_median_70_initial(self) -> None:
        """C in C major with soprano median 70, initial placement -> C5 (72)."""
        key = Key(tonic="C", mode="major")
        result = select_octave(key, 1, median=70)
        assert result == 72  # C5

    def test_d_major_degree_1_bass_median_48_initial(self) -> None:
        """D in D major with bass median 48, initial placement -> D3 (50)."""
        key = Key(tonic="D", mode="major")
        result = select_octave(key, 1, median=48)
        assert result == 50  # D3

    def test_d_major_degree_1_soprano_median_70_initial(self) -> None:
        """D in D major with soprano median 70, initial placement -> D5 (74)."""
        key = Key(tonic="D", mode="major")
        result = select_octave(key, 1, median=70)
        assert result == 74  # D5

    def test_g_major_degree_5_bass_median_48_initial(self) -> None:
        """D (degree 5) in G major with bass median 48, initial -> D3 (50)."""
        key = Key(tonic="G", mode="major")
        result = select_octave(key, 5, median=48)
        assert result == 50  # D3

    def test_a_minor_degree_1_bass_median_48_initial(self) -> None:
        """A in A minor with bass median 48, initial placement -> A2 (45)."""
        key = Key(tonic="A", mode="minor")
        result = select_octave(key, 1, median=48)
        assert result == 45  # A2

    def test_voice_leading_stays_near_prev(self) -> None:
        """With prev_pitch, prefer nearest octave."""
        key = Key(tonic="C", mode="major")
        # prev at C4 (60), target degree 2 (D) -> should pick D4 (62)
        result = select_octave(key, 2, median=70, prev_pitch=60)
        assert result == 62  # D4 (nearest to prev 60)

    def test_voice_leading_snaps_back_when_drifted(self) -> None:
        """When drift exceeds threshold, snap back toward median."""
        key = Key(tonic="C", mode="major")
        # Median 70, prev at 84 (drift = 14). If we go to degree 1 (C),
        # nearest C to 84 is C6 (84), but that's 14 from median.
        # DRIFT_THRESHOLD is 12, so snap back to C5 (72) which is 2 from median.
        result = select_octave(key, 1, median=70, prev_pitch=84)
        assert result == 72  # C5 (snapped back toward median)

    def test_alter_shifts_pitch(self) -> None:
        """Chromatic alteration shifts result by semitones."""
        key = Key(tonic="C", mode="major")
        # Degree 7 in C major = B. With alter=+1, should be B# (= C).
        # Median 70 -> nearest B is B4 (71), +1 = 72
        result = select_octave(key, 7, median=70, alter=1)
        assert result == 72  # B4 + 1 = 72


class TestDistributeArrivals:
    """Tests for distribute_arrivals function."""

    def test_3_stages_in_2_bars_4_4(self) -> None:
        """3 stages in 2 bars of 4/4 should use beats 1.1, 1.3, 2.1."""
        result = distribute_arrivals(3, 1, 2, "4/4")
        assert result == ["1.1", "1.3", "2.1"]

    def test_2_stages_in_1_bar_4_4(self) -> None:
        """2 stages in 1 bar of 4/4 should use beats 1.1, 1.3."""
        result = distribute_arrivals(2, 1, 1, "4/4")
        assert result == ["1.1", "1.3"]

    def test_2_stages_in_2_bars_3_4(self) -> None:
        """2 stages in 2 bars of 3/4 should use beats 1.1, 2.1."""
        result = distribute_arrivals(2, 1, 2, "3/4")
        assert result == ["1.1", "2.1"]

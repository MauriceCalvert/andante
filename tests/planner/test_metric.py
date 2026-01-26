"""Tests for planner.metric package."""
from planner.metric.distribution import distribute_arrivals
from planner.metric.pitch import compute_base_octave, degree_to_midi
from shared.key import Key


class TestDegreeToMidiWithOctave:
    """Tests for degree_to_midi with compute_base_octave."""

    def test_c_major_degree_1_bass_median_48(self) -> None:
        """C in C major with bass median 48 should select C3 (48)."""
        key = Key(tonic="C", mode="major")
        octave = compute_base_octave(key, 1, median=48)
        result = degree_to_midi(key, 1, octave)
        assert result == 48  # C3

    def test_c_major_degree_1_soprano_median_70(self) -> None:
        """C in C major with soprano median 70 should select C5 (72)."""
        key = Key(tonic="C", mode="major")
        octave = compute_base_octave(key, 1, median=70)
        result = degree_to_midi(key, 1, octave)
        assert result == 72  # C5

    def test_d_major_degree_1_bass_median_48(self) -> None:
        """D in D major with bass median 48 should select D3 (50)."""
        key = Key(tonic="D", mode="major")
        octave = compute_base_octave(key, 1, median=48)
        result = degree_to_midi(key, 1, octave)
        assert result == 50  # D3

    def test_d_major_degree_1_soprano_median_70(self) -> None:
        """D in D major with soprano median 70 should select D5 (74)."""
        key = Key(tonic="D", mode="major")
        octave = compute_base_octave(key, 1, median=70)
        result = degree_to_midi(key, 1, octave)
        assert result == 74  # D5

    def test_g_major_degree_5_bass_median_48(self) -> None:
        """D (degree 5) in G major with bass median 48 should select D3 (50)."""
        key = Key(tonic="G", mode="major")
        octave = compute_base_octave(key, 5, median=48)
        result = degree_to_midi(key, 5, octave)
        assert result == 50  # D3

    def test_a_minor_degree_1_bass_median_48(self) -> None:
        """A in A minor with bass median 48 should select A2 (45)."""
        key = Key(tonic="A", mode="minor")
        octave = compute_base_octave(key, 1, median=48)
        result = degree_to_midi(key, 1, octave)
        assert result == 45  # A2


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

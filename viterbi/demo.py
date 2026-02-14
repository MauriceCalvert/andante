"""Worked examples demonstrating corridor-based melodic pathfinding.

Run from the andante directory:
    python -m viterbi.demo

Each example builds a leader voice, places follower knots, and solves
the path. Full diagnostics show corridors, DP candidates, and the
chosen path.
"""
import os
import sys
from viterbi.midi_out import write_midi
from viterbi.pipeline import solve_phrase
from viterbi.mtypes import ExistingVoice, Knot, LeaderNote, pitch_name
from viterbi.scale import CMAJ


def _solve_with_leader(
    leader: list[LeaderNote],
    knots: list[Knot],
    **kwargs,
) -> object:
    """Convenience: convert LeaderNote list to new solve_phrase API."""
    beat_grid = [ln.beat for ln in leader]
    voice = ExistingVoice(
        pitches_at_beat={ln.beat: ln.midi_pitch for ln in leader},
        is_above=False,
    )
    return solve_phrase(beat_grid, [voice], knots, **kwargs)

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def example_1_rising_scale() -> None:
    """Rising C-major bass scale, soprano descends from E5 to C5.

    The simplest possible case. Bass rises stepwise C3 to C4.
    Soprano has 3 knots: E5 at beat 0, C5 at beat 3, C5 at beat 7.

    What to look for:
    - The solver should produce mostly stepwise motion in the soprano.
    - Contrary motion to the bass (soprano descending while bass rises)
      should be preferred.
    - All strong-beat intervals should be consonant.
    - Weak-beat dissonances (if any) should be approached and left by step.
    """
    print("=" * 70)
    print("EXAMPLE 1: Rising bass scale, soprano E5 -> C5 -> C5")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0, midi_pitch=48),   # C3
        LeaderNote(beat=1, midi_pitch=50),   # D3
        LeaderNote(beat=2, midi_pitch=52),   # E3
        LeaderNote(beat=3, midi_pitch=53),   # F3
        LeaderNote(beat=4, midi_pitch=55),   # G3
        LeaderNote(beat=5, midi_pitch=57),   # A3
        LeaderNote(beat=6, midi_pitch=59),   # B3
        LeaderNote(beat=7, midi_pitch=60),   # C4
    ]
    knots = [
        Knot(beat=0, midi_pitch=76),   # E5
        Knot(beat=3, midi_pitch=72),   # C5
        Knot(beat=7, midi_pitch=72),   # C5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=CMAJ)
    _write_output(result, "example_1.mid")


def example_2_descending_bass() -> None:
    """Descending bass from G3, soprano rises from C5 to G5.

    Tests contrary motion when bass descends and soprano ascends.
    Wider knot spacing (5 beats between knots) tests longer fills.

    What to look for:
    - Strong contrary motion preference (bass down, soprano up).
    - The solver should handle the larger gap between knots without
      resorting to leaps or runs.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Descending bass, soprano rises C5 -> G5")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0, midi_pitch=55),   # G3
        LeaderNote(beat=1, midi_pitch=53),   # F3
        LeaderNote(beat=2, midi_pitch=52),   # E3
        LeaderNote(beat=3, midi_pitch=50),   # D3
        LeaderNote(beat=4, midi_pitch=48),   # C3
        LeaderNote(beat=5, midi_pitch=50),   # D3  (turns around)
        LeaderNote(beat=6, midi_pitch=52),   # E3
        LeaderNote(beat=7, midi_pitch=48),   # C3  (cadence)
    ]
    knots = [
        Knot(beat=0, midi_pitch=72),   # C5
        Knot(beat=4, midi_pitch=76),   # E5
        Knot(beat=7, midi_pitch=79),   # G5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True)
    _write_output(result, "example_2.mid")


def example_3_tight_knots() -> None:
    """Close knots with large intervals -- the hard case.

    Knots are only 2 beats apart but a 4th or 5th apart in pitch.
    The solver must find paths that may require a leap, and if so,
    must ensure leap recovery.

    What to look for:
    - When the gap is too short for stepwise filling, the solver
      should produce a single leap and recover.
    - No painting-into-corners: the solver sees the whole segment.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Tight knots with large intervals")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0, midi_pitch=48),   # C3
        LeaderNote(beat=1, midi_pitch=48),   # C3
        LeaderNote(beat=2, midi_pitch=55),   # G3
        LeaderNote(beat=3, midi_pitch=55),   # G3
        LeaderNote(beat=4, midi_pitch=53),   # F3
        LeaderNote(beat=5, midi_pitch=53),   # F3
        LeaderNote(beat=6, midi_pitch=55),   # G3
        LeaderNote(beat=7, midi_pitch=48),   # C3
    ]
    knots = [
        Knot(beat=0, midi_pitch=72),   # C5
        Knot(beat=2, midi_pitch=79),   # G5  (up a 5th in 2 beats)
        Knot(beat=4, midi_pitch=72),   # C5  (down a 5th in 2 beats)
        Knot(beat=7, midi_pitch=76),   # E5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True)
    _write_output(result, "example_3.mid")


def example_4_realistic_bass() -> None:
    """A more realistic bass line with mixed motion.

    Bass outlines I-IV-V-I in C major over 12 beats.
    Soprano has 4 knots outlining a melodic arch.

    What to look for:
    - Natural melodic contour in the soprano.
    - Mixed motion types (contrary, similar, oblique) responding
      to the bass.
    - Phrase position affecting behaviour near the cadence.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Realistic bass (I-IV-V-I), soprano melodic arch")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0, midi_pitch=48),    # C3  (I)
        LeaderNote(beat=1, midi_pitch=48),    # C3
        LeaderNote(beat=2, midi_pitch=48),    # C3
        LeaderNote(beat=3, midi_pitch=53),    # F3  (IV)
        LeaderNote(beat=4, midi_pitch=53),    # F3
        LeaderNote(beat=5, midi_pitch=53),    # F3
        LeaderNote(beat=6, midi_pitch=55),    # G3  (V)
        LeaderNote(beat=7, midi_pitch=55),    # G3
        LeaderNote(beat=8, midi_pitch=55),    # G3
        LeaderNote(beat=9, midi_pitch=48),    # C3  (I)
        LeaderNote(beat=10, midi_pitch=50),   # D3
        LeaderNote(beat=11, midi_pitch=48),   # C3
    ]
    knots = [
        Knot(beat=0, midi_pitch=72),    # C5
        Knot(beat=3, midi_pitch=76),    # E5  (rising)
        Knot(beat=6, midi_pitch=79),    # G5  (peak)
        Knot(beat=9, midi_pitch=76),    # E5  (descending)
        Knot(beat=11, midi_pitch=72),   # C5  (home)
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, follower_low=60, follower_high=84, verbose=True)
    _write_output(result, "example_4.mid")


def example_5_sixteen_beats() -> None:
    """Sixteen beats, C major, I–vi–IV–V–I progression.

    Leader outlines a basic progression with one note per beat.
    Soprano has 5 knots outlining a melodic arch.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Sixteen beats, C major, I–vi–IV–V–I")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0, midi_pitch=48),    # C3
        LeaderNote(beat=1, midi_pitch=48),    # C3
        LeaderNote(beat=2, midi_pitch=52),    # E3
        LeaderNote(beat=3, midi_pitch=52),    # E3
        LeaderNote(beat=4, midi_pitch=45),    # A2
        LeaderNote(beat=5, midi_pitch=45),    # A2
        LeaderNote(beat=6, midi_pitch=48),    # C3
        LeaderNote(beat=7, midi_pitch=48),    # C3
        LeaderNote(beat=8, midi_pitch=53),    # F3
        LeaderNote(beat=9, midi_pitch=53),    # F3
        LeaderNote(beat=10, midi_pitch=57),   # A3
        LeaderNote(beat=11, midi_pitch=57),   # A3
        LeaderNote(beat=12, midi_pitch=55),   # G3
        LeaderNote(beat=13, midi_pitch=55),   # G3
        LeaderNote(beat=14, midi_pitch=55),   # G3
        LeaderNote(beat=15, midi_pitch=48),   # C3
    ]
    knots = [
        Knot(beat=0, midi_pitch=76),    # E5
        Knot(beat=4, midi_pitch=79),    # G5
        Knot(beat=8, midi_pitch=81),    # A5
        Knot(beat=12, midi_pitch=79),   # G5
        Knot(beat=15, midi_pitch=72),   # C5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=CMAJ)
    _write_output(result, "example_5.mid")


def example_6_quaver_grid() -> None:
    """Quaver grid, C major, 4 bars.

    16 quaver positions (0.0, 0.5, 1.0 … 7.5).
    Leader: descending scale C4→C3 then back up.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 6: Quaver grid, C major, 4 bars")
    print("=" * 70)
    leader = [
        LeaderNote(beat=0.0, midi_pitch=60),    # C4
        LeaderNote(beat=0.5, midi_pitch=59),    # B3
        LeaderNote(beat=1.0, midi_pitch=57),    # A3
        LeaderNote(beat=1.5, midi_pitch=55),    # G3
        LeaderNote(beat=2.0, midi_pitch=53),    # F3
        LeaderNote(beat=2.5, midi_pitch=52),    # E3
        LeaderNote(beat=3.0, midi_pitch=50),    # D3
        LeaderNote(beat=3.5, midi_pitch=48),    # C3
        LeaderNote(beat=4.0, midi_pitch=50),    # D3
        LeaderNote(beat=4.5, midi_pitch=52),    # E3
        LeaderNote(beat=5.0, midi_pitch=53),    # F3
        LeaderNote(beat=5.5, midi_pitch=55),    # G3
        LeaderNote(beat=6.0, midi_pitch=57),    # A3
        LeaderNote(beat=6.5, midi_pitch=59),    # B3
        LeaderNote(beat=7.0, midi_pitch=60),    # C4
        LeaderNote(beat=7.5, midi_pitch=60),    # C4
    ]
    knots = [
        Knot(beat=0.0, midi_pitch=72),    # C5
        Knot(beat=2.0, midi_pitch=76),    # E5
        Knot(beat=4.0, midi_pitch=79),    # G5
        Knot(beat=6.0, midi_pitch=76),    # E5
        Knot(beat=7.5, midi_pitch=72),    # C5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=CMAJ)
    _write_output(result, "example_6.mid")


def example_7_g_major_gavotte() -> None:
    """G major, 12 beats, gavotte-like.

    Tests the solver in G major with a simple stepwise bass.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 7: G major, 12 beats, gavotte-like")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    g_major = KeyInfo(frozenset({7, 9, 11, 0, 2, 4, 6}), tonic_pc=7)
    leader = [
        LeaderNote(beat=0, midi_pitch=43),    # G2
        LeaderNote(beat=1, midi_pitch=43),    # G2
        LeaderNote(beat=2, midi_pitch=47),    # B2
        LeaderNote(beat=3, midi_pitch=47),    # B2
        LeaderNote(beat=4, midi_pitch=50),    # D3
        LeaderNote(beat=5, midi_pitch=50),    # D3
        LeaderNote(beat=6, midi_pitch=55),    # G3
        LeaderNote(beat=7, midi_pitch=55),    # G3
        LeaderNote(beat=8, midi_pitch=50),    # D3
        LeaderNote(beat=9, midi_pitch=50),    # D3
        LeaderNote(beat=10, midi_pitch=43),   # G2
        LeaderNote(beat=11, midi_pitch=43),   # G2
    ]
    knots = [
        Knot(beat=0, midi_pitch=71),    # B4
        Knot(beat=4, midi_pitch=74),    # D5
        Knot(beat=8, midi_pitch=71),    # B4
        Knot(beat=11, midi_pitch=67),   # G4
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=g_major)
    _write_output(result, "example_7.mid")


def example_8_d_minor_sarabande() -> None:
    """D minor, 16 beats, sarabande weight.

    Tests the solver in D minor with slow, sustained bass notes.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 8: D minor, 16 beats, sarabande weight")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    d_minor = KeyInfo(frozenset({2, 4, 5, 7, 9, 10, 0}), tonic_pc=2)
    leader = [
        LeaderNote(beat=0, midi_pitch=50),    # D3
        LeaderNote(beat=1, midi_pitch=50),    # D3
        LeaderNote(beat=2, midi_pitch=50),    # D3
        LeaderNote(beat=3, midi_pitch=45),    # A2
        LeaderNote(beat=4, midi_pitch=45),    # A2
        LeaderNote(beat=5, midi_pitch=45),    # A2
        LeaderNote(beat=6, midi_pitch=46),    # Bb2
        LeaderNote(beat=7, midi_pitch=46),    # Bb2
        LeaderNote(beat=8, midi_pitch=43),    # G2
        LeaderNote(beat=9, midi_pitch=43),    # G2
        LeaderNote(beat=10, midi_pitch=45),   # A2
        LeaderNote(beat=11, midi_pitch=45),   # A2
        LeaderNote(beat=12, midi_pitch=50),   # D3
        LeaderNote(beat=13, midi_pitch=50),   # D3
        LeaderNote(beat=14, midi_pitch=50),   # D3
        LeaderNote(beat=15, midi_pitch=50),   # D3
    ]
    knots = [
        Knot(beat=0, midi_pitch=77),    # F5
        Knot(beat=4, midi_pitch=76),    # E5
        Knot(beat=8, midi_pitch=74),    # D5
        Knot(beat=12, midi_pitch=69),   # A4
        Knot(beat=15, midi_pitch=74),   # D5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=d_minor)
    _write_output(result, "example_8.mid")


def example_9_f_major_longer() -> None:
    """F major, 20 beats, longer phrase.

    Tests the solver with a longer phrase in F major.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 9: F major, 20 beats, longer phrase")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    f_major = KeyInfo(frozenset({5, 7, 9, 10, 0, 2, 4}), tonic_pc=5)
    leader = [
        LeaderNote(beat=0, midi_pitch=53),    # F3
        LeaderNote(beat=1, midi_pitch=53),    # F3
        LeaderNote(beat=2, midi_pitch=57),    # A3
        LeaderNote(beat=3, midi_pitch=57),    # A3
        LeaderNote(beat=4, midi_pitch=60),    # C4
        LeaderNote(beat=5, midi_pitch=60),    # C4
        LeaderNote(beat=6, midi_pitch=58),    # Bb3
        LeaderNote(beat=7, midi_pitch=58),    # Bb3
        LeaderNote(beat=8, midi_pitch=57),    # A3
        LeaderNote(beat=9, midi_pitch=57),    # A3
        LeaderNote(beat=10, midi_pitch=55),   # G3
        LeaderNote(beat=11, midi_pitch=55),   # G3
        LeaderNote(beat=12, midi_pitch=53),   # F3
        LeaderNote(beat=13, midi_pitch=53),   # F3
        LeaderNote(beat=14, midi_pitch=52),   # E3
        LeaderNote(beat=15, midi_pitch=52),   # E3
        LeaderNote(beat=16, midi_pitch=53),   # F3
        LeaderNote(beat=17, midi_pitch=53),   # F3
        LeaderNote(beat=18, midi_pitch=48),   # C3
        LeaderNote(beat=19, midi_pitch=53),   # F3
    ]
    knots = [
        Knot(beat=0, midi_pitch=81),    # A5
        Knot(beat=4, midi_pitch=84),    # C6
        Knot(beat=8, midi_pitch=81),    # A5
        Knot(beat=12, midi_pitch=77),   # F5
        Knot(beat=16, midi_pitch=79),   # G5
        Knot(beat=19, midi_pitch=77),   # F5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=f_major)
    _write_output(result, "example_9.mid")


def example_10_a_minor_invention() -> None:
    """A minor, 16 beats, invention-like.

    Tests the solver with imitative, angular bass in A minor.
    Note: G#3=56 is chromatic (not in natural A minor).
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 10: A minor, 16 beats, invention-like")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    a_minor = KeyInfo(frozenset({9, 11, 0, 2, 4, 5, 7}), tonic_pc=9)
    leader = [
        LeaderNote(beat=0, midi_pitch=45),    # A2
        LeaderNote(beat=1, midi_pitch=47),    # B2
        LeaderNote(beat=2, midi_pitch=48),    # C3
        LeaderNote(beat=3, midi_pitch=50),    # D3
        LeaderNote(beat=4, midi_pitch=52),    # E3
        LeaderNote(beat=5, midi_pitch=50),    # D3
        LeaderNote(beat=6, midi_pitch=48),    # C3
        LeaderNote(beat=7, midi_pitch=47),    # B2
        LeaderNote(beat=8, midi_pitch=45),    # A2
        LeaderNote(beat=9, midi_pitch=48),    # C3
        LeaderNote(beat=10, midi_pitch=52),   # E3
        LeaderNote(beat=11, midi_pitch=57),   # A3
        LeaderNote(beat=12, midi_pitch=56),   # G#3 (chromatic)
        LeaderNote(beat=13, midi_pitch=57),   # A3
        LeaderNote(beat=14, midi_pitch=47),   # B2
        LeaderNote(beat=15, midi_pitch=45),   # A2
    ]
    knots = [
        Knot(beat=0, midi_pitch=76),    # E5
        Knot(beat=4, midi_pitch=72),    # C5
        Knot(beat=8, midi_pitch=69),    # A4
        Knot(beat=12, midi_pitch=76),   # E5
        Knot(beat=15, midi_pitch=69),   # A4
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=a_minor)
    _write_output(result, "example_10.mid")


def example_11_bb_major_short() -> None:
    """Bb major, 8 beats, short phrase.

    Tests the solver with a short phrase in Bb major.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 11: Bb major, 8 beats, short phrase")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    bb_major = KeyInfo(frozenset({10, 0, 2, 3, 5, 7, 9}), tonic_pc=10)
    leader = [
        LeaderNote(beat=0, midi_pitch=46),    # Bb2
        LeaderNote(beat=1, midi_pitch=46),    # Bb2
        LeaderNote(beat=2, midi_pitch=50),    # D3
        LeaderNote(beat=3, midi_pitch=50),    # D3
        LeaderNote(beat=4, midi_pitch=53),    # F3
        LeaderNote(beat=5, midi_pitch=53),    # F3
        LeaderNote(beat=6, midi_pitch=46),    # Bb2
        LeaderNote(beat=7, midi_pitch=46),    # Bb2
    ]
    knots = [
        Knot(beat=0, midi_pitch=74),    # D5
        Knot(beat=3, midi_pitch=77),    # F5
        Knot(beat=7, midi_pitch=70),    # Bb4
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=bb_major)
    _write_output(result, "example_11.mid")


def example_12_eb_major_walking() -> None:
    """Eb major, 16 beats, walking bass.

    Tests the solver with stepwise walking bass in Eb major.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 12: Eb major, 16 beats, walking bass")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    eb_major = KeyInfo(frozenset({3, 5, 7, 8, 10, 0, 2}), tonic_pc=3)
    leader = [
        LeaderNote(beat=0, midi_pitch=51),    # Eb3
        LeaderNote(beat=1, midi_pitch=53),    # F3
        LeaderNote(beat=2, midi_pitch=55),    # G3
        LeaderNote(beat=3, midi_pitch=56),    # Ab3
        LeaderNote(beat=4, midi_pitch=58),    # Bb3
        LeaderNote(beat=5, midi_pitch=56),    # Ab3
        LeaderNote(beat=6, midi_pitch=55),    # G3
        LeaderNote(beat=7, midi_pitch=53),    # F3
        LeaderNote(beat=8, midi_pitch=51),    # Eb3
        LeaderNote(beat=9, midi_pitch=50),    # D3
        LeaderNote(beat=10, midi_pitch=48),   # C3
        LeaderNote(beat=11, midi_pitch=46),   # Bb2
        LeaderNote(beat=12, midi_pitch=44),   # Ab2
        LeaderNote(beat=13, midi_pitch=46),   # Bb2
        LeaderNote(beat=14, midi_pitch=48),   # C3
        LeaderNote(beat=15, midi_pitch=51),   # Eb3
    ]
    knots = [
        Knot(beat=0, midi_pitch=79),    # G5
        Knot(beat=4, midi_pitch=82),    # Bb5
        Knot(beat=8, midi_pitch=79),    # G5
        Knot(beat=12, midi_pitch=75),   # Eb5
        Knot(beat=15, midi_pitch=75),   # Eb5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=eb_major)
    _write_output(result, "example_12.mid")


def example_13_c_minor_quaver() -> None:
    """C minor, quaver grid, 8 bars.

    32 quaver positions (0.0 … 15.5). Tests the solver with a longer
    quaver-level phrase in C minor.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 13: C minor, quaver grid, 8 bars")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    c_minor = KeyInfo(frozenset({0, 2, 3, 5, 7, 8, 10}), tonic_pc=0)
    leader = [
        # Bar 1-2: C3 D3 Eb3 F3 | G3 F3 Eb3 D3
        LeaderNote(beat=0.0, midi_pitch=48),    # C3
        LeaderNote(beat=0.5, midi_pitch=50),    # D3
        LeaderNote(beat=1.0, midi_pitch=51),    # Eb3
        LeaderNote(beat=1.5, midi_pitch=53),    # F3
        LeaderNote(beat=2.0, midi_pitch=55),    # G3
        LeaderNote(beat=2.5, midi_pitch=53),    # F3
        LeaderNote(beat=3.0, midi_pitch=51),    # Eb3
        LeaderNote(beat=3.5, midi_pitch=50),    # D3
        # Bar 3-4: C3 Bb2 Ab2 G2 | Ab2 Bb2 C3 D3
        LeaderNote(beat=4.0, midi_pitch=48),    # C3
        LeaderNote(beat=4.5, midi_pitch=46),    # Bb2
        LeaderNote(beat=5.0, midi_pitch=44),    # Ab2
        LeaderNote(beat=5.5, midi_pitch=43),    # G2
        LeaderNote(beat=6.0, midi_pitch=44),    # Ab2
        LeaderNote(beat=6.5, midi_pitch=46),    # Bb2
        LeaderNote(beat=7.0, midi_pitch=48),    # C3
        LeaderNote(beat=7.5, midi_pitch=50),    # D3
        # Bar 5-6: Eb3 F3 G3 Ab3 | Bb3 Ab3 G3 F3
        LeaderNote(beat=8.0, midi_pitch=51),    # Eb3
        LeaderNote(beat=8.5, midi_pitch=53),    # F3
        LeaderNote(beat=9.0, midi_pitch=55),    # G3
        LeaderNote(beat=9.5, midi_pitch=56),    # Ab3
        LeaderNote(beat=10.0, midi_pitch=58),   # Bb3
        LeaderNote(beat=10.5, midi_pitch=56),   # Ab3
        LeaderNote(beat=11.0, midi_pitch=55),   # G3
        LeaderNote(beat=11.5, midi_pitch=53),   # F3
        # Bar 7-8: Eb3 D3 C3 Bb2 | Ab2 Bb2 C3 C3
        LeaderNote(beat=12.0, midi_pitch=51),   # Eb3
        LeaderNote(beat=12.5, midi_pitch=50),   # D3
        LeaderNote(beat=13.0, midi_pitch=48),   # C3
        LeaderNote(beat=13.5, midi_pitch=46),   # Bb2
        LeaderNote(beat=14.0, midi_pitch=44),   # Ab2
        LeaderNote(beat=14.5, midi_pitch=46),   # Bb2
        LeaderNote(beat=15.0, midi_pitch=48),   # C3
        LeaderNote(beat=15.5, midi_pitch=48),   # C3
    ]
    knots = [
        Knot(beat=0.0, midi_pitch=79),    # G5
        Knot(beat=4.0, midi_pitch=75),    # Eb5
        Knot(beat=8.0, midi_pitch=72),    # C5
        Knot(beat=12.0, midi_pitch=79),   # G5
        Knot(beat=15.5, midi_pitch=72),   # C5
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=c_minor)
    _write_output(result, "example_13.mid")


def example_14_g_major_cadence() -> None:
    """G major, quaver grid, cadential test.

    16 quaver positions (0.0 … 7.5). Tests cadential approach in G major.
    """
    print("\n" + "=" * 70)
    print("EXAMPLE 14: G major, quaver grid, cadential test")
    print("=" * 70)
    from viterbi.scale import KeyInfo
    g_major = KeyInfo(frozenset({7, 9, 11, 0, 2, 4, 6}), tonic_pc=7)
    leader = [
        LeaderNote(beat=0.0, midi_pitch=55),    # G3
        LeaderNote(beat=0.5, midi_pitch=57),    # A3
        LeaderNote(beat=1.0, midi_pitch=59),    # B3
        LeaderNote(beat=1.5, midi_pitch=60),    # C4
        LeaderNote(beat=2.0, midi_pitch=62),    # D4
        LeaderNote(beat=2.5, midi_pitch=60),    # C4
        LeaderNote(beat=3.0, midi_pitch=59),    # B3
        LeaderNote(beat=3.5, midi_pitch=57),    # A3
        LeaderNote(beat=4.0, midi_pitch=55),    # G3
        LeaderNote(beat=4.5, midi_pitch=54),    # F#3
        LeaderNote(beat=5.0, midi_pitch=55),    # G3
        LeaderNote(beat=5.5, midi_pitch=57),    # A3
        LeaderNote(beat=6.0, midi_pitch=50),    # D3
        LeaderNote(beat=6.5, midi_pitch=50),    # D3
        LeaderNote(beat=7.0, midi_pitch=43),    # G2
        LeaderNote(beat=7.5, midi_pitch=43),    # G2
    ]
    knots = [
        Knot(beat=0.0, midi_pitch=71),    # B4
        Knot(beat=2.0, midi_pitch=74),    # D5
        Knot(beat=4.0, midi_pitch=71),    # B4
        Knot(beat=6.0, midi_pitch=74),    # D5
        Knot(beat=7.5, midi_pitch=67),    # G4
    ]
    _describe_inputs(leader, knots)
    result = _solve_with_leader(leader, knots, verbose=True, key=g_major)
    _write_output(result, "example_14.mid")


def _describe_inputs(
    leader: list[LeaderNote],
    knots: list[Knot],
) -> None:
    """Print the input data before solving."""
    print(f"\n  Leader ({len(leader)} beats):")
    notes = [f"b{ln.beat}:{pitch_name(ln.midi_pitch)}" for ln in leader]
    print(f"    {', '.join(notes)}")
    print(f"\n  Follower knots ({len(knots)}):")
    for k in knots:
        print(f"    {k}")
    spans = []
    for i in range(len(knots) - 1):
        gap = knots[i + 1].beat - knots[i].beat
        interval = knots[i + 1].midi_pitch - knots[i].midi_pitch
        if interval > 0:
            direction = "up"
        elif interval < 0:
            direction = "down"
        else:
            direction = "same"
        spans.append(f"  knot {i}->{i + 1}: {gap} beats, "
                     f"{direction} {abs(interval)} semitones")
    print(f"\n  Segments:")
    for s in spans:
        print(f"    {s}")


def _write_output(result, filename: str) -> None:
    """Write MIDI if midiutil is available."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, filename)
    write_midi(result, path)


if __name__ == "__main__":
    examples = {
        "1": example_1_rising_scale,
        "2": example_2_descending_bass,
        "3": example_3_tight_knots,
        "4": example_4_realistic_bass,
        "5": example_5_sixteen_beats,
        "6": example_6_quaver_grid,
        "7": example_7_g_major_gavotte,
        "8": example_8_d_minor_sarabande,
        "9": example_9_f_major_longer,
        "10": example_10_a_minor_invention,
        "11": example_11_bb_major_short,
        "12": example_12_eb_major_walking,
        "13": example_13_c_minor_quaver,
        "14": example_14_g_major_cadence,
    }
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            if arg in examples:
                examples[arg]()
            else:
                print(f"Unknown example: {arg}. Choose from: {', '.join(examples.keys())}")
    else:
        for fn in examples.values():
            fn()

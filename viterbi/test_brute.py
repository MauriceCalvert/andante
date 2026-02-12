"""Brute-force optimality test for the Viterbi pathfinder.

Enumerates every legal path, computes total cost identically to the DP,
and verifies the Viterbi result is optimal.

Usage:
    python -m viterbi.test_brute [n_beats] [n_trials]

Defaults: 5 beats, 200 trials.
"""
import itertools
import random
import sys
from viterbi.corridors import build_corridors
from viterbi.costs import transition_cost
from viterbi.mtypes import Knot, LeaderNote
from viterbi.pathfinder import find_path, _sign, _next_run, CROSS_RELATION_BEAT_WINDOW, compute_contour_targets
from viterbi.scale import build_pitch_set, is_consonant

INF = float("inf")
FOLLOWER_LOW = 60
FOLLOWER_HIGH = 79
LEADER_LOW = 43
LEADER_HIGH = 60


def brute_force_cost(
    path: list[int],
    corridors_list: list,
    n_beats: int,
    contour_targets: list[int] | None = None,
) -> float:
    """Compute total path cost with exact run-state tracking."""
    # Precompute nearby leader pitch-class sets for cross-relation detection
    beats = [c.beat for c in corridors_list]
    leader_map = {c.beat: c.leader_pitch for c in corridors_list}
    nearby_ldr_pcs: list[frozenset[int]] = []
    for t in range(n_beats):
        pcs = frozenset(
            leader_map[beats[j]] % 12
            for j in range(n_beats)
            if abs(beats[j] - beats[t]) <= CROSS_RELATION_BEAT_WINDOW
        )
        nearby_ldr_pcs.append(pcs)
    total = 0.0
    run_dir = 0
    run_count = 1
    for t in range(1, n_beats):
        prev_p = path[t - 1]
        curr_p = path[t]
        prev_prev_p = path[t - 2] if t >= 2 else None
        new_dir = _sign(curr_p - prev_p)
        run_dir, run_count = _next_run(run_dir, run_count, new_dir)
        phrase_pos = t / max(n_beats - 1, 1)
        ct = contour_targets[t] if contour_targets is not None else 0
        cost, _ = transition_cost(
            prev_pitch=prev_p,
            curr_pitch=curr_p,
            prev_leader=corridors_list[t - 1].leader_pitch,
            curr_leader=corridors_list[t].leader_pitch,
            prev_beat_strength=corridors_list[t - 1].beat_strength,
            curr_beat_strength=corridors_list[t].beat_strength,
            prev_prev_pitch=prev_prev_p,
            phrase_position=phrase_pos,
            target_pitch=path[-1],
            run_count=run_count,
            nearby_leader_pcs=nearby_ldr_pcs[t],
            contour_target=ct,
        )
        total += cost
    return total


def random_leader(
    n_beats: int,
) -> list[LeaderNote]:
    """Generate a random diatonic leader voice."""
    pitches = build_pitch_set(LEADER_LOW, LEADER_HIGH)
    leader = []
    p = random.choice(pitches)
    for b in range(n_beats):
        leader.append(LeaderNote(beat=b, midi_pitch=p))
        candidates = [q for q in pitches if abs(q - p) <= 5]
        p = random.choice(candidates)
    return leader


def random_knots(
    n_beats: int,
    leader_notes: list[LeaderNote],
) -> list[Knot]:
    """Generate knots at first and last beat, consonant with leader."""
    follower_pitches = build_pitch_set(FOLLOWER_LOW, FOLLOWER_HIGH)
    knots = []
    for b in [0, n_beats - 1]:
        lp = leader_notes[b].midi_pitch
        consonant = [p for p in follower_pitches if is_consonant(abs(p - lp))]
        assert consonant, f"No consonant follower for leader {lp} at beat {b}"
        knots.append(Knot(beat=b, midi_pitch=random.choice(consonant)))
    return knots


def enumerate_paths(
    corridors_list: list,
    knot_map: dict[int, int],
    n_beats: int,
) -> list[list[int]]:
    """Enumerate all legal paths respecting knot constraints."""
    options = []
    for t in range(n_beats):
        beat = corridors_list[t].beat
        if beat in knot_map:
            options.append([knot_map[beat]])
        else:
            options.append(list(corridors_list[t].legal_pitches))
    return [list(combo) for combo in itertools.product(*options)]


def run_one_trial(
    n_beats: int,
    trial: int,
) -> bool:
    """Run one random trial. Returns True if Viterbi matches brute force."""
    leader = random_leader(n_beats)
    knots = random_knots(n_beats, leader)
    knot_map = {k.beat: k.midi_pitch for k in knots}
    corridors = build_corridors(
        leader,
        follower_low=FOLLOWER_LOW,
        follower_high=FOLLOWER_HIGH,
    )
    beats, viterbi_path, viterbi_cost = find_path(
        corridors=corridors,
        knots=knots,
        final_pitch=knots[-1].midi_pitch,
        phrase_length=n_beats,
        verbose=False,
    )
    if viterbi_cost == INF:
        return True
    # Build legal pitch lists (same logic as pathfinder) for contour targets
    legal: list[list[int]] = []
    for c in corridors:
        if c.beat in knot_map:
            legal.append([knot_map[c.beat]])
        else:
            legal.append(list(c.legal_pitches))
    ct = compute_contour_targets(corridors, legal)
    all_paths = enumerate_paths(corridors, knot_map, n_beats)
    best_cost = INF
    best_path = None
    for path in all_paths:
        cost = brute_force_cost(path, corridors, n_beats, contour_targets=ct)
        if cost < best_cost:
            best_cost = cost
            best_path = path
    tolerance = 1e-6
    if abs(viterbi_cost - best_cost) > tolerance:
        print(f"\n  MISMATCH in trial {trial}:")
        print(f"    Leader: {[(ln.beat, ln.midi_pitch) for ln in leader]}")
        print(f"    Knots:  {knots}")
        print(f"    Viterbi path: {viterbi_path}  cost={viterbi_cost:.6f}")
        print(f"    Brute path:   {best_path}  cost={best_cost:.6f}")
        print(f"    Delta: {viterbi_cost - best_cost:.6f}")
        return False
    return True


def main() -> None:
    """Run brute-force optimality trials."""
    n_beats = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    n_trials = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    print(f"Brute-force optimality test: {n_beats} beats, {n_trials} trials")
    print(f"  Follower range: {FOLLOWER_LOW}-{FOLLOWER_HIGH}")
    sample_leader = random_leader(n_beats)
    sample_corridors = build_corridors(
        sample_leader,
        follower_low=FOLLOWER_LOW,
        follower_high=FOLLOWER_HIGH,
    )
    sizes = [len(c.legal_pitches) for c in sample_corridors]
    space = 1
    for s in sizes:
        space *= s
    print(f"  Typical corridor widths: {sizes}")
    print(f"  Typical search space: ~{space:,} paths per trial")
    passed = 0
    failed = 0
    for t in range(n_trials):
        if run_one_trial(n_beats, t):
            passed += 1
        else:
            failed += 1
        if (t + 1) % 50 == 0:
            print(f"  ... {t + 1}/{n_trials}  passed={passed} failed={failed}")
    print(f"\nResult: {passed} passed, {failed} failed out of {n_trials}")
    if failed == 0:
        print("ALL PASSED")
    else:
        print(f"*** {failed} FAILURES ***")
        sys.exit(1)


if __name__ == "__main__":
    main()

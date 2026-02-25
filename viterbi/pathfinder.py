"""Second-order Viterbi pathfinder with run-length state.

DP state: (prev_pitch, curr_pitch, run_dir, run_count)

This captures every dependency in the cost function exactly:
- zigzag and leap recovery depend on prev_prev_pitch (the prev_pitch
  in the predecessor state)
- run penalty depends on the count of consecutive same-direction steps

run_dir is -1 (descending), 0 (unison), or +1 (ascending).
run_count is capped at MAX_RUN (6). Runs longer than this are never
optimal because the penalty already exceeds alternative costs.
"""
from collections import Counter

from viterbi.costs import transition_cost
from viterbi.mtypes import (
    ContourShape,
    Corridor,
    ExistingVoice,
    Knot,
    pitch_name,
)
from viterbi.scale import interval_name, is_consonant, scale_degree_distance, KeyInfo, CMAJ

INF = float("inf")
MAX_RUN = 6
BEAM_WIDTH = 500  # max DP states retained per beat
CROSS_RELATION_BEAT_WINDOW = 0.25  # whole-note units = one crotchet

# State: (prev_pitch, curr_pitch, run_dir, run_count)
State = tuple[int, int, int, int]


def _sign(x: int) -> int:
    """Sign of x: -1, 0, or +1."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _next_run(
    run_dir: int,
    run_count: int,
    new_dir: int,
) -> tuple[int, int]:
    """Compute new run state after a step in new_dir."""
    if new_dir != 0 and new_dir == run_dir:
        return new_dir, min(run_count + 1, MAX_RUN)
    return new_dir, 1


def _beam_prune(
    dp: dict[State, float],
    bt: dict[State, State | None],
    details: dict[State, dict[str, float]] | None,
    width: int,
) -> None:
    """Keep only the top `width` states by cost, discard the rest in-place."""
    if len(dp) <= width:
        return
    keep = set(s for s, _ in sorted(dp.items(), key=lambda x: x[1])[:width])
    to_remove = [s for s in dp if s not in keep]
    for s in to_remove:
        del dp[s]
        del bt[s]
        if details is not None and s in details:
            del details[s]


def compute_contour_targets(
    corridors: list[Corridor],
    legal: list[list[int]],
    contour: ContourShape | None = None,
    key: KeyInfo = CMAJ,
) -> list[int]:
    """Precompute one contour target pitch per beat for phrase arc shaping.

    Uses a three-point piecewise-linear contour: start → apex → end.
    Each value is a degree offset from the corridor midpoint.
    If contour is None, ContourShape() is used (approximates the former
    Gaussian arc: rise to +4 degrees at 65%, return to 0).
    """
    if contour is None:
        contour = ContourShape()
    n_beats = len(corridors)
    # Average semitones per scale degree in the current key
    pc_count: int = len(key.pitch_class_set)
    avg_step: float = 12.0 / max(pc_count, 1)

    targets: list[int] = []
    for t in range(n_beats):
        p: float = t / max(n_beats - 1, 1)
        # Piecewise linear interpolation between start, apex, end
        if contour.apex_pos <= 0.0:
            # Apex is at the very start: everything maps to the end segment
            denom: float = 1.0 - contour.apex_pos if contour.apex_pos < 1.0 else 1.0
            offset: float = contour.apex + (contour.end - contour.apex) * (p / denom)
        elif p <= contour.apex_pos:
            denom = contour.apex_pos
            offset = contour.start + (contour.apex - contour.start) * (p / denom)
        else:
            denom = 1.0 - contour.apex_pos if contour.apex_pos < 1.0 else 1.0
            offset = contour.apex + (contour.end - contour.apex) * ((p - contour.apex_pos) / denom)
        range_low: int = min(legal[t])
        range_high: int = max(legal[t])
        range_mid: int = (range_low + range_high) // 2
        target: int = range_mid + round(offset * avg_step)
        targets.append(max(range_low, min(range_high, target)))
    return targets


def find_path(
    corridors: list[Corridor],
    knots: list[Knot],
    final_pitch: int,
    phrase_length: int,
    existing_voices: list[ExistingVoice],
    verbose: bool = False,
    key: KeyInfo = CMAJ,
    chord_pcs_at: list[frozenset[int]] | None = None,
    hard_constraints: bool = True,
    contour: ContourShape | None = None,
    degree_affinity: tuple[float, ...] | None = None,
    interval_affinity: dict[int, float] | None = None,
    genome_entries: tuple[tuple[float, int], ...] | None = None,
) -> tuple[list[float], list[int], float]:
    """Find minimum-cost path through corridors with knot constraints."""
    knot_map = {k.beat: k.midi_pitch for k in knots}
    n_beats = len(corridors)
    assert n_beats >= 2, "Need at least 2 beats"
    beats = [c.beat for c in corridors]
    leader_map = {c.beat: c.leader_pitch for c in corridors}
    legal: list[list[int]] = []
    for c in corridors:
        if c.beat in knot_map:
            legal.append([knot_map[c.beat]])
        else:
            legal.append(list(c.legal_pitches))

    # Precompute per-voice nearby pitch-class sets for cross-relation detection
    n_voices = len(existing_voices)
    nearby_pcs: list[list[frozenset[int]]] = []  # [beat_index][voice_index]
    for t in range(n_beats):
        per_voice: list[frozenset[int]] = []
        for v in existing_voices:
            pcs = frozenset(
                v.pitches_at_beat[beats[j]] % 12
                for j in range(n_beats)
                if abs(beats[j] - beats[t]) <= CROSS_RELATION_BEAT_WINDOW
            )
            per_voice.append(pcs)
        nearby_pcs.append(per_voice)

    # Pre-resolve voice pitches per beat: voice_pitches[t][v] = MIDI pitch
    voice_pitches: list[list[int]] = [
        [v.pitches_at_beat[beats[t]] for v in existing_voices]
        for t in range(n_beats)
    ]
    is_above_list: list[bool] = [v.is_above for v in existing_voices]

    contour_targets = compute_contour_targets(corridors, legal, contour=contour, key=key)
    contour_weight: float = contour.weight if contour is not None else 1.0

    # DP tables: dp[t] maps State -> cost, bt[t] maps State -> predecessor State or None
    dp: list[dict[State, float]] = [{} for _ in range(n_beats)]
    bt: list[dict[State, State | None]] = [{} for _ in range(n_beats)]
    details: list[dict[State, dict[str, float]]] = [{} for _ in range(n_beats)] if verbose else None
    # Beat 0: seed state (we use a dummy state with prev=start, curr=start)
    assert beats[0] in knot_map, "First beat must be a knot"
    start_pitch = knot_map[beats[0]]
    # Beat 1: first real transitions (no prev_prev_pitch)
    if n_beats < 2:
        return beats, [start_pitch], 0.0
    hc_blocks_1: Counter = Counter()
    for curr_p in legal[1]:
        new_dir = _sign(curr_p - start_pitch)
        phrase_pos = 1 / max(n_beats - 1, 1)
        cost, bd = transition_cost(
            prev_pitch=start_pitch,
            curr_pitch=curr_p,
            prev_beat_strength=corridors[0].beat_strength,
            curr_beat_strength=corridors[1].beat_strength,
            prev_others=voice_pitches[0],
            curr_others=voice_pitches[1],
            nearby_pcs_per_voice=nearby_pcs[1],
            is_above_per_voice=is_above_list,
            prev_prev_pitch=None,
            phrase_position=phrase_pos,
            target_pitch=final_pitch,
            run_count=1,
            key=key,
            contour_target=contour_targets[1],
            chord_pcs=chord_pcs_at[1] if chord_pcs_at else frozenset(),
            hard_constraints=hard_constraints,
            contour_weight=contour_weight,
            degree_affinity=degree_affinity,
            interval_affinity=interval_affinity,
            genome_entries=genome_entries,
        )
        if cost == INF:
            hc_blocks_1[bd.get("rule", "unknown")] += 1
            continue
        state: State = (start_pitch, curr_p, new_dir, 1)
        if state not in dp[1] or cost < dp[1][state]:
            dp[1][state] = cost
            bt[1][state] = None
            if details is not None:
                details[1][state] = bd
    # Check if beat 1 has no valid states due to hard constraints
    if hard_constraints and not dp[1]:
        import logging
        rule_summary = ", ".join(f"{r}={c}" for r, c in hc_blocks_1.most_common())
        logging.getLogger("andante.viterbi").warning(
            "Hard constraints blocked all %d candidates at beat %s "
            "[%s] — falling back to soft-only",
            sum(hc_blocks_1.values()), beats[1], rule_summary,
        )
        return find_path(
            corridors=corridors,
            knots=knots,
            final_pitch=final_pitch,
            phrase_length=phrase_length,
            existing_voices=existing_voices,
            verbose=verbose,
            key=key,
            chord_pcs_at=chord_pcs_at,
            hard_constraints=False,
            contour=contour,
            degree_affinity=degree_affinity,
            interval_affinity=interval_affinity,
            genome_entries=genome_entries,
        )
    # Beats 2..n-1: full second-order transitions
    for t in range(2, n_beats):
        phrase_pos = t / max(n_beats - 1, 1)
        prev_dp = dp[t - 1]
        t_prev_others = voice_pitches[t - 1]
        t_curr_others = voice_pitches[t]
        t_nearby_pcs = nearby_pcs[t]
        hc_blocks_t: Counter = Counter()
        for curr_p in legal[t]:
            for prev_state, prev_cost in prev_dp.items():
                pp, prev_p, rd, rc = prev_state
                new_dir = _sign(curr_p - prev_p)
                new_rd, new_rc = _next_run(rd, rc, new_dir)
                cost, bd = transition_cost(
                    prev_pitch=prev_p,
                    curr_pitch=curr_p,
                    prev_beat_strength=corridors[t - 1].beat_strength,
                    curr_beat_strength=corridors[t].beat_strength,
                    prev_others=t_prev_others,
                    curr_others=t_curr_others,
                    nearby_pcs_per_voice=t_nearby_pcs,
                    is_above_per_voice=is_above_list,
                    prev_prev_pitch=pp,
                    phrase_position=phrase_pos,
                    target_pitch=final_pitch,
                    run_count=new_rc,
                    key=key,
                    contour_target=contour_targets[t],
                    chord_pcs=chord_pcs_at[t] if chord_pcs_at else frozenset(),
                    hard_constraints=hard_constraints,
                    contour_weight=contour_weight,
                    degree_affinity=degree_affinity,
                    interval_affinity=interval_affinity,
                    genome_entries=genome_entries,
                )
                if cost == INF:
                    hc_blocks_t[bd.get("rule", "unknown")] += 1
                    continue
                total = prev_cost + cost
                state = (prev_p, curr_p, new_rd, new_rc)
                if state not in dp[t] or total < dp[t][state]:
                    dp[t][state] = total
                    bt[t][state] = prev_state
                    if details is not None:
                        details[t][state] = bd
        # Beam prune to keep DP tractable
        _beam_prune(dp[t], bt[t], details[t] if details is not None else None, BEAM_WIDTH)
        # Infeasibility fallback: if all transitions were hard-blocked, retry with soft-only
        if hard_constraints and not dp[t]:
            import logging
            rule_summary = ", ".join(f"{r}={c}" for r, c in hc_blocks_t.most_common())
            logging.getLogger("andante.viterbi").warning(
                "Hard constraints blocked all %d transitions at beat %s "
                "[%s] — falling back to soft-only",
                sum(hc_blocks_t.values()), beats[t], rule_summary,
            )
            return find_path(
                corridors=corridors,
                knots=knots,
                final_pitch=final_pitch,
                phrase_length=phrase_length,
                existing_voices=existing_voices,
                verbose=verbose,
                key=key,
                chord_pcs_at=chord_pcs_at,
                hard_constraints=False,
                contour=contour,
                degree_affinity=degree_affinity,
                interval_affinity=interval_affinity,
                genome_entries=genome_entries,
            )
    # Find best final state
    end_pitch = knot_map[beats[-1]]
    best_cost = INF
    best_state: State | None = None
    for state, cost in dp[n_beats - 1].items():
        if state[1] == end_pitch and cost < best_cost:
            best_cost = cost
            best_state = state
    if best_state is None:
        if verbose:
            print("  *** NO PATH FOUND ***")
        return beats, [0] * n_beats, INF
    # Backtrack
    path = [0] * n_beats
    state_chain: list[State | None] = [None] * n_beats
    state_chain[n_beats - 1] = best_state
    path[n_beats - 1] = best_state[1]
    cur = best_state
    for t in range(n_beats - 1, 1, -1):
        prev_state = bt[t][cur]
        state_chain[t - 1] = prev_state
        path[t - 1] = prev_state[1]
        cur = prev_state
    path[0] = start_pitch
    if verbose:
        _print_path(beats, path, corridors, leader_map, knot_map,
                     state_chain, details, best_cost, key, contour_targets)
    return beats, path, best_cost


def _print_path(
    beats: list[float],
    pitches: list[int],
    corridors: list[Corridor],
    leader_map: dict[float, int],
    knot_map: dict[float, int],
    state_chain: list[State | None],
    details: list[dict[State, dict[str, float]]],
    total_cost: float,
    key: KeyInfo = CMAJ,
    contour_targets: list[int] | None = None,
) -> None:
    """Print the chosen path with full annotation."""
    print(f"\n  +--- CHOSEN PATH (total cost: {total_cost:.1f}) ---")
    for i, (b, p) in enumerate(zip(beats, pitches)):
        lp = leader_map[b]
        iv = abs(p - lp)
        cons = "cons" if is_consonant(iv) else "DISS"
        knot = " *" if b in knot_map else "  "
        motion = ""
        if i > 0:
            prev_p = pitches[i - 1]
            dist = scale_degree_distance(prev_p, p, key)
            arrow = "^" if p > prev_p else ("v" if p < prev_p else "-")
            prev_lp = leader_map[beats[i - 1]]
            f_dir = p - prev_p
            l_dir = lp - prev_lp
            if f_dir * l_dir < 0:
                rel = "contr"
            elif f_dir == 0 or l_dir == 0:
                rel = "obliq"
            else:
                rel = "simil"
            st = state_chain[i]
            bd = details[i].get(st, {}) if st is not None else {}
            rc = st[3] if st is not None else 0
            motion = (f"  {arrow}{dist}step {rel:5s}  "
                      f"cost={bd.get('total', 0):.1f} "
                      f"[s={bd.get('step', 0):.0f} m={bd.get('motion', 0):.1f} "
                      f"lr={bd.get('leap_rec', 0):.0f} z={bd.get('zigzag', 0):.0f} "
                      f"r={bd.get('run', 0):.0f} d={bd.get('diss', 0):.0f} "
                      f"p={bd.get('phrase', 0):.1f} xr={bd.get('cross_rel', 0):.0f} "
                      f"sp={bd.get('spacing', 0):.0f} vc={bd.get('crossing', 0):.0f} "
                      f"iq={bd.get('iv_qual', 0):.1f} dp={bd.get('direct_perf', 0):.0f} "
                      f"ct={bd.get('contour', 0):.1f} ch={bd.get('chord', 0):.1f}]"
                      f"{'  run=' + str(rc) if rc > 2 else ''}")
        strength = corridors[i].beat_strength
        ct_str = ""
        if contour_targets is not None:
            ct_str = f"  arc={pitch_name(contour_targets[i]):4s}"
        print(f"  |{knot}b{b} [{strength:6s}]  "
              f"fol={pitch_name(p):4s}  ldr={pitch_name(lp):4s}  "
              f"{interval_name(iv):8s}({cons}){ct_str}"
              f"{motion}")
    print(f"  +--- end (cost {total_cost:.1f}) ---")

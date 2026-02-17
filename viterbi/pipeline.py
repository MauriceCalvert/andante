"""Pipeline: validate, build corridors, solve in one Viterbi pass."""
import logging

from viterbi.corridors import build_corridors
from viterbi.pathfinder import find_path
from viterbi.scale import interval_name, is_consonant, KeyInfo, CMAJ
from viterbi.mtypes import (
    ContourShape,
    ExistingVoice,
    Knot,
    PhraseResult,
    pitch_name,
)

_log: logging.Logger = logging.getLogger(__name__)


def solve_phrase(
    beat_grid: list[float],
    existing_voices: list[ExistingVoice],
    follower_knots: list[Knot],
    follower_low: int = 60,
    follower_high: int = 84,
    verbose: bool = False,
    key: KeyInfo = CMAJ,
    chord_pcs_per_beat: list[frozenset[int]] | None = None,
    beats_per_bar: float = 4.0,
    contour: ContourShape | None = None,
) -> PhraseResult:
    """Solve a complete phrase: validate, build corridors, pathfind."""
    assert len(follower_knots) >= 2, "Need at least 2 knots"
    assert all(follower_knots[i].beat < follower_knots[i + 1].beat
               for i in range(len(follower_knots) - 1)), "Knots must be in beat order"
    assert len(beat_grid) >= 2, "Need at least 2 beats in grid"
    assert abs(follower_knots[0].beat - beat_grid[0]) < 1e-6, "First knot must align with first beat"
    assert abs(follower_knots[-1].beat - beat_grid[-1]) < 1e-6, "Last knot must align with last beat"
    if chord_pcs_per_beat is not None:
        assert len(chord_pcs_per_beat) == len(beat_grid), (
            f"chord_pcs_per_beat length ({len(chord_pcs_per_beat)}) != "
            f"beat_grid length ({len(beat_grid)})"
        )
    # Validate that every beat in beat_grid has a pitch in every ExistingVoice
    for v_idx, voice in enumerate(existing_voices):
        for beat in beat_grid:
            assert beat in voice.pitches_at_beat, (
                f"ExistingVoice[{v_idx}] has no pitch at beat {beat}"
            )
    # Build a leader_map from first voice for validation and diagnostics
    leader_map: dict[float, int] = {}
    if existing_voices:
        leader_map = {beat: existing_voices[0].pitches_at_beat[beat] for beat in beat_grid}
    _validate_knots(follower_knots, leader_map)
    corridors = build_corridors(
        beat_grid=beat_grid,
        existing_voices=existing_voices,
        follower_low=follower_low,
        follower_high=follower_high,
        key=key,
        beats_per_bar=beats_per_bar,
    )
    final_pitch = follower_knots[-1].midi_pitch
    beats, pitches, total_cost = find_path(
        corridors=corridors,
        knots=follower_knots,
        final_pitch=final_pitch,
        phrase_length=len(beat_grid),
        existing_voices=existing_voices,
        verbose=verbose,
        key=key,
        chord_pcs_at=chord_pcs_per_beat,
        contour=contour,
    )
    if verbose:
        _print_phrase_summary(beats, pitches, leader_map, follower_knots)
    return PhraseResult(
        leader_notes=[],
        follower_knots=follower_knots,
        corridors=corridors,
        beats=beats,
        pitches=pitches,
        total_cost=total_cost,
    )


def _validate_knots(
    knots: list[Knot],
    leader_map: dict[float, int],
) -> None:
    """Warn if any knot is dissonant with the leader at that beat."""
    for k in knots:
        if k.beat not in leader_map:
            continue
        interval = abs(k.midi_pitch - leader_map[k.beat])
        if not is_consonant(interval):
            _log.debug(
                "knot %s dissonant with leader %s (interval %s)",
                k, pitch_name(leader_map[k.beat]), interval_name(interval),
            )


def _print_phrase_summary(
    beats: list[float],
    pitches: list[int],
    leader_map: dict[float, int],
    knots: list[Knot],
) -> None:
    """Print the complete phrase in a compact visual format."""
    knot_beats = {k.beat for k in knots}
    print("\n+==============================================================+")
    print("|                  COMPLETE PHRASE                              |")
    print("+==============================================================+")
    beat_strs = [f"{'b' + str(b):>6s}" for b in beats]
    print(f"| Beat    {'  '.join(beat_strs)}")
    leader_strs = [f"{pitch_name(leader_map.get(b, 0)):>6s}" for b in beats]
    print(f"| Leader  {'  '.join(leader_strs)}")
    follower_strs = []
    for b, p in zip(beats, pitches):
        marker = "*" if b in knot_beats else " "
        follower_strs.append(f"{marker + pitch_name(p):>6s}")
    print(f"| Follow  {'  '.join(follower_strs)}")
    iv_strs = []
    for b, p in zip(beats, pitches):
        lp = leader_map.get(b, 0)
        iv = abs(p - lp)
        flag = "." if is_consonant(iv) else "!"
        iv_strs.append(f"{interval_name(iv) + flag:>6s}")
    print(f"| Intvl   {'  '.join(iv_strs)}")
    motion_strs = ["     ."]
    for i in range(1, len(pitches)):
        f_dir = pitches[i] - pitches[i - 1]
        l_dir = leader_map.get(beats[i], 0) - leader_map.get(beats[i - 1], 0)
        if f_dir * l_dir < 0:
            m = "contr"
        elif f_dir == 0 or l_dir == 0:
            m = "obliq"
        elif f_dir * l_dir > 0:
            m = "simil"
        else:
            m = "     "
        motion_strs.append(f"{m:>6s}")
    print(f"| Motion  {'  '.join(motion_strs)}")
    print("+==============================================================+")

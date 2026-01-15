"""Virtuosic passage generation for fantasia episodes."""
from fractions import Fraction
from pathlib import Path

import yaml

from shared.pitch import FloatingNote, Pitch, Rest, wrap_degree
from shared.timed_material import TimedMaterial

DATA_DIR = Path(__file__).parent.parent / "data"
FIGURATIONS: dict = yaml.safe_load(open(DATA_DIR / "figurations.yaml", encoding="utf-8"))
SPAN_DEGREES: dict[str, int] = {"third": 2, "fifth": 4, "octave": 7, "two_octaves": 14}


def get_passage_for_episode(
    episode: str | None, phrase_index: int = 0, virtuosic: bool = False
) -> str | None:
    """Find passage pattern matching episode type, or None.

    Uses phrase_index to select among multiple matching figurations.
    Returns None if virtuosic=False (default), since passages are for virtuosic genres.
    """
    if not virtuosic:
        return None
    if episode is None:
        return None
    matches: list[str] = []
    for name, fig in FIGURATIONS.items():
        triggers: list[str] = fig.get("triggers", [])
        if episode in triggers:
            matches.append(name)
    if not matches:
        return None
    return matches[phrase_index % len(matches)]


def generate_scalar(
    start_degree: int, direction: str, span: str, note_count: int, phrase_index: int = 0
) -> tuple[Pitch, ...]:
    """Generate stepwise scale degrees with phrase-aware variation every segment."""
    span_size: int = SPAN_DEGREES.get(span, 7)
    pitches: list[Pitch] = []
    segment_size: int = span_size + 1
    segments: int = (note_count + segment_size - 1) // segment_size
    idx: int = 0
    direction_cycle: list[str] = ["up", "down", "up", "down"]
    start_offsets: list[int] = [0, 2, 4, 1, 3, 5, 6]
    phrase_dir_offset: int = phrase_index % len(direction_cycle)
    phrase_start_offset: int = (phrase_index * 3) % len(start_offsets)
    for seg in range(segments):
        seg_dir: str = direction_cycle[(seg + phrase_dir_offset) % len(direction_cycle)]
        if direction == "down":
            seg_dir = "down" if seg_dir == "up" else "up"
        seg_start: int = start_degree + start_offsets[(seg + phrase_start_offset) % len(start_offsets)]
        extra_var: int = (seg * phrase_index) % 4
        for j in range(segment_size):
            if idx >= note_count:
                break
            if seg_dir == "up":
                deg: int = seg_start + j + extra_var
            else:
                deg = seg_start + span_size - j + extra_var
            pitches.append(FloatingNote(wrap_degree(deg)))
            idx += 1
    return tuple(pitches)


def generate_arpeggiated(
    start_degree: int, direction: str, span: str, note_count: int, phrase_index: int = 0
) -> tuple[Pitch, ...]:
    """Generate arpeggio pattern with phrase-aware variation every segment."""
    chord_patterns: list[list[int]] = [
        [0, 2, 4, 7, 9, 11, 14],
        [0, 4, 7, 11, 14, 9, 2],
        [0, 7, 4, 11, 2, 9, 14],
        [0, 4, 2, 7, 4, 9, 7],
    ]
    pitches: list[Pitch] = []
    direction_cycle: list[str] = ["up", "down", "up", "down"]
    root_offsets: list[int] = [0, 3, 5, 2, 4, 1, 6]
    phrase_pattern_offset: int = phrase_index % len(chord_patterns)
    phrase_dir_offset: int = phrase_index % len(direction_cycle)
    phrase_root_offset: int = (phrase_index * 2) % len(root_offsets)
    idx: int = 0
    seg: int = 0
    while idx < note_count:
        chord_steps: list[int] = chord_patterns[(seg + phrase_pattern_offset) % len(chord_patterns)]
        seg_dir: str = direction_cycle[(seg + phrase_dir_offset) % len(direction_cycle)]
        if direction == "down":
            seg_dir = "down" if seg_dir == "up" else "up"
        seg_start: int = start_degree + root_offsets[(seg + phrase_root_offset) % len(root_offsets)]
        extra_var: int = (seg * phrase_index) % 3
        for j in range(len(chord_steps)):
            if idx >= note_count:
                break
            if seg_dir == "up":
                step: int = chord_steps[j] + extra_var
            else:
                step = chord_steps[len(chord_steps) - 1 - j] + extra_var
            deg: int = seg_start + step
            pitches.append(FloatingNote(wrap_degree(deg)))
            idx += 1
        seg += 1
    return tuple(pitches)


def generate_tremolo(
    start_degree: int, interval: int, note_count: int, phrase_index: int = 0
) -> tuple[Pitch, ...]:
    """Generate alternating tremolo pattern with phrase-aware variation.

    Limits alternations to 6 notes per segment to avoid endless_trill detection.
    """
    pitches: list[Pitch] = []
    intervals: list[int] = [interval, interval + 1, interval - 1, interval + 2]
    root_shifts: list[int] = [0, 2, -1, 3, 1, -2]
    phrase_interval_offset: int = phrase_index % len(intervals)
    phrase_root_offset: int = (phrase_index * 2) % len(root_shifts)
    seg_size: int = 6
    idx: int = 0
    seg: int = 0
    while idx < note_count:
        seg_start: int = start_degree + root_shifts[(seg + phrase_root_offset) % len(root_shifts)]
        seg_interval: int = intervals[(seg + phrase_interval_offset) % len(intervals)]
        upper: int = seg_start + seg_interval
        intra_var: int = (seg + phrase_index) % 3
        for j in range(seg_size):
            if idx >= note_count:
                break
            if j < 4:
                deg: int = seg_start if j % 2 == 0 else upper
            else:
                deg = seg_start + intra_var + (j - 4)
            pitches.append(FloatingNote(wrap_degree(deg)))
            idx += 1
        seg += 1
    return tuple(pitches)


def _count_consecutive(pitches: list[Pitch]) -> int:
    """Count maximum consecutive same degrees."""
    if len(pitches) < 2:
        return 1
    max_consec: int = 1
    consec: int = 1
    prev: int = pitches[0].degree if hasattr(pitches[0], 'degree') else -99
    for p in pitches[1:]:
        curr: int = p.degree if hasattr(p, 'degree') else -99
        if curr == prev:
            consec += 1
            max_consec = max(max_consec, consec)
        else:
            consec = 1
        prev = curr
    return max_consec


def generate_broken(
    start_degree: int, pattern: list[int], note_count: int, phrase_index: int = 0
) -> tuple[Pitch, ...]:
    """Generate broken interval pattern with phrase-aware variation every segment.

    Avoids more than 3 consecutive same degrees.
    """
    patterns: list[list[int]] = [
        pattern,
        [p + 2 for p in pattern],
        [pattern[i] + (i % 3) for i in range(len(pattern))],
        list(reversed(pattern)),
    ]
    root_shifts: list[int] = [0, 3, 1, 4, 2, 5]
    phrase_pattern_offset: int = phrase_index % len(patterns)
    phrase_root_offset: int = (phrase_index * 2) % len(root_shifts)
    pitches: list[Pitch] = []
    seg_size: int = len(pattern) * 2
    idx: int = 0
    seg: int = 0
    max_consecutive: int = 3
    while idx < note_count:
        seg_pattern: list[int] = patterns[(seg + phrase_pattern_offset) % len(patterns)]
        seg_start: int = start_degree + root_shifts[(seg + phrase_root_offset) % len(root_shifts)]
        extra_var: int = (seg * phrase_index) % 3
        for j in range(seg_size):
            if idx >= note_count:
                break
            step: int = seg_pattern[j % len(seg_pattern)] + extra_var
            deg: int = seg_start + step
            candidate: FloatingNote = FloatingNote(wrap_degree(deg))
            if pitches and _count_consecutive(pitches + [candidate]) > max_consecutive:
                deg = seg_start + step + 1
                candidate = FloatingNote(wrap_degree(deg))
            pitches.append(candidate)
            idx += 1
        seg += 1
    return tuple(pitches)


STANDARD_DURATIONS: tuple[Fraction, ...] = (
    Fraction(1, 16), Fraction(1, 8), Fraction(3, 16), Fraction(1, 4),
    Fraction(3, 8), Fraction(1, 2), Fraction(3, 4), Fraction(1, 1),
)


def quantize_duration(dur: Fraction) -> Fraction:
    """Quantize to nearest standard rhythmic value (power of 2 division)."""
    best: Fraction = STANDARD_DURATIONS[0]
    best_diff: Fraction = abs(dur - best)
    for s in STANDARD_DURATIONS[1:]:
        diff: Fraction = abs(dur - s)
        if diff < best_diff:
            best = s
            best_diff = diff
    return best


def generate_varied_durations(base_dur: Fraction, count: int, fig_type: str) -> tuple[Fraction, ...]:
    """Generate rhythmically varied durations using only standard values."""
    base_q: Fraction = quantize_duration(base_dur)
    if fig_type == "tremolo":
        return tuple(base_q for _ in range(count))
    patterns: dict[str, list[int]] = {
        "scalar": [1, 1, 1, 2, 1, 1, 2, 1],
        "arpeggiated": [2, 1, 1, 2, 1, 1, 1, 1],
        "broken": [1, 1, 2, 1, 1, 1, 2, 1],
    }
    pattern: list[int] = patterns.get(fig_type, [1, 1, 1, 1])
    result: list[Fraction] = []
    for i in range(count):
        weight: int = pattern[i % len(pattern)]
        result.append(base_q * weight)
    return tuple(result)


def generate_passage(
    passage_name: str, budget: Fraction, start_degree: int, phrase_index: int = 0
) -> TimedMaterial:
    """Generate virtuosic passage pattern to fill budget exactly.

    phrase_index varies both starting degree and internal patterns for variety.
    Uses only standard rhythmic values (1/16, 1/8, etc.).
    """
    assert passage_name in FIGURATIONS, f"Unknown passage: {passage_name}"
    fig: dict = FIGURATIONS[passage_name]
    fig_type: str = fig.get("type", "scalar")
    degrees_per_beat: int = fig.get("degrees_per_beat", 4)
    beats: int = int(budget * 4)
    note_count: int = max(1, beats * degrees_per_beat)
    base_dur: Fraction = budget / note_count
    base_q: Fraction = quantize_duration(base_dur)
    actual_count: int = max(1, int(budget / base_q))
    varied_start: int = start_degree + phrase_index
    if fig_type == "scalar":
        direction: str = fig.get("direction", "up")
        span: str = fig.get("span", "octave")
        pitches: tuple[Pitch, ...] = generate_scalar(varied_start, direction, span, actual_count, phrase_index)
    elif fig_type == "arpeggiated":
        direction = fig.get("direction", "up")
        span = fig.get("span", "two_octaves")
        pitches = generate_arpeggiated(varied_start, direction, span, actual_count, phrase_index)
    elif fig_type == "tremolo":
        interval: int = fig.get("interval", 2)
        pitches = generate_tremolo(varied_start, interval, actual_count, phrase_index)
    elif fig_type == "broken":
        pattern: list[int] = fig.get("pattern", [0, 2, 1, 3])
        pitches = generate_broken(varied_start, pattern, actual_count, phrase_index)
    else:
        pitches = generate_scalar(varied_start, "up", "octave", actual_count, phrase_index)
    durations: list[Fraction] = list(generate_varied_durations(base_q, len(pitches), fig_type))
    total: Fraction = sum(durations)
    if total < budget:
        durations[-1] += budget - total
    elif total > budget:
        excess: Fraction = total - budget
        for i in range(len(durations) - 1, -1, -1):
            if durations[i] > excess:
                durations[i] -= excess
                break
            excess -= durations[i]
            durations[i] = Fraction(0)
        durations = [d for d in durations if d > 0]
        pitches = pitches[:len(durations)]
    return TimedMaterial(tuple(pitches), tuple(durations), budget)

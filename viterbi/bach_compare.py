"""Compare Viterbi solver output against Bach's actual bass lines."""
import csv
import statistics
from pathlib import Path
from fractions import Fraction
from collections import Counter

from viterbi.pipeline import solve_phrase
from viterbi.mtypes import ExistingVoice, Knot, LeaderNote, pitch_name
from viterbi.scale import KeyInfo, is_consonant, scale_degree_distance, CMAJ


# ---------------------------------------------------------------------------
# Krumhansl-Schmuckler key profiles
# ---------------------------------------------------------------------------

MAJOR_PROFILE = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
MINOR_PROFILE = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]

# Scale pitch class sets for all 24 keys
MAJOR_SCALES = {
    0: frozenset({0, 2, 4, 5, 7, 9, 11}),      # C major
    1: frozenset({1, 3, 5, 6, 8, 10, 0}),      # Db major
    2: frozenset({2, 4, 6, 7, 9, 11, 1}),      # D major
    3: frozenset({3, 5, 7, 8, 10, 0, 2}),      # Eb major
    4: frozenset({4, 6, 8, 9, 11, 1, 3}),      # E major
    5: frozenset({5, 7, 9, 10, 0, 2, 4}),      # F major
    6: frozenset({6, 8, 10, 11, 1, 3, 5}),     # F# major
    7: frozenset({7, 9, 11, 0, 2, 4, 6}),      # G major
    8: frozenset({8, 10, 0, 1, 3, 5, 7}),      # Ab major
    9: frozenset({9, 11, 1, 2, 4, 6, 8}),      # A major
    10: frozenset({10, 0, 2, 3, 5, 7, 9}),     # Bb major
    11: frozenset({11, 1, 3, 4, 6, 8, 10}),    # B major
}

MINOR_SCALES = {
    0: frozenset({0, 2, 3, 5, 7, 8, 10}),      # C minor
    1: frozenset({1, 3, 4, 6, 8, 9, 11}),      # C# minor
    2: frozenset({2, 4, 5, 7, 9, 10, 0}),      # D minor
    3: frozenset({3, 5, 6, 8, 10, 11, 1}),     # Eb minor
    4: frozenset({4, 6, 7, 9, 11, 0, 2}),      # E minor
    5: frozenset({5, 7, 8, 10, 0, 1, 3}),      # F minor
    6: frozenset({6, 8, 9, 11, 1, 2, 4}),      # F# minor
    7: frozenset({7, 9, 10, 0, 2, 3, 5}),      # G minor
    8: frozenset({8, 10, 11, 1, 3, 4, 6}),     # G# minor
    9: frozenset({9, 11, 0, 2, 4, 5, 7}),      # A minor
    10: frozenset({10, 0, 1, 3, 5, 6, 8}),     # Bb minor
    11: frozenset({11, 1, 2, 4, 6, 7, 9}),     # B minor
}

KEY_NAMES = {
    (0, True): "C maj", (0, False): "C min",
    (1, True): "Db maj", (1, False): "C# min",
    (2, True): "D maj", (2, False): "D min",
    (3, True): "Eb maj", (3, False): "Eb min",
    (4, True): "E maj", (4, False): "E min",
    (5, True): "F maj", (5, False): "F min",
    (6, True): "F# maj", (6, False): "F# min",
    (7, True): "G maj", (7, False): "G min",
    (8, True): "Ab maj", (8, False): "G# min",
    (9, True): "A maj", (9, False): "A min",
    (10, True): "Bb maj", (10, False): "Bb min",
    (11, True): "B maj", (11, False): "B min",
}


# ---------------------------------------------------------------------------
# Note file parsing
# ---------------------------------------------------------------------------

def parse_note_file(path: Path) -> list[dict]:
    """Parse .note CSV file, return list of note dicts."""
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        notes = []
        for row in reader:
            notes.append({
                'offset': float(row['offset']),
                'midinote': int(row['midinote']),
                'duration': Fraction(row['duration']),
                'track': int(row['track']),
                'bar': int(row['bar']) if row['bar'] else None,
                'beat': float(row['beat']) if row['beat'] else None,
            })
        return notes


def detect_key(notes: list[dict]) -> KeyInfo:
    """Detect key using Krumhansl-Schmuckler algorithm."""
    # Build pitch class histogram
    pc_histogram = [0] * 12
    for note in notes:
        pc = note['midinote'] % 12
        pc_histogram[pc] += 1

    # Normalize histogram
    total = sum(pc_histogram)
    if total == 0:
        return CMAJ
    pc_histogram = [count / total for count in pc_histogram]

    # Correlate with all 24 key profiles
    best_correlation = -float('inf')
    best_key = (0, True)  # (tonic_pc, is_major)

    for tonic_pc in range(12):
        for is_major in [True, False]:
            profile = MAJOR_PROFILE if is_major else MINOR_PROFILE
            # Rotate profile to align with tonic
            rotated = profile[tonic_pc:] + profile[:tonic_pc]
            # Pearson correlation
            mean_hist = statistics.mean(pc_histogram)
            mean_prof = statistics.mean(rotated)
            numerator = sum((h - mean_hist) * (p - mean_prof)
                          for h, p in zip(pc_histogram, rotated))
            denom_hist = sum((h - mean_hist) ** 2 for h in pc_histogram) ** 0.5
            denom_prof = sum((p - mean_prof) ** 2 for p in rotated) ** 0.5
            if denom_hist == 0 or denom_prof == 0:
                correlation = 0
            else:
                correlation = numerator / (denom_hist * denom_prof)

            if correlation > best_correlation:
                best_correlation = correlation
                best_key = (tonic_pc, is_major)

    tonic_pc, is_major = best_key
    pitch_class_set = MAJOR_SCALES[tonic_pc] if is_major else MINOR_SCALES[tonic_pc]
    return KeyInfo(pitch_class_set=pitch_class_set, tonic_pc=tonic_pc)


def identify_tracks(notes: list[dict]) -> tuple[int, int]:
    """Identify soprano (high) and bass (low) tracks by median pitch."""
    tracks = {}
    for note in notes:
        track = note['track']
        if track not in tracks:
            tracks[track] = []
        tracks[track].append(note['midinote'])

    assert len(tracks) == 2, f"Expected 2 tracks, got {len(tracks)}"

    track_medians = {t: statistics.median(pitches) for t, pitches in tracks.items()}
    sorted_tracks = sorted(track_medians.items(), key=lambda x: x[1])
    bass_track = sorted_tracks[0][0]
    soprano_track = sorted_tracks[1][0]

    return soprano_track, bass_track


QUAVER_IN_WHOLE_NOTES = 0.125  # 1/8 of a whole note

def build_monophonic_grid(
    notes: list[dict],
    soprano_track: int,
    bass_track: int,
    grid_step: float = QUAVER_IN_WHOLE_NOTES,
) -> tuple[list[float], list[int], list[int]]:
    """Build quaver grid with monophonic soprano and bass."""
    # Find extent
    first_onset = min(n['offset'] for n in notes)
    last_onset = max(n['offset'] for n in notes)

    # Build grid
    grid_beats = []
    beat = first_onset
    while beat <= last_onset:
        grid_beats.append(beat)
        beat += grid_step

    # Extract soprano and bass at each grid position
    soprano_line = []
    bass_line = []

    for grid_pos in grid_beats:
        # Find all notes sounding at grid_pos
        soprano_pitches = []
        bass_pitches = []

        for note in notes:
            onset = note['offset']
            offset_end = onset + float(note['duration'])
            if onset <= grid_pos < offset_end:
                if note['track'] == soprano_track:
                    soprano_pitches.append(note['midinote'])
                elif note['track'] == bass_track:
                    bass_pitches.append(note['midinote'])

        # Soprano: highest pitch, bass: lowest pitch
        if soprano_pitches:
            soprano_line.append(max(soprano_pitches))
        elif soprano_line:
            soprano_line.append(soprano_line[-1])  # sustain
        else:
            soprano_line.append(60)  # arbitrary default

        if bass_pitches:
            bass_line.append(min(bass_pitches))
        elif bass_line:
            bass_line.append(bass_line[-1])  # sustain
        else:
            bass_line.append(48)  # arbitrary default

    return grid_beats, soprano_line, bass_line


def extract_knots(
    grid_beats: list[float],
    bass_line: list[int],
    notes: list[dict],
    bass_track: int,
) -> list[Knot]:
    """Extract knots at bar downbeats from Bach's bass."""
    # Find bar downbeats from notes
    bar_offsets = set()
    for note in notes:
        if note['bar'] is not None and note['beat'] is not None:
            if abs(note['beat'] - 1.0) < 0.01:  # downbeat
                bar_offsets.add(note['offset'])

    bar_offsets = sorted(bar_offsets)

    knots = []

    # First grid position is always a knot
    knots.append(Knot(beat=grid_beats[0], midi_pitch=bass_line[0]))

    # Add knots at bar downbeats
    for bar_offset in bar_offsets:
        # Find closest grid position
        closest_idx = min(range(len(grid_beats)),
                         key=lambda i: abs(grid_beats[i] - bar_offset))
        grid_beat = grid_beats[closest_idx]
        bass_pitch = bass_line[closest_idx]

        # Only add if not duplicate and not first/last
        if grid_beat != grid_beats[0] and grid_beat != grid_beats[-1]:
            if not knots or knots[-1].beat != grid_beat:
                knots.append(Knot(beat=grid_beat, midi_pitch=bass_pitch))

    # Last grid position is always a knot
    if not knots or knots[-1].beat != grid_beats[-1]:
        knots.append(Knot(beat=grid_beats[-1], midi_pitch=bass_line[-1]))

    return knots


# ---------------------------------------------------------------------------
# Comparison metrics
# ---------------------------------------------------------------------------

def motion_type(p1: int, p2: int, l1: int, l2: int) -> str:
    """Classify relative motion between voices."""
    f_dir = p2 - p1
    l_dir = l2 - l1
    if f_dir * l_dir < 0:
        return "contrary"
    if f_dir == 0 and l_dir == 0:
        return "static"
    if f_dir == 0 or l_dir == 0:
        return "oblique"
    return "similar"


def compute_metrics(
    grid_beats: list[float],
    soprano_line: list[int],
    bach_bass: list[int],
    vit_bass: list[int],
    key: KeyInfo,
) -> dict:
    """Compute comparison metrics between solver and Bach."""
    n = len(grid_beats)
    assert len(soprano_line) == n
    assert len(bach_bass) == n
    assert len(vit_bass) == n

    exact_matches = 0
    pc_matches = 0
    interval_matches = 0
    direction_matches = 0
    motion_matches = 0
    abs_errors = []
    consonances = 0
    strong_beats = 0

    for i in range(n):
        sop = soprano_line[i]
        bach = bach_bass[i]
        vit = vit_bass[i]

        # Exact match
        if bach == vit:
            exact_matches += 1

        # Pitch class match
        if (bach % 12) == (vit % 12):
            pc_matches += 1

        # Interval match (mod 12)
        bach_iv = abs(bach - sop) % 12
        vit_iv = abs(vit - sop) % 12
        if bach_iv == vit_iv:
            interval_matches += 1

        # Step direction
        if i > 0:
            bach_dir = bach - bach_bass[i - 1]
            vit_dir = vit - vit_bass[i - 1]
            if (bach_dir > 0 and vit_dir > 0) or \
               (bach_dir < 0 and vit_dir < 0) or \
               (bach_dir == 0 and vit_dir == 0):
                direction_matches += 1

        # Motion type
        if i > 0:
            bach_motion = motion_type(
                bach_bass[i - 1], bach,
                soprano_line[i - 1], sop
            )
            vit_motion = motion_type(
                vit_bass[i - 1], vit,
                soprano_line[i - 1], sop
            )
            if bach_motion == vit_motion:
                motion_matches += 1

        # Absolute error
        abs_errors.append(abs(bach - vit))

        # Consonance on strong beats (downbeats: every 4 quavers in 4/4)
        # Simplified: consider every 4th grid position as strong
        if i % 4 == 0:
            strong_beats += 1
            vit_interval = abs(vit - sop)
            if is_consonant(vit_interval):
                consonances += 1

    metrics = {
        'exact_pct': 100.0 * exact_matches / n if n > 0 else 0,
        'pc_pct': 100.0 * pc_matches / n if n > 0 else 0,
        'interval_pct': 100.0 * interval_matches / n if n > 0 else 0,
        'direction_pct': 100.0 * direction_matches / (n - 1) if n > 1 else 0,
        'motion_pct': 100.0 * motion_matches / (n - 1) if n > 1 else 0,
        'mae': statistics.mean(abs_errors) if abs_errors else 0,
        'consonance_pct': 100.0 * consonances / strong_beats if strong_beats > 0 else 0,
        'grid_length': n,
    }

    return metrics


def write_comparison_file(
    output_dir: Path,
    bwv: str,
    grid_beats: list[float],
    soprano_line: list[int],
    bach_bass: list[int],
    vit_bass: list[int],
) -> None:
    """Write side-by-side comparison to file."""
    output_path = output_dir / f"compare_{bwv}.txt"

    with open(output_path, 'w') as f:
        f.write(f"pos      soprano  bach_bass  vit_bass  match  iv_bach  iv_vit   motion\n")
        f.write("-" * 80 + "\n")

        for i, (beat, sop, bach, vit) in enumerate(
            zip(grid_beats, soprano_line, bach_bass, vit_bass)
        ):
            match = "=" if bach == vit else "."

            bach_iv = abs(bach - sop)
            vit_iv = abs(vit - sop)

            from viterbi.scale import interval_name
            bach_iv_name = interval_name(bach_iv)
            vit_iv_name = interval_name(vit_iv)

            if i == 0:
                motion = "-"
            else:
                motion = motion_type(
                    bach_bass[i - 1], bach,
                    soprano_line[i - 1], sop
                )[:5]

            f.write(f"{beat:<8.2f} {pitch_name(sop):<8s} {pitch_name(bach):<10s} "
                   f"{pitch_name(vit):<9s} {match:<6s} {bach_iv_name:<8s} "
                   f"{vit_iv_name:<8s} {motion}\n")


# ---------------------------------------------------------------------------
# Main comparison
# ---------------------------------------------------------------------------

def compare_piece(note_path: Path, output_dir: Path) -> dict | None:
    """Run solver on one piece, return metrics or None if failed."""
    bwv = note_path.stem
    print(f"Processing {bwv}...", end=" ", flush=True)

    try:
        # Parse
        notes = parse_note_file(note_path)

        # Detect key
        key = detect_key(notes)
        key_name = KEY_NAMES.get((key.tonic_pc,
                                  MAJOR_SCALES.get(key.tonic_pc) == key.pitch_class_set),
                                 "unknown")

        # Identify tracks
        soprano_track, bass_track = identify_tracks(notes)

        # Build grid
        grid_beats, soprano_line, bach_bass = build_monophonic_grid(
            notes, soprano_track, bass_track
        )

        # Extract knots
        knots = extract_knots(grid_beats, bach_bass, notes, bass_track)

        # Build ExistingVoice from soprano
        soprano_voice = ExistingVoice(
            pitches_at_beat={b: p for b, p in zip(grid_beats, soprano_line)},
            is_above=True,
        )

        # Determine bass range
        bass_low = min(bach_bass) - 2
        bass_high = max(bach_bass) + 2

        # Solve (in segments if too long)
        segment_size = 32
        stride = segment_size - 1  # overlap by 1
        if len(grid_beats) > 64:
            # Solve in overlapping segments
            vit_bass = []
            i = 0
            while i < len(grid_beats):
                end = min(i + segment_size, len(grid_beats))
                # Absorb tiny trailing segment into this one
                remaining = len(grid_beats) - end
                if 0 < remaining < 3:
                    end = len(grid_beats)
                seg_beats = grid_beats[i:end]
                seg_voice = ExistingVoice(
                    pitches_at_beat={b: soprano_voice.pitches_at_beat[b] for b in seg_beats},
                    is_above=True,
                )
                seg_knots = [k for k in knots if grid_beats[i] <= k.beat <= grid_beats[end - 1]]
                # Ensure first and last are knots
                if not seg_knots or seg_knots[0].beat != grid_beats[i]:
                    seg_knots.insert(0, Knot(beat=grid_beats[i], midi_pitch=bach_bass[i]))
                if seg_knots[-1].beat != grid_beats[end - 1]:
                    seg_knots.append(Knot(beat=grid_beats[end - 1], midi_pitch=bach_bass[end - 1]))
                result = solve_phrase(
                    seg_beats,
                    [seg_voice],
                    seg_knots,
                    bass_low,
                    bass_high,
                    verbose=False,
                    key=key,
                )
                # Skip first pitch if not first segment (avoid duplication at knot)
                start_idx = 1 if i > 0 else 0
                vit_bass.extend(result.pitches[start_idx:])
                i += stride
                if end == len(grid_beats):
                    break
        else:
            result = solve_phrase(
                grid_beats,
                [soprano_voice],
                knots,
                bass_low,
                bass_high,
                verbose=False,
                key=key,
            )
            vit_bass = result.pitches

        # Compute metrics
        metrics = compute_metrics(grid_beats, soprano_line, bach_bass, vit_bass, key)

        # Write comparison file
        write_comparison_file(output_dir, bwv, grid_beats,
                            soprano_line, bach_bass, vit_bass)

        print(f"OK")

        return {
            'bwv': bwv,
            'key': key_name,
            **metrics,
        }

    except Exception as e:
        print(f"FAIL: {e}")
        return None


def main() -> None:
    """Run comparison on all Bach samples."""
    samples_dir = Path("viterbi/bachsamples")
    output_dir = Path("viterbi/output")
    output_dir.mkdir(exist_ok=True)

    note_files = sorted(samples_dir.glob("*.note"))

    print(f"Found {len(note_files)} Bach pieces\n")

    results = []
    for note_path in note_files:
        result = compare_piece(note_path, output_dir)
        if result:
            results.append(result)

    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"{'BWV':<15s} {'Key':<8s} {'Grid':<6s} {'Exact%':<8s} {'PC%':<8s} "
          f"{'Iv%':<8s} {'Dir%':<8s} {'Mot%':<8s} {'MAE':<6s} {'Cons%':<8s}")
    print("-" * 90)

    for r in results:
        print(f"{r['bwv']:<15s} {r['key']:<8s} {r['grid_length']:<6d} "
              f"{r['exact_pct']:<8.1f} {r['pc_pct']:<8.1f} {r['interval_pct']:<8.1f} "
              f"{r['direction_pct']:<8.1f} {r['motion_pct']:<8.1f} "
              f"{r['mae']:<6.1f} {r['consonance_pct']:<8.1f}")

    print("-" * 90)

    # Aggregate
    if results:
        agg = {
            'exact_pct': statistics.mean(r['exact_pct'] for r in results),
            'pc_pct': statistics.mean(r['pc_pct'] for r in results),
            'interval_pct': statistics.mean(r['interval_pct'] for r in results),
            'direction_pct': statistics.mean(r['direction_pct'] for r in results),
            'motion_pct': statistics.mean(r['motion_pct'] for r in results),
            'mae': statistics.mean(r['mae'] for r in results),
            'consonance_pct': statistics.mean(r['consonance_pct'] for r in results),
            'total_grid': sum(r['grid_length'] for r in results),
        }

        print(f"{'AGGREGATE':<15s} {'':<8s} {agg['total_grid']:<6d} "
              f"{agg['exact_pct']:<8.1f} {agg['pc_pct']:<8.1f} {agg['interval_pct']:<8.1f} "
              f"{agg['direction_pct']:<8.1f} {agg['motion_pct']:<8.1f} "
              f"{agg['mae']:<6.1f} {agg['consonance_pct']:<8.1f}")
        print("=" * 90)

    # Write full results
    results_path = output_dir / "bach_results.txt"
    with open(results_path, 'w') as f:
        f.write("Bach Comparison Results\n")
        f.write("=" * 90 + "\n\n")
        f.write(f"{'BWV':<15s} {'Key':<8s} {'Grid':<6s} {'Exact%':<8s} {'PC%':<8s} "
                f"{'Iv%':<8s} {'Dir%':<8s} {'Mot%':<8s} {'MAE':<6s} {'Cons%':<8s}\n")
        f.write("-" * 90 + "\n")

        for r in results:
            f.write(f"{r['bwv']:<15s} {r['key']:<8s} {r['grid_length']:<6d} "
                   f"{r['exact_pct']:<8.1f} {r['pc_pct']:<8.1f} {r['interval_pct']:<8.1f} "
                   f"{r['direction_pct']:<8.1f} {r['motion_pct']:<8.1f} "
                   f"{r['mae']:<6.1f} {r['consonance_pct']:<8.1f}\n")

        f.write("-" * 90 + "\n")

        if results:
            f.write(f"{'AGGREGATE':<15s} {'':<8s} {agg['total_grid']:<6d} "
                   f"{agg['exact_pct']:<8.1f} {agg['pc_pct']:<8.1f} {agg['interval_pct']:<8.1f} "
                   f"{agg['direction_pct']:<8.1f} {agg['motion_pct']:<8.1f} "
                   f"{agg['mae']:<6.1f} {agg['consonance_pct']:<8.1f}\n")

    print(f"\nFull results written to {results_path}")
    print(f"Per-piece comparisons written to {output_dir}/compare_*.txt")


if __name__ == "__main__":
    main()

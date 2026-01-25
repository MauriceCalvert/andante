"""Analyse melodic interval frequencies from baroque corpus."""
import csv
from collections import Counter
from pathlib import Path

INTERVAL_NAMES = {
    0: 'unison',
    1: 'minor 2nd',
    2: 'major 2nd',
    3: 'minor 3rd',
    4: 'major 3rd',
    5: 'perfect 4th',
    6: 'tritone',
    7: 'perfect 5th',
    8: 'minor 6th',
    9: 'major 6th',
    10: 'minor 7th',
    11: 'major 7th',
    12: 'octave',
}

def load_notes(path: Path) -> list[dict]:
    """Load notes from CSV file."""
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def compute_intervals(notes: list[dict], track: int | None = None) -> list[int]:
    """Compute successive melodic intervals for a track (or all tracks if None)."""
    if track is not None:
        notes = [n for n in notes if int(n['track']) == track]
    # Sort by offset, then by midinote (for simultaneous notes)
    notes = sorted(notes, key=lambda n: (float(n['offset']), int(n['midinote'])))
    # Group by offset to handle chords
    intervals = []
    prev_offset = None
    prev_pitches = []
    for note in notes:
        offset = float(note['offset'])
        pitch = int(note['midinote'])
        if prev_offset is not None and offset > prev_offset:
            # New time point - compute intervals from previous pitches to current
            # For melodic analysis, use the highest previous pitch to current highest
            if prev_pitches:
                # Simple approach: interval from highest of prev to current pitch
                intervals.append(abs(pitch - max(prev_pitches)))
        if prev_offset is None or offset > prev_offset:
            prev_pitches = [pitch]
            prev_offset = offset
        else:
            prev_pitches.append(pitch)
    return intervals

def compute_intervals_per_voice(notes: list[dict], track: int) -> list[int]:
    """Compute successive intervals within a single voice/track."""
    track_notes = [n for n in notes if int(n['track']) == track]
    track_notes = sorted(track_notes, key=lambda n: float(n['offset']))
    intervals = []
    prev_pitch = None
    prev_offset = None
    for note in track_notes:
        offset = float(note['offset'])
        pitch = int(note['midinote'])
        # Skip simultaneous notes in same track (chord tones)
        if prev_offset is not None and offset > prev_offset:
            intervals.append(abs(pitch - prev_pitch))
        prev_pitch = pitch
        prev_offset = offset
    return intervals

def interval_name(semitones: int) -> str:
    """Return interval name."""
    if semitones <= 12:
        return INTERVAL_NAMES.get(semitones, f'{semitones} semitones')
    return f'{semitones} semitones'

def classify_interval(semitones: int) -> str:
    """Classify interval into step/skip/leap categories."""
    if semitones == 0:
        return 'unison'
    elif semitones <= 2:
        return 'step'
    elif semitones <= 4:
        return 'skip'
    elif semitones <= 7:
        return 'leap'
    else:
        return 'large_leap'

def find_highest_track(notes: list[dict]) -> int:
    """Find track with highest average MIDI pitch."""
    track_pitches: dict[int, list[int]] = {}
    for note in notes:
        track = int(note['track'])
        pitch = int(note['midinote'])
        if track not in track_pitches:
            track_pitches[track] = []
        track_pitches[track].append(pitch)
    track_avgs = {t: sum(p) / len(p) for t, p in track_pitches.items()}
    return max(track_avgs, key=track_avgs.get)

def compute_tessitura_deviations(notes: list[dict], track: int) -> tuple[list[int], int, int, int]:
    """Compute distance from median for each note in track.
    
    Returns:
        (deviations, median, min_pitch, max_pitch)
    """
    track_notes = [n for n in notes if int(n['track']) == track]
    pitches = sorted(int(n['midinote']) for n in track_notes)
    median = pitches[len(pitches) // 2]
    deviations = [abs(p - median) for p in pitches]
    return deviations, median, min(pitches), max(pitches)

def analyse_file(path: Path) -> dict:
    """Analyse a single file (highest track only)."""
    notes = load_notes(path)
    top_track = find_highest_track(notes)
    track_notes = [n for n in notes if int(n['track']) == top_track]
    avg_pitch = sum(int(n['midinote']) for n in track_notes) / len(track_notes)
    intervals = compute_intervals_per_voice(notes, top_track)
    deviations, median, min_pitch, max_pitch = compute_tessitura_deviations(notes, top_track)
    return {
        'file': path.stem,
        'track': top_track,
        'avg_pitch': avg_pitch,
        'median_pitch': median,
        'min_pitch': min_pitch,
        'max_pitch': max_pitch,
        'range': max_pitch - min_pitch,
        'count': len(intervals),
        'intervals': Counter(intervals),
        'deviations': Counter(deviations),
        'note_count': len(deviations),
    }

def print_distribution(intervals: Counter, total: int) -> None:
    """Print interval distribution."""
    # By semitones
    print("\n  By semitones:")
    for i in range(13):
        count = intervals.get(i, 0)
        pct = 100 * count / total if total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"    {i:2d} ({interval_name(i):12s}): {count:5d} ({pct:5.1f}%) {bar}")
    # Larger intervals
    large = sum(c for i, c in intervals.items() if i > 12)
    if large > 0:
        pct = 100 * large / total
        print(f"    >12 (compound)       : {large:5d} ({pct:5.1f}%)")
    # By category
    print("\n  By category:")
    categories = Counter()
    for i, count in intervals.items():
        categories[classify_interval(i)] += count
    for cat in ['unison', 'step', 'skip', 'leap', 'large_leap']:
        count = categories.get(cat, 0)
        pct = 100 * count / total if total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"    {cat:12s}: {count:5d} ({pct:5.1f}%) {bar}")

def print_tessitura_distribution(deviations: Counter, total: int) -> None:
    """Print tessitura deviation distribution."""
    print("\n  Distance from median (semitones):")
    max_dev = max(deviations.keys()) if deviations else 0
    for i in range(min(max_dev + 1, 16)):
        count = deviations.get(i, 0)
        pct = 100 * count / total if total > 0 else 0
        bar = '#' * int(pct / 2)
        print(f"    {i:2d}: {count:5d} ({pct:5.1f}%) {bar}")
    beyond = sum(c for d, c in deviations.items() if d >= 16)
    if beyond > 0:
        pct = 100 * beyond / total
        print(f"   >15: {beyond:5d} ({pct:5.1f}%)")
    # Cumulative percentages
    print("\n  Cumulative (% within N semitones of median):")
    cumulative = 0
    for threshold in [3, 5, 7, 9, 12]:
        cumulative = sum(c for d, c in deviations.items() if d <= threshold)
        pct = 100 * cumulative / total if total > 0 else 0
        print(f"    <={threshold:2d}: {pct:5.1f}%")

def main() -> None:
    """Main entry point."""
    freq_dir = Path(__file__).parent
    note_files = sorted(freq_dir.glob('*.note'))
    all_intervals = Counter()
    all_deviations = Counter()
    total_intervals = 0
    total_notes = 0
    all_ranges = []
    print("=" * 70)
    print("BAROQUE CORPUS INTERVAL ANALYSIS")
    print("=" * 70)
    for path in note_files:
        results = analyse_file(path)
        print(f"\n{results['file'].upper()}")
        print("-" * 40)
        print(f"  Track {results['track']} (median: {results['median_pitch']}, range: {results['min_pitch']}-{results['max_pitch']} = {results['range']} semitones)")
        file_intervals = results['intervals']
        file_count = results['count']
        all_intervals.update(file_intervals)
        total_intervals += file_count
        all_deviations.update(results['deviations'])
        total_notes += results['note_count']
        all_ranges.append(results['range'])
        print(f"  Intervals: {file_count}, Notes: {results['note_count']}")
        print_distribution(file_intervals, file_count)
        print_tessitura_distribution(results['deviations'], results['note_count'])
    print("\n" + "=" * 70)
    print("AGGREGATE INTERVALS (ALL FILES)")
    print("=" * 70)
    print(f"  Total intervals: {total_intervals}")
    print_distribution(all_intervals, total_intervals)
    print("\n" + "=" * 70)
    print("AGGREGATE TESSITURA (ALL FILES)")
    print("=" * 70)
    print(f"  Total notes: {total_notes}")
    print(f"  Range across pieces: {min(all_ranges)}-{max(all_ranges)} semitones (avg: {sum(all_ranges)/len(all_ranges):.1f})")
    print_tessitura_distribution(all_deviations, total_notes)
    # Derive cost ratios
    print("\n" + "=" * 70)
    print("DERIVED MELODIC COST RATIOS")
    print("=" * 70)
    categories = Counter()
    for i, count in all_intervals.items():
        categories[classify_interval(i)] += count
    step_count = categories.get('step', 1)
    print(f"\n  If step cost = 1.0:")
    for cat in ['unison', 'step', 'skip', 'leap', 'large_leap']:
        count = categories.get(cat, 0)
        if count > 0:
            ratio = step_count / count
            print(f"    {cat:12s}: {ratio:6.2f}x (frequency: {count})")
        else:
            print(f"    {cat:12s}: N/A (frequency: 0)")
    # Derive tessitura cost ratios
    print("\n" + "=" * 70)
    print("DERIVED TESSITURA COST RATIOS")
    print("=" * 70)
    # Notes at median (deviation=0) are the baseline
    at_median = all_deviations.get(0, 1)
    print(f"\n  If at-median cost = 0 (baseline), cost per semitone from median:")
    print(f"  (Derived as inverse frequency relative to deviation=1)")
    at_one = all_deviations.get(1, 1)
    for dev in range(0, 13):
        count = all_deviations.get(dev, 0)
        if count > 0:
            # Ratio relative to notes 1 semitone from median
            ratio = at_one / count
            print(f"    {dev:2d} semitones: {ratio:6.2f}x (frequency: {count})")
        else:
            print(f"    {dev:2d} semitones: N/A (frequency: 0)")

if __name__ == '__main__':
    main()

"""Melodic feature analysis based on cognitive research.
Implements features from:
- Huron 2006: Information theory, expectation
- Jakubowski et al. 2017: Earworm properties
- Schellenberg 1997: Melodic analysis
- Müllensiefen: Hit prediction metrics
"""
from collections import Counter
import math
from typing import Dict, List, Optional, Tuple
# Priority 1: Information-Theoretic Measures

def pitch_entropy(
    note_sequence: List[int]
) -> float:
    """Shannon entropy of pitch class distribution.
    Low entropy + wide range = memorable (Müllensiefen Beatles study).
    Memorable melodies often have entropy < 2.5 bits.
    Args:
        note_sequence: List of pitch classes (0-11) or MIDI pitches (mod 12 applied)
    Returns:
        Entropy in bits
    """
    if not note_sequence:
        return 0.0
    pitch_classes: List[int] = [p % 12 for p in note_sequence]
    pitch_counts: Counter = Counter(pitch_classes)
    total: int = len(pitch_classes)
    entropy: float = 0.0
    for count in pitch_counts.values():
        p: float = count / total
        entropy -= p * math.log2(p)
    return entropy

def interval_entropy(
    intervals: List[int]
) -> float:
    """Entropy of interval transitions (bigram model).
    Measures predictability without corpus comparison.
    Args:
        intervals: List of intervals (can be semitones or scale degrees)
    Returns:
        Entropy in bits
    """
    if len(intervals) < 2:
        return 0.0
    transitions: List[Tuple[int, int]] = [
        (intervals[i], intervals[i + 1])
        for i in range(len(intervals) - 1)
    ]
    transition_counts: Counter = Counter(transitions)
    total: int = len(transitions)
    entropy: float = 0.0
    for count in transition_counts.values():
        p: float = count / total
        entropy -= p * math.log2(p)
    return entropy
# Priority 2: Metric Position Analysis

def strong_beat_alignment(
    notes_with_metrics: List[Tuple[int, float]]
) -> float:
    """Percentage of melodic peaks occurring on strong beats.
    Huron: tonally important pitches gravitate to strong metric positions.
    Well-formed melodies typically > 60% peak alignment.
    Args:
        notes_with_metrics: List of (pitch, metric_strength) tuples
                           metric_strength: 0.0-1.0, where 1.0 = downbeat
    Returns:
        Fraction of peaks on strong beats (0.0-1.0)
    """
    if len(notes_with_metrics) < 3:
        return 0.0
    peaks: List[Tuple[int, float]] = []
    for i in range(1, len(notes_with_metrics) - 1):
        pitch_prev: int = notes_with_metrics[i - 1][0]
        pitch_curr: int = notes_with_metrics[i][0]
        pitch_next: int = notes_with_metrics[i + 1][0]
        if pitch_curr > pitch_prev and pitch_curr > pitch_next:
            peaks.append(notes_with_metrics[i])
    if not peaks:
        return 0.0
    strong_peaks: int = sum(1 for pitch, metric in peaks if metric > 0.5)
    return strong_peaks / len(peaks)

def syncopation_score(
    notes_with_metrics: List[Tuple[Optional[int], float]]
) -> float:
    """Quantify rhythmic displacement from expected metric positions.
    Syncopation creates memorable "surprise".
    Args:
        notes_with_metrics: List of (pitch, metric_strength) tuples
                           pitch can be None for rests
    Returns:
        Syncopation ratio (0.0-1.0)
    """
    if len(notes_with_metrics) < 2:
        return 0.0
    syncopations: int = 0
    for i in range(len(notes_with_metrics) - 1):
        current_pitch, current_metric = notes_with_metrics[i]
        next_pitch, next_metric = notes_with_metrics[i + 1]
        if current_pitch is None:
            continue
        if current_metric < 0.5 and next_metric > current_metric:
            if next_pitch is None or next_pitch == current_pitch:
                syncopations += 1
    return syncopations / len(notes_with_metrics)
# Priority 3: Harmonic Implication Strength

def triadic_content(
    pitches: List[int],
    key_tonic: int
) -> float:
    """Percentage of melody that spells tonic triad.
    Strong harmonic implication aids memory and expectation.
    Args:
        pitches: List of MIDI pitches
        key_tonic: MIDI pitch of tonic (e.g., 60 for C)
    Returns:
        Fraction of notes that are chord tones (0.0-1.0)
    """
    if not pitches:
        return 0.0
    triad: set = {key_tonic % 12, (key_tonic + 4) % 12, (key_tonic + 7) % 12}
    chord_tones: int = sum(1 for p in pitches if (p % 12) in triad)
    return chord_tones / len(pitches)

def triadic_content_minor(
    pitches: List[int],
    key_tonic: int
) -> float:
    """Percentage of melody that spells minor tonic triad.
    Args:
        pitches: List of MIDI pitches
        key_tonic: MIDI pitch of tonic (e.g., 60 for C)
    Returns:
        Fraction of notes that are chord tones (0.0-1.0)
    """
    if not pitches:
        return 0.0
    triad: set = {key_tonic % 12, (key_tonic + 3) % 12, (key_tonic + 7) % 12}
    chord_tones: int = sum(1 for p in pitches if (p % 12) in triad)
    return chord_tones / len(pitches)

def opens_with_triad(
    pitches: List[int],
    key_tonic: int,
    mode: str = "major"
) -> bool:
    """Check if melody opens by arpeggiating tonic triad.
    Args:
        pitches: List of MIDI pitches
        key_tonic: MIDI pitch of tonic
        mode: "major" or "minor"
    Returns:
        True if first 3 distinct pitches outline triad
    """
    if len(pitches) < 3:
        return False
    third_offset: int = 4 if mode == "major" else 3
    triad: set = {key_tonic % 12, (key_tonic + third_offset) % 12, (key_tonic + 7) % 12}
    distinct: List[int] = []
    for p in pitches[:8]:
        pc: int = p % 12
        if pc not in distinct:
            distinct.append(pc)
        if len(distinct) == 3:
            break
    if len(distinct) < 3:
        return False
    return all(pc in triad for pc in distinct[:3])
# Priority 4: Interval Distribution Detail
INTERVAL_NAMES: Dict[int, str] = {
    0: 'unison',
    1: 'minor_2nd',
    2: 'major_2nd',
    3: 'minor_3rd',
    4: 'major_3rd',
    5: 'perfect_4th',
    6: 'tritone',
    7: 'perfect_5th',
    8: 'minor_6th',
    9: 'major_6th',
    10: 'minor_7th',
    11: 'major_7th',
}

def interval_distribution(
    intervals: List[int]
) -> Dict[str, float]:
    """Track specific interval classes.
    Jakubowski: "unusual interval patterns" predict earworms.
    Args:
        intervals: List of signed intervals in semitones
    Returns:
        Dict of interval class percentages
    """
    categories: Dict[str, int] = {
        'unison': 0,
        'minor_2nd': 0,
        'major_2nd': 0,
        'minor_3rd': 0,
        'major_3rd': 0,
        'perfect_4th': 0,
        'tritone': 0,
        'perfect_5th': 0,
        'minor_6th': 0,
        'major_6th': 0,
        'minor_7th': 0,
        'major_7th': 0,
        'octave_plus': 0
    }
    if not intervals:
        return {k: 0.0 for k in categories}
    for interval in intervals:
        abs_interval: int = abs(interval)
        if abs_interval >= 12:
            categories['octave_plus'] += 1
        elif abs_interval in INTERVAL_NAMES:
            categories[INTERVAL_NAMES[abs_interval]] += 1
        else:
            categories['octave_plus'] += 1
    total: int = len(intervals)
    return {k: v / total for k, v in categories.items()}

def unusual_interval_density(
    distribution: Dict[str, float]
) -> float:
    """Intervals larger than perfect 4th are "unusual".
    Jakubowski: earworms have occasional large leaps.
    Memorable melodies: 5-15% unusual intervals.
    Args:
        distribution: Output from interval_distribution()
    Returns:
        Fraction of unusual intervals (0.0-1.0)
    """
    unusual: List[str] = [
        'tritone', 'perfect_5th', 'minor_6th', 'major_6th',
        'minor_7th', 'major_7th', 'octave_plus'
    ]
    return sum(distribution.get(k, 0.0) for k in unusual)

def step_leap_ratio(
    intervals: List[int]
) -> Tuple[float, float]:
    """Calculate step (<=2 semitones) vs leap (>2 semitones) ratio.
    Returns:
        Tuple of (step_ratio, leap_ratio)
    """
    if not intervals:
        return 0.0, 0.0
    steps: int = sum(1 for i in intervals if abs(i) <= 2)
    leaps: int = len(intervals) - steps
    total: int = len(intervals)
    return steps / total, leaps / total
# Priority 5: Contour Parsimony

def contour_parsimony(
    pitches: List[int]
) -> float:
    """Count how many times melodic direction reverses.
    Simpler contours (fewer changes) are more memorable.
    Generic, memorable contours: < 0.3 changes per note.
    Args:
        pitches: List of pitches
    Returns:
        Number of direction changes per note
    """
    if len(pitches) < 3:
        return 0.0
    changes: int = 0
    for i in range(1, len(pitches) - 1):
        direction_before: int = pitches[i] - pitches[i - 1]
        direction_after: int = pitches[i + 1] - pitches[i]
        if direction_before != 0 and direction_after != 0:
            if (direction_before > 0) != (direction_after > 0):
                changes += 1
    return changes / len(pitches)

def classify_contour(
    pitches: List[int]
) -> str:
    """Classify overall melodic shape.
    Huron/Jakubowski: arch and descending contours most common/memorable.
    Args:
        pitches: List of pitches
    Returns:
        One of: 'ascending', 'descending', 'arch', 'valley', 'oscillating', 'too_short'
    """
    if len(pitches) < 4:
        return 'too_short'
    apex_idx: int = pitches.index(max(pitches))
    nadir_idx: int = pitches.index(min(pitches))
    n: int = len(pitches)
    apex_position: float = apex_idx / n
    nadir_position: float = nadir_idx / n
    start: int = pitches[0]
    end: int = pitches[-1]
    max_pitch: int = max(pitches)
    min_pitch: int = min(pitches)
    if 0.3 < apex_position < 0.7 and end < start + (max_pitch - start) * 0.2:
        return 'arch'
    if 0.3 < nadir_position < 0.7 and end > start - (start - min_pitch) * 0.2:
        return 'valley'
    if end > start + 3:
        return 'ascending'
    if end < start - 3:
        return 'descending'
    return 'oscillating'

def contour_string(
    pitches: List[int]
) -> str:
    """Generate Parsons code contour string.
    Parsons code: U=up, D=down, R=repeat.
    Useful for contour matching across transpositions.
    Args:
        pitches: List of pitches
    Returns:
        String of U/D/R characters
    """
    if len(pitches) < 2:
        return ""
    result: List[str] = []
    for i in range(1, len(pitches)):
        diff: int = pitches[i] - pitches[i - 1]
        if diff > 0:
            result.append('U')
        elif diff < 0:
            result.append('D')
        else:
            result.append('R')
    return ''.join(result)
# Priority 6: Tessitura Analysis

def tessitura_leap_interaction(
    pitches: List[int]
) -> Dict[str, float]:
    """Measure if large intervals push toward range extremes.
    Von Hippel & Huron: post-skip reversals explained by range constraints.
    Args:
        pitches: List of MIDI pitches
    Returns:
        Dict with 'upper_leaps', 'lower_leaps', 'middle_leaps' fractions
    """
    if len(pitches) < 3:
        return {'upper_leaps': 0.0, 'lower_leaps': 0.0, 'middle_leaps': 1.0}
    melody_min: int = min(pitches)
    melody_max: int = max(pitches)
    melody_range: int = melody_max - melody_min
    if melody_range == 0:
        return {'upper_leaps': 0.0, 'lower_leaps': 0.0, 'middle_leaps': 1.0}
    upper_leaps: int = 0
    lower_leaps: int = 0
    middle_leaps: int = 0
    for i in range(len(pitches) - 1):
        interval: int = abs(pitches[i + 1] - pitches[i])
        if interval > 4:
            position: float = (pitches[i] - melody_min) / melody_range
            if position > 0.6:
                upper_leaps += 1
            elif position < 0.4:
                lower_leaps += 1
            else:
                middle_leaps += 1
    total_leaps: int = upper_leaps + lower_leaps + middle_leaps
    if total_leaps == 0:
        return {'upper_leaps': 0.0, 'lower_leaps': 0.0, 'middle_leaps': 1.0}
    return {
        'upper_leaps': upper_leaps / total_leaps,
        'lower_leaps': lower_leaps / total_leaps,
        'middle_leaps': middle_leaps / total_leaps
    }

def range_utilization(
    pitches: List[int]
) -> Dict[str, float]:
    """Analyse how the melodic range is used.
    Args:
        pitches: List of MIDI pitches
    Returns:
        Dict with range statistics
    """
    if not pitches:
        return {'range': 0, 'mean': 0.0, 'std': 0.0, 'median_position': 0.0}
    melody_min: int = min(pitches)
    melody_max: int = max(pitches)
    melody_range: int = melody_max - melody_min
    mean: float = sum(pitches) / len(pitches)
    variance: float = sum((p - mean) ** 2 for p in pitches) / len(pitches)
    std: float = math.sqrt(variance)
    sorted_pitches: List[int] = sorted(pitches)
    median: float = sorted_pitches[len(sorted_pitches) // 2]
    median_position: float = (median - melody_min) / melody_range if melody_range > 0 else 0.5
    return {
        'range': melody_range,
        'mean': mean,
        'std': std,
        'median_position': median_position
    }
# Priority 7: Phrase Rhythm

def phrase_length_regularity(
    phrase_lengths: List[float]
) -> float:
    """Measure phrase length regularity.
    Regular phrasing aids memory (4+4, 8+8 bar structures).
    Regular phrasing: CV < 0.2.
    Args:
        phrase_lengths: List of phrase durations in beats
    Returns:
        Coefficient of variation (lower = more regular)
    """
    if len(phrase_lengths) < 2:
        return 0.0
    mean_length: float = sum(phrase_lengths) / len(phrase_lengths)
    if mean_length == 0:
        return 0.0
    variance: float = sum((x - mean_length) ** 2 for x in phrase_lengths) / len(phrase_lengths)
    std_dev: float = math.sqrt(variance)
    return std_dev / mean_length

def is_power_of_two_phrasing(
    phrase_lengths: List[float],
    tolerance: float = 0.1
) -> bool:
    """Check if phrase lengths follow power-of-two structure.
    Common in baroque/classical: 2, 4, 8 bar phrases.
    Args:
        phrase_lengths: List of phrase durations
        tolerance: Fractional tolerance for matching
    Returns:
        True if all phrases match 2^n pattern
    """
    powers: List[float] = [1, 2, 4, 8, 16]
    for length in phrase_lengths:
        matched: bool = False
        for power in powers:
            if abs(length - power) / power < tolerance:
                matched = True
                break
        if not matched:
            return False
    return True
# Aggregate Feature Extraction

def extract_all_features(
    pitches: List[int],
    intervals: Optional[List[int]] = None,
    durations: Optional[List[float]] = None,
    key_tonic: int = 60,
    mode: str = "major"
) -> Dict[str, float]:
    """Extract all melodic features at once.
    Args:
        pitches: List of MIDI pitches
        intervals: Pre-computed intervals (optional)
        durations: Note durations (optional, for rhythm features)
        key_tonic: Tonic MIDI pitch
        mode: "major" or "minor"
    Returns:
        Dict of all feature values
    """
    if intervals is None:
        intervals = [pitches[i + 1] - pitches[i] for i in range(len(pitches) - 1)]
    features: Dict[str, float] = {}
    features['pitch_entropy'] = pitch_entropy(pitches)
    features['interval_entropy'] = interval_entropy(intervals)
    if mode == "major":
        features['triadic_content'] = triadic_content(pitches, key_tonic)
    else:
        features['triadic_content'] = triadic_content_minor(pitches, key_tonic)
    features['opens_with_triad'] = 1.0 if opens_with_triad(pitches, key_tonic, mode) else 0.0
    dist: Dict[str, float] = interval_distribution(intervals)
    features['unusual_interval_density'] = unusual_interval_density(dist)
    step_ratio, leap_ratio = step_leap_ratio(intervals)
    features['step_ratio'] = step_ratio
    features['leap_ratio'] = leap_ratio
    features['contour_parsimony'] = contour_parsimony(pitches)
    contour: str = classify_contour(pitches)
    features['contour_arch'] = 1.0 if contour == 'arch' else 0.0
    features['contour_descending'] = 1.0 if contour == 'descending' else 0.0
    features['contour_ascending'] = 1.0 if contour == 'ascending' else 0.0
    features['contour_valley'] = 1.0 if contour == 'valley' else 0.0
    tessitura: Dict[str, float] = tessitura_leap_interaction(pitches)
    features.update({f'tessitura_{k}': v for k, v in tessitura.items()})
    range_stats: Dict[str, float] = range_utilization(pitches)
    features['range'] = float(range_stats['range'])
    features['range_std'] = range_stats['std']
    return features

class MelodicFeatureScorer:
    """Score melodies using cognitive research-based features."""

    def __init__(
        self,
        key_tonic: int = 60,
        mode: str = "major",
        weights: Optional[Dict[str, float]] = None
    ) -> None:
        """Initialise with key context and optional custom weights."""
        self.key_tonic: int = key_tonic
        self.mode: str = mode
        self.weights: Dict[str, float] = weights or self._default_weights()

    def _default_weights(self) -> Dict[str, float]:
        """Default feature weights based on research importance."""
        return {
            'pitch_entropy': 0.15,
            'triadic_content': 0.12,
            'unusual_interval_density': 0.10,
            'contour_parsimony': 0.10,
            'step_ratio': 0.08,
            'range_normalised': 0.08,
            'contour_arch': 0.07,
            'opens_with_triad': 0.05,
            'interval_entropy': 0.05,
        }

    def score(
        self,
        pitches: List[int],
        durations: Optional[List[float]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """Score a melody for memorability.
        Args:
            pitches: List of MIDI pitches
            durations: Optional list of durations
        Returns:
            Tuple of (total_score, feature_breakdown)
        """
        features: Dict[str, float] = extract_all_features(
            pitches,
            key_tonic=self.key_tonic,
            mode=self.mode
        )
        subscores: Dict[str, float] = {}
        entropy_score: float = self._score_entropy(features['pitch_entropy'])
        subscores['pitch_entropy'] = entropy_score * self.weights.get('pitch_entropy', 0)
        triadic_score: float = features['triadic_content']
        subscores['triadic_content'] = triadic_score * self.weights.get('triadic_content', 0)
        unusual_score: float = self._score_unusual_intervals(features['unusual_interval_density'])
        subscores['unusual_interval_density'] = unusual_score * self.weights.get('unusual_interval_density', 0)
        parsimony_score: float = self._score_parsimony(features['contour_parsimony'])
        subscores['contour_parsimony'] = parsimony_score * self.weights.get('contour_parsimony', 0)
        step_score: float = self._score_step_ratio(features['step_ratio'])
        subscores['step_ratio'] = step_score * self.weights.get('step_ratio', 0)
        range_score: float = self._score_range(features['range'])
        subscores['range_normalised'] = range_score * self.weights.get('range_normalised', 0)
        if features['contour_arch'] > 0:
            subscores['contour_arch'] = self.weights.get('contour_arch', 0)
        if features['opens_with_triad'] > 0:
            subscores['opens_with_triad'] = self.weights.get('opens_with_triad', 0)
        interval_ent_score: float = self._score_interval_entropy(features['interval_entropy'])
        subscores['interval_entropy'] = interval_ent_score * self.weights.get('interval_entropy', 0)
        total: float = sum(subscores.values())
        weight_sum: float = sum(self.weights.values())
        normalised_total: float = total / weight_sum if weight_sum > 0 else 0.0
        return normalised_total, subscores

    def _score_entropy(self, entropy: float) -> float:
        """Score pitch entropy (optimal around 2.0-2.5 bits)."""
        if entropy < 1.5:
            return entropy / 1.5
        elif entropy <= 2.5:
            return 1.0
        else:
            return max(0.0, 1.0 - (entropy - 2.5) / 2.0)

    def _score_unusual_intervals(self, density: float) -> float:
        """Score unusual interval density (optimal 5-15%)."""
        if density < 0.05:
            return density / 0.05
        elif density <= 0.15:
            return 1.0
        else:
            return max(0.0, 1.0 - (density - 0.15) / 0.35)

    def _score_parsimony(self, parsimony: float) -> float:
        """Score contour parsimony (lower is better, < 0.3 optimal)."""
        if parsimony <= 0.3:
            return 1.0
        else:
            return max(0.0, 1.0 - (parsimony - 0.3) / 0.4)

    def _score_step_ratio(self, ratio: float) -> float:
        """Score step ratio (optimal around 0.5-0.7)."""
        if ratio < 0.5:
            return ratio / 0.5
        elif ratio <= 0.7:
            return 1.0
        else:
            return max(0.0, 1.0 - (ratio - 0.7) / 0.3)

    def _score_range(self, range_val: float) -> float:
        """Score melodic range (optimal 7-12 semitones)."""
        if range_val < 7:
            return range_val / 7
        elif range_val <= 12:
            return 1.0
        else:
            return max(0.0, 1.0 - (range_val - 12) / 12)

    def _score_interval_entropy(self, entropy: float) -> float:
        """Score interval transition entropy (moderate is best)."""
        if entropy < 1.0:
            return entropy
        elif entropy <= 2.5:
            return 1.0
        else:
            return max(0.0, 1.0 - (entropy - 2.5) / 2.0)

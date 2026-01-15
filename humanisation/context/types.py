"""Data types for humanisation analysis contexts and profiles."""
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engine.note import Note


@dataclass(frozen=True)
class PhraseContext:
    """Phrase-level context for a note."""

    phrase_id: int
    position_in_phrase: float  # 0.0 = start, 1.0 = end
    distance_to_peak: float  # signed, negative = before peak
    is_phrase_boundary: bool
    boundary_type: str  # 'breath' | 'cadence' | 'none'
    phrase_treatment: str  # from lyric field


@dataclass(frozen=True)
class MetricContext:
    """Metric hierarchy context for a note."""

    metric_weight: float  # 0.0 to 1.0
    is_downbeat: bool
    is_syncopation: bool
    beat_subdivision: int  # 1, 2, 4, 8...
    bar_position: float  # 0.0 to 1.0 within bar


@dataclass(frozen=True)
class HarmonicContext:
    """Vertical harmonic context for a note."""

    tension: float  # 0.0 = consonant, 1.0 = harsh dissonance
    is_resolution: bool
    is_prepared_dissonance: bool
    interval_class: int  # interval mod 12 with other voice


@dataclass(frozen=True)
class MelodicContext:
    """Melodic contour context for a note."""

    interval_from_previous: int  # semitones, signed
    is_leap: bool  # abs(interval) > 2
    is_peak: bool  # local maximum
    is_trough: bool  # local minimum
    contour_direction: int  # -1, 0, +1


@dataclass(frozen=True)
class VoiceContext:
    """Voice role context for a note."""

    is_melody: bool
    is_thematic: bool  # stating subject/countersubject (from lyric)
    activity_ratio: float  # note density relative to other voices
    voice_id: int  # track number


@dataclass(frozen=True)
class NoteContext:
    """Combined analysis context for a single note."""

    note_index: int
    phrase: PhraseContext
    metric: MetricContext
    harmonic: HarmonicContext
    melodic: MelodicContext
    voice: VoiceContext


# Profile dataclasses


@dataclass(frozen=True)
class TimingProfile:
    """Timing parameters for an instrument/style."""

    melodic_lead_ms: float  # Melody arrives early (negative offset)
    agogic_downbeat_ms: float  # Downbeat delay
    agogic_peak_ms: float  # Phrase peak delay
    agogic_syncopation_ms: float  # Syncopation anticipation (negative)
    rubato_max_accel: float  # Max tempo multiplier (e.g., 1.08)
    rubato_max_decel: float  # Min tempo multiplier (e.g., 0.85)
    rubato_peak_position: float  # Position in phrase for max tempo
    rubato_cadence_start: float  # When cadence ritardando begins
    stochastic_sigma: float  # O-U volatility
    stochastic_theta: float  # O-U mean reversion
    motor_interval_coef: float  # ms per semitone beyond octave


@dataclass(frozen=True)
class DynamicsProfile:
    """Dynamics parameters for an instrument/style."""

    velocity_min: int  # Floor velocity
    velocity_max: int  # Ceiling velocity
    phrase_envelope_strength: float  # 0.0-1.0
    phrase_peak_position: float  # Where phrase peaks (0.4 typical)
    metric_weight_range: int  # +/- offset from metric weight
    harmonic_tension_boost: int  # Max velocity boost for dissonance
    contour_range: int  # Velocity range for pitch height
    voice_balance_melody: int  # Boost for melody voice
    voice_balance_thematic: int  # Boost for thematic material
    touch_variation: int  # Random +/- velocity


@dataclass(frozen=True)
class ArticulationProfile:
    """Articulation parameters for an instrument/style."""

    default_gate: float  # Base duration factor (e.g., 0.92)
    legato_gate: float  # Legato duration factor (e.g., 1.05)
    staccato_gate: float  # Staccato duration factor (e.g., 0.60)
    phrase_end_gate: float  # Phrase boundary factor (e.g., 0.85)
    fast_passage_gate: float  # Fast notes factor (e.g., 0.88)
    notes_inegales_ratio: float  # Long:short ratio for swing (0 = disabled)
    notes_inegales_threshold: float  # Max duration for swing to apply


@dataclass(frozen=True)
class HumanisationProfile:
    """Complete humanisation profile."""

    name: str
    timing: TimingProfile
    dynamics: DynamicsProfile
    articulation: ArticulationProfile
    enabled_models: tuple[str, ...]  # Which model groups to apply


# Default profiles for fallback


DEFAULT_TIMING = TimingProfile(
    melodic_lead_ms=20.0,
    agogic_downbeat_ms=15.0,
    agogic_peak_ms=25.0,
    agogic_syncopation_ms=-20.0,
    rubato_max_accel=1.08,
    rubato_max_decel=0.85,
    rubato_peak_position=0.4,
    rubato_cadence_start=0.85,
    stochastic_sigma=0.008,
    stochastic_theta=0.3,
    motor_interval_coef=8.0,
)

DEFAULT_DYNAMICS = DynamicsProfile(
    velocity_min=40,
    velocity_max=110,
    phrase_envelope_strength=1.0,
    phrase_peak_position=0.4,
    metric_weight_range=8,
    harmonic_tension_boost=12,
    contour_range=10,
    voice_balance_melody=8,
    voice_balance_thematic=5,
    touch_variation=4,
)

DEFAULT_ARTICULATION = ArticulationProfile(
    default_gate=0.92,
    legato_gate=1.05,
    staccato_gate=0.60,
    phrase_end_gate=0.85,
    fast_passage_gate=0.88,
    notes_inegales_ratio=0.0,
    notes_inegales_threshold=0.125,
)

DEFAULT_PROFILE = HumanisationProfile(
    name="default",
    timing=DEFAULT_TIMING,
    dynamics=DEFAULT_DYNAMICS,
    articulation=DEFAULT_ARTICULATION,
    enabled_models=("timing", "dynamics", "articulation"),
)

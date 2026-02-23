"""Subject generator constants and configuration."""

# ── Duration vocabulary ─────────────────────────────────────────────
DURATION_TICKS: tuple[int, ...] = (1, 2, 4, 8)
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'crotchet', 'minim')
NUM_DURATIONS: int = len(DURATION_TICKS)
SEMIQUAVER_DI: int = 0

# ── Tick / bar geometry ─────────────────────────────────────────────
X2_TICKS_PER_WHOLE: int = 16


def _bar_x2_ticks(metre: tuple[int, int]) -> int:
    """X2-ticks per bar for the given metre."""
    return X2_TICKS_PER_WHOLE * metre[0] // metre[1]


# ── Bar-fill constraints ────────────────────────────────────────────
MIN_NOTES_PER_BAR: int = 2
MAX_NOTES_PER_BAR: int = 8
MAX_SAME_DUR_RUN: int = 4
MIN_LAST_DUR_TICKS: int = 4
MAX_SUBJECT_NOTES: int = 16
MIN_SEMIQUAVER_GROUP: int = 2

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7
PITCH_HI: int = 7
MAX_LARGE_LEAPS: int = 4
MIN_STEP_FRACTION: float = 0.5
RANGE_LO: int = 4
RANGE_HI: int = 11
MAX_SAME_SIGN_RUN: int = 5
ALLOWED_FINALS: frozenset[int] = frozenset({0, 2, 4})
MAX_PITCH_FREQ: int = 3

# ── Shape scoring parameters ────────────────────────────────────────
IDEAL_CLIMAX_LO: float = 0.3
IDEAL_CLIMAX_HI: float = 0.6
IDEAL_STEP_FRACTION: float = 0.67
IDEAL_RHYTHMIC_ENTROPY: float = 0.75

# ── Pitch scoring parameters ────────────────────────────────────────
MIN_SIGNATURE_LEAP: int = 3
MAX_STEPWISE_RUN: int = 3
MIN_DISTINCT_INTERVALS: int = 3
LEAP_RECOVERY_WINDOW: int = 2

# ── Duration scoring parameters ─────────────────────────────────────
MAX_OPENING_TICKS: int = 4
MIN_DURATION_KINDS: int = 3

# ── CP-SAT sampling parameters ───────────────────────────────────────
CPSAT_NUM_RESTARTS: int = 40
CPSAT_SOLUTIONS_PER_RESTART: int = 50
CPSAT_SOLVER_TIMEOUT: float = 3.0

# ── Selection parameters ────────────────────────────────────────────
QUALITY_FLOOR_FRACTION: float = 0.85  # keep candidates scoring >= this fraction of best
DIVERSITY_POOL_CAP: int = 2500  # max candidates for diversity selection
DURATIONS_PER_NOTE_COUNT: int = 5  # top-K duration patterns paired with each pitch
MIN_STRETTO_OFFSETS: int = 3
CONTOUR_PREFERENCE_BONUS: float = 0.05

"""Subject generator constants and configuration."""

# ── Duration vocabulary ─────────────────────────────────────────────
DURATION_TICKS: tuple[int, ...] = (1, 2, 4)
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'crotchet')
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
MIN_SUBJECT_NOTES: int = 8
MIN_SEMIQUAVER_GROUP: int = 2

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7
PITCH_HI: int = 7
MAX_LARGE_LEAPS: int = 4
MIN_STEP_FRACTION: float = 0.65
RANGE_LO: int = 3
RANGE_HI: int = 11
MAX_SAME_SIGN_RUN: int = 5
ALLOWED_FINALS: frozenset[int] = frozenset({0, 2, 4})
MAX_PITCH_FREQ: int = 3

# ── CP-SAT sampling parameters ───────────────────────────────────────
CPSAT_NUM_RESTARTS: int = 40
CPSAT_SOLUTIONS_PER_RESTART: int = 50
CPSAT_SOLVER_TIMEOUT: float = 3.0

# ── Selection parameters ────────────────────────────────────────────

MIN_STRETTO_OFFSETS: int = 1

# ── Aesthetic scoring weights (each criterion 0–1, weighted sum) ────

W_RANGE: float = 1.0
W_SIGNATURE_INTERVAL: float = 1.0
W_RHYTHMIC_CONTRAST: float = 1.0
W_DIRECTION_COMMITMENT: float = 1.0
W_REPETITION_PENALTY: float = 1.0

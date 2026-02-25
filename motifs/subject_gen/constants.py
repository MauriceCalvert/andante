"""Subject generator constants and configuration."""

# ── Duration vocabulary ─────────────────────────────────────────────
# DURATION_TICKS: tuple[int, ...] = (1, 2, 3, 4, 6)
# DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'dotted quaver', 'crotchet', 'dotted crotchet')
DURATION_TICKS: tuple[int, ...] = (1, 2, 4)          # semiquaver, quaver, crotchet in x2-ticks
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'crotchet')
NUM_DURATIONS: int = len(DURATION_TICKS)              # derived; keep in sync with DURATION_TICKS

# ── Head (Kopfmotiv) constraints ─────────────────────────────────────
HEAD_LENGTHS: tuple[int, ...] = (4,)                  # allowed head note counts; later (3, 4, 5)
HEAD_SIZE: int = max(HEAD_LENGTHS)                    # max head size — used for duration filter
MIN_HEAD_LEAP: int = 4                                # diatonic interval: 3 = a 4th
MIN_HEAD_FINAL_DUR_TICKS: int = 4                     # crotchet — rhythmic articulation at head/tail boundary

# ── Tick / bar geometry ─────────────────────────────────────────────
X2_TICKS_PER_WHOLE: int = 16                          # ticks per semibreve at semiquaver resolution


def _bar_x2_ticks(metre: tuple[int, int]) -> int:
    """X2-ticks per bar for the given metre."""
    return X2_TICKS_PER_WHOLE * metre[0] // metre[1]


# ── Bar-fill constraints ────────────────────────────────────────────
MIN_NOTES_PER_BAR: int = 2           # fewest notes allowed in any bar
MAX_NOTES_PER_BAR: int = 8           # most notes allowed in any bar
MAX_SAME_DUR_RUN: int = 6            # no more than N consecutive identical durations
MAX_DUR_RATIO: int = 2               # max ratio between adjacent note durations (2 = quaver↔crotchet ok)
MIN_LAST_DUR_TICKS: int = 2          # final note of subject must be at least a crotchet
MAX_SUBJECT_NOTES: int = 16          # hard ceiling on subject length in notes
MIN_SUBJECT_NOTES: int = 8           # hard floor on subject length in notes
MIN_SEMIQUAVER_GROUP: int = 2        # semiquavers must appear in groups of at least this size

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7                   # lowest allowed diatonic step from tonic (an octave below)
PITCH_HI: int = 7                    # highest allowed diatonic step from tonic (an octave above)
MAX_LARGE_LEAPS: int = 2             # max leaps of a 5th or larger in the whole subject
MIN_STEP_FRACTION: float = 0.30      # at least half of all intervals must be steps (±1–2)
RANGE_LO: int = 4                    # minimum melodic range in diatonic steps
RANGE_HI: int = 11                   # maximum melodic range in diatonic steps (an octave + 5th)
MAX_SAME_SIGN_RUN: int = 5           # max consecutive notes moving in the same direction
ALLOWED_FINALS: frozenset[int] = frozenset({0, 4})  # diatonic finals: tonic (0) or dominant (4)
MAX_PITCH_FREQ: int = 2              # no pitch class may appear more than this many times

# ── CP-SAT tail solver parameters ────────────────────────────────────
CPSAT_SOLUTIONS_PER_HEAD: int = 200  # candidate tails to collect per head motif
CPSAT_TAIL_TIMEOUT: float = 2.0      # seconds before CP-SAT solver gives up on one head

# ── Selection parameters ────────────────────────────────────────────
MIN_STRETTO_OFFSETS: int = 1         # minimum number of viable stretto offsets required
MAX_DURS_PER_COUNT: int = 1000       # cap on duration sequences per note-count bucket

# ── Aesthetic scoring weights (each criterion 0–1, weighted sum) ────
W_RANGE: float = 1.0                 # reward subjects that use a good melodic range
W_SIGNATURE_INTERVAL: float = 1.0   # reward a characteristic interval (6th, 7th, etc.)
W_RHYTHMIC_CONTRAST: float = 1.0    # reward variety of note lengths
W_DIRECTION_COMMITMENT: float = 1.0  # reward clear directional arcs
W_REPETITION_PENALTY: float = 1.0   # penalise exact pitch-class repetition

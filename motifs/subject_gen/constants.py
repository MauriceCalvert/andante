"""Subject generator constants and configuration."""

# ── Duration vocabulary ─────────────────────────────────────────────
DURATION_TICKS: tuple[int, ...] = (1, 2, 3, 4, 6, 8)
DURATION_NAMES: tuple[str, ...] = ('semiquaver', 'quaver', 'dotted quaver', 'crotchet', 'dotted crotchet', 'minim')
NUM_DURATIONS: int = len(DURATION_TICKS)              # derived; keep in sync with DURATION_TICKS

# ── Head (Kopfmotiv) constraints ─────────────────────────────────────
HEAD_LENGTHS: tuple[int, ...] = (3, 4, 5)                  # allowed head note counts; later (3, 4, 5)
HEAD_SIZE: int = max(HEAD_LENGTHS)                    # max head size — used for duration filter
MIN_HEAD_LEAP: int = 4                                # diatonic interval: 3 = a 4th
MIN_HEAD_FINAL_DUR_TICKS: int = 4                     # crotchet — rhythmic articulation at head/tail boundary

# ── Tick / bar geometry ─────────────────────────────────────────────
X2_TICKS_PER_WHOLE: int = 16                          # ticks per semibreve at semiquaver resolution


def _bar_x2_ticks(metre: tuple[int, int]) -> int:
    """X2-ticks per bar for the given metre."""
    return X2_TICKS_PER_WHOLE * metre[0] // metre[1]


# ── Subject length constraints ─────────────────────────────────────
MIN_LAST_DUR_TICKS: int = 4          # final note of subject must be at least a crotchet
MAX_SUBJECT_NOTES: int = 12          # hard ceiling on subject length in notes
MIN_SUBJECT_NOTES: int = 8           # hard floor on subject length in notes

# ── Pitch constraints ───────────────────────────────────────────────
PITCH_LO: int = -7                   # lowest allowed diatonic step from tonic (an octave below)
PITCH_HI: int = 7                    # highest allowed diatonic step from tonic (an octave above)
MAX_LARGE_LEAPS: int = 2             # max leaps of a 5th or larger in the whole subject
MIN_STEP_FRACTION: float = 0.30      # at least half of all intervals must be steps (+-1-2)
RANGE_LO: int = 4                    # minimum melodic range in diatonic steps
RANGE_HI: int = 11                   # maximum melodic range in diatonic steps (an octave + 5th)
MAX_SAME_SIGN_RUN: int = 5           # max consecutive notes moving in the same direction
ALLOWED_FINALS: frozenset[int] = frozenset({0, 4})  # diatonic finals: tonic (0) or dominant (4)
MAX_PITCH_FREQ: int = 2              # no pitch may appear more than twice
MAX_FILL_LEAP: int = 3               # max residual leap (diatonic steps) after stepwise P-slot fill
DEGREES_PER_OCTAVE: int = 7          # diatonic degrees per octave

# ── CP-SAT tail solver parameters ────────────────────────────────────
CPSAT_SOLUTIONS_PER_HEAD: int = 200  # candidate tails to collect per head motif
CPSAT_TAIL_TIMEOUT: float = 2.0      # seconds before CP-SAT solver gives up on one head

# ── Selection parameters ────────────────────────────────────────────
MIN_STRETTO_OFFSETS: int = 1         # minimum number of viable stretto offsets required
MAX_DURS_PER_COUNT: int = 5000       # cap on duration sequences per note-count bucket
MIN_AESTHETIC_SCORE: float = 8.0     # floor: candidates below this are excluded before diversity selection
HEAD_IV_FEATURE_SCALE: float = 2.0   # boost head-interval weight in diversity feature vector
HEAD_IV_FEATURE_WINDOW: int = 3       # number of head/tail intervals in diversity features (independent of HEAD_SIZE)
MIN_DIVERSITY_DISTANCE: float = 1.0   # minimum feature-space distance to accept a new pick

# ── Aesthetic scoring weights (each criterion 0-1, weighted sum) ────
W_RANGE: float = 1.0                 # reward subjects that use a good melodic range
W_DIRECTION_COMMITMENT: float = 1.0  # reward clear directional arcs
W_REPETITION_PENALTY: float = 0.5   # penalise exact pitch-class repetition (reduced SUB-2, pending SUB-3)
W_HARMONIC_VARIETY: float = 1.0     # reward subjects that touch multiple chords
W_FAST_NOTE_DENSITY: float = 1.0    # reward semiquaver presence
W_DURATION_VARIETY: float = 1.0     # reward using multiple distinct note values
W_SCALIC_MONOTONY: float = 2.5      # penalise overwhelmingly stepwise subjects
W_HEAD_CHARACTER: float = 1.5       # reward a characteristic leap in the Kopfmotiv
W_TAIL_MOMENTUM: float = 2.0        # penalise consecutive long notes at subject end
W_DENSITY_TRAJECTORY: float = 3.0   # reward measurable density shift between head and tail (SUB-2)

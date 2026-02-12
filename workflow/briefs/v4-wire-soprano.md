## Task: V4 — Wire viterbi into soprano_writer

Read these files first:
- `viterbi/pipeline.py`
- `viterbi/mtypes.py`
- `viterbi/scale.py`
- `builder/soprano_writer.py`
- `builder/voice_writer.py`
- `builder/voice_types.py`
- `builder/phrase_types.py`
- `shared/key.py`

### Goal

Replace the span-based `write_voice` + `DiminutionFill` pipeline in
`generate_soprano_phrase` with the viterbi solver. The soprano becomes the
follower; the bass (already generated) is the leader.

### Implementation

**New adapter module: `viterbi/adapter.py`**

This bridges the real system's types to the viterbi solver's types.

```python
def key_to_keyinfo(key: Key) -> KeyInfo:
    """Convert shared.key.Key to viterbi.scale.KeyInfo."""

def notes_to_leader(notes: tuple[Note, ...]) -> list[LeaderNote]:
    """Convert finished bass Notes to LeaderNote list."""
    # For each follower grid position, find the bass note sounding at
    # that offset (onset <= position < onset + duration).

def structural_tones_to_knots(
    tones: list[tuple[Fraction, int, Key]],
) -> list[Knot]:
    """Convert soprano structural tones to Knot list."""

def solver_output_to_notes(
    beats: list[float],
    pitches: list[int],
    grid_durations: list[Fraction],
    track: int,
) -> tuple[Note, ...]:
    """Convert solver pitch assignments to Note objects."""
```

**soprano_writer.py changes:**

Replace the bottom half of `generate_soprano_phrase` (from "Build
VoiceConfig" onward). The new flow:

1. `_place_structural_tones` — unchanged, produces knots.
2. Determine rhythm grid positions from the existing rhythm cell
   infrastructure (this already determines onset positions; extract them
   as a list of Fraction offsets).
3. Convert bass `lower_notes` → `LeaderNote` list via adapter.
4. Convert structural tones → `Knot` list via adapter.
5. Convert `plan.local_key` → `KeyInfo` via adapter.
6. Build corridors and solve phrase.
7. Convert solver output → `Note` objects via adapter.

The rhythm cell selection step (which determines HOW MANY notes and their
onset times between structural tones) is retained. Only the PITCH
selection changes. Rhythm cells determine the grid; the solver fills it.

**Grid position derivation:**

The existing span pipeline determines onset positions for each note
within a span. Extract this logic as a separate function that returns
`list[Fraction]` — the onset times at which the solver must assign
pitches. This is the grid the solver operates on.

### CostProfile

Add a `CostProfile` dataclass to `viterbi/costs.py` that holds all cost
weights as fields with the current module-level constants as defaults:

```python
@dataclass(frozen=True)
class CostProfile:
    """Tuneable cost weights for the solver."""
    step_unison: float = 8.0
    step_second: float = 0.0
    step_third: float = 4.0
    step_fourth: float = 10.0
    step_fifth_plus: float = 18.0
    contrary_bonus: float = -2.0
    oblique_bonus: float = -0.5
    similar_penalty: float = 1.0
    parallel_perfect: float = 25.0
    leap_no_recovery: float = 20.0
    zigzag: float = 4.0
    run_penalty: float = 5.0
    passing_tone: float = 1.0
    half_resolved: float = 15.0
    unresolved_diss: float = 50.0
    cadence_bonus: float = -2.5
    cadence_onset: float = 0.65
    cross_relation: float = 30.0
    spacing_too_close: float = 8.0
    spacing_too_far: float = 4.0
    spacing_low: int = 7
    spacing_high: int = 24
    perfect_on_strong: float = 1.5

DEFAULT_PROFILE = CostProfile()
```

Also add:

```python
INVERTIBLE_PROFILE = CostProfile(
    spacing_too_close=0.0,
    spacing_low=0,
)
```

This profile removes the penalty for voices being close together or
crossing, which is required for invertible counterpoint between two
voices in the same register.

Thread `profile: CostProfile = DEFAULT_PROFILE` through:
- `transition_cost` (replaces module-level constant lookups)
- `find_path`
- `solve_phrase`

All individual cost functions (`step_cost`, `motion_cost`, etc.) read
weights from the profile instead of module globals. The module-level
constants remain as documentation but `DEFAULT_PROFILE` is the single
source of truth.

The adapter in `soprano_writer.py` passes `DEFAULT_PROFILE` for normal
galant soprano generation.

### Constraints

- Aside from adding CostProfile and threading it, do not change any
  viterbi algorithm logic. All adaptation happens in adapter.py and
  soprano_writer.py.
- Do not modify `_place_structural_tones`.
- Do not modify bass_writer.py.
- Rhythm cell selection is untouched. Only pitch assignment changes.
- `validate_voice` in voice_writer.py remains as a post-hoc safety net.
  Call it on the solver output.
- `audit_voice` becomes informational only (log warnings, don't fail).

### Checkpoint

Generate a gavotte phrase. Compare the soprano output against the
pre-V4 output:

1. Same number of notes (rhythm unchanged).
2. Same structural tone placements (knots unchanged).
3. All strong-beat intervals consonant with the bass.
4. Predominantly stepwise motion between structural tones.
5. No parallel perfect intervals with bass.

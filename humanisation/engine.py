"""Main humanisation engine.

Orchestrates analysis, timing, dynamics, and articulation to transform
mechanical note output into expressive musical performance.
"""
from engine.note import Note
from humanisation.context.types import HumanisationProfile, NoteContext
from humanisation.context.harmonic import analyze_harmonic
from humanisation.context.melodic import analyze_melodic
from humanisation.context.metric import analyze_metric
from humanisation.context.phrase import analyze_phrases
from humanisation.context.voice import analyze_voice
from humanisation.timing.engine import apply_timing
from humanisation.dynamics.engine import apply_dynamics
from humanisation.articulation.engine import apply_articulation


def _build_contexts(notes: list[Note], metre: str) -> list[NoteContext]:
    """Build combined analysis contexts for all notes.

    Args:
        notes: List of Note objects
        metre: Time signature string (e.g., "4/4")

    Returns:
        List of NoteContext, one per note
    """
    phrase_contexts = analyze_phrases(notes)
    metric_contexts = analyze_metric(notes, metre)
    melodic_contexts = analyze_melodic(notes)
    voice_contexts = analyze_voice(notes)
    harmonic_contexts = analyze_harmonic(notes)

    return [
        NoteContext(
            note_index=i,
            phrase=phrase_contexts[i],
            metric=metric_contexts[i],
            harmonic=harmonic_contexts[i],
            melodic=melodic_contexts[i],
            voice=voice_contexts[i],
        )
        for i in range(len(notes))
    ]


def humanise(
    notes: list[Note],
    profile: HumanisationProfile,
    metre: str,
    tempo_bpm: int,
    seed: int = 42,
) -> list[Note]:
    """Apply humanisation to transform mechanical notes into expressive performance.

    The humanisation process:
    1. Analyze each note for phrase, metric, harmonic, melodic, and voice context
    2. Apply timing models (rubato, agogic, melodic lead, motor, stochastic)
    3. Apply dynamics models (phrase envelope, metric, harmonic, contour, balance, touch)
    4. Apply articulation model (duration adjustment)

    Each stage creates new Note instances (immutable transformation).

    Args:
        notes: List of Note objects from formatter
        profile: Humanisation profile (instrument + style)
        metre: Time signature string (e.g., "4/4")
        tempo_bpm: Base tempo in beats per minute
        seed: Random seed for reproducibility (stochastic models)

    Returns:
        New list of Note objects with humanised timing, velocity, and duration
    """
    if not notes:
        return []

    # Build analysis contexts
    contexts = _build_contexts(notes, metre)

    result = notes
    enabled = profile.enabled_models

    # Apply timing models
    if "timing" in enabled:
        result = apply_timing(result, contexts, profile, tempo_bpm, seed)

    # Apply dynamics models
    if "dynamics" in enabled:
        result = apply_dynamics(result, contexts, profile, seed + 1000)

    # Apply articulation model
    if "articulation" in enabled:
        result = apply_articulation(result, contexts, profile)

    # Re-sort by offset (timing adjustments may have changed order)
    result.sort(key=lambda n: (n.Offset, n.track))

    return result

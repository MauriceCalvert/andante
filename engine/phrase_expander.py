"""Phrase expansion: expand_phrase and related functions."""
from fractions import Fraction

from shared.pitch import Pitch
from engine.cadence import CADENCE_FORMULAS, get_cadence_material, apply_final_cadence
from engine.cadenza import generate_cadenza_bass
from engine.episode import get_energy_profile, resolve_rhythm, resolve_treatment
from engine.episode_registry import generate_episode_soprano
from engine.energy import get_rhythm_override as get_energy_rhythm
from engine.expander_util import (
    CADENCE_BUDGET, TONAL_ROOTS,
    apply_device, apply_rhythm, bar_duration, subject_to_motif_ast,
)
from engine.hemiola import apply_hemiola, can_apply_hemiola, detect_hemiola_trigger
from engine.key import Key
from engine.surprise import (
    get_cadence_override as get_surprise_cadence,
    get_fill_override as get_surprise_fill,
    get_rhythm_override as get_surprise_rhythm,
    get_treatment_override as get_surprise_treatment,
)
from shared.tracer import get_tracer
from engine.engine_types import ExpandedPhrase, PhraseAST
from engine.voice_expander import expand_voices
from engine.voice_material import ExpandedVoices, VoiceMaterial
from shared.timed_material import TimedMaterial
from planner.subject import Subject


def resolve_overrides(phrase: PhraseAST, episode_type: str | None) -> tuple[str, str | None, str | None]:
    """Resolve treatment, rhythm, and cadence with surprise overrides."""
    treatment: str = resolve_treatment(phrase.treatment, episode_type)
    if (surprise_treatment := get_surprise_treatment(phrase.surprise)) is not None:
        treatment = surprise_treatment
    rhythm: str | None = resolve_rhythm(phrase.rhythm, episode_type)
    if (surprise_rhythm := get_surprise_rhythm(phrase.surprise)) is not None:
        rhythm = surprise_rhythm
    energy: str = phrase.energy or get_energy_profile(episode_type)
    if (energy_rhythm := get_energy_rhythm(energy)) is not None and rhythm is None:
        rhythm = energy_rhythm
    cadence: str | None = phrase.cadence
    if (surprise_cadence := get_surprise_cadence(phrase.surprise)) is not None:
        cadence = surprise_cadence
    return treatment, rhythm, cadence


def _build_nvoice_phrase(
    phrase: PhraseAST,
    voice_materials: tuple[TimedMaterial, ...],
    main_budget: Fraction,
    rhythm: str | None,
    cadence: str | None,
    energy: str,
    texture: str,
    episode_type: str | None,
    metre: str,
    total_phrases: int,
) -> ExpandedPhrase:
    """Build ExpandedPhrase from N voice materials with full assignments."""
    tracer = get_tracer()
    voice_count: int = len(voice_materials)
    all_voices: list[VoiceMaterial] = []
    for v_idx, mat in enumerate(voice_materials):
        pitches: list[Pitch] = list(mat.pitches)
        durations: list[Fraction] = list(mat.durations)
        if rhythm:
            pitches, durations = list(apply_rhythm(tuple(pitches), tuple(durations), rhythm, main_budget))
        if can_apply_hemiola(metre):
            hemiola_pattern: str | None = detect_hemiola_trigger(
                phrase.index, total_phrases, phrase.is_climax, cadence
            )
            if hemiola_pattern is not None:
                tm: TimedMaterial = TimedMaterial(tuple(pitches), tuple(durations), main_budget)
                tm = apply_hemiola(tm, hemiola_pattern, metre)
                pitches, durations = list(tm.pitches), list(tm.durations)
        tracer.voice(f"phrase_{phrase.index}", f"voice_{v_idx}", pitches, durations)
        all_voices.append(VoiceMaterial(voice_index=v_idx, pitches=pitches, durations=durations))
    voices: ExpandedVoices = ExpandedVoices(voices=all_voices)
    return ExpandedPhrase(
        index=phrase.index, bars=phrase.bars, voices=voices, cadence=phrase.cadence,
        tonal_target=phrase.tonal_target, is_climax=phrase.is_climax,
        articulation=phrase.articulation, gesture=phrase.gesture,
        energy=energy, surprise=phrase.surprise, texture=texture, episode_type=episode_type,
    )

"""Voice expansion: expand_voices and related functions."""
from fractions import Fraction

from shared.pitch import FloatingNote, Pitch
from engine.expander_util import TONAL_ROOTS, TREATMENTS, subject_to_motif_ast, cs_to_motif_ast
from engine.figured_bass import realise_figured_bass, generate_figures_for_bass
from engine.key import Key
from engine.pedal import generate_pedal_bass, get_pedal_type
from engine.schema import apply_schema
from engine.engine_types import MotifAST
from engine.vocabulary import BASS_SCHEMAS
from engine.voice_pipeline import VoiceSpec, expand_voice, voice_spec_from_treatment
from engine.walking_bass import generate_walking_bass, WALKING_PATTERNS
from shared.timed_material import TimedMaterial
from planner.subject import Subject


def get_bass_schema(tonal_target: str) -> tuple[tuple[Pitch, ...], tuple[Fraction, ...]]:
    """Get bass schema for tonal target (used for figured bass texture)."""
    schema_key: str = f"{tonal_target}_statement"
    if schema_key in BASS_SCHEMAS:
        schema = BASS_SCHEMAS[schema_key]
        pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in schema.degrees)
        return pitches, schema.durations
    root: int = TONAL_ROOTS.get(tonal_target, 1)
    pitches = (FloatingNote(root), FloatingNote(5), FloatingNote(root))
    durs: tuple[Fraction, ...] = (Fraction(1, 4), Fraction(1, 4), Fraction(1, 2))
    return pitches, durs


def expand_n_voices(
    subj: Subject,
    voice_assignments: tuple[str, ...],
    budget: Fraction,
    voice_count: int,
) -> list[TimedMaterial]:
    """Expand N voices using explicit motif assignments."""
    result: list[TimedMaterial] = []
    for i, motif_name in enumerate(voice_assignments):
        motif = subj.get_motif_extended(motif_name, budget)
        pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in motif.degrees)
        mat: TimedMaterial = TimedMaterial(pitches, motif.durations, budget)
        result.append(mat)
    return result


def expand_voices(
    treatment_name: str,
    subj: Subject,
    tonal_target: str,
    budget: Fraction,
    seed: int,
    is_opening: bool = False,
    is_cadential: bool = False,
    texture: str = "polyphonic",
    key: Key | None = None,
    bass_elaboration: str | None = None,
    bar_dur: Fraction = Fraction(1, 1),
    voice_assignments: tuple[str, ...] | None = None,
    voice_count: int = 2,
) -> tuple[TimedMaterial, ...]:
    """Expand voices using treatment pipeline."""
    if voice_assignments is not None and len(voice_assignments) == voice_count:
        return tuple(expand_n_voices(subj, voice_assignments, budget, voice_count))
    treatment: dict = TREATMENTS.get(treatment_name, {})
    if treatment_name == "counterpoint":
        ext_subj, ext_cs = subj.extend_to(budget)
        sop_pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in ext_subj.degrees)
        sop_mat: TimedMaterial = TimedMaterial(sop_pitches, ext_subj.durations, budget)
        bass_pitches: tuple[Pitch, ...] = tuple(FloatingNote(d) for d in ext_cs.degrees)
        bass_mat: TimedMaterial = TimedMaterial(bass_pitches, ext_cs.durations, budget)
        return sop_mat, bass_mat
    subject: MotifAST = subject_to_motif_ast(subj)
    counter_subject: MotifAST = cs_to_motif_ast(subj)
    if texture == "figured_bass" and key is not None:
        bass_schema = get_bass_schema(tonal_target)
        bass_p, bass_d = bass_schema
        bass: TimedMaterial = TimedMaterial.repeat_to_budget(list(bass_p), list(bass_d), budget)
        figures: tuple[str, ...] = generate_figures_for_bass(bass.pitches, style="varied")
        soprano: TimedMaterial = realise_figured_bass(
            bass.pitches, bass.durations, figures, key, budget
        )
        return soprano, bass
    if treatment.get("soprano_source") == "schema":
        schema_name: str = treatment.get("schema", "romanesca")
        root: int = TONAL_ROOTS.get(tonal_target, 1)
        return apply_schema(schema_name, budget, root)
    if treatment.get("bass_source") == "pedal":
        pedal_type: str | None = get_pedal_type(treatment_name)
        if pedal_type is not None:
            bass = generate_pedal_bass(pedal_type, budget)
            sop_spec: VoiceSpec = voice_spec_from_treatment(treatment, "soprano")
            soprano = expand_voice(
                sop_spec, subject, counter_subject, budget, seed, "soprano"
            )
            return soprano, bass
    # Handle swap_at for voice_exchange: voices swap material at the swap point
    swap_at_str: str | None = treatment.get("swap_at")
    if swap_at_str is not None:
        swap_at: Fraction = Fraction(swap_at_str)
        swap_point: Fraction = budget * swap_at
        return _expand_with_swap(
            treatment, subject, counter_subject, budget, swap_point, seed
        )
    sop_spec = voice_spec_from_treatment(treatment, "soprano")
    soprano = expand_voice(
        sop_spec, subject, counter_subject, budget, seed, "soprano"
    )
    bass_spec: VoiceSpec = voice_spec_from_treatment(treatment, "bass")
    if bass_elaboration is not None and bass_elaboration in WALKING_PATTERNS:
        root: int = TONAL_ROOTS.get(tonal_target, 1)
        bars: int = max(1, int(budget / Fraction(1, 1)))
        bass = generate_walking_bass(root, root, bass_elaboration, bars, Fraction(1, 1))
        if bass.budget != budget:
            bass = TimedMaterial.repeat_to_budget(list(bass.pitches), list(bass.durations), budget)
    else:
        bass = expand_voice(
            bass_spec, subject, counter_subject, budget, seed, "bass"
        )
    return soprano, bass


def _expand_with_swap(
    treatment: dict,
    subject: MotifAST,
    counter_subject: MotifAST,
    budget: Fraction,
    swap_point: Fraction,
    seed: int,
) -> tuple[TimedMaterial, TimedMaterial]:
    """Expand voices with material swap at swap_point.

    Before swap_point:
      - soprano uses soprano_source
      - bass uses bass_source
    After swap_point:
      - soprano uses bass_source
      - bass uses soprano_source

    This creates a true voice exchange (Stimmtausch).
    """
    # Get specs for first half
    sop_spec_first = voice_spec_from_treatment(treatment, "soprano")
    bass_spec_first = voice_spec_from_treatment(treatment, "bass")

    # Create swapped specs for second half by exchanging sources
    sop_spec_second = VoiceSpec(
        source=bass_spec_first.source,
        transform=bass_spec_first.transform,
        transform_params=bass_spec_first.transform_params,
        delay=Fraction(0),
        direct=bass_spec_first.direct,
        derivation=bass_spec_first.derivation,
        derivation_params=bass_spec_first.derivation_params,
    )
    bass_spec_second = VoiceSpec(
        source=sop_spec_first.source,
        transform=sop_spec_first.transform,
        transform_params=sop_spec_first.transform_params,
        delay=Fraction(0),
        direct=sop_spec_first.direct,
        derivation=sop_spec_first.derivation,
        derivation_params=sop_spec_first.derivation_params,
    )

    # Expand first half
    first_budget: Fraction = swap_point
    sop_first = expand_voice(
        sop_spec_first, subject, counter_subject, first_budget, seed, "soprano"
    )
    bass_first = expand_voice(
        bass_spec_first, subject, counter_subject, first_budget, seed, "bass"
    )

    # Expand second half with swapped sources
    second_budget: Fraction = budget - swap_point
    sop_second = expand_voice(
        sop_spec_second, subject, counter_subject, second_budget, seed + 1, "soprano"
    )
    bass_second = expand_voice(
        bass_spec_second, subject, counter_subject, second_budget, seed + 1, "bass"
    )

    # Concatenate the halves
    soprano = TimedMaterial.concatenate(sop_first, sop_second)
    bass = TimedMaterial.concatenate(bass_first, bass_second)

    return soprano, bass

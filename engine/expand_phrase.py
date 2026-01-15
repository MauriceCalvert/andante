"""Single phrase expansion function."""
from fractions import Fraction
from pathlib import Path

import yaml

from engine.cadence import CADENCE_FORMULAS, get_cadence_material, apply_final_cadence
from engine.cadenza import generate_cadenza_bass
from engine.episode import get_energy_profile
from engine.episode_registry import generate_episode_soprano
from engine.expander_util import (
    CADENCE_BUDGET, TONAL_ROOTS,
    apply_device, apply_rhythm, bar_duration, subject_to_motif_ast, cs_to_motif_ast,
)
from engine.hemiola import apply_hemiola, can_apply_hemiola, detect_hemiola_trigger
from engine.key import Key
from engine.phrase_expander import resolve_overrides
from engine.texture import get_texture, apply_texture
from engine.transform import apply_transform
from shared.tracer import get_tracer
from engine.engine_types import ExpandedPhrase, PhraseAST
from engine.voice_expander import expand_voices
from engine.voice_material import ExpandedVoices
from engine.voice_pipeline import voice_spec_from_treatment, expand_voice
from engine.n_voice_expander import (
    generate_baroque_entries,
    expand_single_voice,
    VoiceExpansionContext,
)
from engine.voice_entry import PhraseVoiceEntry
from shared.timed_material import TimedMaterial
from planner.subject import Subject

DATA_DIR: Path = Path(__file__).parent.parent / "data"
_TREATMENTS: dict = yaml.safe_load(open(DATA_DIR / "treatments.yaml", encoding="utf-8"))


def _get_effective_texture(phrase_texture: str | None, episode_texture: str) -> str:
    """Get effective texture: phrase overrides episode."""
    return phrase_texture if phrase_texture is not None else episode_texture


def expand_phrase(
    phrase: PhraseAST,
    subj: Subject,
    metre: str,
    is_final: bool = False,
    episode_type: str | None = None,
    episode_texture: str = "polyphonic",
    virtuosic: bool = False,
    seed: int = 0,
    key: Key | None = None,
    total_phrases: int = 1,
    voice_count: int = 2,
) -> ExpandedPhrase:
    """Expand a single phrase to bar-level pitches.

    Pipeline: treatment -> texture -> voices

    Treatment transforms the melodic material (invert, fragment, etc.)
    Texture arranges voices (polyphonic, interleaved, canon, etc.)
    """
    tracer = get_tracer()
    treatment_name, rhythm, cadence = resolve_overrides(phrase, episode_type)
    energy: str = phrase.energy or get_energy_profile(episode_type)
    texture_name: str = _get_effective_texture(phrase.texture, episode_texture)
    tracer.phrase(phrase.index, treatment_name, phrase.bars,
                  tonal_target=phrase.tonal_target, cadence=phrase.cadence, is_climax=phrase.is_climax)

    bar_dur: Fraction = bar_duration(metre)
    phrase_budget: Fraction = bar_dur * phrase.bars
    has_cadence: bool = cadence is not None and cadence in CADENCE_FORMULAS
    use_final_cadence: bool = is_final and phrase.cadence == "authentic"
    main_budget: Fraction = phrase_budget if (use_final_cadence or not has_cadence) else phrase_budget - CADENCE_BUDGET
    root: int = TONAL_ROOTS.get(phrase.tonal_target, 1)
    is_opening: bool = phrase.index == 0
    is_cadential: bool = cadence is not None

    # Get treatment and texture specs
    treatment: dict = _TREATMENTS.get(treatment_name, {})
    texture = get_texture(texture_name)

    # Get source material
    subject_ast = subject_to_motif_ast(subj)
    cs_ast = cs_to_motif_ast(subj)

    # Step 1: Apply treatment to get transformed soprano material
    sop_spec = voice_spec_from_treatment(treatment, "soprano")
    treated_soprano = expand_voice(sop_spec, subject_ast, cs_ast, main_budget, seed, "soprano")

    # Step 2: Apply texture to arrange voices

    # Baroque invention texture: use entry system with rotating subjects
    if texture.name == "baroque_invention":
        # Generate baroque-appropriate entry schedule
        subject_bars = subj.bars if hasattr(subj, 'bars') else 2
        entry: PhraseVoiceEntry = generate_baroque_entries(
            phrase.index, voice_count, treatment_name, subject_bars, phrase.bars
        )

        # Create expansion context
        ctx = VoiceExpansionContext(
            subject=subject_ast,
            counter_subject=cs_ast,
            budget=main_budget,
            phrase_index=phrase.index,
            tonal_target=phrase.tonal_target,
            bar_dur=bar_dur,
        )

        # Expand each voice according to entry spec
        voice_materials: list[tuple[list, list]] = []
        for i in range(voice_count):
            spec = entry.spec_for_voice(i)
            material = expand_single_voice(spec, ctx, i, bar_dur)
            voice_materials.append((material.pitches, material.durations))

        # Extract pitches and durations for each voice
        v1_p, v1_d = voice_materials[0]
        if voice_count >= 2:
            bass_p, bass_d = voice_materials[-1]
        if voice_count == 3:
            v2_p, v2_d = voice_materials[1]

        # Apply cadence if needed
        if use_final_cadence:
            v1_p, v1_d, bass_p, bass_d = apply_final_cadence(
                tuple(v1_p), tuple(v1_d), tuple(bass_p), tuple(bass_d),
                bar_dur, phrase_budget, phrase.tonal_target
            )
            v1_p, v1_d, bass_p, bass_d = list(v1_p), list(v1_d), list(bass_p), list(bass_d)
            if voice_count == 3:
                v2_total = sum(v2_d, Fraction(0))
                if v2_total < phrase_budget:
                    v2_p = list(v2_p) + [v1_p[-1]]
                    v2_d = list(v2_d) + [phrase_budget - v2_total]
        elif has_cadence:
            cad_sop, cad_bass = get_cadence_material(cadence, CADENCE_BUDGET, phrase.tonal_target)
            v1_p = list(v1_p) + list(cad_sop.pitches)
            v1_d = list(v1_d) + list(cad_sop.durations)
            bass_p = list(bass_p) + list(cad_bass.pitches)
            bass_d = list(bass_d) + list(cad_bass.durations)
            if voice_count == 3:
                v2_p = list(v2_p) + list(cad_sop.pitches)
                v2_d = list(v2_d) + list(cad_sop.durations)

        # Log voices
        tracer.voice(f"phrase_{phrase.index}", "soprano", list(v1_p), list(v1_d))
        if voice_count == 3:
            tracer.voice(f"phrase_{phrase.index}", "alto", list(v2_p), list(v2_d))
        tracer.voice(f"phrase_{phrase.index}", "bass", list(bass_p), list(bass_d))

        # Build ExpandedVoices
        if voice_count == 2:
            voices = ExpandedVoices.from_two_voices(
                list(v1_p), list(v1_d), list(bass_p), list(bass_d)
            )
        else:
            voices = ExpandedVoices.from_three_voices(
                list(v1_p), list(v1_d), list(v2_p), list(v2_d), list(bass_p), list(bass_d)
            )

        return ExpandedPhrase(
            index=phrase.index, bars=phrase.bars, voices=voices, cadence=phrase.cadence,
            tonal_target=phrase.tonal_target, is_climax=phrase.is_climax,
            articulation=phrase.articulation, gesture=phrase.gesture,
            energy=energy, surprise=phrase.surprise, texture=texture_name, episode_type=episode_type,
            treatment=treatment_name,
        )

    if texture.name == "interleaved" and voice_count == 3:
        # Use texture system for interleaved 3-voice
        cs_material = TimedMaterial(cs_ast.pitches, cs_ast.durations, sum(cs_ast.durations, Fraction(0)))
        voice_mats = apply_texture(
            treated_soprano, cs_material, texture, main_budget, voice_count,
            phrase.tonal_target, bar_dur
        )
        v1_p, v1_d = voice_mats[0].pitches, voice_mats[0].durations
        v2_p, v2_d = voice_mats[1].pitches, voice_mats[1].durations
        bass_p, bass_d = voice_mats[2].pitches, voice_mats[2].durations

        # Apply cadence to all voices if needed
        if use_final_cadence:
            v1_p, v1_d, bass_p, bass_d = apply_final_cadence(
                v1_p, v1_d, bass_p, bass_d, bar_dur, phrase_budget, phrase.tonal_target
            )
            v2_total = sum(v2_d, Fraction(0))
            if v2_total < phrase_budget:
                v2_p = v2_p + v1_p[-1:]
                v2_d = v2_d + (phrase_budget - v2_total,)
        elif has_cadence:
            cad_sop, cad_bass = get_cadence_material(cadence, CADENCE_BUDGET, phrase.tonal_target)
            v1_p = v1_p + cad_sop.pitches
            v1_d = v1_d + cad_sop.durations
            v2_p = v2_p + cad_sop.pitches
            v2_d = v2_d + cad_sop.durations
            bass_p = bass_p + cad_bass.pitches
            bass_d = bass_d + cad_bass.durations

        tracer.voice(f"phrase_{phrase.index}", "voice_1", list(v1_p), list(v1_d))
        tracer.voice(f"phrase_{phrase.index}", "voice_2", list(v2_p), list(v2_d))
        tracer.voice(f"phrase_{phrase.index}", "bass", list(bass_p), list(bass_d))

        v1_total: Fraction = sum(v1_d, Fraction(0))
        v2_total_final: Fraction = sum(v2_d, Fraction(0))
        bass_total: Fraction = sum(bass_d, Fraction(0))
        assert v1_total == phrase_budget, f"Phrase {phrase.index} voice_1 {v1_total} != {phrase_budget}"
        assert v2_total_final == phrase_budget, f"Phrase {phrase.index} voice_2 {v2_total_final} != {phrase_budget}"
        assert bass_total == phrase_budget, f"Phrase {phrase.index} bass {bass_total} != {phrase_budget}"

        voices: ExpandedVoices = ExpandedVoices.from_three_voices(
            list(v1_p), list(v1_d), list(v2_p), list(v2_d), list(bass_p), list(bass_d)
        )
        return ExpandedPhrase(
            index=phrase.index, bars=phrase.bars, voices=voices, cadence=phrase.cadence,
            tonal_target=phrase.tonal_target, is_climax=phrase.is_climax,
            articulation=phrase.articulation, gesture=phrase.gesture,
            energy=energy, surprise=phrase.surprise, texture=texture_name, episode_type=episode_type,
            treatment=treatment_name,
        )

    # Standard 2-voice expansion (uses existing voice_expander path for now)
    episode_soprano: TimedMaterial | None = generate_episode_soprano(
        episode_type, subject_ast, main_budget, root, seed, virtuosic
    )
    if episode_soprano is not None:
        sop_p, sop_d = episode_soprano.pitches, episode_soprano.durations
        voice_mats = expand_voices(
            treatment_name, subj, phrase.tonal_target, main_budget, seed,
            is_opening, is_cadential, episode_texture, key, None, bar_dur,
        )
        bass_p, bass_d = voice_mats[-1].pitches, voice_mats[-1].durations
    else:
        voice_mats = expand_voices(
            treatment_name, subj, phrase.tonal_target, main_budget, seed,
            is_opening, is_cadential, episode_texture, key, None, bar_dur,
        )
        sop_p, sop_d = voice_mats[0].pitches, voice_mats[0].durations
        bass_p, bass_d = voice_mats[-1].pitches, voice_mats[-1].durations

    if episode_type == "cadenza":
        bass_tm: TimedMaterial = generate_cadenza_bass(main_budget, root)
        bass_p, bass_d = bass_tm.pitches, bass_tm.durations
    if phrase.device:
        sop_p, sop_d = apply_device(sop_p, sop_d, phrase.device, main_budget)
        bass_p, bass_d = apply_device(bass_p, bass_d, phrase.device, main_budget)
    if rhythm:
        sop_p, sop_d = apply_rhythm(sop_p, sop_d, rhythm, main_budget)
    if can_apply_hemiola(metre):
        hemiola_pattern: str | None = detect_hemiola_trigger(
            phrase.index, total_phrases, phrase.is_climax, cadence
        )
        if hemiola_pattern is not None:
            sop_tm: TimedMaterial = TimedMaterial(sop_p, sop_d, main_budget)
            sop_tm = apply_hemiola(sop_tm, hemiola_pattern, metre)
            sop_p, sop_d = sop_tm.pitches, sop_tm.durations
            bass_tm = TimedMaterial(bass_p, bass_d, main_budget)
            bass_tm = apply_hemiola(bass_tm, hemiola_pattern, metre)
            bass_p, bass_d = bass_tm.pitches, bass_tm.durations
    if use_final_cadence:
        sop_p, sop_d, bass_p, bass_d = apply_final_cadence(
            sop_p, sop_d, bass_p, bass_d, bar_dur, phrase_budget, phrase.tonal_target
        )
    elif has_cadence:
        cad_sop, cad_bass = get_cadence_material(cadence, CADENCE_BUDGET, phrase.tonal_target)
        sop_p = sop_p + cad_sop.pitches
        sop_d = sop_d + cad_sop.durations
        bass_p = bass_p + cad_bass.pitches
        bass_d = bass_d + cad_bass.durations
    tracer.voice(f"phrase_{phrase.index}", "soprano", list(sop_p), list(sop_d))
    tracer.voice(f"phrase_{phrase.index}", "bass", list(bass_p), list(bass_d))
    sop_total: Fraction = sum(sop_d, Fraction(0))
    bass_total: Fraction = sum(bass_d, Fraction(0))
    assert sop_total == phrase_budget, f"Phrase {phrase.index} soprano {sop_total} != {phrase_budget}"
    assert bass_total == phrase_budget, f"Phrase {phrase.index} bass {bass_total} != {phrase_budget}"
    voices = ExpandedVoices.from_two_voices(
        list(sop_p), list(sop_d), list(bass_p), list(bass_d)
    )
    return ExpandedPhrase(
        index=phrase.index, bars=phrase.bars, voices=voices, cadence=phrase.cadence,
        tonal_target=phrase.tonal_target, is_climax=phrase.is_climax,
        articulation=phrase.articulation, gesture=phrase.gesture,
        energy=energy, surprise=phrase.surprise, texture=texture_name, episode_type=episode_type,
        treatment=treatment_name,
    )

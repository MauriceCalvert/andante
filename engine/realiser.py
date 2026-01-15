"""E4 Realiser: Pitch types -> MIDI pitches.

Delegates to:
- voice_realiser.py: Voice realisation
- octave.py: Octave selection
- realiser_guards.py: Guard checking
- metrics.py: Piece metrics
"""
from fractions import Fraction
from pathlib import Path

import yaml

from engine.energy import get_register_shift as get_energy_shift
from engine.guards.registry import create_guards, run_piece_guards, Diagnostic
from engine.key import Key
from engine.metrics import BASS_LEAD_EPISODES, compute_metrics
from engine.octave import register, voice_range
from engine.ornament import apply_ornaments
from engine.realiser_guards import check_guards
from engine.realiser_passes import apply_bass_passes
from engine.surprise import get_register_shift as get_surprise_shift
from engine.treatment_caps import allows
from engine.texture import texture_allows
from shared.tracer import get_tracer
from engine.engine_types import ExpandedPhrase, RealisedNote, RealisedPhrase, RealisedVoice
from engine.voice_pair import VoicePairSet
from engine.voice_realiser import realise_voice, realise_voice_against, realise_interleaved_voices

DATA_DIR: Path = Path(__file__).parent.parent / "data"
_PREDICATES: dict = yaml.safe_load(open(DATA_DIR / "predicates.yaml", encoding="utf-8"))
INTERLEAVED_RANGES: dict[str, list[int]] = _PREDICATES.get("interleaved_ranges", {})
INTERLEAVED_MEDIANS: dict[str, int] = _PREDICATES.get("interleaved_medians", {})


def beat(metre: str) -> Fraction:
    """One beat in the given metre."""
    return Fraction(1, int(metre.split("/")[1]))


def shortest(metre: str) -> Fraction:
    """Smallest subdivision: beat divided by 8 (32nd in 4/4)."""
    return beat(metre) / 8


def apply_phrase_gap(notes: tuple[RealisedNote, ...], metre: str) -> tuple[RealisedNote, ...]:
    """Shorten final note by smallest subdivision for articulation."""
    assert notes, "Cannot apply phrase gap to empty notes"
    gap: Fraction = shortest(metre)
    final: RealisedNote = notes[-1]
    if final.duration <= gap:
        return notes
    shortened: RealisedNote = RealisedNote(
        offset=final.offset, pitch=final.pitch,
        duration=final.duration - gap, voice=final.voice)
    return notes[:-1] + (shortened,)


def validate_notes(notes: tuple[RealisedNote, ...], voice: str, metre: str, allow_gaps: bool = False) -> None:
    """Assert note sequence has valid durations and no unintended gaps."""
    min_dur: Fraction = shortest(metre)
    for i, note in enumerate(notes):
        assert note.duration >= min_dur, f"{voice} note {i}: duration {note.duration} < {min_dur}"
        if i < len(notes) - 1 and not allow_gaps:
            next_note: RealisedNote = notes[i + 1]
            gap: Fraction = next_note.offset - (note.offset + note.duration)
            assert gap <= min_dur, f"{voice} gap after note {i}: {gap} > {min_dur}"


def _is_interleaved_texture(texture: str) -> bool:
    """Check if texture is interleaved (Goldberg-style)."""
    return texture == "interleaved"


def _get_interleaved_medians() -> tuple[int, int]:
    """Get separate medians for interleaved voices from predicates.

    Returns:
        Tuple of (voice1_median, voice2_median) for ~octave separation.
        V1 in upper register (~C5), V2 in lower register (~C4).
    """
    v1_median = INTERLEAVED_MEDIANS.get("voice_1", 72)  # C5
    v2_median = INTERLEAVED_MEDIANS.get("voice_2", 60)  # C4
    return v1_median, v2_median


def _get_interleaved_ranges() -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Get voice ranges for interleaved voices.

    Returns:
        Tuple of (voice1_range, voice2_range) or (None, None) if not defined.
    """
    v1_range = INTERLEAVED_RANGES.get("voice_1")
    v2_range = INTERLEAVED_RANGES.get("voice_2")
    return (
        tuple(v1_range) if v1_range else None,
        tuple(v2_range) if v2_range else None,
    )


def realise_phrase(
    phrase: ExpandedPhrase,
    home_key: Key,
    phrase_offset: Fraction,
    bar_dur: Fraction,
    metre: str,
    is_final: bool = False,
) -> RealisedPhrase:
    """Realise expanded phrase to concrete notes for N voices."""
    tracer = get_tracer()
    treatment: str | None = phrase.treatment
    climax_boost: int = 12 if phrase.is_climax and allows(treatment, "climax_boost") else 0
    energy_shift: int = get_energy_shift(phrase.energy) if phrase.energy and allows(treatment, "energy_shift") else 0
    surprise_shift: int = get_surprise_shift(phrase.surprise)
    total_shift: int = climax_boost + energy_shift + surprise_shift
    tonal_target: str = phrase.tonal_target
    if tonal_target not in ("I", "i"):
        tracer.trace("REALISE", f"phrase_{phrase.index}", "tonal_target",
                     target=tonal_target, key=f"{home_key.tonic} {home_key.mode}")

    # Check for interleaved mode (Goldberg-style crossing voices)
    is_interleaved: bool = _is_interleaved_texture(phrase.texture)

    # Handle interleaved 3-voice texture: voice_1, voice_2 (interleaved pair) + bass
    if is_interleaved and phrase.voices.count == 3:
        voice_names = ("voice_1", "voice_2", "bass")
        # Interleaved voices use separate medians for ~octave separation
        # V1 high (C5), V2 low (C4) - creates audible voice distinction
        v1_median, v2_median = _get_interleaved_medians()
        v1_range, v2_range = _get_interleaved_ranges()
        bass_median: int = register("bass") + total_shift

        # Realise the interleaved pair together with separate registers
        voice1_mat = phrase.voices.voices[0]
        voice2_mat = phrase.voices.voices[1]
        voice1_notes, voice2_notes = realise_interleaved_voices(
            tuple(voice1_mat.pitches), tuple(voice1_mat.durations),
            tuple(voice2_mat.pitches), tuple(voice2_mat.durations),
            home_key, v1_median, phrase_offset, tonal_target,
            voice2_median=v2_median, voice1_range=v1_range, voice2_range=v2_range,
        )

        realised_voices: list[RealisedVoice] = [
            RealisedVoice(0, list(voice1_notes)),
            RealisedVoice(1, list(voice2_notes)),
        ]
        realised_notes: list[tuple[RealisedNote, ...]] = [voice1_notes, voice2_notes]

        # Realise bass against both interleaved voices
        bass_mat = phrase.voices.voices[2]
        bass_notes: tuple[RealisedNote, ...] = realise_voice_against(
            tuple(bass_mat.pitches), tuple(bass_mat.durations), home_key,
            bass_median, "bass", phrase_offset, realised_notes, tonal_target
        )
        has_cadence: bool = phrase.cadence is not None
        bass_notes = apply_bass_passes(
            voice1_notes, bass_notes, bar_dur, phrase.index, home_key,
            phrase.episode_type, phrase.texture, has_cadence, phrase.voices.count,
        )
        realised_voices.append(RealisedVoice(2, list(bass_notes)))

        for i, rv in enumerate(realised_voices):
            voice_name = voice_names[i]
            validate_notes(tuple(rv.notes), f"phrase_{phrase.index}/{voice_name}", metre, allow_gaps=not texture_allows(phrase.texture, "gap_validation"))
            tracer.realise(f"phrase_{phrase.index}", voice_name, len(rv.notes), offset=phrase_offset)
        return RealisedPhrase(index=phrase.index, voices=realised_voices, treatment=phrase.treatment, texture=phrase.texture)

    # Handle interleaved 2-voice texture: voice_1, voice_2 (no separate bass)
    if is_interleaved and phrase.voices.count == 2:
        voice_names = ("voice_1", "voice_2")
        # Interleaved voices use separate medians for ~octave separation
        v1_median, v2_median = _get_interleaved_medians()
        v1_range, v2_range = _get_interleaved_ranges()

        voice1_mat = phrase.voices.voices[0]
        voice2_mat = phrase.voices.voices[1]
        voice1_notes, voice2_notes = realise_interleaved_voices(
            tuple(voice1_mat.pitches), tuple(voice1_mat.durations),
            tuple(voice2_mat.pitches), tuple(voice2_mat.durations),
            home_key, v1_median, phrase_offset, tonal_target,
            voice2_median=v2_median, voice1_range=v1_range, voice2_range=v2_range,
        )

        realised_voices = [
            RealisedVoice(0, list(voice1_notes)),
            RealisedVoice(1, list(voice2_notes)),
        ]

        for i, rv in enumerate(realised_voices):
            voice_name = voice_names[i]
            validate_notes(tuple(rv.notes), f"phrase_{phrase.index}/{voice_name}", metre, allow_gaps=not texture_allows(phrase.texture, "gap_validation"))
            tracer.realise(f"phrase_{phrase.index}", voice_name, len(rv.notes), offset=phrase_offset)
        return RealisedPhrase(index=phrase.index, voices=realised_voices, treatment=phrase.treatment, texture=phrase.texture)

    # Standard voice realisation (non-interleaved)
    voice_names: tuple[str, ...] = ("soprano", "alto", "tenor", "bass")[:phrase.voices.count]
    if phrase.voices.count == 2:
        voice_names = ("soprano", "bass")
    elif phrase.voices.count == 3:
        voice_names = ("soprano", "alto", "bass")
    realised_voices = []
    realised_notes = []
    has_cadence = phrase.cadence is not None
    is_statement: bool = phrase.episode_type == "statement"
    is_bass_lead: bool = phrase.episode_type in BASS_LEAD_EPISODES
    soprano_mat = phrase.voices.voices[0]
    soprano_median: int = register("soprano") + total_shift
    soprano_range: tuple[int, int] = voice_range("soprano")
    soprano_notes: tuple[RealisedNote, ...] = realise_voice(
        tuple(soprano_mat.pitches), tuple(soprano_mat.durations), home_key,
        soprano_median, "soprano", phrase_offset, tonal_target, soprano_range
    )
    if not has_cadence and not is_statement and not is_bass_lead and allows(treatment, "ornaments"):
        soprano_notes = apply_ornaments(soprano_notes, home_key, False, bar_dur, phrase.index)
    realised_voices.append(RealisedVoice(0, list(soprano_notes)))
    realised_notes.append(soprano_notes)
    # For baroque_invention, skip parallel penalties - imitative entries naturally create parallels
    skip_parallels: bool = phrase.texture == "baroque_invention"
    for i, voice_mat in enumerate(phrase.voices.voices[1:], start=1):
        voice_name: str = voice_names[i]
        median: int = register(voice_name) + total_shift
        v_range: tuple[int, int] = voice_range(voice_name)
        notes: tuple[RealisedNote, ...] = realise_voice_against(
            tuple(voice_mat.pitches), tuple(voice_mat.durations), home_key,
            median, voice_name, phrase_offset, realised_notes, tonal_target, v_range,
            skip_parallels
        )
        realised_voices.append(RealisedVoice(i, list(notes)))
        realised_notes.append(notes)
    bass_notes = tuple(realised_voices[-1].notes)
    bass_notes = apply_bass_passes(
        soprano_notes, bass_notes, bar_dur, phrase.index, home_key,
        phrase.episode_type, phrase.texture, has_cadence, phrase.voices.count,
    )
    realised_voices[-1] = RealisedVoice(phrase.voices.count - 1, list(bass_notes))
    for i, rv in enumerate(realised_voices):
        voice_name = voice_names[i]
        validate_notes(tuple(rv.notes), f"phrase_{phrase.index}/{voice_name}", metre, allow_gaps=not texture_allows(phrase.texture, "gap_validation"))
        tracer.realise(f"phrase_{phrase.index}", voice_name, len(rv.notes), offset=phrase_offset)
    return RealisedPhrase(index=phrase.index, voices=realised_voices, treatment=phrase.treatment, texture=phrase.texture)


def realise_phrases(
    phrases: list[ExpandedPhrase],
    home_key: Key,
    bar_duration: Fraction,
    metre: str,
) -> list[RealisedPhrase]:
    """Realise all phrases and run guards for N voices."""
    tracer = get_tracer()
    realised: list[RealisedPhrase] = []
    offset: Fraction = Fraction(0)
    for i, phrase in enumerate(phrases):
        is_final: bool = i == len(phrases) - 1
        if phrase.tonal_target != "I" and phrase.tonal_target != "i":
            tracer.trace("HARMONIC", f"phrase_{phrase.index}", f"target {phrase.tonal_target}",
                         home_key=f"{home_key.tonic} {home_key.mode}")
        rp: RealisedPhrase = realise_phrase(phrase, home_key, offset, bar_duration, metre, is_final)
        realised.append(rp)
        offset += sum(phrase.soprano_durations, Fraction(0))
    guards = create_guards()
    diagnostics: list[Diagnostic] = check_guards(realised, phrases, guards, bar_duration, metre, key=home_key)
    if realised:
        voice_count: int = len(realised[0].voices)
        pairs: VoicePairSet = VoicePairSet.compute(voice_count)
        for pair in pairs.pairs:
            all_upper: list[tuple[Fraction, int]] = []
            all_lower: list[tuple[Fraction, int]] = []
            for rp in realised:
                all_upper.extend((n.offset, n.pitch) for n in rp.voices[pair.upper_index].notes)
                all_lower.extend((n.offset, n.pitch) for n in rp.voices[pair.lower_index].notes)
            diagnostics.extend(run_piece_guards(guards, all_upper, all_lower, bar_duration))
    blockers: list[Diagnostic] = [d for d in diagnostics if d.severity == "blocker"]
    if blockers:
        for b in blockers:
            print(f"BLOCKER: {b.guard_id} - {b.message} ({b.location})")
        raise ValueError(f"Guard check failed: {len(blockers)} blocker(s)")
    for d in diagnostics:
        if d.severity == "major":
            print(f"WARNING: {d.guard_id} - {d.message} ({d.location})")
    metrics = compute_metrics(phrases, bar_duration)
    tracer.trace("METRICS", "piece", "proportions",
                 total=metrics.total_bars, subject=metrics.subject_bars,
                 derived=metrics.derived_bars, episode=metrics.episode_bars,
                 free=metrics.free_bars, thematic_ratio=f"{metrics.thematic_ratio:.1%}")
    if metrics.thematic_ratio < 0.5:
        print(f"WARNING: Low thematic ratio {metrics.thematic_ratio:.1%} (target: 50-70%)")
    return realised

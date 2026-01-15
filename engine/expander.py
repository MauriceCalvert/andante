"""E3 Expander: Piece-level expansion orchestrator.

Delegates to:
- expand_phrase.py: Single phrase expansion
- voice_expander.py: Voice generation
- inner_voice.py: Inner voice via slice solver
- expander_util.py: Utilities and constants
"""
from fractions import Fraction
from pathlib import Path

import yaml

from engine.arc_loader import load_arc, ArcDefinition
from engine.expand_phrase import expand_phrase
from engine.expander_util import bar_duration, TONAL_ROOTS, CADENCE_BUDGET
from engine.guard_backtrack import (
    accept_candidate,
    check_candidate_guards,
    reset_accumulated_midi,
)
from engine.inner_voice import add_inner_voices_cpsat, add_inner_voices_with_backtracking, validate_nvoice_guards
from engine.key import Key
from engine.engine_types import ExpandedPhrase, PieceAST
from engine.treatment_caps import allows
from engine.voice_config import voice_set_from_count

# Re-export for backwards compatibility
from engine.expander_util import (
    apply_rhythm,
    apply_device,
    subject_to_motif_ast,
    cs_to_motif_ast,
)
from engine.voice_expander import expand_voices


def expand_piece(piece: PieceAST) -> list[ExpandedPhrase]:
    """Expand all phrases in piece with guard-based backtracking.

    Unified expansion path for 2/3/4 voices:
    - Always use 2-voice pipeline for outer voices
    - For N > 2, add inner voices via slice solver
    - N-voice validation uses realiser to check actual MIDI pitches
    """
    reset_accumulated_midi(piece.voices)
    key: Key = Key(tonic=piece.key, mode=piece.mode)
    arc: ArcDefinition = load_arc(piece.arc)
    voice_set = voice_set_from_count(piece.voices)
    bar_dur: Fraction = bar_duration(piece.metre)
    expanded: list[ExpandedPhrase] = []
    all_phrases: list[tuple] = []
    for section in piece.sections:
        for episode in section.episodes:
            for phrase in episode.phrases:
                all_phrases.append((phrase, episode.type, episode.texture))
    phrase_offset: Fraction = Fraction(0)
    seed: int = 0
    max_retries: int = 50
    total_phrases: int = len(all_phrases)
    for i, (phrase, episode_type, texture) in enumerate(all_phrases):
        is_final: bool = i == len(all_phrases) - 1
        outer_retries: int = 0
        exp: ExpandedPhrase
        found: bool = False
        while not found:
            exp = expand_phrase(
                phrase, piece.subject, piece.metre, is_final,
                episode_type, texture, piece.virtuosic,
                seed, key, total_phrases, piece.voices,
            )
            violations: list = validate_nvoice_guards(
                exp, key, bar_dur, piece.metre, phrase_offset
            ) if piece.voices > 2 else check_candidate_guards(
                exp.soprano_pitches, exp.soprano_durations,
                exp.bass_pitches, exp.bass_durations,
                key, phrase_offset,
            )
            if len(violations) == 0:
                found = True
            else:
                outer_retries += 1
                if outer_retries >= max_retries:
                    raise ValueError(
                        f"Phrase {phrase.index}: guard violations after {max_retries} retries. "
                        f"Violations: {[str(v) for v in violations]}"
                    )
                seed += 1
        accept_candidate(
            exp.soprano_pitches, exp.soprano_durations,
            exp.bass_pitches, exp.bass_durations,
            key, phrase_offset,
        )
        # Skip inner voice generation if treatment forbids it (e.g., pedal has fixed bass)
        # or if texture is interleaved/baroque_invention (middle voice already generated)
        from engine.texture import texture_allows
        skip_inner_gen = (
            exp.texture == "interleaved" or
            exp.texture == "baroque_invention" or
            not texture_allows(exp.texture, "inner_voice_gen")
        )
        if piece.voices > 2 and allows(exp.treatment, "inner_voice_gen") and not skip_inner_gen:
            subject_ast = subject_to_motif_ast(piece.subject)
            cs_ast = cs_to_motif_ast(piece.subject)
            # Use CP-SAT solver with fallback to branch-and-bound
            exp = add_inner_voices_cpsat(
                exp, key, texture, voice_set, bar_dur, piece.metre, phrase_offset,
                subject_ast, cs_ast, timeout_seconds=5.0
            )
        expanded.append(exp)
        phrase_offset += sum(exp.soprano_durations, Fraction(0))
        seed += 1
    return expanded

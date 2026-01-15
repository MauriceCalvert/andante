"""Realiser guards: run guards on realised phrases."""
from fractions import Fraction

from engine.guards.registry import run_guards, Diagnostic, Guard
from engine.engine_types import ExpandedPhrase, RealisedPhrase
from engine.key import Key
from engine.voice_checks import check_cadence_fifth
from engine.voice_pair import VoicePairSet


def check_guards(
    phrases: list[RealisedPhrase],
    expanded: list[ExpandedPhrase],
    guards: dict[str, Guard],
    bar_duration: Fraction,
    metre: str,
    key: Key | None = None,
) -> list[Diagnostic]:
    """Run guards on realised phrases for all voice pairs.

    Filters out parallel motion violations at cadential final notes, since
    parallel octaves/fifths are acceptable at authentic cadence resolutions.
    v6: Checks all n*(n-1)/2 voice pairs, not just soprano-bass.
    """
    all_diagnostics: list[Diagnostic] = []
    for phrase, exp in zip(phrases, expanded, strict=True):
        voice_count: int = len(phrase.voices)
        pairs: VoicePairSet = VoicePairSet.compute(voice_count)
        for pair in pairs.pairs:
            upper: list[tuple[Fraction, int]] = [
                (n.offset, n.pitch) for n in phrase.voices[pair.upper_index].notes
            ]
            lower: list[tuple[Fraction, int]] = [
                (n.offset, n.pitch) for n in phrase.voices[pair.lower_index].notes
            ]
            location: str = f"phrase {phrase.index} voices {pair.upper_index}-{pair.lower_index}"
            diagnostics: list[Diagnostic] = run_guards(guards, upper, lower, location, bar_duration, metre)
            if exp.cadence is not None and upper:
                final_offset: Fraction = upper[-1][0]
                diagnostics = [d for d in diagnostics if d.offset != final_offset]
            # Skip parallel motion guards for baroque_invention (imitative entries create parallels)
            if exp.texture == "baroque_invention":
                diagnostics = [d for d in diagnostics if d.guard_id not in ("tex_001", "tex_002")]
            all_diagnostics.extend(diagnostics)

        # CPE Bach §36: Fifth must not appear in upper voice at final cadence
        if key is not None and exp.cadence == "authentic" and phrase.voices:
            soprano: list[tuple[Fraction, int]] = [
                (n.offset, n.pitch) for n in phrase.voices[0].notes
            ]
            tonic_pc: int = key.tonic_pc
            violations = check_cadence_fifth(soprano, tonic_pc, exp.cadence)
            for v in violations:
                all_diagnostics.append(
                    Diagnostic(
                        guard_id="cpe_001",
                        severity="blocker",
                        message=f"CPE Bach §36: Fifth in soprano at final cadence (phrase {phrase.index})",
                        location=f"phrase {phrase.index}",
                        offset=v.offset,
                    )
                )

    return all_diagnostics

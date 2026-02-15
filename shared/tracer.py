"""Pipeline tracer — dense diagnostic output per layer.

Usage:
    tracer = get_tracer()
    tracer.start("minuet", "Freudigkeit", "c_major")
    tracer.trace_L1(...)
    ...
    tracer.write()  # writes to output_dir / "minuet_Freudigkeit.trace"
"""
from __future__ import annotations

from fractions import Fraction
from io import StringIO
from pathlib import Path
from typing import Any, TYPE_CHECKING

from shared.constants import NOTE_NAMES_SHARP

if TYPE_CHECKING:
    from builder.phrase_types import PhrasePlan, PhraseResult
    from builder.types import (
        Anchor, Fault, SchemaChain, TonalPlan,
    )
    from shared.key import Key

TRACE_ENABLED: bool = False


def set_trace_enabled(enabled: bool) -> None:
    """Turn tracing on or off globally."""
    global TRACE_ENABLED
    TRACE_ENABLED = enabled


def _pitch(midi: int) -> str:
    """MIDI number to note name, e.g. 60 -> C4."""
    return f"{NOTE_NAMES_SHARP[midi % 12]}{midi // 12 - 1}"


def _key_str(key: Key) -> str:
    """Key to short string, e.g. C maj / D min."""
    mode_short: str = "maj" if key.mode == "major" else "min"
    return f"{key.tonic} {mode_short}"


def _frac(f: Fraction) -> str:
    """Fraction to compact string."""
    if f.denominator == 1:
        return str(f.numerator)
    return f"{f.numerator}/{f.denominator}"


class PipelineTracer:
    """Accumulates dense diagnostic lines, writes to .trace file."""

    def __init__(self) -> None:
        self._buf: StringIO = StringIO()
        self._name: str = ""
        self._output_dir: Path | None = None

    def start(
        self,
        genre: str,
        affect: str,
        key: str,
        output_dir: Path | None = None,
        trace_name: str | None = None,
    ) -> None:
        """Begin a new trace for one piece."""
        self._buf = StringIO()
        self._name = trace_name if trace_name else f"{genre}_{key}"
        self._output_dir = output_dir
        self._line(f"=== {genre} / {affect} / {key} ===")

    def _line(self, text: str) -> None:
        """Append one line."""
        if not TRACE_ENABLED:
            return
        self._buf.write(text + "\n")

    # ── Layer 1: Rhetorical ──────────────────────────────────────────

    def trace_L1(
        self,
        trajectory: list[str],
        tempo: int,
        rhythmic_unit: str,
        metre: str,
    ) -> None:
        """L1 output: sections, tempo, rhythm."""
        if not TRACE_ENABLED:
            return
        sections: str = " → ".join(trajectory)
        self._line(f"L1 Rhetorical: {sections} | {metre} | unit={rhythmic_unit} | tempo={tempo}")

    # ── Layer 2: Tonal ───────────────────────────────────────────────

    def trace_L2(self, tonal_plan: TonalPlan) -> None:
        """L2 output: tonal regions per section."""
        if not TRACE_ENABLED:
            return
        parts: list[str] = [
            f"{s.name}={s.key_area}({s.cadence_type})"
            for s in tonal_plan.sections
        ]
        self._line(
            f"L2 Tonal: {' | '.join(parts)} | "
            f"density={tonal_plan.density} modality={tonal_plan.modality}"
        )

    # ── Layer 3: Schematic ───────────────────────────────────────────

    def trace_L3(self, schema_chain: SchemaChain) -> None:
        """L3 output: schema sequence with key areas and cadences."""
        if not TRACE_ENABLED:
            return
        n: int = len(schema_chain.schemas)
        self._line(f"L3 Schematic: {n} schemas, boundaries={list(schema_chain.section_boundaries)}")
        for i in range(n):
            cad: str = f" [{schema_chain.cadences[i]}]" if schema_chain.cadences[i] else ""
            self._line(f"  [{i}] {schema_chain.schemas[i]:22s} {schema_chain.key_areas[i]}{cad}")

    # ── Layer 4: Metric ──────────────────────────────────────────────

    def trace_L4(
        self,
        bar_assignments: dict[str, tuple[int, int]],
        anchors: list[Anchor],
        total_bars: int,
    ) -> None:
        """L4 output: bar layout and anchors."""
        if not TRACE_ENABLED:
            return
        bar_parts: list[str] = [
            f"{name}={s}-{e}" for name, (s, e) in bar_assignments.items()
        ]
        self._line(f"L4 Metric: {total_bars} bars | {' | '.join(bar_parts)}")
        self._line(f"  {len(anchors)} anchors:")
        for a in anchors:
            self._line(
                f"  {a.bar_beat:>5s}: U={a.upper_degree} L={a.lower_degree} "
                f"{_key_str(key=a.local_key):7s} ({a.schema}.{a.stage}) {a.section}"
            )

    # ── Layer 5: Phrase plans ────────────────────────────────────────

    def trace_L5(self, plans: tuple[PhrasePlan, ...]) -> None:
        """L5 output: phrase plan sequence."""
        if not TRACE_ENABLED:
            return
        self._line(f"L5 Phrases: {len(plans)} plans")
        for i, p in enumerate(plans):
            cad_tag: str = " CAD" if p.is_cadential else ""
            deg_up: str = ",".join(str(d) for d in p.degrees_upper)
            deg_lo: str = ",".join(str(d) for d in p.degrees_lower)
            seq_tag: str = ""
            keys_unique: list[str] = []
            prev: str = ""
            for dk in p.degree_keys:
                ks: str = _key_str(key=dk)
                if ks != prev:
                    keys_unique.append(ks)
                    prev = ks
            # Only show seq tag if multiple unique keys (sequential modulation)
            if len(keys_unique) > 1:
                seq_tag = f" seq[{'>'.join(keys_unique)}]"
            self._line(
                f"  [{i}] {p.schema_name:22s} bars {p.start_bar}-{p.start_bar + p.bar_span - 1:>2d} "
                f"{_key_str(key=p.local_key):7s} S({deg_up}) B({deg_lo}){cad_tag}{seq_tag}"
            )

    # ── Layer 6: Phrase results ──────────────────────────────────────

    def trace_phrase_result(
        self,
        index: int,
        plan: PhrasePlan,
        result: PhraseResult,
    ) -> None:
        """One phrase's composed output."""
        if not TRACE_ENABLED:
            return
        s_pitches: str = " ".join(_pitch(midi=n.pitch) for n in result.upper_notes)
        b_pitches: str = " ".join(_pitch(midi=n.pitch) for n in result.lower_notes)
        self._line(
            f"  [{index}] {plan.schema_name:22s} "
            f"S: {s_pitches}"
        )
        self._line(
            f"       {'':22s} "
            f"B: {b_pitches}"
        )
        if result.soprano_figures:
            self._line(
                f"       {'':22s} "
                f"fig: {' '.join(result.soprano_figures)}"
            )
        if result.bass_pattern_name:
            self._line(
                f"       {'':22s} "
                f"bass_pattern: {result.bass_pattern_name}"
            )

    def trace_L6_header(self, total_upper: int, total_lower: int) -> None:
        """L6 composition summary header."""
        if not TRACE_ENABLED:
            return
        self._line(f"L6 Composition: {total_upper} soprano + {total_lower} bass notes")

    # ── Layer 4b: Thematic plan ──────────────────────────────────

    def trace_thematic_plan(
        self,
        plan: tuple[Any, ...],  # tuple[BeatRole, ...]
        entry_count: int,
        total_bars: int,
        metre: str,
    ) -> None:
        """L4b Thematic plan summary: bar table with roles per voice.

        Shows one line per bar with both voices' roles and keys.
        Includes coverage statistics per role.
        """
        if not TRACE_ENABLED:
            return

        # Parse metre to get beats per bar
        metre_parts: list[str] = metre.split("/")
        beats_per_bar: int = int(metre_parts[0])

        # Build bar-level view
        # Group roles by (bar, voice)
        bar_voice_roles: dict[tuple[int, int], list[Any]] = {}
        for role in plan:
            key: tuple[int, int] = (role.bar, role.voice)
            if key not in bar_voice_roles:
                bar_voice_roles[key] = []
            bar_voice_roles[key].append(role)

        # Count total beats per role across both voices
        from collections import Counter
        role_counts: Counter = Counter()
        for role in plan:
            role_counts[role.role.value.upper()] += 1

        # Compute thematic beat count (non-FREE)
        thematic_beats: int = sum(
            count for role_name, count in role_counts.items()
            if role_name != "FREE"
        )
        total_beats: int = len(plan)
        thematic_pct: float = (thematic_beats / total_beats * 100) if total_beats > 0 else 0.0

        # Header
        self._line(f"L4b Thematic: {entry_count} entries parsed, {total_bars} bars, "
                  f"{thematic_beats // beats_per_bar} thematic ({thematic_pct:.1f}%)")

        # Role coverage line
        role_parts: list[str] = [
            f"{role_name}={count}"
            for role_name, count in sorted(role_counts.items())
        ]
        self._line(f"  Roles: {' '.join(role_parts)}")

        # Bar table header
        self._line(f"  Bar  Upper               Lower")

        # One line per bar
        for bar in range(1, total_bars + 1):
            # Get roles for voice 0 (upper)
            v0_roles: list[Any] = bar_voice_roles.get((bar, 0), [])
            # Get roles for voice 1 (lower)
            v1_roles: list[Any] = bar_voice_roles.get((bar, 1), [])

            # Collapse beats within bar
            v0_str: str = self._collapse_bar_roles(v0_roles)
            v1_str: str = self._collapse_bar_roles(v1_roles)

            self._line(f"  {bar:3d}  {v0_str:19s} {v1_str}")

    def _collapse_bar_roles(self, roles: list[Any]) -> str:
        """Collapse beat roles within a bar into compact string.

        Returns:
            - "SUBJECT I" if all beats are SUBJECT in key I
            - "SUBJECT+ I" if first beat is SUBJECT but others differ
            - "---" if all FREE and no material
            - "FREE" if FREE with material
        """
        if not roles:
            return "---"

        # Check if all beats have same role
        first_role = roles[0]
        all_same: bool = all(
            r.role == first_role.role and r.material == first_role.material
            for r in roles
        )

        role_name: str = first_role.role.value.upper()

        # Special handling for FREE
        if first_role.role.value == "free":
            if first_role.material is None:
                return "---"
            return "FREE"

        # Format key string
        key_str: str = _key_str(key=first_role.material_key)

        if all_same:
            return f"{role_name:8s} {key_str}"
        else:
            return f"{role_name}+{' ' * (7 - len(role_name))} {key_str}"

    # ── Layer 6t: Thematic render ────────────────────────────────

    def trace_thematic_render(
        self,
        bar: int,
        voice_name: str,
        role_name: str,
        key_str: str,
        note_count: int,
        low_pitch: int,
        high_pitch: int,
    ) -> None:
        """L6t Render dispatch: one line per entry per voice.

        Shows bar, voice, role, key, note count, and pitch range.
        """
        if not TRACE_ENABLED:
            return

        if note_count == 0:
            self._line(f"L6t Render: bar {bar:2d} {voice_name} ---")
        else:
            low_str: str = _pitch(midi=low_pitch)
            high_str: str = _pitch(midi=high_pitch)
            self._line(
                f"L6t Render: bar {bar:2d} {voice_name} {role_name:7s} {key_str:7s} "
                f"-> {note_count:2d} notes {low_str}..{high_str}"
            )

    def trace_thematic_coverage(
        self,
        plan: tuple[Any, ...],  # tuple[BeatRole, ...]
        total_bars: int,
        beats_per_bar: int,
    ) -> None:
        """L6t Coverage summary: thematic vs FREE beats with largest gap.

        Shows total thematic beat count, percentage, FREE count, and
        largest contiguous run of bars where both voices are FREE.
        """
        if not TRACE_ENABLED:
            return

        # Count FREE beats
        free_beats: int = sum(1 for role in plan if role.role.value == "free")
        total_beats: int = len(plan)
        thematic_beats: int = total_beats - free_beats
        thematic_pct: float = (thematic_beats / total_beats * 100) if total_beats > 0 else 0.0

        # Find largest FREE gap (bars where both voices are FREE)
        # Build bar-level FREE status
        bar_both_free: list[bool] = []
        for bar in range(1, total_bars + 1):
            # Check if both voices are FREE for all beats in this bar
            bar_roles: list[Any] = [r for r in plan if r.bar == bar]
            v0_roles: list[Any] = [r for r in bar_roles if r.voice == 0]
            v1_roles: list[Any] = [r for r in bar_roles if r.voice == 1]

            v0_all_free: bool = all(r.role.value == "free" for r in v0_roles)
            v1_all_free: bool = all(r.role.value == "free" for r in v1_roles)

            bar_both_free.append(v0_all_free and v1_all_free)

        # Scan for largest contiguous run
        max_gap_start: int = 0
        max_gap_end: int = 0
        current_gap_start: int | None = None

        for bar_idx, is_free in enumerate(bar_both_free):
            bar_num: int = bar_idx + 1
            if is_free:
                if current_gap_start is None:
                    current_gap_start = bar_num
            else:
                if current_gap_start is not None:
                    # End of gap
                    gap_len: int = bar_num - current_gap_start
                    if gap_len > (max_gap_end - max_gap_start):
                        max_gap_start = current_gap_start
                        max_gap_end = bar_num - 1
                    current_gap_start = None

        # Handle gap extending to end
        if current_gap_start is not None:
            gap_len = total_bars - current_gap_start + 1
            if gap_len > (max_gap_end - max_gap_start + 1):
                max_gap_start = current_gap_start
                max_gap_end = total_bars

        # Format gap string
        gap_str: str = ""
        if max_gap_end > 0:
            gap_str = f" | largest FREE gap: bars {max_gap_start}-{max_gap_end}"

        self._line(
            f"L6t Coverage: {thematic_beats}/{total_beats} beats thematic ({thematic_pct:.1f}%) "
            f"| FREE {free_beats}{gap_str}"
        )

    # ── Faults ───────────────────────────────────────────────────────

    def trace_faults(self, faults: list[Fault]) -> None:
        """Post-composition fault summary."""
        if not TRACE_ENABLED:
            return
        if not faults:
            self._line("Faults: 0")
            return
        self._line(f"Faults: {len(faults)}")
        for f in faults:
            self._line(f"  {f.bar_beat}: {f.category} — {f.message}")

    # ── Output ───────────────────────────────────────────────────────

    def get_output(self) -> str:
        """Return accumulated trace text."""
        return self._buf.getvalue()

    def write(self, output_dir: Path | None = None) -> Path | None:
        """Write trace to <name>.trace in output_dir. Returns path or None."""
        if not TRACE_ENABLED:
            return None
        target: Path | None = output_dir or self._output_dir
        if target is None:
            return None
        path: Path = target / f"{self._name}.trace"
        path.write_text(self._buf.getvalue(), encoding="utf-8")
        return path

    def clear(self) -> None:
        """Discard buffer."""
        self._buf = StringIO()
        self._name = ""


# ── Module-level singleton ───────────────────────────────────────────

_tracer: PipelineTracer | None = None


def get_tracer() -> PipelineTracer:
    """Return the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = PipelineTracer()
    return _tracer


def reset_tracer() -> PipelineTracer:
    """Reset and return a fresh tracer."""
    global _tracer
    _tracer = PipelineTracer()
    return _tracer

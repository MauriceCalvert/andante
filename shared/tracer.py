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
        Anchor, Composition, Fault, SchemaChain, TonalPlan,
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
    ) -> None:
        """Begin a new trace for one piece."""
        self._buf = StringIO()
        self._name = f"{genre}_{key}"
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

"""Pipeline Tracer - Hierarchical logging for andante pipeline debugging.

Trace levels:
    0: No tracing
    1: High-level layer summaries (config, layer outputs)
    2: Mid-level details (schema chains, bar assignments, anchors)
    3: Fine-grained details (individual notes, figure selections)

Usage:
    from shared.tracer import get_tracer, set_trace_level
    set_trace_level(2)
    tracer = get_tracer()
    tracer.L1("Rhetorical", trajectory=trajectory, tempo=tempo)
"""
from __future__ import annotations
from fractions import Fraction
from io import StringIO
from pathlib import Path
from typing import Any

TRACE_LEVEL: int = 0
MAX_LIST_ITEMS: int = 10
MAX_VALUE_LEN: int = 80


def set_trace_level(level: int) -> None:
    """Set global trace level (0-3)."""
    global TRACE_LEVEL
    assert 0 <= level <= 3, f"Trace level must be 0-3, got {level}"
    TRACE_LEVEL = level


def get_trace_level() -> int:
    """Get current trace level."""
    return TRACE_LEVEL


class PipelineTracer:
    """Hierarchical tracer with indentation for nested output."""

    def __init__(self) -> None:
        self._buffer: StringIO = StringIO()
        self._indent: int = 0

    def _format_value(self, value: Any) -> str:
        """Format a value for output, truncating if needed."""
        if isinstance(value, Fraction):
            return f"{float(value):.3g}"
        if isinstance(value, dict):
            items = [f"{k}={self._format_value(value=v)}" for k, v in list(value.items())[:MAX_LIST_ITEMS]]
            suffix = f"...+{len(value) - MAX_LIST_ITEMS}" if len(value) > MAX_LIST_ITEMS else ""
            return "{" + ", ".join(items) + suffix + "}"
        if isinstance(value, (list, tuple)):
            if len(value) > MAX_LIST_ITEMS:
                items = [self._format_value(value=v) for v in value[:MAX_LIST_ITEMS]]
                return "[" + ", ".join(items) + f"...+{len(value) - MAX_LIST_ITEMS}]"
            return "[" + ", ".join(self._format_value(value=v) for v in value) + "]"
        result = str(value)
        if len(result) > MAX_VALUE_LEN:
            return result[:MAX_VALUE_LEN] + "..."
        return result

    def _write(self, min_level: int, prefix: str, message: str, **kwargs: Any) -> None:
        """Write a trace line if current level >= min_level."""
        if TRACE_LEVEL < min_level:
            return
        indent_str = "  " * self._indent
        if kwargs:
            parts = [f"{k}={self._format_value(value=v)}" for k, v in kwargs.items()]
            detail = ", ".join(parts)
            line = f"{indent_str}[{prefix}] {message}: {detail}"
        else:
            line = f"{indent_str}[{prefix}] {message}"
        self._buffer.write(line + "\n")

    def _write_sub(self, min_level: int, message: str) -> None:
        """Write a sub-item line (indented, no prefix)."""
        if TRACE_LEVEL < min_level:
            return
        indent_str = "  " * (self._indent + 1)
        self._buffer.write(f"{indent_str}{message}\n")

    # Level 1: High-level summaries
    def config(self, genre: str, affect: str, key: str) -> None:
        """L1: Configuration summary."""
        self._write(min_level=1, prefix="Config", message=f"genre={genre}, affect={affect}, key={key}")

    def L1(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer output summary."""
        self._write(1, f"L1 {layer}", "output", **kwargs)

    def L2(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer 2 output summary."""
        self._write(1, f"L2 {layer}", "output", **kwargs)

    def L3(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer 3 output summary."""
        self._write(1, f"L3 {layer}", "output", **kwargs)

    def L4(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer 4 output summary."""
        self._write(1, f"L4 {layer}", "output", **kwargs)

    def L5(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer 5 output summary."""
        self._write(1, f"L5 {layer}", "output", **kwargs)

    def L6(self, layer: str, **kwargs: Any) -> None:
        """L1: Layer 6 output summary."""
        self._write(1, f"L6 {layer}", "output", **kwargs)

    # Level 2: Mid-level details
    def schema_chain(self, schemas: tuple[str, ...]) -> None:
        """L2: Schema chain listing."""
        self._write(min_level=2, prefix="L3 Detail", message=f"schema_chain has {len(schemas)} schemas")
        for i, s in enumerate(schemas):
            self._write_sub(min_level=2, message=f"[{i}] {s}")

    def bar_assignments(self, assignments: dict[str, tuple[int, int]]) -> None:
        """L2: Bar assignments per section."""
        self._write(min_level=2, prefix="L4 Detail", message="bar_assignments")
        for name, (start, end) in assignments.items():
            self._write_sub(min_level=2, message=f"{name}: bars {start}-{end}")

    def anchors_summary(self, anchors: list, limit: int = 10) -> None:
        """L2: Anchor summary with limit."""
        self._write(min_level=2, prefix="L4 Detail", message=f"anchors={len(anchors)}")
        for a in anchors[:limit]:
            self._write_sub(min_level=2, message=f"bar {a.bar_beat}: U={a.upper_degree} L={a.lower_degree} key={a.local_key.tonic} ({a.schema})")
        if len(anchors) > limit:
            self._write_sub(min_level=2, message=f"...and {len(anchors) - limit} more anchors")

    def passage_assignments(self, assignments: list) -> None:
        """L2: Passage assignments listing."""
        self._write(min_level=2, prefix="L5 Detail", message=f"{len(assignments)} passage assignments")
        for pa in assignments:
            self._write_sub(min_level=2, message=f"bars {pa.start_bar}-{pa.end_bar}: {pa.function}, lead={pa.lead_voice}")

    def tonal_plan(self, plan: dict[str, tuple[str, ...]]) -> None:
        """L2: Tonal plan per section."""
        self._write(min_level=2, prefix="L2 Detail", message="tonal_plan")
        for section, areas in plan.items():
            self._write_sub(min_level=2, message=f"{section}: {' -> '.join(areas)}")

    # Level 3: Fine-grained details
    def anchor(self, bar_beat: str, upper: int, lower: int, key: str, schema: str, stage: int, section: str = "") -> None:
        """L3: Individual anchor detail."""
        self._write(3, "Anchor", f"{bar_beat}", upper=upper, lower=lower, key=key, schema=schema, stage=stage, section=section)

    def figure_selection(self, bar: int, figure: str, density: str) -> None:
        """L3: Figure selection for bar."""
        self._write(3, "Figure", f"bar {bar}", figure=figure, density=density)

    def bass_pattern(self, bar: int, pattern: str, degree: int) -> None:
        """L3: Bass pattern for bar."""
        self._write(3, "Bass", f"bar {bar}", pattern=pattern, degree=degree)

    def note_output(self, voice: str, offset: Fraction, pitch: int, duration: Fraction) -> None:
        """L3: Individual note output."""
        self._write(3, "Note", voice, offset=offset, pitch=pitch, duration=duration)

    def expansion(self, bar: int, function: str, expansion: str) -> None:
        """L3: Voice expansion for bar."""
        self._write(3, "Expansion", f"bar {bar}", function=function, expansion=expansion)

    def warning(self, location: str, message: str, **kwargs: Any) -> None:
        """Any level: Warning message."""
        self._write(1, "WARN", f"{location}: {message}", **kwargs)

    def error(self, location: str, message: str, **kwargs: Any) -> None:
        """Any level: Error message."""
        self._write(1, "ERROR", f"{location}: {message}", **kwargs)

    # Context managers for nested sections
    def section(self, name: str, min_level: int = 2) -> "TracerSection":
        """Create a nested section with increased indentation."""
        return TracerSection(tracer=self, name=name, min_level=min_level)

    # Output methods
    def get_output(self) -> str:
        """Get accumulated trace output."""
        return self._buffer.getvalue()

    def write_to_file(self, path: Path | str) -> None:
        """Write trace output to file."""
        Path(path).write_text(self._buffer.getvalue(), encoding="utf-8")

    def clear(self) -> None:
        """Clear the trace buffer."""
        self._buffer = StringIO()
        self._indent = 0


class TracerSection:
    """Context manager for nested trace sections."""

    def __init__(self, tracer: PipelineTracer, name: str, min_level: int) -> None:
        self._tracer = tracer
        self._name = name
        self._min_level = min_level

    def __enter__(self) -> "TracerSection":
        if TRACE_LEVEL >= self._min_level:
            self._tracer._write(min_level=self._min_level, prefix="Section", message=self._name)
            self._tracer._indent += 1
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if TRACE_LEVEL >= self._min_level:
            self._tracer._indent -= 1


_tracer: PipelineTracer | None = None


def get_tracer() -> PipelineTracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = PipelineTracer()
    return _tracer


def reset_tracer() -> PipelineTracer:
    """Reset and return a fresh tracer instance."""
    global _tracer
    _tracer = PipelineTracer()
    return _tracer

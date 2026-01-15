"""Pipeline Tracer - Minimal logging for andante pipeline debugging.

Disabled by default. Enable with TRACE_ENABLED=True or tracer.enable().
Only logs errors and warnings unless explicitly enabled.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

MAX_EVENTS: int = 500  # Limit events to prevent memory bloat
MAX_DETAIL_LEN: int = 50  # Truncate long detail values


@dataclass
class TraceEvent:
    """Single trace event."""
    stage: str
    location: str
    event: str
    details: dict[str, Any] = field(default_factory=dict)
    level: int = 0


class PipelineTracer:
    """Collects trace information during pipeline execution."""

    def __init__(self) -> None:
        self.events: list[TraceEvent] = []
        self.indent_level: int = 0
        self._enabled: bool = False

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    def trace(self, stage: str, location: str, event: str, **details: Any) -> None:
        if not self._enabled:
            return
        # Limit total events
        if len(self.events) >= MAX_EVENTS:
            return
        clean: dict[str, Any] = {}
        for k, v in details.items():
            if isinstance(v, Fraction):
                clean[k] = f"{float(v):.2f}"
            elif isinstance(v, (list, tuple)):
                if len(v) > 5:
                    clean[k] = f"[{len(v)} items]"
                else:
                    clean[k] = [f"{float(x):.2f}" if isinstance(x, Fraction) else str(x)[:MAX_DETAIL_LEN] for x in v]
            elif isinstance(v, str) and len(v) > MAX_DETAIL_LEN:
                clean[k] = v[:MAX_DETAIL_LEN] + "..."
            else:
                clean[k] = v
        self.events.append(TraceEvent(stage, location, event, clean, self.indent_level))

    def enter(self, stage: str, location: str, **details: Any) -> None:
        self.trace(stage, location, "ENTER", **details)
        self.indent_level += 1

    def exit(self, stage: str, location: str, **details: Any) -> None:
        self.indent_level = max(0, self.indent_level - 1)
        self.trace(stage, location, "EXIT", **details)

    def phrase(self, index: int, treatment: str, bars: int, **details: Any) -> None:
        self.trace("EXPAND", f"p{index}", f"{treatment}/{bars}b")

    def voice(self, location: str, voice: str, pitches: list, durations: list) -> None:
        self.trace("VOICE", f"{location}/{voice}", f"n={len(pitches)}")

    def realise(self, location: str, voice: str, notes: int, **details: Any) -> None:
        self.trace("REALISE", f"{location}/{voice}", f"n={notes}")

    def fix(self, location: str, event: str, **details: Any) -> None:
        self.trace("FIX", location, event, **details)

    def guard(self, guard_id: str, severity: str, message: str, location: str) -> None:
        self.trace("GUARD", location, f"{severity}: {guard_id} - {message}")

    def warning(self, location: str, message: str, **details: Any) -> None:
        self.trace("WARNING", location, message, **details)

    def error(self, location: str, message: str, **details: Any) -> None:
        self.trace("ERROR", location, message, **details)

    def format_log(self) -> str:
        """Format log concisely - one line per event."""
        lines: list[str] = [f"TRACE ({len(self.events)} events)"]
        for evt in self.events:
            detail_str = " ".join(f"{k}={v}" for k, v in evt.details.items()) if evt.details else ""
            lines.append(f"{'  '*evt.level}{evt.stage}:{evt.location} {evt.event} {detail_str}".rstrip())
        return "\n".join(lines)

    def write_log(self, path: str) -> None:
        Path(path).write_text(self.format_log(), encoding="utf-8")

    def clear(self) -> None:
        self.events = []
        self.indent_level = 0


_tracer: PipelineTracer | None = None
TRACE_ENABLED: bool = False  # Disabled by default; enable for debugging


def get_tracer() -> PipelineTracer:
    global _tracer
    if _tracer is None:
        _tracer = PipelineTracer()
        if TRACE_ENABLED:
            _tracer.enable()
    return _tracer


def reset_tracer() -> PipelineTracer:
    global _tracer
    _tracer = PipelineTracer()
    return _tracer


def trace(stage: str, location: str, event: str, **details: Any) -> None:
    get_tracer().trace(stage, location, event, **details)

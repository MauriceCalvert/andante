"""Pipeline Tracer - Detailed logging for andante pipeline debugging."""
from __future__ import annotations
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

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
        clean: dict[str, Any] = {}
        for k, v in details.items():
            if isinstance(v, Fraction):
                clean[k] = f"{float(v):.4f}"
            elif isinstance(v, (list, tuple)):
                clean[k] = [f"{float(x):.4f}" if isinstance(x, Fraction) else str(x) for x in v]
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
        self.trace("EXPAND", f"phrase_{index}", f"treatment={treatment} bars={bars}", **details)

    def voice(self, location: str, voice: str, pitches: list, durations: list) -> None:
        total: Fraction = sum(durations, Fraction(0)) if durations else Fraction(0)
        self.trace("VOICE", f"{location}/{voice}", f"notes={len(pitches)} total={float(total):.4f}",
                   pitches=pitches, durations=durations)

    def realise(self, location: str, voice: str, notes: int, **details: Any) -> None:
        self.trace("REALISE", f"{location}/{voice}", f"notes={notes}", **details)

    def fix(self, location: str, event: str, **details: Any) -> None:
        self.trace("FIX", location, event, **details)

    def guard(self, guard_id: str, severity: str, message: str, location: str) -> None:
        self.trace("GUARD", location, f"{severity}: {guard_id} - {message}")

    def warning(self, location: str, message: str, **details: Any) -> None:
        self.trace("WARNING", location, message, **details)

    def error(self, location: str, message: str, **details: Any) -> None:
        self.trace("ERROR", location, message, **details)

    def format_log(self) -> str:
        lines: list[str] = ["=" * 70, "ANDANTE PIPELINE TRACE", "=" * 70, ""]
        current_stage: str = ""
        for evt in self.events:
            indent: str = "  " * evt.level
            if evt.stage != current_stage:
                if current_stage:
                    lines.append("")
                lines.append(f"--- {evt.stage} ---")
                current_stage = evt.stage
            lines.append(f"{indent}[{evt.location}] {evt.event}")
            if evt.details:
                for key, value in evt.details.items():
                    if isinstance(value, list) and len(value) > 12:
                        val_str: str = f"[{len(value)} items: {value[:3]}...{value[-2:]}]"
                    else:
                        val_str = str(value)
                    lines.append(f"{indent}    {key}: {val_str}")
        lines.extend(["", "=" * 70, f"Total events: {len(self.events)}", "=" * 70])
        return "\n".join(lines)

    def write_log(self, path: str) -> None:
        Path(path).write_text(self.format_log(), encoding="utf-8")

    def clear(self) -> None:
        self.events = []
        self.indent_level = 0


_tracer: PipelineTracer | None = None
TRACE_ENABLED: bool = True  # Enable during development


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

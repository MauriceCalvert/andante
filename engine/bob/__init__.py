"""Bob diagnostic module - automated voice-leading and phrase analysis."""
from engine.bob.checker import diagnose
from engine.bob.formatter import Issue, Report

__all__ = ["diagnose", "Issue", "Report"]

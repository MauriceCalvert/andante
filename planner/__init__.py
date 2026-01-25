"""Planner package for Andante.

Entry point: generate(genre, affect, key=None) -> NoteFile

When key is omitted, derives appropriate key from affect using Mattheson's
Affektenlehre (baroque_theory.md section 8.1).
"""
from planner.planner import generate, generate_to_files


__all__ = ["generate", "generate_to_files"]

"""E1 Parser: YAML -> PieceAST with validation.

Subject is the authoritative representation of thematic material.
Counter-subject is auto-generated via CSP if not provided in YAML.
"""
from fractions import Fraction
from pathlib import Path

import yaml

from engine.engine_types import EpisodeAST, PhraseAST, PieceAST, SectionAST
from engine.validate import validate_yaml
from planner.subject import Subject


def parse_fraction(value: str) -> Fraction:
    """Parse fraction string like '1/4' to Fraction."""
    if "/" in str(value):
        num, den = str(value).split("/")
        return Fraction(int(num), int(den))
    return Fraction(value)


def parse_subject(material: dict, mode: str, voice_count: int, genre: str = "") -> Subject:
    """Parse subject and optional counter-subject into Subject object.

    If counter_subject is provided in YAML, it's used directly.
    Otherwise, CSP solver generates one with optimized rhythm.
    """
    subject_data: dict = material["subject"]
    degrees: tuple[int, ...] = tuple(subject_data["degrees"])
    durations: tuple[Fraction, ...] = tuple(parse_fraction(d) for d in subject_data["durations"])
    bars: int = subject_data["bars"]
    subj: Subject = Subject(degrees, durations, bars, mode, genre=genre, voice_count=voice_count)
    if "counter_subject" in material:
        cs_data: dict = material["counter_subject"]
        cs_degrees: tuple[int, ...] = tuple(cs_data["degrees"])
        cs_durations: tuple[Fraction, ...] = tuple(parse_fraction(d) for d in cs_data["durations"])
        subj._cs_degrees = cs_degrees
        subj._cs_durations = cs_durations
    return subj


def parse_phrase(data: dict) -> PhraseAST:
    """Parse phrase dictionary to PhraseAST."""
    voice_assignments: tuple[str, ...] | None = None
    if "voices" in data:
        voices_dict: dict = data["voices"]
        assignments: list[str] = []
        for voice_name in ("soprano", "alto", "tenor", "bass"):
            if voice_name in voices_dict:
                assignments.append(voices_dict[voice_name])
        if assignments:
            voice_assignments = tuple(assignments)
    # Strip figurae annotations like "statement[fuga+lombardic]" -> "statement"
    treatment_raw: str = data["treatment"]
    treatment: str = treatment_raw.split("[")[0] if "[" in treatment_raw else treatment_raw
    return PhraseAST(
        index=data["index"],
        bars=data["bars"],
        tonal_target=data["tonal_target"],
        cadence=data.get("cadence"),
        treatment=treatment,
        surprise=data.get("surprise"),
        is_climax=data.get("is_climax", False),
        articulation=data.get("articulation"),
        rhythm=data.get("rhythm"),
        device=data.get("device"),
        gesture=data.get("gesture"),
        energy=data.get("energy"),
        texture=data.get("texture"),  # Phrase-level texture override
        voice_assignments=voice_assignments,
    )


def parse_episode(data: dict) -> EpisodeAST:
    """Parse episode dictionary to EpisodeAST."""
    phrases: tuple[PhraseAST, ...] = tuple(parse_phrase(p) for p in data["phrases"])
    return EpisodeAST(
        type=data["type"],
        bars=data["bars"],
        texture=data.get("texture", "polyphonic"),
        phrases=phrases,
        is_transition=data.get("is_transition", False),
    )


def parse_section(data: dict) -> SectionAST:
    """Parse section dictionary to SectionAST."""
    episodes: tuple[EpisodeAST, ...] = tuple(parse_episode(e) for e in data["episodes"])
    return SectionAST(
        label=data["label"],
        tonal_path=tuple(data["tonal_path"]),
        final_cadence=data["final_cadence"],
        episodes=episodes,
    )


def parse_yaml(yaml_str: str) -> PieceAST:
    """Parse YAML string to PieceAST."""
    data: dict = yaml.safe_load(yaml_str)
    validate_yaml(data)
    frame: dict = data["frame"]
    material: dict = data["material"]
    structure: dict = data["structure"]
    sections: tuple[SectionAST, ...] = tuple(parse_section(s) for s in structure["sections"])
    upbeat: Fraction = parse_fraction(frame.get("upbeat", "0"))
    form: str = frame.get("form", "through_composed")
    mode: str = frame["mode"]
    voice_count: int = frame["voices"]
    brief: dict = data.get("brief", {})
    genre: str = brief.get("genre", "")
    subject: Subject = parse_subject(material, mode, voice_count, genre)
    virtuosic: bool = brief.get("virtuosic", False)
    return PieceAST(
        key=frame["key"],
        mode=mode,
        metre=frame["metre"],
        tempo=frame["tempo"],
        voices=voice_count,
        subject=subject,
        sections=sections,
        arc=structure["arc"],
        upbeat=upbeat,
        form=form,
        virtuosic=virtuosic,
    )


def parse_file(path: Path) -> PieceAST:
    """Parse YAML file to PieceAST."""
    with open(path, encoding="utf-8") as f:
        return parse_yaml(f.read())

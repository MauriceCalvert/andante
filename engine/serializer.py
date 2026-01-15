"""Serializer: ExpandedPhrase list -> Expanded YAML."""
from fractions import Fraction

import yaml

from engine.engine_types import ExpandedPhrase, PieceAST
from shared.pitch import FloatingNote, MidiPitch, Rest, is_rest
from shared.types import VoiceMaterial


def fraction_representer(dumper: yaml.Dumper, data: Fraction) -> yaml.Node:
    """Represent Fraction as string for YAML."""
    if data == 0:
        return dumper.represent_int(0)
    return dumper.represent_str(str(data))


class InlineList(list):
    """Marker for lists that should be inline."""
    pass


def inline_list_representer(dumper: yaml.Dumper, data: InlineList) -> yaml.Node:
    """Represent InlineList with flow style."""
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)


yaml.add_representer(Fraction, fraction_representer)
yaml.add_representer(InlineList, inline_list_representer)


def _serialize_voice(voice: VoiceMaterial) -> dict:
    """Serialize a VoiceMaterial to dictionary.

    Pipeline is diatonic - all pitches should be FloatingNote (scale degrees).
    Uses degree: 0 for rests per design decision.
    MidiPitch should never appear here - realiser converts degrees to MIDI.
    """
    degrees: list[int] = []
    for p in voice.pitches:
        if is_rest(p):
            degrees.append(0)
        elif isinstance(p, FloatingNote):
            degrees.append(p.degree)
        elif isinstance(p, MidiPitch):
            # This is an architectural violation - MIDI should not appear before realiser
            raise ValueError(
                f"MidiPitch found in voice {voice.voice_index} before realisation. "
                "Pipeline should be diatonic (FloatingNote) until realiser."
            )
        else:
            degrees.append(0)
    return {
        "voice_index": voice.voice_index,
        "degrees": InlineList(degrees),
        "durations": InlineList(str(d) for d in voice.durations),
    }


def _serialize_phrase(phrase: ExpandedPhrase) -> dict:
    """Serialize an ExpandedPhrase to dictionary."""
    result: dict = {
        "index": phrase.index,
        "bars": phrase.bars,
        "tonal_target": phrase.tonal_target,
        "voices": [_serialize_voice(v) for v in phrase.voices.voices],
    }
    if phrase.cadence:
        result["cadence"] = phrase.cadence
    if phrase.is_climax:
        result["is_climax"] = phrase.is_climax
    if phrase.energy:
        result["energy"] = phrase.energy
    if phrase.texture != "polyphonic":
        result["texture"] = phrase.texture
    if phrase.episode_type:
        result["episode_type"] = phrase.episode_type
    if phrase.articulation:
        result["articulation"] = phrase.articulation
    if phrase.gesture:
        result["gesture"] = phrase.gesture
    if phrase.surprise:
        result["surprise"] = phrase.surprise
    return result


def expanded_to_dict(piece: PieceAST, phrases: list[ExpandedPhrase]) -> dict:
    """Convert expanded piece to dictionary for YAML serialization."""
    return {
        "frame": {
            "key": piece.key,
            "mode": piece.mode,
            "metre": piece.metre,
            "tempo": piece.tempo,
            "voices": piece.voices,
            "upbeat": piece.upbeat,
            "form": piece.form,
        },
        "phrases": [_serialize_phrase(p) for p in phrases],
    }


def serialize_expanded(piece: PieceAST, phrases: list[ExpandedPhrase]) -> str:
    """Serialize expanded piece to YAML string."""
    data: dict = expanded_to_dict(piece, phrases)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)

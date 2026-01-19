"""Plan serializer: Plan -> YAML.

Two serializers:
- serialize_plan(): For legacy Plan with Episode/Phrase hierarchy
- serialize_schema_plan(): For SchemaPlan with schema-based structure
"""
from fractions import Fraction
from typing import TYPE_CHECKING

import yaml

from planner.plannertypes import DerivedMotif, Material, Motif, Plan

if TYPE_CHECKING:
    from planner.planner import SchemaPlan


def fraction_representer(dumper: yaml.Dumper, data: Fraction) -> yaml.Node:
    """Represent Fraction as string for YAML, or int if zero."""
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


def _serialize_motif(motif: Motif) -> dict:
    """Serialize a Motif to dictionary.

    Outputs pitches (MIDI) if available, otherwise degrees.
    """
    result: dict = {
        "durations": InlineList(str(d) for d in motif.durations),
        "bars": motif.bars,
    }
    if motif.pitches is not None:
        result["pitches"] = InlineList(motif.pitches)
        if motif.source_key is not None:
            result["source_key"] = motif.source_key
    elif motif.degrees is not None:
        result["degrees"] = InlineList(motif.degrees)
    return result


def _serialize_material(material: Material) -> dict:
    """Serialize Material to dictionary."""
    result: dict = {"subject": _serialize_motif(material.subject)}
    if material.counter_subject is not None:
        result["counter_subject"] = _serialize_motif(material.counter_subject)
    return result


def plan_to_dict(plan: Plan) -> dict:
    """Convert Plan to dictionary for YAML serialization."""
    return {
        "brief": {
            "affect": plan.brief.affect,
            "genre": plan.brief.genre,
            "forces": plan.brief.forces,
            "bars": plan.brief.bars,
        },
        "frame": {
            "key": plan.frame.key,
            "mode": plan.frame.mode,
            "metre": plan.frame.metre,
            "tempo": plan.frame.tempo,
            "voices": plan.frame.voices,
            "upbeat": plan.frame.upbeat,
            "form": plan.frame.form,
        },
        "material": _serialize_material(plan.material),
        "structure": {
            "arc": plan.structure.arc,
            "sections": [
                {
                    "label": section.label,
                    "tonal_path": InlineList(section.tonal_path),
                    "final_cadence": section.final_cadence,
                    "episodes": [
                        {
                            "type": episode.type,
                            "bars": episode.bars,
                            "texture": episode.texture,
                            "is_transition": episode.is_transition,
                            "phrases": [
                                {
                                    "index": phrase.index,
                                    "bars": phrase.bars,
                                    "tonal_target": phrase.tonal_target,
                                    "cadence": phrase.cadence,
                                    "treatment": phrase.treatment,
                                    "surprise": phrase.surprise,
                                    "is_climax": phrase.is_climax,
                                    "energy": phrase.energy,
                                    "harmony": InlineList(phrase.harmony) if phrase.harmony else None,
                                }
                                for phrase in episode.phrases
                            ],
                        }
                        for episode in section.episodes
                    ],
                }
                for section in plan.structure.sections
            ],
        },
        "actual_bars": plan.actual_bars,
    }


def serialize_plan(plan: Plan) -> str:
    """Serialize Plan to YAML string."""
    data: dict = plan_to_dict(plan)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# =============================================================================
# Schema-First Plan Serialization (planner_design.md)
# =============================================================================


def schema_plan_to_dict(plan: "SchemaPlan") -> dict:
    """Convert SchemaPlan to dictionary for YAML serialization.

    Output format:
    ```yaml
    brief: {...}
    frame: {...}
    material: {...}
    cadence_plan:
      - bar: 4
        type: half
        target: V
    structure:
      sections:
        - label: A
          key_area: I
          cadence_plan: [...]
          schemas:
            - type: romanesca
              bars: 2
              texture: imitative
              treatment: statement
              voice_entry: soprano
              cadence: null
    actual_bars: 16
    ```
    """
    return {
        "brief": {
            "affect": plan.brief.affect,
            "genre": plan.brief.genre,
            "forces": plan.brief.forces,
            "bars": plan.brief.bars,
        },
        "frame": {
            "key": plan.frame.key,
            "mode": plan.frame.mode,
            "metre": plan.frame.metre,
            "tempo": plan.frame.tempo,
            "voices": plan.frame.voices,
            "upbeat": plan.frame.upbeat,
            "form": plan.frame.form,
        },
        "material": _serialize_material(plan.material),
        "cadence_plan": [
            {
                "bar": cp.bar,
                "type": cp.type,
                "target": cp.target,
            }
            for cp in plan.cadence_plan
        ],
        "structure": {
            "sections": [
                {
                    "label": section.label,
                    "key_area": section.key_area,
                    "cadence_plan": [
                        {
                            "bar": cp.bar,
                            "type": cp.type,
                            "target": cp.target,
                        }
                        for cp in section.cadence_plan
                    ],
                    "schemas": [
                        {
                            "type": slot.type,
                            "bars": slot.bars,
                            "texture": slot.texture,
                            "treatment": slot.treatment,
                            "voice_entry": slot.voice_entry,
                            "cadence": slot.cadence,
                        }
                        for slot in section.schemas
                    ],
                }
                for section in plan.structure.sections
            ],
        },
        "actual_bars": plan.actual_bars,
    }


def serialize_schema_plan(plan: "SchemaPlan") -> str:
    """Serialize SchemaPlan to YAML string."""
    data: dict = schema_plan_to_dict(plan)
    return yaml.dump(data, default_flow_style=False, sort_keys=False)

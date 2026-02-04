"""Plan serializer: Plan -> YAML.

Uses dataclasses.asdict for elegant serialization with custom converters.
"""
from dataclasses import asdict, fields, is_dataclass
from fractions import Fraction
from typing import TYPE_CHECKING, Any

import yaml

from planner.plannertypes import Material, Motif, Plan

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


def _convert_value(value: Any) -> Any:
    """Convert a value for YAML serialization."""
    if value is None:
        return None
    if isinstance(value, Fraction):
        return str(value) if value != 0 else 0
    if isinstance(value, tuple):
        # Convert tuples to InlineList for compact display
        return InlineList(_convert_value(value=v) for v in value)
    if isinstance(value, list):
        return [_convert_value(value=v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        return _dataclass_to_dict(obj=value)
    return value


def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass to dict with proper value conversion."""
    result: dict[str, Any] = {}
    for field in fields(obj):
        value = getattr(obj, field.name)
        result[field.name] = _convert_value(value=value)
    return result


def _serialize_motif(motif: Motif) -> dict:
    """Serialize a Motif to dictionary."""
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
    result: dict = {"subject": _serialize_motif(motif=material.subject)}
    if material.counter_subject is not None:
        result["counter_subject"] = _serialize_motif(motif=material.counter_subject)
    return result


def plan_to_dict(plan: Plan) -> dict:
    """Convert Plan to dictionary for YAML serialization."""
    return {
        "brief": _dataclass_to_dict(obj=plan.brief),
        "frame": _dataclass_to_dict(obj=plan.frame),
        "material": _serialize_material(material=plan.material),
        "structure": {
            "arc": plan.structure.arc,
            "sections": [
                {
                    **_dataclass_to_dict(obj=section),
                    "tonal_path": InlineList(section.tonal_path),
                    "episodes": [
                        {
                            **_dataclass_to_dict(obj=episode),
                            "phrases": [
                                {
                                    **_dataclass_to_dict(obj=phrase),
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
    return yaml.dump(plan_to_dict(plan=plan), default_flow_style=False, sort_keys=False)


# =============================================================================
# Schema-First Plan Serialization
# =============================================================================


def schema_plan_to_dict(plan: "SchemaPlan") -> dict:
    """Convert SchemaPlan to dictionary for YAML serialization."""
    return {
        "brief": _dataclass_to_dict(obj=plan.brief),
        "frame": _dataclass_to_dict(obj=plan.frame),
        "material": _serialize_material(material=plan.material),
        "tonal_sections": [_dataclass_to_dict(obj=ts) for ts in plan.tonal_sections],
        "cadence_plan": [_dataclass_to_dict(obj=cp) for cp in plan.cadence_plan],
        "structure": {
            "sections": [
                {
                    **_dataclass_to_dict(obj=section),
                    "cadence_plan": [_dataclass_to_dict(obj=cp) for cp in section.cadence_plan],
                    "schemas": [_dataclass_to_dict(obj=slot) for slot in section.schemas],
                }
                for section in plan.structure.sections
            ],
        },
        "schema_chain": [_dataclass_to_dict(obj=slot) for slot in plan.schema_chain],
        "actual_bars": plan.actual_bars,
    }


def serialize_schema_plan(plan: "SchemaPlan") -> str:
    """Serialize SchemaPlan to YAML string."""
    return yaml.dump(schema_plan_to_dict(plan=plan), default_flow_style=False, sort_keys=False)

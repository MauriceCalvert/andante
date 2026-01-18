"""Config loader adapter — loads treatment and transform specs from YAML.
Category: Adapter (external I/O)
All YAML file reading for builder config is centralized here.
"""
from pathlib import Path
from typing import Any
import yaml
from builder.types import BarTreatment
BUILDER_DATA_DIR: Path = Path(__file__).parent.parent / "data"
ROOT_DATA_DIR: Path = Path(__file__).parent.parent.parent / "data"

def load_transform_specs() -> dict[str, dict[str, Any]]:
    """Load transform specs from builder/data/transforms.yaml."""
    path: Path = BUILDER_DATA_DIR / "transforms.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_treatment_cycles() -> dict[str, Any]:
    """Load treatment cycles from builder/data/treatment_cycles.yaml."""
    path: Path = BUILDER_DATA_DIR / "treatment_cycles.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

def load_bar_treatments() -> dict[str, BarTreatment]:
    """Load bar treatments from data/bar_treatments.yaml."""
    path: Path = ROOT_DATA_DIR / "bar_treatments.yaml"
    with open(path, encoding="utf-8") as f:
        data: Any = yaml.safe_load(f)
    return {
        t["name"]: BarTreatment(t["name"], t["transform"], t["shift"])
        for t in data["treatments"]
    }
# Pre-loaded configs (loaded once at import)
TRANSFORM_SPECS: dict[str, dict[str, Any]] = load_transform_specs()
BAR_TREATMENTS: dict[str, BarTreatment] = load_bar_treatments()
_TREATMENT_CYCLES: dict[str, Any] = load_treatment_cycles()
TREATMENT_TO_TRANSFORM: dict[str, str] = _TREATMENT_CYCLES.get("treatment_mapping", {})
BAR_CONTINUATION_CYCLE: tuple[tuple[str, int], ...] = tuple(
    tuple(entry) for entry in _TREATMENT_CYCLES.get("bar_continuation", [])
)
PHRASE_TRANSFORM_CYCLE: tuple[str, ...] = tuple(
    _TREATMENT_CYCLES.get("phrase_transforms", [])
)

"""Vocabulary loader: articulations, rhythms, devices from YAML."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass(frozen=True)
class Articulation:
    """Articulation definition."""
    name: str
    duration_factor: Fraction
    velocity_factor: Fraction


@dataclass(frozen=True)
class Rhythm:
    """Rhythm pattern definition."""
    name: str
    durations: tuple[Fraction, ...]


@dataclass(frozen=True)
class Device:
    """Contrapuntal device definition."""
    name: str
    imitation_offset: Fraction | None
    duration_factor: Fraction | None
    voice_swap: bool


@dataclass(frozen=True)
class BassSchema:
    """Bass pattern for harmonic foundation."""
    name: str
    degrees: tuple[int, ...]
    durations: tuple[Fraction, ...]


@dataclass(frozen=True)
class GestureEffect:
    """Single effect within a gesture."""
    position: str  # first, last, downbeats, upbeats, all
    articulation: str


@dataclass(frozen=True)
class Gesture:
    """Rhetorical gesture with note-level effects."""
    name: str
    effects: tuple[GestureEffect, ...]


@dataclass(frozen=True)
class OrnamentTrigger:
    """Conditions for ornament application."""
    position: str  # cadence, downbeat, any
    min_duration: Fraction
    interval_down: bool = False


@dataclass(frozen=True)
class Ornament:
    """Ornament pattern definition."""
    name: str
    steps: tuple[int, ...]  # degree offsets from main note
    durations: tuple[Fraction, ...]  # relative fractions (sum to 1)
    trigger: OrnamentTrigger


def load_articulations() -> dict[str, Articulation]:
    """Load articulation definitions from YAML."""
    with open(DATA_DIR / "articulations.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, Articulation] = {}
    for name, defn in data.items():
        art: Articulation = Articulation(
            name=name,
            duration_factor=Fraction(defn["duration_factor"]),
            velocity_factor=Fraction(defn["velocity_factor"]),
        )
        result[name] = art
    return result


def load_rhythms() -> dict[str, Rhythm]:
    """Load rhythm pattern definitions from YAML."""
    with open(DATA_DIR / "rhythms.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, Rhythm] = {}
    for name, defn in data.items():
        durs: list[Fraction] = [Fraction(d) for d in defn["durations"]]
        rhythm: Rhythm = Rhythm(name=name, durations=tuple(durs))
        result[name] = rhythm
    return result


def load_devices() -> dict[str, Device]:
    """Load contrapuntal device definitions from YAML."""
    with open(DATA_DIR / "devices.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, Device] = {}
    for name, defn in data.items():
        offset_raw = defn.get("imitation_offset")
        offset: Fraction | None = Fraction(offset_raw) if offset_raw else None
        factor_raw = defn.get("duration_factor")
        factor: Fraction | None = Fraction(factor_raw) if factor_raw else None
        swap: bool = defn.get("voice_swap", False)
        device: Device = Device(
            name=name,
            imitation_offset=offset,
            duration_factor=factor,
            voice_swap=swap,
        )
        result[name] = device
    return result


def load_bass_schemas() -> dict[str, BassSchema]:
    """Load bass schema definitions from YAML."""
    with open(DATA_DIR / "bass_schemas.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, BassSchema] = {}
    for name, defn in data.items():
        degrees: tuple[int, ...] = tuple(defn["degrees"])
        durs: tuple[Fraction, ...] = tuple(Fraction(d) for d in defn["durations"])
        schema: BassSchema = BassSchema(name=name, degrees=degrees, durations=durs)
        result[name] = schema
    return result


def load_gestures() -> dict[str, Gesture]:
    """Load gesture definitions from YAML."""
    with open(DATA_DIR / "gestures.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, Gesture] = {}
    for name, defn in data.items():
        effects: list[GestureEffect] = []
        for eff in defn.get("effects", []):
            effects.append(GestureEffect(
                position=eff["position"],
                articulation=eff["articulation"],
            ))
        gesture: Gesture = Gesture(name=name, effects=tuple(effects))
        result[name] = gesture
    return result


def load_ornaments() -> dict[str, Ornament]:
    """Load ornament definitions from YAML."""
    with open(DATA_DIR / "ornaments.yaml", encoding="utf-8") as f:
        data: dict = yaml.safe_load(f)
    result: dict[str, Ornament] = {}
    for name, defn in data.items():
        steps: tuple[int, ...] = tuple(defn["steps"])
        durs: tuple[Fraction, ...] = tuple(Fraction(d) for d in defn["durations"])
        trig: dict = defn["trigger"]
        trigger: OrnamentTrigger = OrnamentTrigger(
            position=trig["position"],
            min_duration=Fraction(trig["min_duration"]),
            interval_down=trig.get("interval_down", False),
        )
        ornament: Ornament = Ornament(name=name, steps=steps, durations=durs, trigger=trigger)
        result[name] = ornament
    return result


ARTICULATIONS: dict[str, Articulation] = load_articulations()
RHYTHMS: dict[str, Rhythm] = load_rhythms()
DEVICES: dict[str, Device] = load_devices()
BASS_SCHEMAS: dict[str, BassSchema] = load_bass_schemas()
GESTURES: dict[str, Gesture] = load_gestures()
ORNAMENTS: dict[str, Ornament] = load_ornaments()

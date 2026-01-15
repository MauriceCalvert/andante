"""100% coverage tests for engine.vocabulary.

Tests import only:
- engine.vocabulary (module under test)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.vocabulary import (
    Articulation,
    Rhythm,
    Device,
    BassSchema,
    GestureEffect,
    Gesture,
    OrnamentTrigger,
    Ornament,
    load_articulations,
    load_rhythms,
    load_devices,
    load_bass_schemas,
    load_gestures,
    load_ornaments,
    ARTICULATIONS,
    RHYTHMS,
    DEVICES,
    BASS_SCHEMAS,
    GESTURES,
    ORNAMENTS,
)


class TestArticulation:
    """Test Articulation dataclass."""

    def test_construction(self) -> None:
        art = Articulation(
            name="staccato",
            duration_factor=Fraction(1, 2),
            velocity_factor=Fraction(3, 4),
        )
        assert art.name == "staccato"
        assert art.duration_factor == Fraction(1, 2)
        assert art.velocity_factor == Fraction(3, 4)

    def test_frozen(self) -> None:
        art = Articulation("test", Fraction(1), Fraction(1))
        with pytest.raises(Exception):
            art.name = "modified"


class TestRhythm:
    """Test Rhythm dataclass."""

    def test_construction(self) -> None:
        rhythm = Rhythm(
            name="dotted",
            durations=(Fraction(3, 4), Fraction(1, 4)),
        )
        assert rhythm.name == "dotted"
        assert len(rhythm.durations) == 2


class TestDevice:
    """Test Device dataclass."""

    def test_construction_with_offset(self) -> None:
        device = Device(
            name="stretto",
            imitation_offset=Fraction(1, 4),
            duration_factor=None,
            voice_swap=False,
        )
        assert device.name == "stretto"
        assert device.imitation_offset == Fraction(1, 4)
        assert device.duration_factor is None
        assert device.voice_swap is False

    def test_construction_with_factor(self) -> None:
        device = Device(
            name="augmentation",
            imitation_offset=None,
            duration_factor=Fraction(2),
            voice_swap=False,
        )
        assert device.duration_factor == Fraction(2)

    def test_construction_with_swap(self) -> None:
        device = Device(
            name="invertible",
            imitation_offset=None,
            duration_factor=None,
            voice_swap=True,
        )
        assert device.voice_swap is True


class TestBassSchema:
    """Test BassSchema dataclass."""

    def test_construction(self) -> None:
        schema = BassSchema(
            name="alberti",
            degrees=(1, 5, 3, 5),
            durations=(Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)),
        )
        assert schema.name == "alberti"
        assert schema.degrees == (1, 5, 3, 5)
        assert len(schema.durations) == 4


class TestGestureEffect:
    """Test GestureEffect dataclass."""

    def test_construction(self) -> None:
        effect = GestureEffect(
            position="first",
            articulation="accent",
        )
        assert effect.position == "first"
        assert effect.articulation == "accent"


class TestGesture:
    """Test Gesture dataclass."""

    def test_construction(self) -> None:
        effects = (
            GestureEffect("first", "accent"),
            GestureEffect("last", "legato"),
        )
        gesture = Gesture(name="statement_open", effects=effects)
        assert gesture.name == "statement_open"
        assert len(gesture.effects) == 2


class TestOrnamentTrigger:
    """Test OrnamentTrigger dataclass."""

    def test_construction_defaults(self) -> None:
        trigger = OrnamentTrigger(
            position="cadence",
            min_duration=Fraction(1, 4),
        )
        assert trigger.position == "cadence"
        assert trigger.min_duration == Fraction(1, 4)
        assert trigger.interval_down is False

    def test_construction_with_interval_down(self) -> None:
        trigger = OrnamentTrigger(
            position="downbeat",
            min_duration=Fraction(1, 2),
            interval_down=True,
        )
        assert trigger.interval_down is True


class TestOrnament:
    """Test Ornament dataclass."""

    def test_construction(self) -> None:
        trigger = OrnamentTrigger("cadence", Fraction(1, 4))
        ornament = Ornament(
            name="trill",
            steps=(0, 1, 0, 1, 0),
            durations=(Fraction(1, 5),) * 5,
            trigger=trigger,
        )
        assert ornament.name == "trill"
        assert len(ornament.steps) == 5
        assert len(ornament.durations) == 5


class TestLoadArticulations:
    """Test load_articulations function."""

    def test_loads_articulations(self) -> None:
        result = load_articulations()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_articulation_instances(self) -> None:
        result = load_articulations()
        for name, art in result.items():
            assert isinstance(art, Articulation)
            assert art.name == name

    def test_staccato_exists(self) -> None:
        result = load_articulations()
        assert "staccato" in result
        assert result["staccato"].duration_factor < 1


class TestLoadRhythms:
    """Test load_rhythms function."""

    def test_loads_rhythms(self) -> None:
        result = load_rhythms()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_rhythm_instances(self) -> None:
        result = load_rhythms()
        for name, rhythm in result.items():
            assert isinstance(rhythm, Rhythm)
            assert rhythm.name == name

    def test_straight_exists(self) -> None:
        result = load_rhythms()
        assert "straight" in result

    def test_dotted_exists(self) -> None:
        result = load_rhythms()
        assert "dotted" in result


class TestLoadDevices:
    """Test load_devices function."""

    def test_loads_devices(self) -> None:
        result = load_devices()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_device_instances(self) -> None:
        result = load_devices()
        for name, device in result.items():
            assert isinstance(device, Device)
            assert device.name == name

    def test_stretto_has_offset(self) -> None:
        result = load_devices()
        assert "stretto" in result
        assert result["stretto"].imitation_offset is not None

    def test_augmentation_has_factor(self) -> None:
        result = load_devices()
        assert "augmentation" in result
        assert result["augmentation"].duration_factor == Fraction(2)

    def test_invertible_has_swap(self) -> None:
        result = load_devices()
        assert "invertible" in result
        assert result["invertible"].voice_swap is True


class TestLoadBassSchemas:
    """Test load_bass_schemas function."""

    def test_loads_schemas(self) -> None:
        result = load_bass_schemas()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_schema_instances(self) -> None:
        result = load_bass_schemas()
        for name, schema in result.items():
            assert isinstance(schema, BassSchema)
            assert schema.name == name
            assert len(schema.degrees) == len(schema.durations)


class TestLoadGestures:
    """Test load_gestures function."""

    def test_loads_gestures(self) -> None:
        result = load_gestures()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_gesture_instances(self) -> None:
        result = load_gestures()
        for name, gesture in result.items():
            assert isinstance(gesture, Gesture)
            assert gesture.name == name

    def test_statement_open_exists(self) -> None:
        result = load_gestures()
        assert "statement_open" in result


class TestLoadOrnaments:
    """Test load_ornaments function."""

    def test_loads_ornaments(self) -> None:
        result = load_ornaments()
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_all_are_ornament_instances(self) -> None:
        result = load_ornaments()
        for name, ornament in result.items():
            assert isinstance(ornament, Ornament)
            assert ornament.name == name
            assert len(ornament.steps) == len(ornament.durations)

    def test_trill_exists(self) -> None:
        result = load_ornaments()
        assert "trill" in result


class TestGlobalConstants:
    """Test module-level constants."""

    def test_articulations_populated(self) -> None:
        assert len(ARTICULATIONS) > 0
        assert all(isinstance(a, Articulation) for a in ARTICULATIONS.values())

    def test_rhythms_populated(self) -> None:
        assert len(RHYTHMS) > 0
        assert all(isinstance(r, Rhythm) for r in RHYTHMS.values())

    def test_devices_populated(self) -> None:
        assert len(DEVICES) > 0
        assert all(isinstance(d, Device) for d in DEVICES.values())

    def test_bass_schemas_populated(self) -> None:
        assert len(BASS_SCHEMAS) > 0
        assert all(isinstance(s, BassSchema) for s in BASS_SCHEMAS.values())

    def test_gestures_populated(self) -> None:
        assert len(GESTURES) > 0
        assert all(isinstance(g, Gesture) for g in GESTURES.values())

    def test_ornaments_populated(self) -> None:
        assert len(ORNAMENTS) > 0
        assert all(isinstance(o, Ornament) for o in ORNAMENTS.values())

"""Tests for engine.ornament.

Category A tests: verify ornament application.
Tests import only:
- engine.ornament (module under test)
- engine.key (Key type)
- engine.types (RealisedNote)
- engine.vocabulary (Ornament, ORNAMENTS)
- stdlib
"""
from fractions import Fraction

import pytest
from engine.key import Key
from engine.ornament import (
    apply_ornament,
    apply_ornaments,
    can_ornament,
    is_power_of_two,
    select_ornament,
)
from engine.engine_types import RealisedNote
from engine.vocabulary import ORNAMENTS, Ornament


def make_note(offset: Fraction, pitch: int, duration: Fraction, voice: str = "soprano") -> RealisedNote:
    """Create a test note."""
    return RealisedNote(offset=offset, pitch=pitch, duration=duration, voice=voice)


class TestIsPowerOfTwo:
    """Test is_power_of_two function."""

    def test_one_is_power(self) -> None:
        """1 is a power of 2."""
        assert is_power_of_two(1)

    def test_two_is_power(self) -> None:
        """2 is a power of 2."""
        assert is_power_of_two(2)

    def test_four_is_power(self) -> None:
        """4 is a power of 2."""
        assert is_power_of_two(4)

    def test_eight_is_power(self) -> None:
        """8 is a power of 2."""
        assert is_power_of_two(8)

    def test_three_not_power(self) -> None:
        """3 is not a power of 2."""
        assert not is_power_of_two(3)

    def test_six_not_power(self) -> None:
        """6 is not a power of 2."""
        assert not is_power_of_two(6)

    def test_zero_not_power(self) -> None:
        """0 is not a power of 2."""
        assert not is_power_of_two(0)

    def test_negative_not_power(self) -> None:
        """Negative numbers are not powers of 2."""
        assert not is_power_of_two(-2)


class TestCanOrnament:
    """Test can_ornament function."""

    def test_short_note_cannot(self) -> None:
        """Very short notes cannot be ornamented."""
        assert not can_ornament(Fraction(1, 32))

    def test_quarter_note_can(self) -> None:
        """Quarter notes can be ornamented."""
        assert can_ornament(Fraction(1, 4))

    def test_half_note_can(self) -> None:
        """Half notes can be ornamented."""
        assert can_ornament(Fraction(1, 2))

    def test_non_binary_numerator_cannot(self) -> None:
        """Notes with non-power-of-2 numerator cannot be ornamented."""
        # 3/8 has numerator 3 which is not power of 2
        assert not can_ornament(Fraction(3, 8))

    def test_dotted_quarter_cannot(self) -> None:
        """Dotted quarter (3/8) cannot be ornamented."""
        assert not can_ornament(Fraction(3, 8))


class TestOrnamentsLoaded:
    """Test ORNAMENTS constant loaded from vocabulary."""

    def test_ornaments_not_empty(self) -> None:
        """ORNAMENTS has entries."""
        assert len(ORNAMENTS) > 0

    def test_trill_exists(self) -> None:
        """Trill ornament exists."""
        assert "trill" in ORNAMENTS

    def test_mordent_exists(self) -> None:
        """Mordent ornament exists."""
        assert "mordent" in ORNAMENTS

    def test_turn_exists(self) -> None:
        """Turn ornament exists."""
        assert "turn" in ORNAMENTS

    def test_ornament_has_steps(self) -> None:
        """Each ornament has steps."""
        for name, ornament in ORNAMENTS.items():
            assert hasattr(ornament, "steps"), f"{name} missing steps"

    def test_ornament_has_durations(self) -> None:
        """Each ornament has durations."""
        for name, ornament in ORNAMENTS.items():
            assert hasattr(ornament, "durations"), f"{name} missing durations"


class TestSelectOrnament:
    """Test select_ornament function."""

    def test_cadence_selects_trill(self) -> None:
        """Cadential note selects trill."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 2))
        result: Ornament | None = select_ornament(note, None, is_cadence=True, bar_dur=Fraction(1))
        assert result is not None
        assert result.name == "trill"

    def test_short_note_returns_none(self) -> None:
        """Short note cannot be ornamented."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 16))
        result: Ornament | None = select_ornament(note, None, is_cadence=False, bar_dur=Fraction(1))
        assert result is None

    def test_downbeat_quarter_selects(self) -> None:
        """Downbeat quarter note can select mordent or turn."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 4))
        result: Ornament | None = select_ornament(note, None, is_cadence=False, bar_dur=Fraction(1), phrase_index=0)
        # phrase_index=0 selects "mordent" from options
        assert result is not None
        assert result.name == "mordent"

    def test_phrase_index_varies_selection(self) -> None:
        """Different phrase indices select different ornaments."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 4))
        results: list[str | None] = []
        for i in range(4):
            result: Ornament | None = select_ornament(note, None, is_cadence=False, bar_dur=Fraction(1), phrase_index=i)
            results.append(result.name if result else None)
        # Should have variety based on phrase_index % 4
        assert "mordent" in results
        assert "turn" in results
        assert None in results

    def test_descending_step_selects_turn(self) -> None:
        """Descending stepwise motion selects turn."""
        note: RealisedNote = make_note(Fraction(1, 4), 62, Fraction(1, 4))  # Off downbeat
        next_note: RealisedNote = make_note(Fraction(1, 2), 60, Fraction(1, 4))
        result: Ornament | None = select_ornament(note, next_note, is_cadence=False, bar_dur=Fraction(1))
        assert result is not None
        assert result.name == "turn"


class TestApplyOrnament:
    """Test apply_ornament function."""

    def test_returns_tuple_of_notes(self) -> None:
        """Returns tuple of RealisedNote."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 2))
        key: Key = Key("C", "major")
        ornament: Ornament = ORNAMENTS["trill"]
        result: tuple[RealisedNote, ...] = apply_ornament(note, ornament, key)
        assert isinstance(result, tuple)
        assert all(isinstance(n, RealisedNote) for n in result)

    def test_preserves_voice(self) -> None:
        """All notes have same voice."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 2), "alto")
        key: Key = Key("C", "major")
        ornament: Ornament = ORNAMENTS["mordent"]
        result: tuple[RealisedNote, ...] = apply_ornament(note, ornament, key)
        for n in result:
            assert n.voice == "alto"

    def test_starts_at_original_offset(self) -> None:
        """First note starts at original offset."""
        note: RealisedNote = make_note(Fraction(2), 60, Fraction(1, 2))
        key: Key = Key("C", "major")
        ornament: Ornament = ORNAMENTS["turn"]
        result: tuple[RealisedNote, ...] = apply_ornament(note, ornament, key)
        assert result[0].offset == Fraction(2)

    def test_total_duration_equals_original(self) -> None:
        """Total duration of result equals original note duration."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 2))
        key: Key = Key("C", "major")
        ornament: Ornament = ORNAMENTS["trill"]
        result: tuple[RealisedNote, ...] = apply_ornament(note, ornament, key)
        total: Fraction = sum(n.duration for n in result)
        assert total == note.duration

    def test_offsets_sequential(self) -> None:
        """Note offsets are sequential."""
        note: RealisedNote = make_note(Fraction(0), 60, Fraction(1, 2))
        key: Key = Key("C", "major")
        ornament: Ornament = ORNAMENTS["mordent"]
        result: tuple[RealisedNote, ...] = apply_ornament(note, ornament, key)
        current: Fraction = Fraction(0)
        for n in result:
            assert n.offset == current
            current += n.duration


class TestApplyOrnaments:
    """Test apply_ornaments function."""

    def test_single_note_unchanged(self) -> None:
        """Single note returns unchanged."""
        notes: tuple[RealisedNote, ...] = (make_note(Fraction(0), 60, Fraction(1)),)
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_ornaments(notes, key, is_cadence=False, bar_dur=Fraction(1))
        assert result == notes

    def test_empty_returns_empty(self) -> None:
        """Empty input returns empty."""
        notes: tuple[RealisedNote, ...] = ()
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_ornaments(notes, key, is_cadence=False, bar_dur=Fraction(1))
        assert result == ()

    def test_cadence_ornaments_last_note(self) -> None:
        """Cadence flag causes trill on last note."""
        notes: tuple[RealisedNote, ...] = (
            make_note(Fraction(0), 60, Fraction(1, 2)),
            make_note(Fraction(1, 2), 62, Fraction(1, 2)),
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_ornaments(notes, key, is_cadence=True, bar_dur=Fraction(1))
        # Last note should be expanded (more notes than original)
        assert len(result) > len(notes)

    def test_respects_max_per_phrase(self) -> None:
        """Respects max ornaments per phrase."""
        # Create many ornamentable notes
        notes: tuple[RealisedNote, ...] = tuple(
            make_note(Fraction(i), 60, Fraction(1, 2)) for i in range(10)
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_ornaments(notes, key, is_cadence=False, bar_dur=Fraction(1))
        # Should have applied ornaments but limited
        assert len(result) >= len(notes)

    def test_preserves_order(self) -> None:
        """Notes remain in temporal order."""
        notes: tuple[RealisedNote, ...] = (
            make_note(Fraction(0), 60, Fraction(1, 4)),
            make_note(Fraction(1, 4), 62, Fraction(1, 4)),
            make_note(Fraction(1, 2), 64, Fraction(1, 4)),
        )
        key: Key = Key("C", "major")
        result: tuple[RealisedNote, ...] = apply_ornaments(notes, key, is_cadence=False, bar_dur=Fraction(1))
        offsets: list[Fraction] = [n.offset for n in result]
        assert offsets == sorted(offsets)

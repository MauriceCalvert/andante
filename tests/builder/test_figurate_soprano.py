"""Tests for soprano figuration span."""
from fractions import Fraction

from builder.figuration.soprano import figurate_soprano_span
from shared.key import Key


def _make_key() -> Key:
    return Key(tonic="C", mode="major")


def test_figurate_span_step_up_3_4() -> None:
    """Step up C4→D4 in 3/4: should fill one bar with notes."""
    notes, fig_name = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=Fraction(3, 4),
        end_midi=62,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    assert len(notes) >= 2
    assert isinstance(fig_name, str)
    assert len(fig_name) > 0


def test_figurate_span_third_down_3_4() -> None:
    """Third down E4→C4 in 3/4."""
    notes, fig_name = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=64,
        end_offset=Fraction(3, 4),
        end_midi=60,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    assert len(notes) >= 2


def test_figurate_span_unison() -> None:
    """Unison C4→C4: should produce ornamental fill."""
    notes, fig_name = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=Fraction(3, 4),
        end_midi=60,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    assert len(notes) >= 2


def test_all_pitches_in_range() -> None:
    """Every note must be within the specified MIDI range."""
    midi_range = (55, 79)
    notes, _ = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=Fraction(3, 4),
        end_midi=67,
        key=_make_key(),
        metre="3/4",
        character="expressive",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=midi_range,
    )
    for offset, pitch, dur in notes:
        assert midi_range[0] <= pitch <= midi_range[1], (
            f"Pitch {pitch} outside range {midi_range} at offset {offset}"
        )


def test_durations_sum_to_gap() -> None:
    """Total duration of notes must equal the gap."""
    gap = Fraction(3, 4)
    notes, _ = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=gap,
        end_midi=64,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    total_dur = sum(dur for _, _, dur in notes)
    assert total_dur == gap, f"Duration sum {total_dur} != gap {gap}"


def test_deterministic() -> None:
    """Same inputs produce identical output."""
    kwargs = dict(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=Fraction(3, 4),
        end_midi=64,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=3,
        midi_range=(55, 79),
    )
    a, name_a = figurate_soprano_span(**kwargs)
    b, name_b = figurate_soprano_span(**kwargs)
    assert a == b
    assert name_a == name_b


def test_first_note_is_anchor() -> None:
    """First pitch must be the start anchor."""
    notes, _ = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=64,
        end_offset=Fraction(3, 4),
        end_midi=60,
        key=_make_key(),
        metre="3/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    assert notes[0][1] == 64, f"First pitch {notes[0][1]} != start_midi 64"


def test_figurate_span_4_4() -> None:
    """4/4 metre should also work."""
    notes, fig_name = figurate_soprano_span(
        start_offset=Fraction(0),
        start_midi=60,
        end_offset=Fraction(1),
        end_midi=67,
        key=_make_key(),
        metre="4/4",
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        midi_range=(55, 79),
    )
    assert len(notes) >= 2
    total_dur = sum(dur for _, _, dur in notes)
    assert total_dur == Fraction(1)

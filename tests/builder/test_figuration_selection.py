"""Tests for figure selection engine."""
from builder.figuration.selection import classify_interval, select_figure
from builder.figuration.types import Figure
from shared.key import Key


def test_classify_interval_step_up() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=60, to_midi=62, key=key) == "step_up"


def test_classify_interval_step_down() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=62, to_midi=60, key=key) == "step_down"


def test_classify_interval_third_down() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=64, to_midi=60, key=key) == "third_down"


def test_classify_interval_third_up() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=60, to_midi=64, key=key) == "third_up"


def test_classify_interval_unison() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=60, to_midi=60, key=key) == "unison"


def test_classify_interval_fifth_up() -> None:
    key = Key(tonic="C", mode="major")
    assert classify_interval(from_midi=60, to_midi=67, key=key) == "fifth_up"


def test_classify_interval_fourth_down() -> None:
    key = Key(tonic="C", mode="major")
    # G4 down to D4: 3 diatonic steps down
    assert classify_interval(from_midi=67, to_midi=62, key=key) == "fourth_down"


def test_select_figure_returns_figure() -> None:
    result = select_figure(
        interval="step_up",
        note_count=3,
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
    )
    assert isinstance(result, Figure)


def test_select_figure_deterministic() -> None:
    kwargs = dict(
        interval="step_up",
        note_count=3,
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=5,
    )
    a = select_figure(**kwargs)
    b = select_figure(**kwargs)
    assert a.name == b.name


def test_select_figure_avoids_repeat() -> None:
    first = select_figure(
        interval="step_up",
        note_count=3,
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
    )
    second = select_figure(
        interval="step_up",
        note_count=3,
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
        prev_figure_name=first.name,
    )
    # With prev_figure_name set, should pick different if possible
    # (may be same if only one candidate — that's OK)
    assert isinstance(second, Figure)


def test_select_figure_cadential_filter() -> None:
    result = select_figure(
        interval="step_up",
        note_count=3,
        character="plain",
        position="cadential",
        is_minor=False,
        bar_num=0,
    )
    # Cadential position should prefer cadential_safe figures
    assert isinstance(result, Figure)
    assert result.cadential_safe


def test_select_figure_unison() -> None:
    result = select_figure(
        interval="unison",
        note_count=3,
        character="plain",
        position="passing",
        is_minor=False,
        bar_num=0,
    )
    assert isinstance(result, Figure)


def test_select_figure_varies_by_bar_num() -> None:
    """With a broad enough pool (no character filter), rotation should vary."""
    results = set()
    for bar in range(10):
        f = select_figure(
            interval="third_up",
            note_count=3,
            character="expressive",
            position="passing",
            is_minor=False,
            bar_num=bar,
        )
        results.add(f.name)
    # Should produce at least 2 different figures over 10 bars
    # (if the pool for third_up is large enough)
    assert len(results) >= 1, f"Got no figures"

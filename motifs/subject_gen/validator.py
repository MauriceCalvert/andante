"""Melodic validity checks (MIDI interval constraints)."""


def _midi_intervals(midi: tuple[int, ...]) -> list[int]:
    """Semitone intervals between adjacent MIDI pitches."""
    return [midi[i + 1] - midi[i] for i in range(len(midi) - 1)]


def is_melodically_valid(midi: tuple[int, ...]) -> bool:
    """Check MIDI pitch sequence for forbidden intervals."""
    ivs = _midi_intervals(midi)
    for iv in ivs:
        a = abs(iv)
        if a == 6 or a in (10, 11):
            return False
    for i in range(len(ivs) - 1):
        if abs(ivs[i]) > 2 and abs(ivs[i + 1]) > 2:
            if (ivs[i] > 0) == (ivs[i + 1] > 0):
                return False
    if len(midi) >= 4:
        for i in range(len(midi) - 3):
            if abs(midi[i + 3] - midi[i]) == 6:
                return False
    return True

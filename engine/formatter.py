"""E6 Formatter: RealisedPhrases -> Note list for output."""
from fractions import Fraction

from engine.note import Note
from engine.engine_types import RealisedNote, RealisedPhrase


def format_notes(phrases: list[RealisedPhrase], metre: str) -> list[Note]:
    """Convert realised phrases to Note objects for N voices."""
    num_str, den_str = metre.split("/")
    bar_dur: Fraction = Fraction(int(num_str), int(den_str))
    notes: list[Note] = []
    for phrase in phrases:
        for voice in phrase.voices:
            track: int = voice.voice_index
            for rn in voice.notes:
                bar: int = int(rn.offset / bar_dur) + 1
                beat: float = float((rn.offset % bar_dur) / Fraction(1, int(den_str))) + 1
                note: Note = Note(
                    midiNote=rn.pitch,
                    Offset=float(rn.offset),
                    Duration=float(rn.duration),
                    track=track,
                    bar=bar,
                    beat=beat,
                )
                notes.append(note)
    notes.sort(key=lambda n: (n.Offset, n.track))
    return notes


def tempo_from_name(tempo: str) -> int:
    """Convert tempo name to BPM."""
    tempo_map: dict[str, int] = {
        "adagio": 66,
        "andante": 80,
        "allegro": 120,
        "presto": 140,
    }
    return tempo_map.get(tempo, 90)

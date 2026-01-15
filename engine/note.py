"""Note class for MIDI/MusicXML output."""
from dataclasses import dataclass


@dataclass
class Note:
    """Note for MIDI/MusicXML output."""
    midiNote: int
    Offset: float
    Duration: float
    track: int
    Length: float = 0.0
    bar: int = 0
    beat: int = 0
    lyric: str = ""

    @staticmethod
    def csv_header() -> str:
        return "Offset,midiNote,Duration,track,Length,bar,beat,noteName,lyric"


TEMPO_MAP: dict[str, int] = {
    "grave": 40,
    "largo": 50,
    "adagio": 66,
    "andante": 76,
    "moderato": 96,
    "allegretto": 112,
    "allegro": 120,
    "vivace": 140,
    "presto": 168,
}


def tempo_from_name(tempo_name: str) -> int:
    """Convert tempo name to BPM."""
    return TEMPO_MAP.get(tempo_name.lower(), 120)

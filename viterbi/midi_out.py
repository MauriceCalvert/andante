"""Write solved phrase to a MIDI file for listening."""
from viterbi.mtypes import PhraseResult

try:
    from midiutil import MIDIFile
except ImportError:
    MIDIFile = None

TICKS_PER_BEAT = 480
DEFAULT_TEMPO = 90
DEFAULT_VELOCITY = 80


def write_midi(
    result: PhraseResult,
    filename: str,
    tempo: int = DEFAULT_TEMPO,
) -> str:
    """Write leader + follower to a 2-track MIDI file.

    Returns the filename on success, empty string if midiutil is missing.
    """
    if MIDIFile is None:
        return ""
    midi = MIDIFile(
        numTracks=2,
        ticks_per_quarternote=TICKS_PER_BEAT,
    )
    midi.addTempo(track=0, time=0, tempo=tempo)
    midi.addTrackName(0, 0, "Leader (Bass)")
    midi.addProgramChange(0, 0, 0, 0)
    for ln in result.leader_notes:
        midi.addNote(
            track=0, channel=0,
            pitch=ln.midi_pitch, time=ln.beat,
            duration=1, volume=DEFAULT_VELOCITY,
        )
    midi.addTrackName(1, 0, "Follower (Soprano)")
    midi.addProgramChange(1, 1, 0, 0)
    for beat, pitch in zip(result.beats, result.pitches):
        midi.addNote(
            track=1, channel=1,
            pitch=pitch, time=beat,
            duration=1, volume=DEFAULT_VELOCITY,
        )
    with open(filename, "wb") as f:
        midi.writeFile(f)
    return filename

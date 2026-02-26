"""FRAGEN proof-of-concept: episode textures and hold-exchange.

Builds motivic cells from a fugue subject, pairs them into two-voice
episode fragments, and writes a demo MIDI file with one empty bar
between each section.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from midiutil import MIDIFile

from motifs.fragen import (
    Motivic,
    Fragment,
    Note,
    VOICE_BASS,
    VOICE_SOPRANO,
    build_chains,
    build_fragments,
    build_hold_fragments,
    dedup_fragments,
    extract_cells,
    realise,
    validate_realisation,
)
from motifs.subject_loader import load_triple
from motifs.head_generator import degrees_to_midi

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FUGUE_NAME: str = "call_response"
NOTE_RELEASE: float = 0.95
TEMPO_BPM: int = 120
VELOCITY: int = 80

# Note name lookup (sharps for sharp keys, flats for flat keys)
_SHARP_KEYS: frozenset[str] = frozenset({"C", "G", "D", "A", "E", "B", "F#"})
_NOTE_CSV_HEADER: str = "offset,midinote,duration,track,bar,beat,notename,degree,section,fragment,leader"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _midi_to_name(pitch: int, tonic: str) -> str:
    """Convert MIDI pitch to note name like C4, F#3."""
    from shared.pitch import midi_to_name
    return midi_to_name(midi=pitch, use_flats=tonic not in _SHARP_KEYS)


def _write_notes(
    midi: MIDIFile,
    notes: list[Note],
    t_start: float,
    tonic_midi: int,
    mode: str,
) -> float:
    """Write note events to MIDI. Returns the end time in beats."""
    end: float = t_start
    for n in notes:
        pitch: int = degrees_to_midi((n.degree,), tonic_midi, mode)[0]
        track: int = 0 if n.voice == VOICE_SOPRANO else 1
        onset: float = t_start + float(n.offset) * 4
        dur: float = float(n.duration) * 4 * NOTE_RELEASE
        midi.addNote(
            track=track,
            channel=track,
            pitch=pitch,
            time=onset,
            duration=dur,
            volume=VELOCITY,
        )
        end = max(end, onset + float(n.duration) * 4)
    return end


def _collect_note_rows(
    notes: list[Note],
    t_start: float,
    bar_length: Fraction,
    tonic_midi: int,
    tonic: str,
    mode: str,
    section_idx: int,
    frag: Fragment,
) -> list[str]:
    """Build CSV rows for a section's notes."""
    rows: list[str] = []
    leader_tag: str = "S" if frag.leader_voice == VOICE_SOPRANO else "B"
    frag_name: str = f"{frag.upper.name}+{frag.lower.name}"
    bar_beats: float = float(bar_length) * 4
    for n in notes:
        pitch: int = degrees_to_midi((n.degree,), tonic_midi, mode)[0]
        track: int = 0 if n.voice == VOICE_SOPRANO else 1
        abs_offset: float = t_start + float(n.offset) * 4
        bar: int = int(abs_offset / bar_beats) + 1
        beat_in_bar: float = round((abs_offset % bar_beats) + 1, 4)
        name: str = _midi_to_name(pitch=pitch, tonic=tonic)
        rows.append(
            f"{abs_offset},{pitch},{n.duration},{track},"
            f"{bar},{beat_in_bar},{name},{n.degree},"
            f"{section_idx},{frag_name},{leader_tag}"
        )
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _fragment_group(frag: Fragment) -> int:
    """0=soprano-led episode, 1=bass-led episode, 2=hold-exchange."""
    is_hold: bool = (
        len(frag.upper.degrees) == 1 or len(frag.lower.degrees) == 1
    )
    if is_hold:
        return 2
    if frag.leader_voice == VOICE_SOPRANO:
        return 0
    return 1


_GROUP_LABELS: tuple[str, ...] = (
    "SOPRANO-LED EPISODES",
    "BASS-LED EPISODES",
    "HOLD-EXCHANGE",
)


def main() -> None:
    """Run the FRAGEN proof-of-concept."""
    fugue = load_triple(name=FUGUE_NAME)
    bar_length: Fraction = Fraction(fugue.metre[0], fugue.metre[1])
    tonic_midi: int = fugue.tonic_midi
    mode: str = fugue.subject.mode
    bar_beats: float = float(bar_length) * 4
    print(f"{'=' * 60}")
    print(f"FRAGEN  {FUGUE_NAME}  {fugue.tonic} {mode}  "
          f"{fugue.metre[0]}/{fugue.metre[1]}")
    print(f"{'=' * 60}")
    # --- Cells ---
    cells: list[Motivic] = extract_cells(fugue=fugue, bar_length=bar_length)
    print(f"\n{len(cells)} cells (raw vocabulary):")
    for c in cells:
        durs: str = "+".join(str(d) for d in c.durations)
        bars_tag: str = f"{float(c.total_duration / bar_length):.2f}"
        print(f"  {c.name:28s}  {str(c.degrees):36s}  {durs}  ({bars_tag}bar)")
    # --- Chains ---
    chains: list[Motivic] = build_chains(cells=cells, bar_length=bar_length)
    print(f"\n{len(chains)} bar-filling chains:")
    for c in chains:
        durs = "+".join(str(d) for d in c.durations)
        print(f"  {c.name:50s}  {str(c.degrees):36s}  {durs}")
    # --- Fragments ---
    fragments: list[Fragment] = build_fragments(
        cells=chains,
        tonic_midi=tonic_midi,
        mode=mode,
        bar_length=bar_length,
    )
    holds: list[Fragment] = build_hold_fragments(
        cells=chains,
        tonic_midi=tonic_midi,
        mode=mode,
        bar_length=bar_length,
    )
    raw_count: int = len(fragments) + len(holds)
    fragments = dedup_fragments(fragments)
    holds = dedup_fragments(holds)
    print(f"\n{raw_count} raw -> {len(fragments)} regular + "
          f"{len(holds)} hold-exchange after dedup")
    # --- Sort: group (S-ep, B-ep, hold), then complexity ascending ---
    def _sort_key(f: Fragment) -> tuple[int, int, int, int]:
        model_dur: Fraction = max(
            f.upper.total_duration,
            f.lower.total_duration + f.offset,
        )
        cell_bars: int = int(model_dur / bar_length)
        return (
            _fragment_group(f),
            cell_bars,
            len(f.upper.degrees) + len(f.lower.degrees),
            f.separation,
        )
    all_sections: list[Fragment] = sorted(
        fragments + holds, key=_sort_key,
    )
    # --- Realise and write MIDI ---
    midi: MIDIFile = MIDIFile(numTracks=2)
    midi.addTempo(track=0, time=0, tempo=TEMPO_BPM)
    midi.addTrackName(track=0, time=0, trackName="Soprano")
    midi.addTrackName(track=1, time=0, trackName="Bass")
    t: float = 0.0
    written: int = 0
    skipped: int = 0
    regular: int = 0
    hold_count: int = 0
    prev_group: int = -1
    all_note_rows: list[str] = []
    print(f"\nSections:")
    for idx, frag in enumerate(all_sections):
        # Derive bar count from fragment: 2 iterations of its natural length
        model_dur: Fraction = max(
            frag.upper.total_duration,
            frag.lower.total_duration + frag.offset,
        )
        cell_bars: int = int(model_dur / bar_length)
        assert cell_bars >= 1, f"Cell bars < 1: {model_dur} / {bar_length}"
        n_bars: int = cell_bars
        step: int = -1 if (idx % 2 == 0) else 1
        notes: list[Note] | None = realise(
            fragment=frag,
            n_bars=n_bars,
            step=step,
            bar_length=bar_length,
            tonic_midi=tonic_midi,
            mode=mode,
        )
        if notes is None:
            skipped += 1
            continue
        if not validate_realisation(
            notes=notes,
            tonic_midi=tonic_midi,
            mode=mode,
            bar_length=bar_length,
        ):
            skipped += 1
            continue
        group: int = _fragment_group(frag)
        if group != prev_group:
            print(f"\n  --- {_GROUP_LABELS[group]} ---")
            prev_group = group
        all_note_rows.extend(_collect_note_rows(
            notes=notes,
            t_start=t,
            bar_length=bar_length,
            tonic_midi=tonic_midi,
            tonic=fugue.tonic,
            mode=mode,
            section_idx=written + 1,
            frag=frag,
        ))
        t = _write_notes(
            midi=midi,
            notes=notes,
            t_start=t,
            tonic_midi=tonic_midi,
            mode=mode,
        )
        t += bar_beats  # one empty bar between sections
        written += 1
        is_hold: bool = group == 2
        if is_hold:
            hold_count += 1
        else:
            regular += 1
        voice_tag: str = "S" if frag.leader_voice == VOICE_SOPRANO else "B"
        dir_tag: str = "desc" if step < 0 else " asc"
        kind: str = "HOLD" if is_hold else "  ep"
        off_tag: str = f"{float(frag.offset):.3f}" if frag.offset else "0"
        note_count: int = len(frag.upper.degrees) + len(frag.lower.degrees)
        print(f"  {written:2d}. {kind}  {frag.upper.name:22s} + "
              f"{frag.lower.name:22s}  sep={frag.separation:2d}  "
              f"{voice_tag}-led  off={off_tag}  {dir_tag}  "
              f"{n_bars}bar  {note_count}n")
    # --- Write file ---
    output_dir: Path = PROJECT_ROOT / "output"
    output_dir.mkdir(exist_ok=True)
    output_path: Path = output_dir / "fragen_poc.mid"
    with open(output_path, "wb") as f:
        midi.writeFile(f)
    # Write .note CSV
    note_path: Path = output_dir / "fragen_poc.note"
    with open(note_path, "w") as nf:
        nf.write(f"## key: {fugue.tonic} {mode}\n")
        nf.write(f"## time: {fugue.metre[0]}/{fugue.metre[1]}\n")
        nf.write(_NOTE_CSV_HEADER + "\n")
        for row in all_note_rows:
            nf.write(row + "\n")
    print(f"\n{regular} episodes + {hold_count} hold-exchange = "
          f"{written} sections ({skipped} skipped)")
    print(f"Written to {output_path}")
    print(f"Notes  to {note_path}")


if __name__ == "__main__":
    main()

"""F3 Checkpoint: Test fragment variety and smooth episode connections across seeds."""
import subprocess
import sys
from fractions import Fraction
from pathlib import Path


def analyze_note_file(note_path: Path) -> dict:
    """Analyze .note file for episode characteristics."""
    with open(note_path, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    # Parse notes (skip header)
    notes = []
    for line in lines:
        parts = line.split(',')
        if len(parts) < 5:
            continue
        # Skip header row
        if parts[0] == 'offset':
            continue
        offset = Fraction(parts[0])
        pitch = int(parts[1])
        duration = Fraction(parts[2])
        voice = int(parts[3])
        lyric = parts[4] if len(parts) > 4 else ""
        notes.append((offset, pitch, duration, voice, lyric))

    # Find episode entries
    episodes = []
    for i, (offset, pitch, dur, voice, lyric) in enumerate(notes):
        if lyric == "episode":
            # Get prior pitch in same voice
            prior_pitch = None
            for j in range(i - 1, -1, -1):
                if notes[j][3] == voice:
                    prior_pitch = notes[j][1]
                    break
            episodes.append({
                'offset': offset,
                'pitch': pitch,
                'voice': voice,
                'prior_pitch': prior_pitch,
                'leap': abs(pitch - prior_pitch) if prior_pitch is not None else None,
            })

    return {'episodes': episodes, 'total_notes': len(notes)}


def main():
    base_dir = Path(__file__).parent.parent
    output_dir = base_dir / "output"
    output_dir.mkdir(exist_ok=True)

    print("F3 Checkpoint: Seeds 1-10\n")
    print("=" * 80)

    for seed in range(1, 11):
        print(f"\n--- Seed {seed} ---")

        # Run pipeline
        result = subprocess.run(
            [
                sys.executable, "-m", "scripts.run_pipeline",
                "invention", "default", "c_major",
                "-o", "output",
                "-seed", str(seed),
            ],
            cwd=str(base_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"  ERROR: Pipeline failed")
            print(result.stderr)
            continue

        # Analyze
        note_path = output_dir / "invention.note"
        if not note_path.exists():
            print(f"  ERROR: No .note file generated")
            continue

        data = analyze_note_file(note_path)
        episodes = data['episodes']

        print(f"  Episodes: {len(episodes)}")

        if episodes:
            # Count unique fragments (by leader voice alternation)
            leaders = [e['voice'] for e in episodes]
            print(f"  Leader voices: {leaders}")

            # Report leaps
            for idx, ep in enumerate(episodes, 1):
                voice_name = "soprano" if ep['voice'] == 0 else "bass"
                leap_st = ep['leap'] if ep['leap'] is not None else 0
                print(f"    Episode {idx} ({voice_name}): entry leap = {leap_st} semitones")
        else:
            print("  No episodes found")

    print("\n" + "=" * 80)
    print("Checkpoint complete. Check leap magnitudes and leader variety.")


if __name__ == "__main__":
    main()

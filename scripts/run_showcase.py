"""Run the treatment/texture showcase for auditory verification.

Generates a piece demonstrating all treatments and textures with
names visible as lyrics in MuseScore.

Usage:
    cd /d/projects/Barok/barok && source .venv/Scripts/activate && cd source/andante
    python -m scripts.run_showcase
"""
from pathlib import Path
from scripts.run_exercises import run_exercise, EXERCISES_OUT

SHOWCASE_BRIEF = Path(__file__).parent.parent / "briefs" / "exercises" / "showcase.brief"


def main() -> None:
    """Run the showcase exercise."""
    EXERCISES_OUT.mkdir(parents=True, exist_ok=True)
    print("Running treatment/texture showcase...")
    print("This generates a piece with all treatments and textures,")
    print("with names as lyrics visible in MuseScore.\n")
    run_exercise(SHOWCASE_BRIEF)
    print(f"\nOutput files in {EXERCISES_OUT}/showcase.*")
    print("Open showcase.musicxml in MuseScore to see treatments/textures as lyrics.")


if __name__ == "__main__":
    main()

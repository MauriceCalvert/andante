"""Run all 8 genres to tests/output with fixed seeds. Deterministic."""
from pathlib import Path

from scripts.run_pipeline import run_from_args

SCRIPT_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = SCRIPT_DIR.parent
OUTPUT_DIR: Path = PROJECT_DIR / "tests" / "output"

GENRES: tuple[str, ...] = (
    "bourree",
    "chorale",
    "fantasia",
    "gavotte",
    "invention",
    "minuet",
    "sarabande",
    "trio_sonata",
)

FIXED_SEED: int = 42


def main() -> None:
    """Run all genres with fixed seed to tests/output."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for genre in GENRES:
        print(f"--- {genre} ---")
        run_from_args(
            genre=genre,
            affect="default",
            output_dir=OUTPUT_DIR,
            seed=FIXED_SEED,
        )
    print(f"\nDone. Output in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

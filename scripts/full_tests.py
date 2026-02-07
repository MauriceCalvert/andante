"""Run the full test suite with summary reporting.

Usage:
    python -m scripts.full_tests          # default: compact summary
    python -m scripts.full_tests -v       # verbose: show every test
    python -m scripts.full_tests -x       # stop on first failure
    python -m scripts.full_tests -k L6    # filter by keyword
    python -m scripts.full_tests --cov    # with coverage report
"""
import subprocess
import sys
import time
from pathlib import Path

ANDANTE_DIR: Path = Path(__file__).resolve().parent.parent
TESTS_DIR: Path = ANDANTE_DIR / "tests"

# Ordered from fast/foundational to slow/integration
TEST_FILES: tuple[str, ...] = (
    # foundational utilities
    "shared/test_key.py",
    "shared/test_music_math.py",
    "data/test_yaml_integrity.py",
    # pipeline layers L1-L5
    "planner/test_L1_rhetorical.py",
    "planner/test_L2_tonal.py",
    "planner/test_L3_schematic.py",
    "planner/test_L4_metric.py",
    "builder/test_L5_phrase_planner.py",
    # generation
    "builder/test_L6_phrase_writer.py",
    # integration
    "builder/test_L7_compose.py",
    "integration/test_cross_phrase_counterpoint.py",
    "integration/test_system.py",
)


def main() -> None:
    """Run pytest with forwarded arguments."""
    # Verify all expected test files exist
    missing: list[str] = [
        f for f in TEST_FILES if not (TESTS_DIR / f).exists()
    ]
    if missing:
        print(f"Missing test files: {missing}")
        sys.exit(1)
    args: list[str] = [
        sys.executable, "-m", "pytest",
        str(TESTS_DIR),
        "-q",
        "--tb=short",
    ]
    args.extend(sys.argv[1:])
    start: float = time.perf_counter()
    result: subprocess.CompletedProcess[bytes] = subprocess.run(
        args,
        cwd=str(ANDANTE_DIR),
    )
    elapsed: float = time.perf_counter() - start
    print(f"\nTotal wall time: {elapsed:.1f}s")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

"""Run the pipeline under coverage analysis to find used/unused code.

Usage:
    python -m scripts.run_pipeline_coverage <same args as run_pipeline>

Example:
    python -m scripts.run_pipeline_coverage invention default
    python -m scripts.run_pipeline_coverage briefs/tests/

After run, open htmlcov/index.html for line-by-line colour-coded report.
Green = executed, red = never reached.
"""
import subprocess
import sys
from pathlib import Path


PROJECT_DIR: Path = Path(__file__).resolve().parent.parent
HTMLCOV_DIR: Path = PROJECT_DIR / "htmlcov"


def main() -> None:
    """Run run_pipeline under coverage, then generate HTML report."""
    pipeline_args: list[str] = sys.argv[1:]
    if not pipeline_args:
        print("Usage: python -m scripts.run_pipeline_coverage <run_pipeline args>")
        print("Example: python -m scripts.run_pipeline_coverage invention default")
        sys.exit(1)
    coverage_data: Path = PROJECT_DIR / ".coverage"
    # Run pipeline under coverage, restricting to andante source only
    cmd: list[str] = [
        sys.executable, "-m", "coverage", "run",
        "--source=builder,motifs,planner,schemas,shared,scripts",
        "--data-file", str(coverage_data),
        "-m", "scripts.run_pipeline",
        *pipeline_args,
    ]
    print(f"Running pipeline with coverage...")
    print(f"  cwd: {PROJECT_DIR}")
    print(f"  args: {' '.join(pipeline_args)}")
    print()
    result: int = subprocess.call(cmd, cwd=str(PROJECT_DIR))
    if result != 0:
        print(f"\nPipeline exited with code {result}")
        sys.exit(result)
    # Generate HTML report
    report_cmd: list[str] = [
        sys.executable, "-m", "coverage", "html",
        "--data-file", str(coverage_data),
        "-d", str(HTMLCOV_DIR),
    ]
    subprocess.call(report_cmd, cwd=str(PROJECT_DIR))
    # Print summary to terminal
    print("\n--- Coverage Summary (lowest first) ---\n")
    summary_cmd: list[str] = [
        sys.executable, "-m", "coverage", "report",
        "--data-file", str(coverage_data),
        "--sort=cover",
    ]
    subprocess.call(summary_cmd, cwd=str(PROJECT_DIR))
    print(f"\nDetailed report: {HTMLCOV_DIR / 'index.html'}")


if __name__ == "__main__":
    main()

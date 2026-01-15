from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Dict
try:
    from radon.raw import analyze
except ImportError as e:
    raise SystemExit("radon is not installed in this interpreter. Run: python -m pip install radon") from e

DEFAULT_EXCLUDE_DIRS: tuple[str, ...] = (
    "tests",
    "archive",
    ".git",
    ".git",
    "output",
    "docs",
    "venv",
    "__pycache__",
    "build",
    "dist",
)

@dataclass(frozen=True, slots=True)
class Totals:
    blank: int
    comments: int
    files_py: int
    files_yaml: int
    loc_py: int
    sloc_py: int
    loc_yaml: int

def is_excluded(path: Path, exclude_dirs: tuple[str, ...]) -> bool:
    parts: tuple[str, ...] = path.parts
    return any(d in parts for d in exclude_dirs)

def iter_files(root: Path, suffix: str, exclude_dirs: tuple[str, ...]) -> Iterable[Path]:
    for path in root.rglob(f"*{suffix}"):
        if is_excluded(path, exclude_dirs):
            continue
        yield path

def safe_int(obj: object, name: str) -> int:
    return int(getattr(obj, name, 0) or 0)

def top_level_dir(root: Path, path: Path) -> str:
    rel: Path = path.relative_to(root)
    if len(rel.parts) == 1:
        return "."
    return rel.parts[0]

def count_lines(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + 1

def add_totals(a: Totals, b: Totals) -> Totals:
    return Totals(
        blank=a.blank + b.blank,
        comments=a.comments + b.comments,
        files_py=a.files_py + b.files_py,
        files_yaml=a.files_yaml + b.files_yaml,
        loc_py=a.loc_py + b.loc_py,
        sloc_py=a.sloc_py + b.sloc_py,
        loc_yaml=a.loc_yaml + b.loc_yaml,
    )

def main() -> int:
    """Sum LOC/SLOC for .py, count files and LOC for .yaml, grouped by top-level subfolder, with grand totals."""
    root: Path = Path.cwd()
    exclude_dirs: tuple[str, ...] = DEFAULT_EXCLUDE_DIRS
    per_dir: Dict[str, Totals] = {}
    failed: list[Path] = []
    for path in iter_files(root, ".py", exclude_dirs):
        key: str = top_level_dir(root, path)
        totals: Totals = per_dir.get(key, Totals(0, 0, 0, 0, 0, 0, 0))
        try:
            text: str = path.read_text(encoding="utf-8", errors="replace")
            metrics = analyze(text)
            per_dir[key] = Totals(
                blank=totals.blank + safe_int(metrics, "blank"),
                comments=totals.comments + safe_int(metrics, "comments"),
                files_py=totals.files_py + 1,
                files_yaml=totals.files_yaml,
                loc_py=totals.loc_py + safe_int(metrics, "loc"),
                sloc_py=totals.sloc_py + safe_int(metrics, "sloc"),
                loc_yaml=totals.loc_yaml,
            )
        except Exception:
            failed.append(path)
    for path in iter_files(root, ".yaml", exclude_dirs):
        key: str = top_level_dir(root, path)
        totals: Totals = per_dir.get(key, Totals(0, 0, 0, 0, 0, 0, 0))
        try:
            text: str = path.read_text(encoding="utf-8", errors="replace")
            loc_yaml: int = count_lines(text)
            per_dir[key] = Totals(
                blank=totals.blank,
                comments=totals.comments,
                files_py=totals.files_py,
                files_yaml=totals.files_yaml + 1,
                loc_py=totals.loc_py,
                sloc_py=totals.sloc_py,
                loc_yaml=totals.loc_yaml + loc_yaml,
            )
        except Exception:
            failed.append(path)
    print(f"Root: {root}")
    print(f"Excluded dirs: {', '.join(exclude_dirs)}")
    grand: Totals = Totals(0, 0, 0, 0, 0, 0, 0)
    for key in sorted(per_dir.keys()):
        totals = per_dir[key]
        grand = add_totals(grand, totals)
        print(f"\n[{key}]")
        print(f"\tPython files: {totals.files_py}")
        print(f"\tYAML files: {totals.files_yaml}")
        print(f"\tPython LOC: {totals.loc_py}")
        print(f"\tPython SourceLOC: {totals.sloc_py}")
        print(f"\tYAML LOC: {totals.loc_yaml}")
        print(f"\tComments: {totals.comments}")
        print(f"\tBlank: {totals.blank}")
    print("\n[TOTAL]")
    print(f"\tPython files: {grand.files_py}")
    print(f"\tYAML files: {grand.files_yaml}")
    print(f"\tPython LOC: {grand.loc_py}")
    print(f"\tPython SourceLOC: {grand.sloc_py}")
    print(f"\tYAML LOC: {grand.loc_yaml}")
    print(f"\tComments: {grand.comments}")
    print(f"\tBlank: {grand.blank}")
    if failed:
        print("\nFailed to analyze:")
        for path in failed:
            print(f"  {path}")
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

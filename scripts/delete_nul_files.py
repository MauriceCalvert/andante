"""Delete all files literally named 'nul' in the current tree.

On Windows, 'nul' is a reserved device name.  Plain os.remove / Path.unlink
silently target the NUL device instead of the file.  The \\?\ extended-length
prefix forces Windows to treat the path as a real file.
"""
import os
from pathlib import Path


def _to_extended(p: Path) -> str:
    """Return an extended-length absolute path string (bypasses device names)."""
    return "\\\\?\\" + str(p.resolve())


def main() -> None:
    root = Path("..")
    found: list[Path] = []

    for dirpath, _dirs, filenames in os.walk(root):
        for name in filenames:
            if name.lower() == "nul":
                found.append(Path(dirpath) / name)

    if not found:
        print("No files named 'nul' found.")
        return

    for p in found:
        ext = _to_extended(p)
        os.remove(ext)
        print(f"Deleted: {p}")

    print(f"\nDone — {len(found)} file(s) removed.")


if __name__ == "__main__":
    main()

"""Disk cache utilities for expensive computations."""
import pickle
from pathlib import Path

# Navigate up 3 levels instead of 2 to maintain same cache location
# subject_gen/cache.py -> subject_gen -> motifs -> andante -> .cache/subject
_CACHE_DIR: Path = Path(__file__).resolve().parent.parent.parent / ".cache" / "subject"


def _cache_path(name: str) -> Path:
    """Return cache file path, creating directory if needed."""
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / name


def _load_cache(name: str) -> object | None:
    """Load pickled object from cache, or None if missing/corrupt."""
    p = _cache_path(name)
    if not p.exists():
        return None
    try:
        with open(p, "rb") as f:
            return pickle.load(f)
    except Exception:
        return None


def _save_cache(name: str, obj: object) -> None:
    """Save object to cache."""
    p = _cache_path(name)
    with open(p, "wb") as f:
        pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)

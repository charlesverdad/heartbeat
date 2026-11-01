"""Shared helpers for the bilingual_cut pipeline."""
import json
from pathlib import Path


def load(work: Path, name: str):
    with open(Path(work) / name, encoding="utf-8") as f:
        return json.load(f)


def save(work: Path, name: str, data):
    path = Path(work) / name
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"wrote {path}")
    return path


def ts(seconds: float) -> str:
    """[HH:MM:SS] for human-readable dumps."""
    s = max(0.0, seconds)
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def srt_ts(seconds: float) -> str:
    s = max(0.0, seconds)
    h, rem = divmod(int(s), 3600)
    m, sec = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    if ms == 1000:  # rounding carry
        ms, sec = 0, sec + 1
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"


def merge_ranges(ranges, gap=0.0):
    """Merge overlapping/adjacent (start, end) pairs. `gap` bridges near-misses."""
    out = []
    for start, end in sorted(ranges):
        if out and start - out[-1][1] <= gap:
            out[-1][1] = max(out[-1][1], end)
        else:
            out.append([start, end])
    return [(a, b) for a, b in out]

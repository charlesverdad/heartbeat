#!/usr/bin/env python3
"""Stage 12 - tidy the spliced subtitle files.

Two passes laid cues out independently (the cut's own cues and the inserted
video's), so a few short continuation fragments end up stranded in cues of
their own and a few cues still overlap by a frame or two. Fold the fragments
back and clamp what is left.
"""
import argparse
import re
from pathlib import Path

MAX_LINE = 42


def parse(path):
    cues, blk = [], []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            if len(blk) >= 3:
                cues.append(blk)
            blk = []
        else:
            blk.append(line)
    if len(blk) >= 3:
        cues.append(blk)
    a_b = [c[1].split(" --> ") for c in cues]
    return [[sec(a), sec(b), "\n".join(c[2:])] for (a, b), c in zip(a_b, cues)]


def sec(t):
    h, m, rest = t.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def fmt(x):
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap(text, width=MAX_LINE, max_lines=2):
    while True:
        out = _wrap(text, width)
        if out.count("\n") < max_lines or width >= 70:
            return out
        width += 4


def _wrap(text, width=MAX_LINE):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def tidy(cues, max_frag=8, max_gap=0.1, min_dur=0.15, sep=0.02, max_dur=None):
    out, folded = [], []
    for cue in cues:
        flat = cue[2].replace("\n", " ").strip()
        if not re.search(r"[\w가-힣]", flat):
            folded.append(f"(dropped {flat!r})")
            continue                      # a cue of bare punctuation is debris
        prev = out[-1] if out else None
        # a dual cue is "korean line(s)" + "english line(s)"; only the english
        # tail may absorb a stranded english fragment, so work on the last line.
        head = prev[2].split("\n") if prev else []
        sliver = max_dur is None or cue[1] - cue[0] <= max_dur
        if (prev and sliver and len(flat) <= max_frag
                and not re.search(r"[가-힣]", flat)
                and cue[0] - prev[1] <= max_gap
                and (head[-1].rstrip()[-1:] not in ".!?"
                     or (cue[1] - cue[0] <= 0.45 and cue[0] - prev[1] <= 0.06))
                and not re.search(r"[가-힣]", head[-1])):
            joiner = "" if flat[0] in "'\".,!?" else " "
            ko = [l for l in head if re.search(r"[가-힣]", l)]
            en = [l for l in head if not re.search(r"[가-힣]", l)]
            en_text = " ".join(en).rstrip() + joiner + flat
            prev[2] = "\n".join(ko + [wrap(en_text)]) if ko else wrap(en_text)
            prev[1] = max(prev[1], cue[1])
            folded.append(flat)
            continue
        out.append(cue)
    clamped = 0
    for i in range(len(out) - 1):
        if out[i][1] > out[i + 1][0] - sep:
            out[i][1] = max(out[i][0] + min_dur, out[i + 1][0] - sep)
            clamped += 1
    return out, folded, clamped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--tracks", default="en,ko,dual")
    ap.add_argument("--suffix", default="_v2")
    args = ap.parse_args()
    work = Path(args.work)
    for name in args.tracks.split(","):
        path = work / f"subs_{name}{args.suffix}.srt"
        cues, folded, clamped = tidy(parse(path))
        path.write_text("\n".join(
            f"{i}\n{fmt(a)} --> {fmt(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)),
            encoding="utf-8")
        left = sum(1 for i in range(len(cues) - 1) if cues[i][1] > cues[i + 1][0] + 0.001)
        print(f"{path.name}: {len(cues)} cues, folded {len(folded)} {folded}, "
              f"clamped {clamped}, overlaps left {left}")


if __name__ == "__main__":
    main()

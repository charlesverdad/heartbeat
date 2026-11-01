#!/usr/bin/env python3
"""Stage 11 - rebuild the subtitle files for the spliced timeline.

05_render lays out cues against the cut alone. Splicing the external video in
pushes everything after the join later by its duration, and the video's own
lines have to be laid out and dropped into the gap.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from common import ts  # noqa: E402

spec = importlib.util.spec_from_file_location("render", HERE / "05_render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)


def parse_srt(path):
    cues, block = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "":
            if len(block) >= 3:
                cues.append(_cue(block))
            block = []
        else:
            block.append(line)
    if len(block) >= 3:
        cues.append(_cue(block))
    return cues


def _cue(block):
    a, b = block[1].split(" --> ")
    return [_sec(a), _sec(b), "\n".join(block[2:])]


def _sec(t):
    h, m, rest = t.strip().split(":")
    s, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--insert-dir", required=True,
                    help="dir holding the inserted video's segments/translations")
    ap.add_argument("--suffix", default="_v2")
    args = ap.parse_args()

    work = Path(args.work)
    sp = json.loads((work / "splice.json").read_text())
    at, dur = sp["insert_at"], sp["insert_dur"]

    ins = Path(args.insert_dir)
    trans = json.loads((ins / "translations.json").read_text(encoding="utf-8"))
    trans = [t for t in trans if t["src_end"] <= dur]
    # one synthetic clip: the inserted video is kept whole, unshifted
    vclip = [{"src_start": 0.0, "src_end": dur, "out_start": 0.0, "out_end": dur}]

    def ins_cues(field):
        items = [{"src_start": t["src_start"], "src_end": t["src_end"],
                  "text": t[field], "compression_ratio": 0.0} for t in trans
                 if t.get(field, "").strip()]
        return [[a + at, b + at, txt]
                for a, b, txt in render.build_cues(items, vclip, "text")]

    def dual_cues():
        items = [{"src_start": t["src_start"], "src_end": t["src_end"],
                  "text": f"{t['ko'].strip()}\n{t['en'].strip()}",
                  "compression_ratio": 0.0} for t in trans]
        return [[a + at, b + at, txt]
                for a, b, txt in render.build_cues(items, vclip, "text")]

    for name, extra in (("en", ins_cues("en")), ("ko", ins_cues("ko")),
                        ("dual", dual_cues())):
        cues = parse_srt(work / f"subs_{name}.srt")
        out = []
        for a, b, txt in cues:
            if b <= at + 0.001:
                out.append([a, b, txt])
            elif a >= at - 0.001:
                out.append([a + dur, b + dur, txt])
            else:                       # straddles the join - end it there
                out.append([a, at, txt])
        out.extend(extra)
        out.sort(key=lambda c: c[0])
        # splitting a long line can strand a short ASCII tail ("'", "you.")
        # in a cue of its own; fold those back into the piece they belong to.
        # Korean is left alone - four characters there is a real word.
        merged = []
        for c in out:
            tail = c[2].strip()
            if (merged and tail.isascii() and len(tail) <= 4
                    and merged[-1][1] >= c[0] - 0.5
                    and merged[-1][2].isascii()):
                joiner = "" if tail[0] in "'\".,!?" else " "
                text = merged[-1][2].replace("\n", " ").rstrip() + joiner + tail
                merged[-1][2] = render.wrap(text)
                merged[-1][1] = max(merged[-1][1], c[1])
                continue
            merged.append(c)
        out = merged
        # the two lists were laid out independently, so clamp once more
        for i in range(len(out) - 1):
            if out[i][1] > out[i + 1][0] - 0.04:
                out[i][1] = max(out[i][0] + 0.3, out[i + 1][0] - 0.04)
        dest = work / f"subs_{name}{args.suffix}.srt"
        render.write_srt(dest, out)
        print(f"  +{len(extra)} inserted cues -> {dest.name}")

    print(f"join at {ts(at)}, inserted {dur:.0f}s")


if __name__ == "__main__":
    main()

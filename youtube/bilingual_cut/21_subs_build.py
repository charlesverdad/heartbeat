#!/usr/bin/env python3
"""Stage 21 - build subtitles for the rendered cut from its own ASR pass.

05_render lays cues out from source-time segments and 11_subs_splice shifts
them past the join; both are correct but inherit the source segmentation, so a
cue can sit slightly late and a segment that survived the cut only partly loses
its translation entirely. Here the finished file's own word timings carry the
existing English, so timing is exact and the gaps are explicit.
"""
import argparse
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("render", HERE / "05_render.py")
render = importlib.util.module_from_spec(spec)
spec.loader.exec_module(render)

_ts = importlib.util.spec_from_file_location("tidy", HERE / "12_subs_tidy.py")
tidy_mod = importlib.util.module_from_spec(_ts)
_ts.loader.exec_module(tidy_mod)

MIN_CUE, MAX_CUE, GAP, CPS = 0.9, 7.0, 0.04, 16.0
SPLIT_AT = 76          # leave slack so a piece wraps to two lines, not three
MAX_LINES = 2


def wrap2(text, width=render.MAX_LINE):
    """Wrap to at most MAX_LINES, widening until it fits rather than spilling."""
    flat = " ".join(text.split())
    while True:
        out = render.wrap(flat, width, MAX_LINES)
        if out.count("\n") < MAX_LINES or width >= 70:
            return out
        width += 4


def srt_ts(x):
    ms = int(round(x * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def merge_costarting(items, window=0.35, cap=200):
    """Two anchors can claim overlapping words and land on the same instant.

    Laying both out squashes the first into an unreadable sliver, so join them
    into one cue over the union of their spans instead.
    """
    items = sorted(items, key=lambda c: (c[0], c[1]))
    out = []
    for start, end, text in items:
        if out and start - out[-1][0] < window and \
                len(out[-1][2]) + len(text) < cap and \
                out[-1][2].strip() != text.strip():
            out[-1][1] = max(out[-1][1], end)
            # dual cues stack korean over english; keep the two languages apart
            if "\n" in out[-1][2] and "\n" in text:
                ka, ea = out[-1][2].split("\n", 1)
                kb, eb = text.split("\n", 1)
                out[-1][2] = f"{ka.strip()} {kb.strip()}\n{ea.strip()} {eb.strip()}"
            else:
                out[-1][2] = f"{out[-1][2].strip()} {text.strip()}"
        else:
            out.append([start, end, text])
    return [tuple(c) for c in out]


def lay_out(items):
    """[(start, end, text)] -> cues, splitting long text across each own span."""
    items = merge_costarting(items)
    cues = []
    for i, (start, end, text) in enumerate(items):
        nxt = items[i + 1][0] if i + 1 < len(items) else end + MAX_CUE
        pieces = render.split_text(text, SPLIT_AT)
        # a cue too short to read gets what room the next one leaves
        want = max(end - start, min(len(text) / CPS, MAX_CUE * len(pieces)))
        stop_all = min(max(start + want, end), max(nxt - GAP, start + MIN_CUE))
        total = sum(len(p) for p in pieces) or 1
        cursor, budget = start, stop_all - start
        for j, piece in enumerate(pieces):
            share = budget * len(piece) / total
            stop = cursor + max(share, MIN_CUE)
            if j == len(pieces) - 1:
                stop = max(stop_all, cursor + MIN_CUE)
            stop = min(stop, cursor + MAX_CUE)
            cues.append([cursor, stop, wrap2(piece)])
            cursor = stop + GAP
    folded = []
    for c in cues:
        flat = c[2].replace("\n", " ").strip()
        if (folded and c[1] - c[0] < 0.6 and len(flat) <= 14
                and c[0] - folded[-1][1] < 0.4 and "\n" not in folded[-1][2]):
            folded[-1][2] = wrap2(folded[-1][2].replace("\n", " ") + " " + flat)
            folded[-1][1] = max(folded[-1][1], c[1])
            continue
        folded.append(c)
    cues = folded
    for i in range(len(cues) - 1):
        if cues[i][1] > cues[i + 1][0] - GAP:
            cues[i][1] = max(cues[i][0] + 0.35, cues[i + 1][0] - GAP)
    return [c for c in cues if c[1] > c[0]]


def write_srt(path, cues):
    Path(path).write_text("\n".join(
        f"{i}\n{srt_ts(a)} --> {srt_ts(b)}\n{t}\n" for i, (a, b, t) in enumerate(cues, 1)),
        encoding="utf-8")
    print(f"wrote {Path(path).name} ({len(cues)} cues)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--insert-dir", required=True)
    ap.add_argument("--stem", default="sermon_korean_cut_v5")
    ap.add_argument("--suffix", default="-v2")
    args = ap.parse_args()
    work = Path(args.work)

    asr = json.loads((work / "v5_asr.json").read_text(encoding="utf-8"))["segments"]
    retime = json.loads((work / "v5_retime.json").read_text(encoding="utf-8"))
    gapfill = json.loads((work / "v5_gapfill.json").read_text(encoding="utf-8"))["cues"]
    reading = json.loads((work / "v5_reading_en.json").read_text(encoding="utf-8"))
    sp = json.loads((work / "splice.json").read_text())
    AT, DUR = sp["insert_at"], sp["insert_dur"]
    ins = json.loads((Path(args.insert_dir) / "translations.json").read_text(encoding="utf-8"))
    ins = [t for t in ins if t["src_end"] <= DUR]

    dropped = {round(t, 1) for g in gapfill for t in g.get("replaces", [])}
    timed = [t for t in retime["timed"] if round(t["out_start"], 1) not in dropped]
    print(f"{len(timed)} re-timed cues, {len(gapfill)} gap cues, "
          f"{len(reading)} reading cues, {len(ins)} inserted cues")

    en, ko, dual = [], [], []
    for t in timed:
        en.append((t["out_start"], t["out_end"], t["en"]))
        dual.append((t["out_start"], t["out_end"], f"{t['ko'].strip()}\n{t['en'].strip()}"))
    for g in gapfill:
        en.append((g["start"], g["end"], g["en"]))
        dual.append((g["start"], g["end"], f"{g['ko'].strip()}\n{g['en'].strip()}"))
    for r in reading:                      # english audio: english track only
        en.append((r["start"], r["end"], r["text"]))
        dual.append((r["start"], r["end"], r["text"]))
    for s in asr:                          # the MC's welcome and handover
        if s["lang"] == "en" and s["compression_ratio"] <= 2.4:
            en.append((s["start"], s["end"], s["text"]))
            dual.append((s["start"], s["end"], s["text"]))
    for t in ins:
        a, b = t["src_start"] + AT, t["src_end"] + AT
        en.append((a, b, t["en"]))
        ko.append((a, b, t["ko"]))
        dual.append((a, b, f"{t['ko'].strip()}\n{t['en'].strip()}"))

    # korean track: the ASR itself, minus what the tail filter and the artifact
    # checks removed (the song, the congregation, the interpreter, decoder loops)
    keep = {(round(w["out_s"], 2)) for w in []}
    kept_spans = [(t["out_start"], t["out_end"]) for t in retime["timed"]]
    kept_spans += [(g["start"], g["end"]) for g in gapfill]
    for s in asr:
        if s["lang"] != "ko" or s["compression_ratio"] > 2.4 or s["no_speech_prob"] > 0.6:
            continue
        if AT <= (s["start"] + s["end"]) / 2 < AT + DUR:
            continue                        # the inserted video brings its own
        mid = (s["start"] + s["end"]) / 2
        if not any(a - 0.6 <= mid <= b + 0.6 for a, b in kept_spans):
            continue                        # nothing english kept it: song or noise
        ko.append((s["start"], s["end"], s["text"]))

    for name, items in (("en", en), ("ko", ko), ("dual", dual)):
        cues = [list(c) for c in lay_out(items)]
        # splitting a long dual cue can strand its english tail in a cue of its
        # own; the tidy pass folds those back and clamps what still overlaps.
        cues, folded, clamped = tidy_mod.tidy(cues, max_frag=20, max_dur=0.65)
        if folded or clamped:
            print(f"  {name}: folded {len(folded)} {folded}, clamped {clamped}")
        write_srt(work / f"{args.stem}.{name}{args.suffix}.srt", cues)


if __name__ == "__main__":
    main()

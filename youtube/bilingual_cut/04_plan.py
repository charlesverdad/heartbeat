#!/usr/bin/env python3
"""Stage 04 - turn language regions + section labels into a cut plan.

sections.json (hand-authored) drives this:
  {"sections": [
     {"start": 1200, "end": 1350, "mode": "all", "label": "guest intro"},
     {"start": 1350, "end": 4200, "mode": "ko",  "label": "sermon"}
  ],
   "drop": [[1500, 1520]]}

mode "ko"  keep only Korean-language regions inside the span
mode "all" keep the span verbatim (used for intros/prayers regardless of language)

Writes cutplan.json: ordered clips carrying BOTH the source timestamps and their
position in the output timeline, so timings stay re-adjustable.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts, merge_ranges  # noqa: E402


def overlap(a, b):
    return max(0.0, min(a[1], b[1]) - max(a[0], b[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--pad-start", type=float, default=0.22)
    ap.add_argument("--pad-end", type=float, default=0.12)
    ap.add_argument("--bridge-gap", type=float, default=1.2,
                    help="keep pauses shorter than this instead of cutting them")
    ap.add_argument("--guard", type=float, default=0.35,
                    help="stay this far clear of the interpreter's first syllable")
    ap.add_argument("--guard-tail", type=float, default=0.12,
                    help="also stay clear after English speech ends")
    ap.add_argument("--min-clip", type=float, default=0.8)
    args = ap.parse_args()

    work = Path(args.work)
    regions = load(work, "regions.json")["regions"]
    langmap = load(work, "langmap.json")["utterances"]
    segdata = load(work, "segments.json")
    duration = segdata["source_duration"]
    sections = load(work, "sections.json")

    kept = []  # (start, end, label)
    for sec in sections["sections"]:
        span = (float(sec["start"]), float(sec["end"]))
        label = sec.get("label", "")
        if sec.get("mode", "ko") == "all":
            kept.append((span[0], span[1], label))
            continue
        want = sec.get("lang", "ko")
        for r in regions:
            if r["lang"] != want:
                continue
            if overlap((r["src_start"], r["src_end"]), span) <= 0:
                continue
            kept.append((max(r["src_start"], span[0]),
                         min(r["src_end"], span[1]), label))

    # extra manual keeps
    for extra in sections.get("keep", []):
        kept.append((float(extra[0]), float(extra[1]),
                     extra[2] if len(extra) > 2 else "manual"))

    # pad, then merge anything that ends up touching
    padded = []
    for s, e, label in kept:
        padded.append((max(0.0, s - args.pad_start), min(duration, e + args.pad_end), label))
    padded.sort()

    merged = []
    for s, e, label in padded:
        if merged and s - merged[-1][1] <= args.bridge_gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e, label])

    # Never let a Korean clip run into the interpreter. Subtracting the English
    # utterances (widened by a guard) both trims the tails that were bleeding
    # the translator's first syllables and removes whole English turns that
    # gap-bridging had swallowed.
    ko_spans = merge_ranges([(float(x["start"]), float(x["end"]))
                             for x in sections["sections"]
                             if x.get("mode", "ko") != "all"])
    english = merge_ranges([
        (u["src_start"] - args.guard, u["src_end"] + args.guard_tail)
        for u in langmap if u["p_en"] > u["p_ko"]], gap=0.05)
    english = [e for e in english
               if any(overlap(e, k) > 0 for k in ko_spans)]

    trimmed = []
    for s0, e0, label in merged:
        pieces = [(s0, e0)]
        for es, ee in english:
            nxt = []
            for ps, pe in pieces:
                if ee <= ps or es >= pe:
                    nxt.append((ps, pe))
                    continue
                if ps < es:
                    nxt.append((ps, es))
                if ee < pe:
                    nxt.append((ee, pe))
            pieces = nxt
        for ps, pe in pieces:
            trimmed.append([ps, pe, label])
    merged = trimmed

    # manual drops
    drops = merge_ranges([(float(a), float(b)) for a, b in sections.get("drop", [])])
    final = []
    for s, e, label in merged:
        pieces = [(s, e)]
        for ds, de in drops:
            nxt = []
            for ps, pe in pieces:
                if de <= ps or ds >= pe:
                    nxt.append((ps, pe))
                    continue
                if ps < ds:
                    nxt.append((ps, ds))
                if de < pe:
                    nxt.append((de, pe))
            pieces = nxt
        for ps, pe in pieces:
            if pe - ps >= args.min_clip:
                final.append((ps, pe, label))

    clips, cursor = [], 0.0
    for i, (s, e, label) in enumerate(final):
        dur = e - s
        clips.append({
            "id": i,
            "label": label,
            "src_start": round(s, 3),
            "src_end": round(e, 3),
            "out_start": round(cursor, 3),
            "out_end": round(cursor + dur, 3),
            "duration": round(dur, 3),
        })
        cursor += dur

    print(f"{len(clips)} clips, output duration {ts(cursor)} "
          f"(source {ts(duration)}, {100 * cursor / duration:.0f}%)")
    by_label = {}
    for c in clips:
        by_label[c["label"]] = by_label.get(c["label"], 0.0) + c["duration"]
    for label, secs in by_label.items():
        print(f"  {label or '(none)':<24} {ts(secs)}")

    save(work, "cutplan.json", {
        "source_duration": duration,
        "output_duration": round(cursor, 3),
        "params": vars(args),
        "clips": clips,
    })


if __name__ == "__main__":
    main()

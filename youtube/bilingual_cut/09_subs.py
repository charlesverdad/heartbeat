#!/usr/bin/env python3
"""Stage 09 - maintain the English subtitle track, keyed by SOURCE TIME.

Translations live in translations_anchored.json as
{src_start, src_end, ko, en} records. Because they carry their own source
timestamps rather than a segment id, re-running VAD/transcription can never
invalidate them again.

  --report   how much kept Korean audio still has no translation
  --batches  write translate_new_NN.json for the uncovered Korean
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402


def overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def load_anchors(work):
    p = work / "translations_anchored.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def kept_korean(work):
    segs = load(work, "segments.json")["segments"]
    clips = load(work, "cutplan.json")["clips"]

    def in_cut(s):
        return sum(overlap(s["src_start"], s["src_end"], c["src_start"], c["src_end"])
                   for c in clips) > 0.5 * max(0.1, s["src_end"] - s["src_start"])

    return [s for s in segs
            if s["lang"] == "ko" and s.get("compression_ratio", 0) <= 2.4 and in_cut(s)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--batches", action="store_true")
    ap.add_argument("--batch-size", type=int, default=70)
    ap.add_argument("--covered-frac", type=float, default=0.6)
    args = ap.parse_args()

    work = Path(args.work)
    anchors = load_anchors(work)
    ko = kept_korean(work)

    todo = []
    for s in ko:
        dur = max(0.1, s["src_end"] - s["src_start"])
        cov = sum(overlap(s["src_start"], s["src_end"], a["src_start"], a["src_end"])
                  for a in anchors)
        if cov / dur < args.covered_frac:
            todo.append(s)

    ko_secs = sum(s["src_end"] - s["src_start"] for s in ko)
    todo_secs = sum(s["src_end"] - s["src_start"] for s in todo)
    print(f"anchors on file      : {len(anchors)}")
    print(f"kept Korean segments : {len(ko)}  ({ts(ko_secs)})")
    print(f"still untranslated   : {len(todo)}  ({ts(todo_secs)})")

    if not args.batches:
        return

    segs = load(work, "segments.json")["segments"]
    en_segs = [s for s in segs
               if s["lang"] == "en" and s.get("compression_ratio", 0) <= 2.4]

    for old in work.glob("translate_new_*.json"):
        old.unlink()

    n = 0
    for i in range(0, len(todo), args.batch_size):
        n += 1
        items = []
        for s in todo[i:i + args.batch_size]:
            ref = " ".join(e["text"] for e in en_segs
                           if s["src_end"] <= e["src_start"] <= s["src_end"] + 75)[:320]
            items.append({
                "src_start": s["src_start"], "src_end": s["src_end"],
                "t": ts(s["src_start"]), "ko": s["text"], "interpreter_en": ref,
            })
        p = work / f"translate_new_{n:02d}.json"
        p.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {p.name} ({len(items)})")


if __name__ == "__main__":
    main()

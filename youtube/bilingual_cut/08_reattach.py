#!/usr/bin/env python3
"""Stage 08 - re-attach hand-written translations after a re-transcription.

Segment ids are positional, so re-running stage 03 invalidates any
translations.json keyed by id. translations_anchored.json stores each
translation against its Korean text and source time instead, which survives
re-segmentation. This matches those anchors back onto the current segments and
reports what still needs translating.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, save, ts  # noqa: E402


def norm(text):
    return re.sub(r"[\s.,!?~…\"'()·\-]+", "", text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--window", type=float, default=6.0,
                    help="seconds of drift allowed when matching an anchor")
    args = ap.parse_args()

    work = Path(args.work)
    anchors = json.loads((work / "translations_anchored.json").read_text(encoding="utf-8"))
    segs = load(work, "segments.json")["segments"]
    ko = [s for s in segs if s["lang"] == "ko" and s.get("compression_ratio", 0) <= 2.4]

    by_norm = {}
    for s in ko:
        by_norm.setdefault(norm(s["text"]), []).append(s)

    out, used, unmatched = {}, set(), []
    for a in anchors:
        cands = by_norm.get(norm(a["ko"]), [])
        free = [c for c in cands if c["id"] not in used]
        if not free:
            unmatched.append(a)
            continue
        near = [c for c in free if abs(c["src_start"] - a["src_start"]) <= args.window]
        pick = min(near or free, key=lambda c: abs(c["src_start"] - a["src_start"]))
        out[str(pick["id"])] = a["en"]
        used.add(pick["id"])

    save(work, "translations.json", out)
    print(f"re-attached {len(out)}/{len(anchors)} anchors; {len(unmatched)} could not be matched")
    for a in unmatched[:15]:
        print(f"  UNMATCHED {ts(a['src_start'])} {a['ko'][:60]}")

    clips_path = work / "cutplan.json"
    if clips_path.exists():
        clips = load(work, "cutplan.json")["clips"]

        def kept(s):
            return any(c["src_start"] <= s["src_start"] <= c["src_end"] or
                       c["src_start"] <= s["src_end"] <= c["src_end"] for c in clips)

        todo = [s for s in ko if kept(s) and str(s["id"]) not in out]
        print(f"\n{len(todo)} kept Korean segments still need a translation")


if __name__ == "__main__":
    main()

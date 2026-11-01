#!/usr/bin/env python3
"""Stage 06 - prepare Korean segments for translation.

Emits translate_batch_NN.json containing the Korean segments that survive the
cut, each paired with the live interpreter's English for the same passage. The
interpreter's wording is the ground truth for names, Bible references and
church-specific terms; the translation itself is done by the model, which can
see the whole discourse rather than one sentence at a time.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--ref-window", type=float, default=90.0,
                    help="seconds after a Korean segment to look for the interpreter")
    args = ap.parse_args()

    work = Path(args.work)
    segs = load(work, "segments.json")["segments"]
    clips = load(work, "cutplan.json")["clips"]

    def kept(s):
        return any(c["src_start"] <= s["src_start"] <= c["src_end"] or
                   c["src_start"] <= s["src_end"] <= c["src_end"] for c in clips)

    en_segs = [s for s in segs if s["lang"] == "en"]
    ko_kept = [s for s in segs if s["lang"] == "ko" and kept(s)
               and s.get("compression_ratio", 0) <= 2.4]
    print(f"{len(ko_kept)} Korean segments to translate "
          f"(of {sum(1 for s in segs if s['lang'] == 'ko')} total)")

    items = []
    for s in ko_kept:
        ref = " ".join(
            e["text"] for e in en_segs
            if e.get("compression_ratio", 0) <= 2.4
            if s["src_end"] <= e["src_start"] <= s["src_end"] + args.ref_window
        )[:600]
        items.append({
            "id": s["id"],
            "t": ts(s["src_start"]),
            "src_start": s["src_start"],
            "src_end": s["src_end"],
            "ko": s["text"],
            "interpreter_en": ref,
        })

    n = 0
    for i in range(0, len(items), args.batch_size):
        n += 1
        path = work / f"translate_batch_{n:02d}.json"
        path.write_text(json.dumps(items[i:i + args.batch_size],
                                   ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"wrote {path} ({len(items[i:i + args.batch_size])} segments)")

    if not (work / "translations.json").exists():
        (work / "translations.json").write_text("{}", encoding="utf-8")
    print(f"\n{n} batches. Fill translations.json as {{\"<id>\": \"<english>\"}}.")


if __name__ == "__main__":
    main()

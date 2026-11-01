#!/usr/bin/env python3
"""Print a compact language timeline so the service structure is readable at a glance.

Buckets the source into fixed windows and reports how much Korean vs English
speech each window holds. Consecutive-interpretation stretches show up as
roughly balanced ko/en; worship and announcements show up as lopsided or empty.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import load, ts  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--bucket", type=float, default=60.0)
    args = ap.parse_args()

    work = Path(args.work)
    lm = load(work, "langmap.json")["utterances"]
    duration = load(work, "vad.json")["source_duration"]

    n = int(duration // args.bucket) + 1
    ko = [0.0] * n
    en = [0.0] * n
    for u in lm:
        dur = u["src_end"] - u["src_start"]
        b = int(u["src_start"] // args.bucket)
        if b < n:
            (ko if u["p_ko"] >= u["p_en"] else en)[b] += dur

    print(f"{'time':<10} {'ko':>5} {'en':>5}  {'speech%':>7}  bar (K=korean, e=english)")
    for i in range(n):
        speech = ko[i] + en[i]
        kbar = "K" * int(round(ko[i] / args.bucket * 30))
        ebar = "e" * int(round(en[i] / args.bucket * 30))
        print(f"{ts(i * args.bucket):<10} {ko[i]:>5.0f} {en[i]:>5.0f}  "
              f"{100 * speech / args.bucket:>6.0f}%  {kbar}{ebar}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Confirm every sentence handed out for translation came back.

This is the one failure in the pipeline that is both likely and silent. A
subagent that truncates its reply returns valid JSON covering only part of its
batch; `build_srt.py` then builds a track with a hole in it, and the hole is a
stretch of sermon with no subtitle at all. Nobody notices until it is on screen.

Run between translating and building. Exits non-zero if anything is missing, so
it can be chained:  check_batches.py <dir> && build_srt.py ...
"""
import argparse, json, pathlib, sys

def load(batchdir):
    bd = pathlib.Path(batchdir)
    asked, per_batch = {}, {}
    for f in sorted(bd.glob("batch_*.json")):
        ids = {s["id"] for s in json.load(open(f))["sentences"]}
        per_batch[f.stem] = ids
        asked.update({i: f.stem for i in ids})
    got, blank = set(), set()
    for f in sorted(bd.glob("zh_*.json")):
        for t in json.load(open(f))["translations"]:
            i = int(t["id"])
            (got if str(t.get("zh", "")).strip() else blank).add(i)
    return asked, per_batch, got, blank

def main(batchdir):
    asked, per_batch, got, blank = load(batchdir)
    if not asked:
        print(f"no batch_*.json in {batchdir}", file=sys.stderr)
        return 2
    missing = set(asked) - got
    stray   = got - set(asked)

    print(f"asked      : {len(asked)}")
    print(f"translated : {len(got)}  ({100*len(got)/len(asked):.1f}%)")

    for name in sorted(per_batch):
        ids  = per_batch[name]
        miss = sorted(ids - got)
        mark = "ok" if not miss else "!!"
        print(f"  {mark} {name}: {len(ids & got)}/{len(ids)}" +
              (f"  missing {len(miss)}: {miss[:8]}{' ...' if len(miss) > 8 else ''}" if miss else ""))

    if blank:
        print(f"  !! {len(blank)} returned with empty zh: {sorted(blank)[:8]}")
    if stray:
        print(f"  -- {len(stray)} ids nobody asked for: {sorted(stray)[:8]}")

    if missing or blank:
        need = sorted({asked[i] for i in missing if i in asked})
        print(f"\nNOT READY. Re-run: {', '.join(need) if need else '(see empty zh above)'}")
        return 1
    print("\nevery sentence came back -- safe to build")
    return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("batches", help="the batches/ directory")
    sys.exit(main(ap.parse_args().batches))

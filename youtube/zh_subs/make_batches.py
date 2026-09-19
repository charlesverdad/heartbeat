#!/usr/bin/env python3
"""Split the speech sentences into batches a translator can hold in its head.

Song and hallucination lines are dropped here rather than translated and thrown
away later. Each batch carries the tail of the previous one as `context_before`,
so a translator starting at sentence 200 still knows what was being talked
about -- pronouns and carried subjects are exactly what breaks otherwise.

    python3 make_batches.py <workdir> [--size 200] [--context 3]
"""
import argparse, json, pathlib

def main(a):
    work = pathlib.Path(a.workdir)
    d = json.loads((work / "sentences_marked.json").read_text())
    sents = d["sentences"]
    speech = [(i, s) for i, s in enumerate(sents) if s["kind"] == "speech"]

    bdir = work / "batches"; bdir.mkdir(exist_ok=True)
    for old in bdir.glob("batch_*.json"):
        old.unlink()

    n = 0
    for b, start in enumerate(range(0, len(speech), a.size)):
        chunk = speech[start:start + a.size]
        ctx = [s["text"] for _, s in speech[max(0, start - a.context):start]]
        payload = {
            "batch": b,
            "context_before": ctx,
            "sentences": [{"id": i, "start": s["start"], "end": s["end"],
                           "en": s.get("en", s["text"])} for i, s in chunk],
        }
        (bdir / f"batch_{b}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
        print(f"  batch_{b}.json  {len(chunk)} sentences  (ids {chunk[0][0]}..{chunk[-1][0]})")

    skipped = len(sents) - len(speech)
    print(f"\nspeech sentences : {len(speech)}")
    print(f"skipped          : {skipped} (song / hallucination)")
    print(f"batches written  : {n} in {bdir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir")
    ap.add_argument("--size", type=int, default=200, help="sentences per batch")
    ap.add_argument("--context", type=int, default=3, help="prior sentences for continuity")
    main(ap.parse_args())

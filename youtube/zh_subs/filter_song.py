#!/usr/bin/env python3
"""Flag sung worship and ASR hallucination so they are not subtitled.

Songs already have lyrics on screen, and Whisper invents filler ("Thank you."
on a ~30s cycle) over music and silence. Both must go before translation.

An earlier version keyed on repeated phrasing alone and flagged the preacher's
deliberate rhetorical repetition as song. Measured on a real sermon, sung lines
separate from speech on RATE and LENGTH together, not on repetition:

    sung   : median 1.18 words/sec over 13.4s
    speech : median 2.94 words/sec over  3.6s

so a line must be both slow and long, and must sit next to another such line,
before it counts as song. Hallucination is identical text repeating in
*adjacent* sentences; scattered "Right?" across a sermon is real speech.
"""
import json, re, sys
from collections import Counter, defaultdict

WPS_MAX  = 2.0     # sung lines are slower than this
DUR_MIN  = 8.0     # ...and longer than this
RUN_MIN  = 2       # ...and do not occur alone

def wps(s):
    d = s["end"] - s["start"]
    return len(s["text"].split()) / d if d > 0 else 99.0

def mark(sents):
    for s in sents:
        s["kind"] = "speech"

    # --- song: contiguous runs of slow, long lines ---
    cand = [i for i, s in enumerate(sents) if wps(s) < WPS_MAX and (s["end"]-s["start"]) > DUR_MIN]
    runs, run = [], []
    for i in cand:
        if run and i - run[-1] <= 2:      # allow a short spoken aside inside a song block
            run.append(i)
        else:
            if len(run) >= RUN_MIN: runs.append(run)
            run = [i]
    if len(run) >= RUN_MIN: runs.append(run)
    for r in runs:
        for i in range(r[0], r[-1] + 1):
            sents[i]["kind"] = "song"

    # --- hallucination: identical short text in adjacent sentences ---
    idx = defaultdict(list)
    for i, s in enumerate(sents):
        if len(s["text"].split()) <= 4:
            idx[s["text"].strip()].append(i)
    for txt, hits in idx.items():
        if len(hits) < 4:
            continue
        adjacent = sum(1 for a, b in zip(hits, hits[1:]) if b - a <= 2)
        if adjacent / (len(hits) - 1) >= 0.8:
            for i in hits:
                sents[i]["kind"] = "halluc"
    return sents

if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    sents = mark(d["sentences"])
    json.dump({**d, "sentences": sents}, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    print("classified:", dict(Counter(s["kind"] for s in sents)))
    for kind in ("song", "halluc"):
        got = [s for s in sents if s["kind"] == kind]
        if got:
            print(f"\n--- {kind}: {len(got)} sentences, {got[0]['start']:.0f}s .. {got[-1]['end']:.0f}s")
            for s in got[:3]:
                print(f"   [{s['start']:7.1f}] {s['text'][:74]}")
            print(f"   ... [{got[-1]['start']:7.1f}] {got[-1]['text'][:74]}")

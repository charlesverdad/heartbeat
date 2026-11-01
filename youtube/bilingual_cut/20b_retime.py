#!/usr/bin/env python3
"""Stage 20b - re-time the anchored English onto the rendered cut's own words.

Each anchor owns a span of *source* time. Map the fresh ASR words back to source
time, collect the words each anchor covers, and the anchor inherits an exact
output-time span. Words no anchor claims are the gaps that need new prose.
"""
import argparse
import json
import re
from pathlib import Path

CLOSE_DEFAULT = 3571.89


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--asr", default="v5_asr.json")
    ap.add_argument("--out", default="v5_retime.json")
    ap.add_argument("--speaker", default="SPEAKER_06")
    ap.add_argument("--verbatim-from", type=float, default=CLOSE_DEFAULT,
                    help="source time after which only --speaker is subtitled")
    ap.add_argument("--speaker-frac", type=float, default=0.15,
                    help="min diarized share of a segment for it to be the speaker")
    args = ap.parse_args()
    work = Path(args.work)

    clips = json.loads((work / "cutplan.json").read_text())["clips"]
    sp = json.loads((work / "splice.json").read_text())
    AT, DUR = sp["insert_at"], sp["insert_dur"]

    def out2src(t):
        if AT <= t < AT + DUR:
            return None                      # inside the inserted video
        u = t if t < AT else t - DUR
        for c in clips:
            if c["out_start"] <= u < c["out_end"]:
                return c["src_start"] + (u - c["out_start"])
        return None

    diar = json.loads((work / "diarization.json").read_text())
    him = [(t["start"], t["end"]) for t in diar["turns"] if t["speaker"] == args.speaker]

    def overlap(a, b, c, d):
        return max(0.0, min(b, d) - max(a, c))

    segs = json.loads((work / args.asr).read_text())["segments"]
    words = []
    for s in segs:
        if s["lang"] != "ko":
            continue
        if s["compression_ratio"] > 2.4 or s["no_speech_prob"] > 0.6:
            continue                         # decoder loop or silence
        a, b = out2src(s["start"]), out2src(s["end"])
        if a is None or b is None:
            continue
        if a >= args.verbatim_from:
            share = sum(overlap(a, b, x, y) for x, y in him) / max(b - a, 0.01)
            if share < args.speaker_frac:
                continue                     # song, congregation, or interpreter
        for w in s["words"]:
            src = out2src((w["start"] + w["end"]) / 2)
            if src is not None:
                words.append({"out_s": w["start"], "out_e": w["end"], "src": src, "w": w["w"]})
    words.sort(key=lambda x: x["out_s"])

    anchors = json.loads((work / "translations_anchored.json").read_text(encoding="utf-8"))
    claimed = [False] * len(words)
    timed = []
    for a in anchors:
        idx = [i for i, w in enumerate(words)
               if a["src_start"] - 0.15 <= w["src"] < a["src_end"] + 0.15]
        if not idx:
            continue                         # this anchor's audio was cut away
        for i in idx:
            claimed[i] = True
        timed.append({"out_start": round(words[idx[0]]["out_s"], 3),
                      "out_end": round(words[idx[-1]]["out_e"], 3),
                      "ko": a["ko"], "en": a["en"], "n": len(idx)})
    timed.sort(key=lambda x: x["out_start"])

    runs, cur = [], None
    for i, w in enumerate(words):
        if claimed[i]:
            continue
        if cur and w["out_s"] - cur["out_end"] < 1.2:
            cur["out_end"] = w["out_e"]
            cur["text"] += w["w"]
            cur["src_end"] = w["src"]
        else:
            if cur:
                runs.append(cur)
            cur = {"out_start": w["out_s"], "out_end": w["out_e"], "text": w["w"],
                   "src_start": w["src"], "src_end": w["src"]}
    if cur:
        runs.append(cur)
    runs = [r for r in runs if len(r["text"].strip()) >= 4 and r["out_end"] - r["out_start"] >= 0.6]

    # a run whose words already sit inside a neighbouring cue's korean is a
    # boundary sliver, not a gap: the sentence is translated, the edge just moved
    def norm(s):
        return re.sub(r"[^가-힣0-9]", "", s)

    real = []
    for r in runs:
        txt = norm(r["text"])
        near = [t for t in timed if t["out_start"] - 6 <= r["out_start"] <= t["out_end"] + 6]
        if not any(txt and txt in norm(t["ko"]) for t in near):
            real.append(r)

    json.dump({"timed": timed, "runs": runs, "real_gaps": real},
              open(work / args.out, "w"), ensure_ascii=False, indent=1)
    print(f"{len(words)} words; {len(timed)}/{len(anchors)} anchors re-timed; "
          f"{len(runs)} unclaimed runs, {len(real)} of them genuine gaps "
          f"({sum(r['out_end'] - r['out_start'] for r in real):.0f}s)")


if __name__ == "__main__":
    main()

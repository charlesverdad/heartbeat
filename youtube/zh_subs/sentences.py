#!/usr/bin/env python3
"""Re-cut Whisper output into sentences with accurate spans.

Whisper's own segment boundaries do not align to sentences (45% end mid-sentence
in our sample). Translation must happen a sentence at a time -- English and
Chinese differ enough in word order that translating a fragment produces
unreadable Chinese -- so we flatten to words, split on sentence-final
punctuation, and take each sentence's span from its first and last word.
"""
import json, re, sys

def flatten(asr):
    """All words in order, each with its own start/end."""
    out = []
    for s in asr["segments"]:
        if s.get("words"):
            out.extend({"w": w["w"], "s": w["s"], "e": w["e"]} for w in s["words"])
        else:                      # segment lacked word timings; fall back to its span
            out.append({"w": s["text"], "s": s["start"], "e": s["end"]})
    return out

# Abbreviations whose full stop does not end a sentence.
ABBREV = re.compile(r"\b(Mr|Mrs|Ms|Dr|St|vs|etc|e\.g|i\.e|Rev|Fr|Jr|Sr)\.$", re.I)

def sentences(words, max_gap=1.6, max_words=60):
    """Group words into sentences. Also breaks on long pauses so a missing full
    stop cannot produce a runaway 200-word 'sentence'."""
    sents, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        txt = w["w"].strip()
        gap = words[i + 1]["s"] - w["e"] if i + 1 < len(words) else 99
        ends = bool(re.search(r"[.?!]['\")\]]?$", txt)) and not ABBREV.search(txt)
        if (ends and gap > 0.06) or gap >= max_gap or len(cur) >= max_words:
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    out = []
    for grp in sents:
        text = re.sub(r"\s+", " ", "".join(w["w"] for w in grp)).strip()
        if text:
            out.append({"start": grp[0]["s"], "end": grp[-1]["e"], "text": text,
                        "n_words": len(grp)})
    return out

if __name__ == "__main__":
    asr = json.load(open(sys.argv[1]))
    ws = flatten(asr)
    ss = sentences(ws)
    json.dump({"offset": asr.get("offset", 0.0), "sentences": ss},
              open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
    durs = [s["end"] - s["start"] for s in ss]
    nw = [s["n_words"] for s in ss]
    print(f"words={len(ws)} sentences={len(ss)}")
    print(f"words/sentence: mean {sum(nw)/len(nw):.1f}  max {max(nw)}")
    print(f"duration/sentence: mean {sum(durs)/len(durs):.2f}s  max {max(durs):.1f}s")
    print(f"wrote {sys.argv[2]}")

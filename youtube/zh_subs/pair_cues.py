#!/usr/bin/env python3
"""Turn one-line bilingual cues into two-line cues so each stays up longer.

build_bilingual.py cuts every sentence into pieces that each fit ONE line. On a
real sermon that gave a median of 2.9 s on screen with 29% of cues under 2 s:
too fast to read. This regroups them so each cue shows up to TWO lines per
language:

  * a sentence that took n one-line pieces becomes ceil(n/2) two-line cues,
    re-split from the whole sentence (not the old pieces, which were often cut
    mid-word) at punctuation, else just after a particle (的/了/是/在...);
  * two consecutive one-line sentences are shown together, one per line.

Use it with `bilingual_ass.py --layout split`: Farsi at the top and Chinese at
the bottom, so two lines of each still leave the middle of the frame clear.
Stacked at the bottom, 2+2 lines would cover a third of the frame.

    python pair_cues.py cues.json cues.paired.json [--max-gap 0.6] [--max-dur 7]
"""
import argparse, json, math, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cjk, fa
from build_bilingual import zh_split, ZH_MAX

ZH_PUNCT = "，、；：。？！」』…"
# function words that almost always end a word, so a break right after one
# rarely lands inside a word (no segmenter needed)
ZH_PARTICLE = "的了着著地得是在和就都也把被讓让給给對对從从但而嗎吗呢吧啊"


def zh_split_k(text, k, window=6, maxw=ZH_MAX):
    """k pieces of similar width, each cut at punctuation near its target,
    else just after a particle, else at zh_split's point."""
    if k <= 1:
        return [text]
    fallback = zh_split(text, k)
    cuts, prev = [], 0
    for j in range(1, k):
        target = len(text) * j / k
        cut = None
        for chars in (ZH_PUNCT, ZH_PARTICLE):
            opts = [i + 1 for i in range(prev, len(text) - 1)
                    if text[i] in chars and abs(i + 1 - target) <= window
                    and text[i + 1] not in ZH_PUNCT]
            if opts:
                cut = min(opts, key=lambda i: abs(i - target))
                break
        if cut is None:
            cut = sum(len(p) for p in fallback[:j])
            # never part a number from its unit ("8 / 點") or a run of digits
            for _ in range(3):
                if 0 < cut < len(text) - 1 and (text[cut - 1].isdigit() or text[cut].isdigit()):
                    cut += 1
            while 0 < cut < len(text) and text[cut] in ZH_PUNCT:
                cut += 1
        cuts.append(cut); prev = cut
    parts = [text[a:b] for a, b in zip([0] + cuts, cuts + [len(text)])]
    if any(not p for p in parts) or any(cjk.visual_len(p) > maxw for p in parts):
        return fallback
    return parts


def regroup(cues, max_gap=0.6, max_dur=7.0):
    # 1. gather each sentence's one-line pieces
    sents = []
    for c in cues:
        if sents and sents[-1]["id"] == c["id"] and c["start"] - sents[-1]["end"] < 0.05:
            s = sents[-1]
            s["zh"] += c["zh"]; s["fa"] += " " + c["fa"]; s["en"] += " " + c.get("en", "")
            s["end"] = c["end"]; s["n"] += 1
        else:
            sents.append(dict(id=c["id"], start=c["start"], end=c["end"], zh=c["zh"],
                              fa=c["fa"], en=c.get("en", ""), n=1))
    # 2. long sentences -> two-line cues; short ones stay single-line for now
    out = []
    for s in sents:
        if s["n"] == 1:
            out.append(dict(start=s["start"], end=s["end"], zh=[s["zh"]], fa=[s["fa"]],
                            en=s["en"], id=s["id"]))
            continue
        # m cues, each language cut into m chunks, then a chunk wraps to a
        # second line only if it doesn't fit on one
        m = math.ceil(s["n"] / 2)
        zc, fc = zh_split_k(s["zh"], m, window=8, maxw=2 * ZH_MAX), fa.split_text(s["fa"], m)
        zc += [""] * (m - len(zc)); fc += [""] * (m - len(fc))
        zt = sum(cjk.visual_len(x) for x in zc) or 1
        ft = sum(len(x) for x in fc) or 1
        t, acc = s["start"], 0.0
        for j in range(m):
            z2 = zh_split_k(zc[j], 2) if cjk.visual_len(zc[j]) > ZH_MAX else [zc[j]]
            f2 = fa.split_text(fc[j], 2) if len(fc[j]) > fa.MAX_CHARS else [fc[j]]
            z2, f2 = [x for x in z2 if x], [x for x in f2 if x]
            acc += (sum(cjk.visual_len(x) for x in z2) / zt + sum(len(x) for x in f2) / ft) / 2
            end = s["end"] if j == m - 1 else s["start"] + (s["end"] - s["start"]) * acc
            out.append(dict(start=round(t, 3), end=round(end, 3), zh=z2 or [""], fa=f2 or [""],
                            en=s["en"], id=s["id"]))
            t = end
    # 3. show two consecutive single-line cues together, one per line
    paired = []
    for c in out:
        p = paired[-1] if paired else None
        if (p is not None and len(p["zh"]) == 1 and len(c["zh"]) == 1
                and len(p["fa"]) == 1 and len(c["fa"]) == 1
                and c["start"] - p["end"] < max_gap and c["end"] - p["start"] <= max_dur):
            p["zh"] += c["zh"]; p["fa"] += c["fa"]
            p["en"] = (p["en"] + " " + c["en"]).strip(); p["end"] = c["end"]
            continue
        paired.append(c)
    # every Farsi line needs its own RLM, or a line opening with a Latin name
    # lays out left to right (bilingual_ass.py adds the first one)
    for c in paired:
        c["zh"] = r"\N".join(c["zh"])
        c["fa"] = (r"\N" + fa.RLM).join(c["fa"])
    return paired


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cues"); ap.add_argument("out")
    ap.add_argument("--max-gap", type=float, default=0.6)
    ap.add_argument("--max-dur", type=float, default=7.0)
    a = ap.parse_args()
    cues = json.load(open(a.cues))
    res = regroup(cues, a.max_gap, a.max_dur)
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    d = sorted(c["end"] - c["start"] for c in res)
    wide = [z for c in res for z in c["zh"].split(r"\N") if cjk.visual_len(z) > ZH_MAX]
    wfa = [f for c in res for f in c["fa"].split(r"\N") if len(f.lstrip(fa.RLM)) > fa.MAX_CHARS]
    print(f"cues {len(cues)} -> {len(res)}   median on screen {d[len(d)//2]:.2f}s   "
          f"under 2s: {100*sum(x < 2 for x in d)//len(d)}%   over-wide lines zh/fa: {len(wide)}/{len(wfa)}")
    print(f"wrote {a.out}")

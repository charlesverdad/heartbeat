#!/usr/bin/env python3
"""Bilingual Korean + Traditional Chinese cues: one Korean line above one Chinese line.

The Korean counterpart of zh_subs/build_bilingual.py (Farsi + Chinese), reusing
its sentence-span logic. Korean breaks at spaces between eojeol, so it is cut
with fa.split_text (word-boundary splitter); its width is measured with
cjk.visual_len because Hangul is full-width.

    python build_ko_zh.py sentences_marked.json batches/ out.cues.json
Reads zh_*.json (Simplified, converted with OpenCC s2tw) and ko_*.json.
Output cues carry {start,end,ko,zh,en,id}.
"""
import argparse, json, math, pathlib, sys
ZH_SUBS = pathlib.Path(__file__).resolve().parents[2] / "zh_subs"
sys.path.insert(0, str(ZH_SUBS))
import cjk, fa, build_srt
from build_bilingual import load, clean_zh, zh_split, QUOTES, ZH_MAX
from to_traditional import convert

KO_MAX = 24          # visual cells; Hangul = 1, space/ASCII = 0.5
KO_CPS = 9.0         # Hangul syllables per second a viewer can comfortably read
SEP, MIN_DUR = build_srt.SEP, 1.0
W = cjk.visual_len

def ko_norm(t):
    return " ".join(t.replace("\n", " ").split())

def split_pair(zh, ko, dur):
    n = max(1, math.ceil(W(zh) / ZH_MAX), math.ceil(W(ko) / KO_MAX))
    cap = max(n, int(dur / MIN_DUR)) + 2
    while True:
        zp, kp = zh_split(zh, n), fa.split_text(ko, n)
        k = min(len(zp), len(kp))
        if k < n:
            zp, kp = zh_split(zh, k), fa.split_text(ko, k)
        bad = any(W(p) > ZH_MAX for p in zp) or any(W(p) > KO_MAX for p in kp)
        if not bad or n >= cap or k < n:
            break
        n += 1
    m = min(len(zp), len(kp))
    zp, kp = zp[:m - 1] + ["".join(zp[m - 1:])], kp[:m - 1] + [" ".join(kp[m - 1:])]
    zt, kt = sum(W(p) for p in zp) or 1, sum(W(p) for p in kp) or 1
    return [(z, k, (W(z) / zt + W(k) / kt) / 2) for z, k in zip(zp, kp)]

def build(marked, zh, ko, offset=0.0):
    sents = marked["sentences"]
    keep = [i for i, s in enumerate(sents) if s["kind"] == "speech" and i in zh and i in ko]
    cues = []
    for n, i in enumerate(keep):
        s = sents[i]
        t1 = s["end"]
        if n + 1 < len(keep):
            t1 = min(t1, sents[keep[n + 1]]["start"] - SEP)
        t0, t1 = s["start"], max(t1, s["start"] + 0.01)
        words = s.get("text", "").split()
        z = convert(clean_zh(zh[i]), "tw").translate(QUOTES)
        pieces = split_pair(z, ko_norm(ko[i]), t1 - t0)
        t, w0, acc = t0, 0, 0.0
        for k, (zp, kp, wt) in enumerate(pieces):
            acc += wt
            end = t1 if k == len(pieces) - 1 else t0 + (t1 - t0) * acc
            w1 = len(words) if k == len(pieces) - 1 else round(len(words) * acc)
            cues.append([t + offset, end + offset, zp, kp, " ".join(words[w0:w1]), i])
            t, w0 = end, w1
    cues.sort(key=lambda c: c[0])
    for k, c in enumerate(cues):            # hold short cues, borrowing silence only
        need = max(1.0, W(c[2]) / cjk.CHARS_PER_SEC, W(c[3]) / KO_CPS)
        if c[1] - c[0] >= need:
            continue
        ceiling = (cues[k + 1][0] - SEP) if k + 1 < len(cues) else c[1] + need
        c[1] = max(c[1], min(c[0] + need, ceiling))
    cues = merge_slivers(build_srt._enforce_order(cues))
    return [dict(start=round(c[0], 3), end=round(c[1], 3), zh=c[2], ko=c[3], en=c[4], id=c[5])
            for c in cues]

def merge_slivers(cues, min_dur=0.7, max_gap=0.45):
    k = 0
    while k < len(cues):
        c = cues[k]
        if c[1] - c[0] >= min_dur:
            k += 1; continue
        for j in (k + 1, k - 1):
            if not 0 <= j < len(cues):
                continue
            a, b = sorted((k, j))
            z, kk = cues[a][2] + cues[b][2], cues[a][3] + " " + cues[b][3]
            if cues[b][0] - cues[a][1] <= max_gap and W(z) <= ZH_MAX and W(kk) <= KO_MAX:
                cues[a] = [cues[a][0], cues[b][1], z, kk,
                           (cues[a][4] + " " + cues[b][4]).strip(), cues[a][5]]
                del cues[b]
                k = max(a - 1, 0)
                break
        else:
            k += 1
    return cues

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("marked"); ap.add_argument("batches"); ap.add_argument("out")
    a = ap.parse_args()
    marked = json.load(open(a.marked))
    zh, ko = load(a.batches, "zh"), load(a.batches, "ko")
    speech = [i for i, s in enumerate(marked["sentences"]) if s["kind"] == "speech"]
    cues = build(marked, zh, ko, marked.get("offset", 0.0))
    pathlib.Path(a.out).write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")
    for lang, d in (("zh", zh), ("ko", ko)):
        miss = [i for i in speech if i not in d]
        print(f"{lang} coverage {100*(len(speech)-len(miss))/len(speech):.1f}%" + (f" missing {miss[:10]}" if miss else ""))
    print(f"cues {len(cues)}; widest zh {max(W(c['zh']) for c in cues)} ko {max(W(c['ko']) for c in cues)}")
    fast = [c for c in cues if W(c['ko']) / max(c['end']-c['start'], .01) > KO_CPS * 1.25]
    print(f"ko too fast (>{KO_CPS*1.25:.1f}/s): {len(fast)}")
    for c in fast[:15]:
        print(f"  {c['start']:.1f} {W(c['ko'])/(c['end']-c['start']):.1f}/s {c['ko']}")
    print("wrote", a.out)

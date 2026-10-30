#!/usr/bin/env python3
"""Assemble the bilingual Farsi + Traditional Chinese track: one line of each.

Takes the same sentence-level translations as build_srt.py (zh_*.json, in
Simplified) plus the Farsi ones (fa_*.json), and lays each sentence across the
span its English occupied as cues holding ONE Chinese line and ONE Farsi line.
Single lines are deliberate: two languages of two lines each would cover a
third of the frame.

Both languages share every cue's timing. Each viewer reads only their own line,
so the two halves of a cue need not match word for word; what matters is that
each stays with the speech. A long sentence is therefore cut into the same
number of pieces in both languages, each at its own natural break, and timed by
how much of the sentence it carries.

Output is a cues JSON in full-video time ({start,end,zh,fa,en}); render it with
bilingual_ass.py and check it with qa_bilingual.py.
"""
import argparse, json, math, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cjk, fa, build_srt
from to_traditional import convert

ZH_MAX      = 22      # Traditional chars per line; ~1400 px at ZH size 90
SEP         = build_srt.SEP
MIN_DUR     = 1.0     # no piece of a split sentence shorter than this

def load(batchdir, lang):
    out = {}
    for p in sorted(pathlib.Path(batchdir).glob(f"{lang}_*.json")):
        for t in json.load(open(p))["translations"]:
            if str(t.get(lang, "")).strip():
                out[int(t["id"])] = t[lang].strip()
    return out

def clean_zh(text):
    # as cjk.cues_for: drop the translator's stray spaces, but keep the space
    # inside a Latin name ("Julie Kim", not "JulieKim")
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"(?<=[0-9A-Za-z]) (?=[0-9A-Za-z])", "\x00", text)
    return text.replace(" ", "").replace("\x00", " ")

def zh_split(text, n):
    """Cut Chinese into n pieces of similar width.

    cjk.split_text only cuts at punctuation, which suits two-line cues but not
    single lines: a sentence with one comma comes out as one long piece and a
    run of one-character slivers. Here a cut prefers punctuation near each
    target but falls back to any legal point, never inside a Latin word or
    before closing punctuation.
    """
    if n <= 1 or len(text) < 2:
        return [text]
    widths, acc = [], 0.0
    for ch in text:
        acc += cjk.visual_len(ch)
        widths.append(acc)                         # width up to and including text[i]
    total = widths[-1]
    ok = [i for i in range(1, len(text))
          if not cjk._midword(text, i) and text[i] not in cjk.NO_LINE_START
          and text[i - 1] not in cjk.NO_LINE_END]
    cuts, last = [], 0
    for k in range(1, n):
        target, window = total * k / n, total / n * 0.25
        cand = [i for i in ok if i > last and len(text) - i >= n - k]
        if not cand:
            break
        punct = [i for i in cand if text[i - 1] in cjk.BREAK_AFTER
                 and abs(widths[i - 1] - target) <= window]
        best = min(punct or cand, key=lambda i: abs(widths[i - 1] - target))
        cuts.append(best)
        last = best
    bounds = [0] + cuts + [len(text)]
    return [text[a:b] for a, b in zip(bounds, bounds[1:]) if b > a]

# Taiwan and Hong Kong quote with corner brackets. Curly quotes are proportional
# in Noto CJK and leave a visible hole before the next full-width mark.
QUOTES = str.maketrans({"\u201c": "「", "\u201d": "」", "\u2018": "『", "\u2019": "』"})

def overflow(zh_parts, fa_parts, zh_max, fa_max):
    return (any(cjk.visual_len(p) > zh_max for p in zh_parts)
            or any(len(p) > fa_max for p in fa_parts))

def split_pair(zh, fat, dur, zh_max=ZH_MAX, fa_max=fa.MAX_CHARS):
    """Cut one sentence into n (zh, fa, weight) pieces that each fit one line."""
    n = max(1, math.ceil(cjk.visual_len(zh) / zh_max), math.ceil(len(fat) / fa_max))
    # Avoid slivers, but a line too wide for the frame is worse: WrapStyle 2
    # never wraps, so it would run off both edges. Width wins over duration.
    cap = max(n, int(dur / MIN_DUR)) + 2
    while True:
        zp, fp = zh_split(zh, n), fa.split_text(fat, n)
        k = min(len(zp), len(fp))                  # a short side can't split further
        if k < n:
            zp, fp = zh_split(zh, k), fa.split_text(fat, k)
        if not overflow(zp, fp, zh_max, fa_max) or n >= cap or k < n:
            break
        n += 1
    m = min(len(zp), len(fp))
    zp, fp = zp[:m - 1] + ["".join(zp[m - 1:])], fp[:m - 1] + [" ".join(fp[m - 1:])]
    zt, ft = sum(cjk.visual_len(p) for p in zp) or 1, sum(len(p) for p in fp) or 1
    return [(z, f, (cjk.visual_len(z) / zt + len(f) / ft) / 2) for z, f in zip(zp, fp)]

def build(marked, zh, fat, offset, variant="tw"):
    sents = marked["sentences"]
    keep = [i for i, s in enumerate(sents) if s["kind"] == "speech" and i in zh and i in fat]
    cues = []
    for n, i in enumerate(keep):
        s = sents[i]
        t1 = s["end"]
        if n + 1 < len(keep):                      # never run into the next sentence
            t1 = min(t1, sents[keep[n + 1]]["start"] - SEP)
        t0, t1 = s["start"], max(t1, s["start"] + 0.01)
        words = s.get("text", "").split()
        z = convert(clean_zh(zh[i]), variant).translate(QUOTES)
        pieces = split_pair(z, fa.normalise(fat[i]), t1 - t0)
        t, w0, acc = t0, 0, 0.0
        for k, (zp, fp, weight) in enumerate(pieces):
            acc += weight
            end = t1 if k == len(pieces) - 1 else t0 + (t1 - t0) * acc
            w1 = len(words) if k == len(pieces) - 1 else round(len(words) * acc)
            cues.append([t + offset, end + offset, zp, fp, " ".join(words[w0:w1]), i])
            t, w0 = end, w1
    cues.sort(key=lambda c: c[0])
    # hold a short cue long enough to read either line, borrowing silence only
    for k, c in enumerate(cues):
        need = max(1.0, cjk.visual_len(c[2]) / cjk.CHARS_PER_SEC, len(c[3]) / fa.CHARS_PER_SEC)
        if c[1] - c[0] >= need:
            continue
        ceiling = (cues[k + 1][0] - SEP) if k + 1 < len(cues) else c[1] + need
        c[1] = max(c[1], min(c[0] + need, ceiling))
    cues = _merge_slivers(build_srt._enforce_order(cues))
    return [dict(start=round(c[0], 3), end=round(c[1], 3), zh=c[2], fa=c[3], en=c[4], id=c[5])
            for c in cues]

def _merge_slivers(cues, min_dur=0.7, max_gap=0.45, zh_max=ZH_MAX, fa_max=fa.MAX_CHARS):
    """Join a cue too short to read to a neighbour when both lines still fit.

    Rapid-fire interjections ("Yeah." "Right.") have no silence after them to
    borrow, so lengthening cannot help; a 0.3 s subtitle is simply unread.
    """
    k = 0
    while k < len(cues):
        c = cues[k]
        if c[1] - c[0] >= min_dur:
            k += 1
            continue
        for j in (k + 1, k - 1):                   # prefer merging forward
            if not 0 <= j < len(cues):
                continue
            a, b = sorted((k, j))
            zh, fat = cues[a][2] + cues[b][2], cues[a][3] + " " + cues[b][3]
            if (cues[b][0] - cues[a][1] <= max_gap
                    and cjk.visual_len(zh) <= zh_max and len(fat) <= fa_max):
                cues[a] = [cues[a][0], cues[b][1], zh, fat,
                           (cues[a][4] + " " + cues[b][4]).strip(), cues[a][5]]
                del cues[b]
                k = max(a - 1, 0)
                break
        else:
            k += 1
    return cues

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("marked",  help="sentences_marked.json (or sentences_edited.json)")
    ap.add_argument("batches", help="directory holding zh_*.json and fa_*.json")
    ap.add_argument("out",     help="output cues JSON, e.g. sermon.fa-zhHant.cues.json")
    ap.add_argument("--variant", default="tw", choices=["tw", "hk"])
    ap.add_argument("--fa-overrides", help="JSON {id: farsi} -- human Farsi, used verbatim")
    a = ap.parse_args()

    marked = json.load(open(a.marked))
    zh, fat = load(a.batches, "zh"), load(a.batches, "fa")
    if a.fa_overrides:
        fat.update({int(k): v for k, v in json.load(open(a.fa_overrides)).items() if v.strip()})
    speech = [i for i, s in enumerate(marked["sentences"]) if s["kind"] == "speech"]
    cues = build(marked, zh, fat, marked.get("offset", 0.0), a.variant)
    pathlib.Path(a.out).write_text(json.dumps(cues, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"speech sentences : {len(speech)}")
    for lang, d in (("zh", zh), ("fa", fat)):
        miss = [i for i in speech if i not in d]
        print(f"  {lang} coverage    : {100 * (len(speech) - len(miss)) / max(len(speech), 1):.1f}%"
              + (f"  missing {miss[:10]}" if miss else ""))
    print(f"cues written     : {len(cues)}")
    if cues:
        print(f"track spans      : {cues[0]['start']:.1f}s .. {cues[-1]['end']:.1f}s (full-video time)")
    print(f"wrote {a.out}")

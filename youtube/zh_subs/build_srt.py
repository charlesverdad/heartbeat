#!/usr/bin/env python3
"""Assemble the Simplified Chinese subtitle track.

Takes the sentence-level translations and lays each one across the span its
English sentence occupied, splitting into cues that fit the box and the reading
speed. Timestamps are shifted back onto FULL-VIDEO time, because the audio we
transcribed was an extract starting at the sermon.
"""
import argparse, json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cjk

def load_translations(batchdir):
    """Returns the translations and, per id, which batch file supplied it.

    Provenance matters: a line whose English was corrected by hand is only
    really fixed once a RE-translation batch covers it. Without knowing which
    file a string came from we cannot tell a fresh translation from the stale
    one it was supposed to replace.
    """
    zh, origin = {}, {}
    for p in sorted(pathlib.Path(batchdir).glob("zh_*.json")):
        d = json.load(open(p))
        for t in d["translations"]:
            if t.get("zh", "").strip():
                zh[int(t["id"])] = t["zh"].strip()
                origin[int(t["id"])] = p.stem
    return zh, origin

def build(marked, zh, offset):
    sents = marked["sentences"]
    cues = []
    for i, s in enumerate(sents):
        if s["kind"] != "speech" or i not in zh:
            continue
        # never run into the next subtitled sentence
        ceiling = s["end"]
        for j in range(i + 1, len(sents)):
            if sents[j]["kind"] == "speech" and j in zh:
                ceiling = min(max(s["end"], s["start"] + 0.3), sents[j]["start"] - 0.04)
                break
        t1 = max(s["start"] + 0.3, min(s["end"], ceiling))
        for a, b, text in cjk.cues_for(zh[i], s["start"], t1):
            cues.append([a + offset, min(b, t1) + offset, text])
    cues.sort(key=lambda c: c[0])
    # final safety clamp against any residual overlap
    for k in range(len(cues) - 1):
        if cues[k][1] > cues[k+1][0]:
            cues[k][1] = max(cues[k][0] + 0.2, cues[k+1][0] - 0.04)
    # A short interjection ("Amen.") inherits a sub-second ASR span, which is
    # too fast to read. Hold it longer by borrowing the silence that follows,
    # never by overlapping the next cue.
    MIN_DISPLAY, SEP = 1.0, 0.04
    for k, c in enumerate(cues):
        chars  = cjk.visual_len(c[2].replace("\n", ""))
        needed = max(MIN_DISPLAY, chars / cjk.CHARS_PER_SEC)
        if c[1] - c[0] >= needed:
            continue
        ceiling = (cues[k+1][0] - SEP) if k + 1 < len(cues) else c[1] + needed
        cues[k][1] = min(max(c[1], c[0] + needed), max(ceiling, c[0] + 0.2))
    cues = _merge_slivers(cues)
    return [tuple(c) for c in cues]

def _merge_slivers(cues, min_dur=0.55, max_gap=0.45):
    """Fold away cues too short to read.

    Some interjections sit in rapid-fire speech with no following silence to
    borrow, so extending cannot help. A 0.2s subtitle is unreadable, so join it
    to a neighbour when the combined text still fits the box.
    """
    changed = True
    while changed:
        changed = False
        for k, c in enumerate(cues):
            if c[1] - c[0] >= min_dur:
                continue
            for j in (k + 1, k - 1):                     # prefer merging forward
                if not (0 <= j < len(cues)):
                    continue
                a, b = (k, j) if j > k else (j, k)
                if cues[b][0] - cues[a][1] > max_gap:
                    continue
                joined = (cues[a][2] + cues[b][2]).replace("\n", "")
                if not cjk.fits(joined):
                    continue
                cues[a] = [cues[a][0], cues[b][1], cjk.wrap(joined)]
                del cues[b]
                changed = True
                break
            if changed:
                break
    return cues

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("marked",  help="sentences_marked.json, or sentences_edited.json after apply_edits")
    ap.add_argument("batches", help="directory of zh_*.json translation batches")
    ap.add_argument("out",     help="output .srt path")
    ap.add_argument("--overrides", help="overrides_zh.json -- human Chinese, used verbatim")
    a = ap.parse_args()

    marked = json.load(open(a.marked))
    zh, origin = load_translations(a.batches)
    offset = marked.get("offset", 0.0)
    sents  = marked["sentences"]

    # A human's own Chinese outranks every machine translation, including a
    # re-translation batch that happens to sort later.
    forced = {}
    if a.overrides:
        forced = {int(k): v.strip() for k, v in json.load(open(a.overrides)).items() if v.strip()}
        zh.update(forced)

    speech  = [i for i, s in enumerate(sents) if s["kind"] == "speech"]
    dropped = [i for i, s in enumerate(sents) if s["kind"] == "dropped"]
    # English that was corrected by hand but never re-translated would ship the
    # old, wrong Chinese under a new source. Say so rather than silently doing it.
    stale = [i for i in speech
             if sents[i].get("en_edited") and i not in forced and i in zh
             and "retrans" not in origin.get(i, "")]
    missing = [i for i in speech if i not in zh]

    cues = build(marked, zh, offset)
    pathlib.Path(a.out).write_text(cjk.to_srt(cues), encoding="utf-8")

    print(f"translations loaded : {len(zh)}" + (f"  ({len(forced)} human overrides)" if forced else ""))
    print(f"speech sentences    : {len(speech)}  (coverage {len(zh and [i for i in speech if i in zh])/max(len(speech),1)*100:.1f}%)")
    if dropped:
        print(f"dropped by hand     : {len(dropped)}")
    print(f"cues written        : {len(cues)}")
    print(f"track spans         : {cues[0][0]:.1f}s .. {cues[-1][1]:.1f}s (full-video time)")
    print(f"wrote {a.out}")
    if missing:
        print(f"\nWARNING: {len(missing)} speech lines have no translation: {missing[:12]}"
              + (" ..." if len(missing) > 12 else ""))
    if stale:
        print(f"\nWARNING: {len(stale)} lines have hand-corrected English but still carry the")
        print(f"         translation of the OLD English: {stale[:12]}"
              + (" ..." if len(stale) > 12 else ""))
        print( "         Translate batches/retranslate.json into batches/zh_retrans.json first.")

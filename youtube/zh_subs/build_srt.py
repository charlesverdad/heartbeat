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

SEP = 0.04      # gap that must remain between one cue and the next

def build(marked, zh, offset):
    sents = marked["sentences"]
    cues = []
    for i, s in enumerate(sents):
        if s["kind"] != "speech" or i not in zh:
            continue
        # Never run into the next subtitled sentence. The ceiling always wins:
        # a cue left too short here is lengthened by the MIN_DISPLAY pass below,
        # which respects the same ceiling. Letting a readability floor overrule
        # the ceiling is exactly how two cues end up on screen at once.
        t1 = s["end"]
        for j in range(i + 1, len(sents)):
            if sents[j]["kind"] == "speech" and j in zh:
                t1 = min(t1, sents[j]["start"] - SEP)
                break
        t1 = max(t1, s["start"] + 0.01)
        for a, b, text in cjk.cues_for(zh[i], s["start"], t1):
            cues.append([a + offset, min(b, t1) + offset, text])
    cues.sort(key=lambda c: c[0])
    # A short interjection ("Amen.") inherits a sub-second ASR span, which is
    # too fast to read. Hold it longer by borrowing the silence that follows,
    # never by overlapping the next cue.
    MIN_DISPLAY = 1.0
    for k, c in enumerate(cues):
        chars  = cjk.visual_len(c[2].replace("\n", ""))
        needed = max(MIN_DISPLAY, chars / cjk.CHARS_PER_SEC)
        if c[1] - c[0] >= needed:
            continue
        ceiling = (cues[k+1][0] - SEP) if k + 1 < len(cues) else c[1] + needed
        cues[k][1] = max(c[1], min(c[0] + needed, ceiling))
    cues = _merge_slivers(cues)
    return [tuple(c) for c in _enforce_order(cues)]

def _enforce_order(cues, sep=SEP):
    """Last word on timing: no cue may still be on screen when the next begins.

    Every earlier pass has a readability motive for lengthening a cue, and both
    the extension pass and _merge_slivers can move an end after the point where
    overlaps were last checked. This one runs last and has no such motive --
    shortening a cue is always preferable to showing two at once.
    """
    for k in range(len(cues) - 1):
        limit = cues[k+1][0] - sep
        if cues[k][1] > limit:
            cues[k][1] = max(cues[k][0] + 0.05, limit)
    return cues

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

    # Re-running prepare.py with a corrected start rewrites meta.json but leaves
    # asr_en.json and the sentence files on the old clock. Building from that mix
    # yields a track that passes every check in qa_srt.py and is silently wrong by
    # the difference -- 41 minutes, in the run that prompted this guard. Nothing
    # downstream can detect it, so refuse here.
    meta_path = pathlib.Path(a.marked).parent / "meta.json"
    if meta_path.exists():
        meta_offset = json.load(open(meta_path)).get("offset", 0.0)
        if abs(meta_offset - offset) > 0.001:
            sys.exit(
                f"ERROR: offset mismatch.\n"
                f"  {pathlib.Path(a.marked).name} was built at offset {offset}s\n"
                f"  meta.json now says {meta_offset}s\n"
                f"prepare.py has been re-run since these sentences were made. Re-run "
                f"asr.py, sentences.py and filter_song.py, or every subtitle will be "
                f"out by {abs(meta_offset - offset):.0f}s.")
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

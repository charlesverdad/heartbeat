#!/usr/bin/env python3
"""Fold the resolver's ASR fixes into sentences_marked.json, before translation.

  high     -> the line's English is replaced; the ASR text is kept as `en_asr`
              so the editor can show what was heard and offer it back
  low      -> the best guess is applied too, but the line is flagged and its
              options become tap-to-pick choices in the editor
  unclear  -> text untouched, flagged for the reviewer to listen to

The untouched original is saved once as sentences_marked.asr.json, so this can
be re-run from scratch.

    python3 asr_apply_fixes.py <workdir> <asr_fixes.json>
"""
import argparse, json, pathlib, shutil, sys

def main(work, fixfile):
    work = pathlib.Path(work)
    m, orig = work / "sentences_marked.json", work / "sentences_marked.asr.json"
    if not orig.exists():
        shutil.copy(m, orig)
    d = json.load(open(orig))                     # always start from the raw ASR
    sents = d["sentences"]
    fixes = json.load(open(fixfile)).get("fixes", [])
    n = {"high": 0, "low": 0, "unclear": 0, "skipped": 0}
    for f in fixes:
        i = int(f["id"])
        if not (0 <= i < len(sents)) or sents[i]["kind"] != "speech":
            n["skipped"] += 1
            print(f"  ! id {i}: no such speech line -- skipped", file=sys.stderr)
            continue
        s, c = sents[i], f.get("confidence", "low")
        asr = s.get("en", s["text"])
        new = (f.get("en") or asr).strip()
        if c == "unclear":
            new = asr
        if new != asr:
            s["en_asr"] = asr
            s["en"] = s["text"] = new
        if c == "high":
            s["asr_fix"] = f.get("why", "")
        else:
            opts = [o.strip() for o in f.get("options", []) if o and o.strip() and o.strip() != new]
            if c == "unclear":
                opts = []
            elif asr != new and asr not in opts:
                opts.append(asr)
            s["asr_doubt"] = {"why": f.get("why", ""), "options": opts, "level": c}
        n[c if c in n else "low"] += 1
    d["asr_fixes"] = {"file": str(fixfile), **n}
    m.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"applied: {n['high']} confident fixes, {n['low']} best guesses (flagged), "
          f"{n['unclear']} left for the reviewer, {n['skipped']} skipped")
    print(f"wrote {m}  (raw ASR kept in {orig.name})")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("workdir"); ap.add_argument("fixes")
    a = ap.parse_args()
    main(a.workdir, a.fixes)

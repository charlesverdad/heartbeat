#!/usr/bin/env python3
"""Fold the editor's JSON back into the pipeline.

The editor exports only what a human changed. Three kinds of change, and they
mean different things downstream:

  edited Chinese  -> use it verbatim, never re-translate over the top of it
  edited English  -> the source was wrong, so the Chinese under it is wrong too;
                     queue the line for a fresh translation
  dropped         -> emit no subtitle for that line at all

Writes the corrected sentence file, the re-translation queue, and the override
map, then tells you whether anything still needs translating before you build.

    python3 apply_edits.py <workdir> <edits.json>
"""
import json, pathlib, sys, argparse

def main(work, editfile):
    work = pathlib.Path(work)
    marked = json.load(open(work / "sentences_marked.json"))
    d = json.load(open(editfile))
    edits = {int(k): v for k, v in d.get("edits", d).items()}
    sents = marked["sentences"]

    queue, overrides, dropped, en_fixed = [], {}, [], 0
    for i, rec in sorted(edits.items()):
        if not (0 <= i < len(sents)):
            print(f"  ! edit for id {i} has no matching sentence -- skipped", file=sys.stderr)
            continue
        s = sents[i]
        if rec.get("drop"):
            s["kind"] = "dropped"
            dropped.append(i)
            continue
        if rec.get("en") is not None:
            s["en"] = s["text"] = rec["en"]
            s["en_edited"] = True
            en_fixed += 1
        if rec.get("retranslate"):
            queue.append({"id": i, "en": s.get("en", s.get("text", "")),
                          "start": s["start"], "end": s["end"]})
        elif rec.get("zh") is not None:
            overrides[str(i)] = rec["zh"]

    marked["edits_applied"] = {"file": str(editfile), "count": len(edits)}
    (work / "sentences_edited.json").write_text(
        json.dumps(marked, ensure_ascii=False, indent=1), encoding="utf-8")

    qpath = work / "batches" / "retranslate.json"
    qpath.parent.mkdir(exist_ok=True)
    qpath.write_text(json.dumps({"sentences": queue}, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    (work / "overrides_zh.json").write_text(
        json.dumps(overrides, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"edits read            : {len(edits)}")
    print(f"  Chinese kept as-is  : {len(overrides)}")
    print(f"  English corrected   : {en_fixed}  ({len(queue)} need re-translation)")
    print(f"  dropped             : {len(dropped)}" + (f"  {dropped}" if dropped else ""))
    print(f"wrote {work/'sentences_edited.json'}")
    print(f"wrote {qpath}")
    print(f"wrote {work/'overrides_zh.json'}")
    if queue:
        print(f"\nNEXT: translate the {len(queue)} queued lines in {qpath}")
        print(f"      write the result to {work/'batches'/'zh_retrans.json'}")
        print( "      (same format as the other batches: {\"translations\":[{\"id\":N,\"zh\":...}]})")
        print( "      then build with --edited")
    else:
        print("\nNothing needs re-translating -- ready to build.")
    return len(queue)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir"); ap.add_argument("edits")
    a = ap.parse_args()
    sys.exit(0 if main(a.workdir, a.edits) == 0 else 0)

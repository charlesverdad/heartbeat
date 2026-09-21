#!/usr/bin/env python3
"""Find key terms that came back rendered two different ways across the course.

Fourteen batches are translated by fourteen agents working in parallel, none of
which can see what the others chose. Within one batch a term is usually
consistent; across a course it is not, and a viewer who meets 学徒 in session 01
and 门徒 for the same English word in session 08 has lost the distinction the
course is built on.

This does not judge which rendering is right. It reports, for each watched
English term, every Chinese rendering that appeared alongside it and where --
so a human (or the next pass) can settle it.

    python3 check_consistency.py
"""
import collections, glob, json, os, pathlib, re, sys

ROOT = pathlib.Path("/Users/charles/work/heartbeat/youtube/ptw-course")

# English term -> the Chinese that should carry it. A term whose expected
# rendering is None is only surveyed, not checked.
WATCH = {
    "apprentice":  "学徒",
    "apprentices": "学徒",
    "disciple":    "门徒",
    "disciples":   "门徒",
    "Rule of Life": "生活准则",
    "spiritual formation": "属灵塑造",
    "Sabbath":     "安息日",
    "solitude":    "独处",
    "hospitality": "款待",
    "Dallas Willard": "魏乐德",
    "Tozer":       "陶恕",
    "Practicing the Way": "Practicing the Way",
}


def load(session_dir):
    """id -> (english, chinese) for one session."""
    out = {}
    b = session_dir / "batches"
    en = {}
    for f in sorted(b.glob("batch_*.json")):
        for s in json.loads(f.read_text())["sentences"]:
            en[int(s["id"])] = s["en"]
    for f in sorted(b.glob("zh_*.json")):
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            print(f"  !! {f.name} does not parse: {e}")
            continue
        for t in d.get("translations", []):
            i = int(t["id"])
            if i in en:
                out[i] = (en[i], t.get("zh", ""))
    return out


def main():
    sessions = sorted(d for d in (ROOT / ".work").glob("session-*") if d.is_dir())
    # term -> rendering -> set of sessions
    seen = collections.defaultdict(lambda: collections.defaultdict(set))
    missing = collections.defaultdict(list)

    for d in sessions:
        pairs = load(d)
        tag = d.name.split("-")[1]
        for i, (en, zh) in pairs.items():
            for term, want in WATCH.items():
                if not re.search(rf"\b{re.escape(term)}\b", en, re.I):
                    continue
                if want and want in zh:
                    seen[term][want].add(tag)
                else:
                    # Record what turned up instead, trimmed for readability.
                    seen[term]["(other)"].add(tag)
                    missing[term].append((tag, i, en[:60], zh[:40]))

    print("=== term survey ===")
    for term in WATCH:
        rends = seen.get(term)
        if not rends:
            continue
        bits = ", ".join(f"{r}[{','.join(sorted(s))}]" for r, s in sorted(rends.items()))
        mark = "  <-- CHECK" if "(other)" in rends and len(rends) > 1 else ""
        print(f"{term:<22} {bits}{mark}")

    if missing:
        print("\n=== lines where the expected rendering is absent ===")
        print("(not necessarily wrong -- a paraphrase can be right, and an English")
        print(" term inside a quoted verse follows CUV, not the glossary)")
        for term, rows in sorted(missing.items()):
            print(f"\n-- {term}  ({len(rows)} lines)")
            for tag, i, en, zh in rows[:6]:
                print(f"   s{tag} #{i}  {en!r}\n            -> {zh!r}")
            if len(rows) > 6:
                print(f"   ... and {len(rows)-6} more")
    return 0


sys.exit(main())

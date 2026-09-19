#!/usr/bin/env python3
"""Check a Chinese subtitle track before it goes anywhere near YouTube."""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cjk import visual_len, MAX_CHARS_PER_LINE, MAX_LINES, CHARS_PER_SEC

def parse(p):
    cues = []
    for blk in pathlib.Path(p).read_text(encoding="utf-8").split("\n\n"):
        L = [x for x in blk.strip().split("\n") if x.strip()]
        if len(L) < 3: continue
        a, b = L[1].split(" --> ")
        def ts(s):
            h, m, rest = s.split(":"); sec, ms = rest.split(",")
            return int(h)*3600 + int(m)*60 + int(sec) + int(ms)/1000
        cues.append((ts(a), ts(b), L[2:]))
    return cues

cues = parse(sys.argv[1])
print(f"cues: {len(cues)}")
fails = 0
over   = [(i,c) for i,c in enumerate(cues[:-1]) if c[1] > cues[i+1][0] + 1e-6]
toolong= [c for c in cues if any(visual_len(l) > MAX_CHARS_PER_LINE for l in c[2])]
toomany= [c for c in cues if len(c[2]) > MAX_LINES]
short  = [c for c in cues if c[1]-c[0] < 0.5]
fast   = [c for c in cues if (c[1]-c[0]) > 0 and
          sum(visual_len(l) for l in c[2])/(c[1]-c[0]) > CHARS_PER_SEC * 1.35]
latin  = [c for c in cues if re.search(r"[A-Za-z]{4,}", " ".join(c[2]))]
empty  = [c for c in cues if not "".join(c[2]).strip()]
for name, bad, show in (("overlapping cues", over, False),
                        ("lines over %d cells" % MAX_CHARS_PER_LINE, toolong, True),
                        ("more than %d lines" % MAX_LINES, toomany, True),
                        ("under 0.5s", short, True),
                        ("faster than reading speed", fast, True),
                        ("empty", empty, False)):
    flag = "ok " if not bad else "!! "
    if bad: fails += 1
    print(f"  {flag}{name}: {len(bad)}")
    if bad and show:
        for c in (bad[:3] if not isinstance(bad[0], tuple) or len(bad[0])==3 else [x[1] for x in bad[:3]]):
            print(f"       [{c[0]:.1f}-{c[1]:.1f}] {' / '.join(c[2])[:60]}")
print(f"  -- untranslated Latin text remaining: {len(latin)}")
if latin:
    for c in latin[:5]: print(f"       [{c[0]:.1f}] {' / '.join(c[2])[:70]}")
durs = [c[1]-c[0] for c in cues]
print(f"duration: mean {sum(durs)/len(durs):.2f}s  min {min(durs):.2f}s  max {max(durs):.2f}s")
print("VERDICT:", "PASS" if fails == 0 else f"{fails} check(s) failed")

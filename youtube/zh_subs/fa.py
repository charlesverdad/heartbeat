#!/usr/bin/env python3
"""Persian (Farsi) subtitle helpers: orthography, register, and cue splitting.

Persian is written right to left in an extended Arabic script, with words
separated by spaces, so it splits on word boundaries like English rather than
anywhere like Chinese. The checks here catch the two mistakes an Iranian reader
notices at once: Arabic letter forms (ي ك) instead of Persian ones (ی ک), and
Islamic vocabulary in a church sermon.
"""
import re

MAX_CHARS      = 50      # one line at FA size 94 on a 1920-wide script; widest seen ~60 fits
CHARS_PER_SEC  = 17.0    # brief asks translators for ~15; QA warns above this

RLM = "‏"           # forces a right-to-left paragraph when a line starts with Latin

# Islamic register a Christian viewer will object to (see glossary_fa.json _avoid).
AVOID = {
    "الله": "God is خدا",
    "حضرت عیسی": "write عیسی / عیسی مسیح",
    "عیسی (ع)": "write عیسی / عیسی مسیح",
    "روح‌الله": "Quranic title for Jesus",
    "نماز": "prayer is دعا",
    "مسجد": "mosque, never church",
}

BREAK_AFTER = "،؛:.!؟?»)…"

def normalise(text):
    """Persian letter forms, single spaces, no stray directional marks."""
    text = text.replace("ي", "ی").replace("ى", "ی").replace("ك", "ک")
    text = text.replace(RLM, "").replace("‎", "")
    return re.sub(r"[ \t\n]+", " ", text).strip()

def problems(text):
    """Register and orthography issues in one line, as short strings."""
    out = []
    if re.search("[يك]", text):
        out.append("Arabic ي/ك (use Persian ی/ک)")
    for word, why in AVOID.items():
        if word in text:
            out.append(f"{word}: {why}")
    return out

def split_text(text, n):
    """Cut `text` into n pieces of similar length at word boundaries, preferring
    a boundary that follows punctuation. Never splits inside a word, so a piece
    may run long; the caller checks widths."""
    words = text.split(" ")
    if n <= 1 or len(words) < 2:
        return [text]
    n = min(n, len(words))
    # character offset at which each word ends, counting the joining spaces
    ends, pos = [], 0
    for w in words:
        pos += len(w) + 1
        ends.append(pos - 1)
    total, cuts, last = len(text), [], 0
    for k in range(1, n):
        target = total * k / n
        best, best_cost = None, None
        for i in range(last, len(words) - (n - k)):
            cost = abs(ends[i] - target) - (6 if words[i][-1] in BREAK_AFTER else 0)
            if best_cost is None or cost < best_cost:
                best, best_cost = i, cost
        cuts.append(best + 1)
        last = best + 1
    bounds = [0] + cuts + [len(words)]
    return [" ".join(words[a:b]) for a, b in zip(bounds, bounds[1:]) if b > a]

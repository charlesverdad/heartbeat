#!/usr/bin/env python3
"""CJK subtitle line-breaking and cue timing.

English subtitle wrapping breaks on spaces at ~42 characters. Chinese has no
word spaces and uses full-width glyphs, so it needs its own rules. Defaults
follow common broadcast practice for Simplified Chinese: at most 16 full-width
characters per line, at most 2 lines, reading speed capped near 9 chars/sec.

Translation happens a SENTENCE at a time (English and Chinese word order differ
too much to translate fragments), so the job here is to lay one finished
Chinese sentence across the time span its English sentence occupied.
"""
import re

MAX_CHARS_PER_LINE = 16
MAX_LINES          = 2
CHARS_PER_SEC      = 9.0
MIN_DUR            = 0.85
MAX_DUR            = 7.0

BREAK_AFTER   = "，。！？；：、）》」』】…—"   # may end a line
NO_LINE_START = "，。！？；：、）》」』】…·"    # may not begin a line
NO_LINE_END   = "（《「『【"                    # may not end a line

def visual_len(s):
    """Full-width chars count 1; ASCII counts half a cell."""
    return sum(0.5 if ord(c) < 0x2E80 else 1.0 for c in s)

_WORDCHAR = re.compile(r"[0-9A-Za-z'\u2019.-]")

def _midword(text, i):
    """True if breaking the line before text[i] would cut a Latin word in half."""
    return (0 < i < len(text)
            and bool(_WORDCHAR.match(text[i-1])) and bool(_WORDCHAR.match(text[i])))

def _breaks(text):
    return [i + 1 for i, c in enumerate(text) if c in BREAK_AFTER and i + 1 < len(text)]

def wrap(text, max_chars=MAX_CHARS_PER_LINE, max_lines=MAX_LINES):
    text = text.strip()
    if visual_len(text) <= max_chars:
        return text
    target, best, best_cost = visual_len(text) / 2, None, None
    for p in _breaks(text):
        if visual_len(text[:p]) <= max_chars and visual_len(text[p:]) <= max_chars * (max_lines - 1):
            cost = abs(visual_len(text[:p]) - target)
            if best_cost is None or cost < best_cost:
                best, best_cost = p, cost
    if best is None:
        p = 1
        while p < len(text) and visual_len(text[:p + 1]) <= max_chars:
            p += 1
        # CJK breaks anywhere, so a width-only break is fine for Chinese and
        # wrong for the Latin runs embedded in it -- this is what set the book
        # "Practicing the Way" as "Practi / cing" and a shepherd's name as
        # "Na / than Choi". Back out of the word, unless the word is itself
        # longer than the line, in which case it has to break somewhere.
        p0 = p
        while p > 1 and p < len(text) and (text[p] in NO_LINE_START
                                           or text[p-1] in NO_LINE_END
                                           or _midword(text, p)):
            p -= 1
        best = p if p > 1 else p0
    head, tail = text[:best].strip(), text[best:].strip()
    if max_lines > 2:
        return head + "\n" + wrap(tail, max_chars, max_lines - 1)
    return head + "\n" + tail

def fits(text, max_chars=MAX_CHARS_PER_LINE, max_lines=MAX_LINES):
    """True if `text` wraps into at most max_lines lines of at most max_chars."""
    lines = wrap(text, max_chars, max_lines).split("\n")
    return len(lines) <= max_lines and all(visual_len(l) <= max_chars for l in lines)

def split_text(text, n):
    if n <= 1:
        return [text]
    pts, out, start = _breaks(text), [], 0
    for k in range(1, n):
        target = len(text) * k / n
        cand = [p for p in pts if p > start]
        p = max(min(cand, key=lambda x: abs(x - target)) if cand else int(target), start + 1)
        # the same mid-word cut, but across two cues instead of two lines
        q = p
        while q > start + 1 and _midword(text, q):
            q -= 1
        p = q if q > start + 1 else p
        out.append(text[start:p].strip()); start = p
    out.append(text[start:].strip())
    return [c for c in out if c]

def cues_for(text, t0, t1):
    """Lay one translated sentence across [t0,t1] as one or more timed cues."""
    # Chinese does not use spaces and the translator leaves stray ones behind,
    # so whitespace goes -- except between two Latin word characters, where it
    # is part of a name. Without this exception "Joshua Choi" reaches the screen
    # as "JoshuaChoi", and every member named in the announcements is mangled.
    text = re.sub(r"\s+", " ", text.strip())
    text = re.sub(r"(?<=[0-9A-Za-z]) (?=[0-9A-Za-z])", "\x00", text)
    text = text.replace(" ", "").replace("\x00", " ")
    if not text:
        return []
    dur = max(t1 - t0, 0.01)
    cap = MAX_CHARS_PER_LINE * MAX_LINES
    n = max(1,
            -(-int(visual_len(text)) // cap),                          # fits the box
            -(-int(visual_len(text)) // max(1, int(dur * CHARS_PER_SEC))))  # readable in time
    n = min(n, max(1, int(dur / MIN_DUR)))                             # no slivers
    parts = split_text(text, n)
    # split_text breaks at punctuation, so a part can still overflow the box
    # even though the total fitted. Grow n until every part wraps cleanly.
    limit = max(n, int(visual_len(text) // 4) + 2)
    while n < limit and not all(fits(p) for p in parts):
        n += 1
        parts = split_text(text, n)
    total = sum(visual_len(p) for p in parts) or 1
    cues, t = [], t0
    for i, p in enumerate(parts):
        d = dur * (visual_len(p) / total)
        end = t1 if i == len(parts) - 1 else min(t + max(d, MIN_DUR), t1)
        if end - t < MIN_DUR:
            end = min(t + MIN_DUR, t1) if t + MIN_DUR <= t1 else t1
        cues.append((t, max(end, t + 0.2), wrap(p)))
        t = cues[-1][1]
    return cues

def ts(t):
    return f"{int(t//3600):02d}:{int(t//60)%60:02d}:{int(t)%60:02d},{int(round((t-int(t))*1000)):03d}"

def to_srt(cues):
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n"
                     for i, (a, b, txt) in enumerate(cues, 1))

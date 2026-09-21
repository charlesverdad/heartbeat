#!/usr/bin/env python3
"""Latin-script subtitle line-breaking and cue timing.

A drop-in counterpart to `cjk.py`, exposing the same names so `build_srt.py`'s
timing machinery -- the overlap ceiling, the minimum-display pass, the sliver
merge -- can drive an English track without being duplicated. Swap the module
and the same algorithms apply:

    import build_srt, latin
    build_srt.cjk = latin

The rules differ from Chinese in every particular that matters. English breaks
on spaces rather than anywhere, counts a character as one cell rather than two,
and is read about twice as fast: broadcast practice is ~42 characters per line
and 17 characters per second, against 16 and 9 for Simplified Chinese.
"""
import re

MAX_CHARS_PER_LINE = 42
MAX_LINES          = 2
CHARS_PER_SEC      = 17.0
MIN_DUR            = 0.85
MAX_DUR            = 7.0

# Punctuation that may end a line, in rough order of how natural a break after
# it feels. A sentence-final mark is the cleanest place to split a long cue.
BREAK_AFTER = ".?!;:,—"


def visual_len(s):
    """One cell per character. Present so the shaper API matches cjk.py."""
    return float(len(s))


def _norm(text):
    return " ".join(text.split())


def _break_points(text):
    """Indices where a line may start, i.e. just after each space."""
    return [m.end() for m in re.finditer(r"\s", text)]


def _punct_points(text):
    """Break indices that also follow punctuation -- the nicer splits."""
    return [i for i in _break_points(text)
            if i >= 2 and text[i - 2] in BREAK_AFTER]


def wrap(text, max_chars=MAX_CHARS_PER_LINE, max_lines=MAX_LINES):
    """Break into at most max_lines lines, as evenly as the words allow.

    Balanced lines read better than a full line above a two-word orphan, so the
    break nearest the midpoint wins among those that fit. A break after
    punctuation is preferred when one is available at a comparable position.
    """
    text = _norm(text)
    if len(text) <= max_chars:
        return text

    target = len(text) / 2
    room_below = max_chars * (max_lines - 1)

    def pick(points):
        best, best_cost = None, None
        for p in points:
            head, tail = text[:p].strip(), text[p:].strip()
            if len(head) <= max_chars and len(tail) <= room_below:
                cost = abs(len(head) - target)
                if best_cost is None or cost < best_cost:
                    best, best_cost = p, cost
        return best, best_cost

    # A punctuation break is worth a little imbalance, but not a lot: past about
    # a fifth of the line it reads worse than the even split it displaced.
    p_best, p_cost = pick(_punct_points(text))
    s_best, s_cost = pick(_break_points(text))
    if p_best is not None and (s_cost is None or p_cost <= s_cost + max_chars * 0.2):
        best = p_best
    else:
        best = s_best

    if best is None:
        # Nothing splits this into max_lines lines that fit -- either one word
        # is longer than the line, or the text is simply too long for the box.
        # Break at the width anyway and keep wrapping the remainder: returning
        # an over-wide line here would put it straight into the file, and it is
        # `fits()` reporting False, not a truncated line, that tells the caller
        # to cut the cue into more pieces.
        best = max_chars
        while best > 1 and text[best - 1] != " ":
            best -= 1
        if best <= 1:
            best = max_chars
        return text[:best].strip() + "\n" + wrap(text[best:], max_chars, max_lines)

    head, tail = text[:best].strip(), text[best:].strip()
    if max_lines > 2:
        return head + "\n" + wrap(tail, max_chars, max_lines - 1)
    return head + "\n" + tail


def fits(text, max_chars=MAX_CHARS_PER_LINE, max_lines=MAX_LINES):
    """True if `text` wraps into at most max_lines lines of at most max_chars."""
    lines = wrap(text, max_chars, max_lines).split("\n")
    return len(lines) <= max_lines and all(len(l) <= max_chars for l in lines)


def _pack(words, width):
    """Greedily group words into runs of at most `width` characters."""
    out, cur = [], ""
    for w in words:
        cand = w if not cur else cur + " " + w
        if len(cand) <= width or not cur:
            cur = cand
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def split_text(text, n):
    """Cut `text` into at most n consecutive pieces at word boundaries.

    Packing by WIDTH rather than by target position. Choosing each break as the
    space nearest to k/n of the way through looks equivalent and is not: once a
    break lands past the next target the following pieces collapse onto single
    words, and a 348-character sentence came out as 35 cues, most of them a
    fifth of a second holding one or two letters. Packing greedily to an even
    width cannot degenerate that way.
    """
    text = _norm(text)
    if n <= 1:
        return [text]
    words = text.split(" ")
    target = max(1, -(-len(text) // n))          # ceil: even share of the text
    for width in range(target, len(text) + 1):
        parts = _pack(words, width)
        if len(parts) <= n:
            break
    return [p for p in parts if p]


def cues_for(text, t0, t1):
    """Lay one sentence across [t0,t1] as one or more timed cues."""
    text = _norm(text)
    if not text:
        return []
    dur = max(t1 - t0, 0.01)
    cap = MAX_CHARS_PER_LINE * MAX_LINES
    n = max(1,
            -(-int(len(text)) // cap),                                    # fits the box
            -(-int(len(text)) // max(1, int(dur * CHARS_PER_SEC))))       # readable in time
    n = min(n, max(1, int(dur / MIN_DUR)))                                # no slivers
    parts = split_text(text, n)
    # split_text aims at a position, not at a width, so a piece can still
    # overflow even when the total fitted. Grow n until every piece wraps.
    limit = max(n, len(text) // 8 + 2)
    while n < limit and not all(fits(p) for p in parts):
        n += 1
        parts = split_text(text, n)
    total = sum(len(p) for p in parts) or 1
    cues, t = [], t0
    for i, p in enumerate(parts):
        d = dur * (len(p) / total)
        end = t1 if i == len(parts) - 1 else min(t + max(d, MIN_DUR), t1)
        if end - t < MIN_DUR:
            end = min(t + MIN_DUR, t1) if t + MIN_DUR <= t1 else t1
        cues.append((t, max(end, t + 0.2), wrap(p)))
        t = cues[-1][1]
    return cues


def join(a, b):
    """Concatenate two cues' text when merging them.

    The space is the whole point. Abutting the runs the way Chinese does turns
    "on your" into "onyour" and "does look" into "doeslook" -- which is exactly
    what the shared merge pass produced before this hook existed.
    """
    a, b = a.strip(), b.strip()
    return (a + " " + b).strip() if a and b else (a or b)


def ts(t):
    return f"{int(t//3600):02d}:{int(t//60)%60:02d}:{int(t)%60:02d},{int(round((t-int(t))*1000)):03d}"


def to_srt(cues):
    return "\n".join(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n"
                     for i, (a, b, txt) in enumerate(cues, 1))

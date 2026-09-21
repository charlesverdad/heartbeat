#!/usr/bin/env python3
"""Convert a Simplified Chinese subtitle track to Traditional (zh-Hant).

These tracks are made for one viewer on the Gold Coast, and she reads
Traditional. She said so after watching a Simplified burn-in she otherwise
liked a lot. That last part decides the method: **convert the script, do not
re-translate the words.** The wording is what she praised, so a converter that
swaps vocabulary for regional synonyms would quietly undo the thing that worked.

That rules out OpenCC's `s2twp`, which rewrites 軟件 to 軟體 and 信息 to 資訊.
We use `s2tw` -- Taiwan character forms, wording untouched. Taiwan forms are a
default, not a finding: Taiwan is the only region anyone has named, and that was
about a second, prospective viewer rather than the one we are actually writing
for. The visible difference from Hong Kong's `s2hk` is 裡 against 裏, which is
frequent enough to notice (76 occurrences in a single sermon), so it is worth
asking her which she reads before assuming.

Simplified merged several distinct Traditional characters, so conversion is not
a table lookup and OpenCC disambiguates by phrase. It gets almost everything
right -- 头发/髮 against 发生/發, 干净/乾 against 树干/幹, 皇后/后 against
后面/後, 一只/隻 against 只有/只 -- but a 里 whose preceding word is not in its
phrase table stays 里 when it should be 裡. So every surviving 里 is reported
with its context for a human to glance at; in a real sermon there were eight and
all eight were 公里, which is correct.

    python3 to_traditional.py sermon.zh-Hans.srt sermon.zh-Hant.srt
"""
import argparse, pathlib, re, sys

CONFIGS = {"tw": "s2tw",      # Taiwan forms, wording untouched  (default)
           "hk": "s2hk",      # Hong Kong forms (裏 rather than 裡)
           "t":  "s2t",       # OpenCC standard forms
           "twp": "s2twp"}    # Taiwan forms AND Taiwan vocabulary -- rewrites wording

# 里 is the one merge OpenCC demonstrably gets wrong: it splits into 里 (the
# distance unit) and 裡 (inside), and a 裡 whose preceding word is missing from
# the phrase table stays 里 -- "教會里面" rather than "教會裡面".
#
# The other merges it handles, verified: 头发/髮 against 发生/發, 干净/乾 against
# 干活/幹 and 树干/幹, 后面/後 against 皇后/后, 一只/隻 against 只有/只, 面条/麵
# against 外面/面, 余下/餘 against 茶几/几. Reporting those too produced 73 hits
# on one sermon, every one of them correct -- noise that teaches you to skip the
# report. They are available behind --check-all when a conversion looks off.
AMBIGUOUS       = "里"
AMBIGUOUS_ALL   = "里后干只几余表面发"

# Nouns after which 里 is the locative "inside" and OpenCC leaves it alone,
# because the compound is absent from its phrase table. Each is a word a
# subtitle says constantly -- "in the church", "in the guide", "in your heart" --
# so the miss is not rare. On the first sermon all eight survivors were 公里 and
# correct; on an eight-session course seven of nine were wrong, all of this
# shape. Applied AFTER conversion, so it cannot disturb anything OpenCC got
# right, and deliberately narrow: a transliterated name keeps its 里 (拉里 for
# Larry, 諾里奇 for Norwich), which a blanket 里->裡 would wreck.
LOCATIVE_BEFORE_LI = ["教會", "指南", "心", "家", "手冊", "房間", "城市",
                      "世界", "生活", "生命", "聖經", "書", "課程", "群體"]


def fix_locative_li(text, inside="裡"):
    """Repair 里 that should be the locative, leaving the distance unit alone."""
    for noun in LOCATIVE_BEFORE_LI:
        text = text.replace(noun + "里", noun + inside)
    return text


def convert(text, variant="tw"):
    try:
        from opencc import OpenCC
    except ImportError:
        sys.exit("opencc is not installed:\n"
                 "  pip install -r youtube/subtitle_downloader/requirements.txt")
    out = OpenCC(CONFIGS[variant]).convert(text)
    # Hong Kong forms use 裏 for the same word, so follow the variant.
    return fix_locative_li(out, "裏" if variant == "hk" else "裡")


def residuals(out, chars=AMBIGUOUS, width=5):
    """Every surviving ambiguous character, with context, for eyeballing."""
    found = []
    for m in re.finditer(f"[{chars}]", out):
        ctx = out[max(0, m.start() - width): m.start() + width + 1]
        found.append((m.group(), ctx.replace("\n", "/")))
    return found


def srt_text_only(path):
    """The subtitle text, without the indices and timestamps.

    Converting the whole file would work -- digits and arrows are untouched --
    but reporting residuals over the timestamps would bury the real hits.
    """
    blocks = re.split(r"\n\s*\n", pathlib.Path(path).read_text(encoding="utf-8").strip())
    return "\n".join(b.split("\n", 2)[2] for b in blocks if len(b.split("\n")) > 2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", help="Simplified .srt (or any UTF-8 text)")
    ap.add_argument("out", nargs="?", help="default: <src with zh-Hans -> zh-Hant>")
    ap.add_argument("--variant", choices=sorted(CONFIGS), default="tw",
                    help="tw (default, Taiwan forms), hk, t, or twp. twp also rewrites "
                         "vocabulary to Taiwan terms -- it changes the translator's wording, "
                         "so do not use it on a track anyone has already approved.")
    ap.add_argument("--quiet", action="store_true", help="skip the residual report")
    ap.add_argument("--check-all", action="store_true",
                    help="report every merged character, not just the one OpenCC misses")
    a = ap.parse_args()

    src = pathlib.Path(a.src)
    out = pathlib.Path(a.out) if a.out else pathlib.Path(
        str(src).replace("zh-Hans", "zh-Hant") if "zh-Hans" in str(src)
        else str(src.with_suffix("")) + ".zh-Hant" + src.suffix)
    if out == src:
        sys.exit("refusing to overwrite the source in place -- give an output path")

    text = src.read_text(encoding="utf-8")
    converted = convert(text, a.variant)
    out.write_text(converted, encoding="utf-8")

    n_hant = sum(converted.count(c) for c in "裡裏們這說會為個來國學點麼樣現開發過還讓經給應該覺認識")
    print(f"variant  : {CONFIGS[a.variant]}")
    print(f"wrote    : {out}")
    print(f"Traditional forms produced: {n_hant:,}")
    print(f"裡 {converted.count('裡')}   裏 {converted.count('裏')}")

    if not a.quiet:
        # report over the subtitle text only, so timestamps do not drown the hits
        body = convert(srt_text_only(src), a.variant) if src.suffix == ".srt" else converted
        res = residuals(body, AMBIGUOUS_ALL if a.check_all else AMBIGUOUS)
        print(f"\nambiguous characters left as-is: {len(res)}")
        if res:
            print("  each of these was a merge in Simplified; check the sense reads right:")
            seen = {}
            for ch, ctx in res:
                seen.setdefault(ch, []).append(ctx)
            for ch, ctxs in sorted(seen.items()):
                print(f"    {ch}  x{len(ctxs)}")
                for c in list(dict.fromkeys(ctxs))[:6]:
                    print(f"        {c}")

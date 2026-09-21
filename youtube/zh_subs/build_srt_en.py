#!/usr/bin/env python3
"""Assemble the English subtitle track from the ASR sentences.

The Chinese track exists because someone translated it; the English one is
already sitting in `sentences_marked.json` and only needs laying out. What it
shares with `build_srt.py` is everything about *timing* -- the ceiling that
stops one cue running into the next, the minimum-display pass, the sliver
merge -- so that logic is reused rather than reimplemented, with the Latin
shaper swapped in for the CJK one:

    python3 build_srt_en.py <sentences_marked.json> <out.srt>

Non-speech sentences are skipped on the same terms as the Chinese track: a
stretch marked `song` or `halluc` gets no cue, because a Whisper loop
transcribed verbatim is worse than silence.
"""
import argparse, json, pathlib, sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import build_srt
import latin

# build_srt reaches its shaper through a module-global, so pointing that at the
# Latin module redirects every wrap/fit/split decision without touching a line
# of its timing code. Both modules expose the same names for exactly this.
build_srt.cjk = latin


def main(a):
    marked = json.loads(pathlib.Path(a.marked).read_text(encoding="utf-8"))
    sents = marked["sentences"]
    offset = marked.get("offset", 0.0)

    # The same offset guard build_srt applies: sentences built against one
    # meta.json and timed against another are wrong by the difference, and
    # nothing downstream can detect it.
    meta_path = pathlib.Path(a.marked).parent / "meta.json"
    if meta_path.exists():
        meta_offset = json.loads(meta_path.read_text()).get("offset", 0.0)
        if abs(meta_offset - offset) > 0.001:
            sys.exit(f"ERROR: offset mismatch -- sentences say {offset}s, "
                     f"meta.json says {meta_offset}s. Re-run the sentence steps.")

    en = {i: s["text"].strip() for i, s in enumerate(sents)
          if s.get("kind", "speech") == "speech" and s.get("text", "").strip()}

    cues = build_srt.build(marked, en, offset)
    pathlib.Path(a.out).write_text(latin.to_srt(cues), encoding="utf-8")

    speech = [i for i, s in enumerate(sents) if s.get("kind", "speech") == "speech"]
    skipped = len(sents) - len(speech)
    print(f"speech sentences : {len(speech)}  ({skipped} non-speech skipped)")
    print(f"cues written     : {len(cues)}")
    if cues:
        print(f"track spans      : {cues[0][0]:.1f}s .. {cues[-1][1]:.1f}s")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("marked", help="sentences_marked.json (or sentences_edited.json)")
    ap.add_argument("out", help="output .srt path")
    main(ap.parse_args())

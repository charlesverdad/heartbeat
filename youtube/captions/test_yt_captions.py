#!/usr/bin/env python3
"""Tests for the caption uploader.

Everything that talks to YouTube is stubbed. What is worth testing here is not
the API call -- it is the two decisions made before the call, because both fail
silently and both fail in public: picking which of several SRTs is current, and
deciding whether a track already exists to be replaced.
"""
import pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import yt_captions as Y

PASS = FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1; print(f"  ok   {name}")
    else:
        FAIL += 1; print(f"  FAIL {name}" + (f"\n       {detail}" if detail else ""))


def test_newest_tracks():
    """A rebuild is written to a NEW filename, so the plain name is the oldest
    file present, not the newest. Uploading it would publish the pre-edit
    wording under the reviewer's nose."""
    print("\nnewest_tracks: the version in the name decides, not mtime")
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d)
        for n in ("sermon.zh-Hans.srt", "sermon.zh-Hant.srt", "sermon.zh-Hant.v2.srt",
                  "sermon.en.srt", "sermon.zh-Hant.v10.srt", "sermon.fr.srt",
                  "notes.txt", "sermon.zh-subbed.mp4"):
            (w / n).write_text("x", encoding="utf-8")
        got = Y.newest_tracks(w)
        check("picks v10 over v2 over unversioned",
              got["zh-Hant"].name == "sermon.zh-Hant.v10.srt", str(got.get("zh-Hant")))
        check("unversioned wins when it is the only one",
              got["zh-Hans"].name == "sermon.zh-Hans.srt", str(got.get("zh-Hans")))
        check("picks up other known languages", got["en"].name == "sermon.en.srt")
        check("ignores a language the pipeline does not produce", "fr" not in got)
        check("ignores non-srt files", not any(str(f).endswith(".mp4") for f in got.values()))

    with tempfile.TemporaryDirectory() as d:
        check("an empty directory yields nothing", Y.newest_tracks(d) == {})


def test_find_existing():
    """YouTube's own ASR track comes back in captions.list. Matching it and
    then calling captions.update fails with a 403 that reads like an auth
    problem, when the right move was simply to insert a new track."""
    print("\nfind_existing: never match YouTube's own ASR track")
    asr  = {"id": "A", "snippet": {"language": "en", "name": "", "trackKind": "asr"}}
    ours = {"id": "B", "snippet": {"language": "en", "name": "", "trackKind": "standard"}}
    hant = {"id": "C", "snippet": {"language": "zh-Hant", "name": "", "trackKind": "standard"}}
    named = {"id": "D", "snippet": {"language": "zh-Hant", "name": "繁體", "trackKind": "standard"}}

    check("asr-only list gives no match (so we insert, not update)",
          Y.find_existing([asr], "en", "") is None)
    check("our own track matches", Y.find_existing([asr, ours], "en", "")["id"] == "B")
    check("a different language does not match",
          Y.find_existing([hant], "en", "") is None)
    check("a different track name does not match",
          Y.find_existing([named], "zh-Hant", "") is None)
    check("a matching name does match",
          Y.find_existing([hant, named], "zh-Hant", "繁體")["id"] == "D")
    check("empty list gives no match", Y.find_existing([], "zh-Hant", "") is None)


def test_upload_is_opt_in():
    """These videos are public and a caption track shows up for viewers at
    once, so the default must be to describe the change and send nothing."""
    print("\nupload: writing requires --confirm")
    calls = []

    class FakeCaptions:
        def list(self, **kw):  return FakeExec({"items": []})
        def insert(self, **kw): calls.append("insert"); return FakeExec({"id": "new"})
        def update(self, **kw): calls.append("update"); return FakeExec({"id": "upd"})

    class FakeExec:
        def __init__(self, v): self.v = v
        def execute(self):     return self.v

    class FakeYT:
        def captions(self):    return FakeCaptions()

    with tempfile.TemporaryDirectory() as d:
        srt = pathlib.Path(d) / "s.srt"
        srt.write_text("1\n00:00:01,000 --> 00:00:02,000\n嗨\n", encoding="utf-8")
        Y.upload(FakeYT(), "VID", srt, "zh-Hant", "", confirm=False)
        check("nothing is sent without --confirm", calls == [], str(calls))
        Y.upload(FakeYT(), "VID", srt, "zh-Hant", "", confirm=True)
        check("--confirm inserts when no track exists", calls == ["insert"], str(calls))


def test_describe():
    print("\ndescribe: says which tracks are YouTube's and which are ours")
    out = Y.describe([{"id": "A", "snippet": {"language": "en", "name": "",
                                              "trackKind": "asr"}}])
    check("flags an asr track as such", "asr" in out, out)
    check("an empty list says so", "no caption tracks" in Y.describe([]))


if __name__ == "__main__":
    for t in (test_newest_tracks, test_find_existing, test_upload_is_opt_in, test_describe):
        try:
            t()
        except Exception as e:
            FAIL += 1
            print(f"  FAIL {t.__name__} raised {type(e).__name__}: {e}")
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)

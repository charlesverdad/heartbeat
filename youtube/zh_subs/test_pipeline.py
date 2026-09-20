#!/usr/bin/env python3
"""Regression tests for the subtitle pipeline.

The failure this guards against is not a crash. It is a track that builds
cleanly and is two seconds out, or attached to the wrong sentence -- nobody
notices until it is on a screen in front of a congregation. So most of these
assert timing invariants rather than outputs.

    python3 test_pipeline.py
"""
import re, json, pathlib, subprocess, sys, tempfile, threading, urllib.request, urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import cjk, build_srt, bake_subs

PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'ok  ' if cond else 'FAIL'} {name}" + (f"  -- {detail}" if detail and not cond else ""))

# ---------------------------------------------------------------- cjk
def test_cjk():
    print("\ncjk: line breaking and cue layout")
    long_zh = "我们在基督里的丰盛生命是神所赐的恩典，不是靠自己的努力赚来的，这一点非常重要。"
    for t in (long_zh, "短句。", "阿们。", "一位DJ把剩下的面包边放到eBay上卖了一千多美元。"):
        lines = cjk.wrap(t).split("\n")
        check(f"wrap fits box: {t[:12]}...",
              len(lines) <= cjk.MAX_LINES and all(cjk.visual_len(l) <= cjk.MAX_CHARS_PER_LINE for l in lines)
              or not cjk.fits(t),
              f"{len(lines)} lines, widths {[cjk.visual_len(l) for l in lines]}")

    # every cue cues_for emits must fit the box and stay inside the span
    cues = cjk.cues_for(long_zh, 10.0, 14.0)
    check("cues_for stays in span", all(10.0 <= a and b <= 14.0 + 1e-6 for a, b, _ in cues),
          str([(a, b) for a, b, _ in cues]))
    check("cues_for is ordered and non-overlapping",
          all(cues[i][1] <= cues[i+1][0] + 1e-9 for i in range(len(cues) - 1)))
    check("cues_for parts all fit", all(cjk.fits(t) for _, _, t in cues))
    check("cues_for emits something", len(cues) >= 1)
    check("cues_for on empty text emits nothing", cjk.cues_for("   ", 0, 1) == [])
    # a zero-length span must not produce a zero or negative duration cue
    z = cjk.cues_for("短句。", 5.0, 5.0)
    check("zero-length span survives", all(b >= a for a, b, _ in z), str(z))

    # Chinese carries no spaces, so cues_for strips them -- but a Latin name is
    # two words and stays two words. "JoshuaChoi" on screen is how this was found.
    for src, want in (("我叫 Joshua Choi。",            "我叫Joshua Choi。"),
                      ("宝宝叫Hannah Bow，",            "宝宝叫Hannah Bow，"),
                      ("我们  今天   要讲。",            "我们今天要讲。"),
                      ("John Mark Comer 说过。",        "John Mark Comer说过。")):
        got = "".join(t.replace("\n", "") for _, _, t in cjk.cues_for(src, 0, 20))
        check(f"name spacing survives: {want}", got == want, f"got {got!r}")

    # ... and the line break must not land inside one either. These three are
    # the cues that shipped as "Practi / cing", "Kevin Ki / m", "Na / than Choi".
    for t in ("两周之后，我们要开始一个叫Practicing the Way的课程。",
              "墨尔本的Pius、黄金海岸的Kevin Kim，还有悉尼的Joshua Lee。",
              "我知道你们有些人认识黄金海岸的Nathan Choi，"):
        lines = [ln for _, _, part in cjk.cues_for(t, 0, 20) for ln in part.split("\n")]
        # breaking at the space in "Kevin Kim" is fine; breaking "Kim" is not,
        # so the invariant is per word, not per adjacent character pair
        words = re.findall(r"[A-Za-z][0-9A-Za-z'.]*", t)
        lost  = [w for w in words if not any(w in ln for ln in lines)]
        check(f"no mid-word break: {t[:10]}...", not lost, f"{lost} split across {lines}")

# ---------------------------------------------------------------- build_srt
def _marked(sents, offset=100.0):
    return {"offset": offset,
            "sentences": [{"start": s, "end": e, "kind": k, "text": "x", "en": "x"}
                          for s, e, k in sents]}

def test_build():
    print("\nbuild_srt: timing invariants")
    marked = _marked([(0.0, 3.0, "speech"), (3.2, 6.0, "speech"),
                      (6.1, 6.4, "speech"), (7.0, 20.0, "song"), (21.0, 24.0, "speech")])
    zh = {0: "第一句话在这里。", 1: "第二句话也在这里。", 2: "是的。", 4: "最后一句。"}
    cues = build_srt.build(marked, zh, marked["offset"])

    check("no overlapping cues", all(cues[i][1] <= cues[i+1][0] + 1e-9 for i in range(len(cues) - 1)))
    check("all durations positive", all(b > a for a, b, _ in cues))
    check("offset applied", cues[0][0] >= marked["offset"],
          f"first cue at {cues[0][0]}, offset {marked['offset']}")
    check("song sentence produced no cue",
          not any(107.0 <= a < 120.0 for a, _, _ in cues), str([c[0] for c in cues]))
    check("every cue text fits the box", all(cjk.fits(t) for _, _, t in cues))

    # a sentence with no translation must be skipped, not emitted blank
    cues2 = build_srt.build(marked, {0: "只有这一句。"}, 0.0)
    check("untranslated sentences are skipped", len(cues2) >= 1 and all(t.strip() for _, _, t in cues2))

    # dropped lines must not appear
    m3 = _marked([(0.0, 3.0, "dropped"), (4.0, 7.0, "speech")], offset=0.0)
    c3 = build_srt.build(m3, {0: "不该出现。", 1: "应该出现。"}, 0.0)
    check("dropped sentences emit no cue", all("不该出现" not in t for _, _, t in c3), str(c3))

def test_provenance():
    print("\nbuild_srt: translation provenance")
    with tempfile.TemporaryDirectory() as d:
        b = pathlib.Path(d)
        (b / "zh_0.json").write_text(json.dumps({"translations": [{"id": 1, "zh": "旧的翻译。"}]}), encoding="utf-8")
        (b / "zh_retrans.json").write_text(json.dumps({"translations": [{"id": 1, "zh": "新的翻译。"}]}), encoding="utf-8")
        zh, origin = build_srt.load_translations(b)
        check("retranslation wins over the stale batch", zh[1] == "新的翻译。", zh.get(1))
        check("provenance identifies the retranslation", "retrans" in origin[1], origin.get(1))

# ---------------------------------------------------------------- shift_srt
def test_shift():
    print("\nbake_subs: re-basing onto a cut")
    srt = ("1\n00:00:10,000 --> 00:00:12,000\n甲\n\n"
           "2\n00:00:20,000 --> 00:00:22,000\n乙\n\n"
           "3\n00:00:30,000 --> 00:00:32,000\n丙\n")
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.srt"; p.write_text(srt, encoding="utf-8")
        out, n = bake_subs.shift_srt(p, 15.0, 25.0)
        check("cues outside the cut are dropped", n == 1, f"kept {n}")
        check("kept cue is re-based to the cut", "00:00:05,000 --> 00:00:07,000" in out, out)
        out2, n2 = bake_subs.shift_srt(p, 0.0, None)
        check("a no-op cut keeps everything", n2 == 3, f"kept {n2}")
        out3, n3 = bake_subs.shift_srt(p, 11.0, None)
        # cue 1 (10->12) straddles the cut: its tail must survive, re-based to 0, never negative
        check("a cue straddling the cut start is clamped to zero",
              out3.split("\n")[1] == "00:00:00,000 --> 00:00:01,000", out3.split("\n")[1])
        check("no negative timestamps anywhere", "-0" not in out3.replace("-->", ""), out3)
        check("straddling cue keeps its text", out3.split("\n")[2] == "\u7532", out3.split("\n")[2])

# ---------------------------------------------------------------- range server
def test_range_server():
    print("\nmake_editor: byte-range HTTP")
    import make_editor, functools, socketserver, socket
    with tempfile.TemporaryDirectory() as d:
        blob = bytes(range(256)) * 400          # 102400 bytes
        (pathlib.Path(d) / "f.bin").write_bytes(blob)

        class S(socketserver.ThreadingTCPServer):
            allow_reuse_address = True; daemon_threads = True
        h = functools.partial(make_editor.RangeHandler, directory=d)
        srv = S(("127.0.0.1", 0), h)
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{port}/f.bin"

        def get(rng=None):
            req = urllib.request.Request(url)
            if rng: req.add_header("Range", rng)
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    return r.status, r.headers, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.headers, e.read()

        st, hd, body = get("bytes=100-199")
        check("206 for a closed range", st == 206, str(st))
        check("closed range returns exactly those bytes", body == blob[100:200], f"{len(body)} bytes")
        check("Content-Range is correct", hd.get("Content-Range") == f"bytes 100-199/{len(blob)}",
              hd.get("Content-Range"))
        check("Content-Length matches body", int(hd.get("Content-Length")) == len(body))

        st, hd, body = get("bytes=0-")
        check("open-ended range returns the whole file", st == 206 and body == blob, f"{st}, {len(body)}")

        st, hd, body = get("bytes=-50")
        check("suffix range returns the last N bytes", st == 206 and body == blob[-50:], f"{st}, {len(body)}")

        st, hd, _ = get(f"bytes={len(blob)+10}-{len(blob)+20}")
        check("416 past the end", st == 416, str(st))
        check("416 carries Content-Range with the size",
              (hd.get("Content-Range") or "").endswith(f"/{len(blob)}"), hd.get("Content-Range"))

        st, hd, body = get()
        check("plain GET still works", st == 200 and body == blob, f"{st}, {len(body)}")
        check("Accept-Ranges advertised exactly once",
              len(hd.get_all("Accept-Ranges") or []) == 1, str(hd.get_all("Accept-Ranges")))

        # keep-alive must not desynchronise: two ranges down one connection
        c = socket.create_connection(("127.0.0.1", port), timeout=10)
        c.sendall(b"GET /f.bin HTTP/1.1\r\nHost: x\r\nRange: bytes=0-9\r\n\r\n"
                  b"GET /f.bin HTTP/1.1\r\nHost: x\r\nRange: bytes=10-19\r\nConnection: close\r\n\r\n")
        got = b""
        while True:
            chunk = c.recv(65536)
            if not chunk: break
            got += chunk
        c.close()
        check("two pipelined ranges both answered on one connection",
              got.count(b"206 Partial Content") == 2, f"saw {got.count(b'206 Partial Content')}")
        srv.shutdown()

# ---------------------------------------------------------------- apply_edits
def test_apply_edits():
    print("\napply_edits: reviewer edit precedence")
    import apply_edits
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d); (w / "batches").mkdir()
        marked = _marked([(0.0, 2.0, "speech")] * 4, offset=0.0)
        for i, s in enumerate(marked["sentences"]):
            s["text"] = s["en"] = f"english {i}"
        (w / "sentences_marked.json").write_text(json.dumps(marked), encoding="utf-8")
        edits = {"edits": {
            "0": {"zh": "人手写的中文。"},                                   # zh only -> verbatim
            "1": {"en": "fixed english", "retranslate": True},              # en only -> queue
            "2": {"en": "fixed too", "zh": "也改了中文。", "retranslate": True},  # both, en newer -> queue
            "3": {"drop": True},
        }}
        ef = w / "e.json"; ef.write_text(json.dumps(edits), encoding="utf-8")
        queued = apply_edits.main(w, ef)

        ov = json.loads((w / "overrides_zh.json").read_text())
        q  = json.loads((w / "batches" / "retranslate.json").read_text())["sentences"]
        ed = json.loads((w / "sentences_edited.json").read_text())["sentences"]
        qids = {s["id"] for s in q}

        check("zh-only edit becomes a verbatim override", ov.get("0") == "人手写的中文。", str(ov))
        check("zh-only edit is NOT queued for retranslation", 0 not in qids, str(qids))
        check("en-only edit is queued", 1 in qids, str(qids))
        check("en-only edit is not also an override", "1" not in ov, str(ov))
        check("corrected english reaches the sentence file", ed[1]["en"] == "fixed english", ed[1]["en"])
        check("en_edited flag is set for the stale-check", ed[1].get("en_edited") is True)
        check("retranslate wins when english was edited last", 2 in qids and "2" not in ov,
              f"queued={qids} overrides={list(ov)}")
        check("dropped line is marked dropped", ed[3]["kind"] == "dropped", ed[3]["kind"])
        check("queue count is reported", queued == 2, str(queued))

# ---------------------------------------------------------------- review regressions
def test_no_overlap_ever():
    """Randomised timings. The extension and merge passes both move cue ends
    after the point where overlaps used to be checked, so the invariant has to
    be enforced last -- a fixed example set will not catch that."""
    print("\nbuild_srt: overlap invariant under randomised timings")
    import random
    random.seed(7)
    ZH = ["对吗？", "阿们。", "是的。", "这就是福音的核心。", "你有没有想过这个问题呢？",
          "神的恩典是白白赐给我们的。",
          "我们今天要讲的这段经文其实非常重要，值得仔细思考它的含义和应用。"]
    overlaps = bad_order = short = 0
    for _ in range(4000):
        n, t, sents = random.randint(2, 5), 0.0, []
        for _i in range(n):
            dur = random.choice([0.05, 0.08, 0.12, 0.3, 1.0, 2.5])
            gap = random.choice([0.061, 0.07, 0.1, 0.141, 0.3, 0.8])
            sents.append({"start": round(t, 3), "end": round(t + dur, 3),
                          "kind": "speech", "text": "x", "en": "x"})
            t += dur + gap
        zh = {i: random.choice(ZH) for i in range(n)}
        cues = build_srt.build({"offset": 0.0, "sentences": sents}, zh, 0.0)
        for k in range(len(cues) - 1):
            if cues[k][1] > cues[k+1][0] + 1e-9: overlaps += 1
            if cues[k][0] > cues[k+1][0]: bad_order += 1
        for a, b, _t in cues:
            if b <= a: short += 1
    check("no cue ever runs into the next", overlaps == 0, f"{overlaps} overlaps")
    check("cues stay in start order", bad_order == 0, f"{bad_order} out of order")
    check("no zero or negative duration cue", short == 0, f"{short} bad durations")

    # the specific shape that used to fail: a fast interjection immediately
    # before the next translated sentence
    marked = _marked([(0.0, 0.08, "speech"), (0.141, 3.0, "speech")], offset=0.0)
    cues = build_srt.build(marked, {0: "对吗？", 1: "我们今天要讲的是这个。"}, 0.0)
    check("fast interjection does not overlap its neighbour",
          all(cues[k][1] <= cues[k+1][0] + 1e-9 for k in range(len(cues) - 1)),
          str([(round(a,3), round(b,3)) for a, b, _ in cues]))

def test_416_keepalive():
    """A 416 with no Content-Length is framed by connection close -- but this
    server keeps the socket open, so the next request on it would stall."""
    print("\nmake_editor: a 416 does not poison the connection")
    import make_editor, functools, socketserver, socket
    with tempfile.TemporaryDirectory() as d:
        blob = bytes(range(256)) * 40
        (pathlib.Path(d) / "f.bin").write_bytes(blob)

        class S(socketserver.ThreadingTCPServer):
            allow_reuse_address = True; daemon_threads = True
        srv = S(("127.0.0.1", 0), functools.partial(make_editor.RangeHandler, directory=d))
        port = srv.server_address[1]
        threading.Thread(target=srv.serve_forever, daemon=True).start()

        c = socket.create_connection(("127.0.0.1", port), timeout=10)
        c.sendall(f"GET /f.bin HTTP/1.1\r\nHost: x\r\nRange: bytes={len(blob)+5}-{len(blob)+9}\r\n\r\n"
                  f"GET /f.bin HTTP/1.1\r\nHost: x\r\nRange: bytes=0-9\r\nConnection: close\r\n\r\n"
                  .encode())
        got = b""
        try:
            while True:
                chunk = c.recv(65536)
                if not chunk: break
                got += chunk
        except socket.timeout:
            got += b"<<TIMED OUT>>"
        c.close(); srv.shutdown()

        check("416 declares a zero-length body",
              b"416" in got and b"Content-Length: 0" in got, got[:160].decode(errors="replace"))
        check("the request after a 416 is still answered",
              b"206 Partial Content" in got, got[:200].decode(errors="replace"))
        check("connection did not stall", b"<<TIMED OUT>>" not in got)

def test_apply_edits_exit_code():
    """Exit code has to mean something, or `apply_edits && build_srt` builds a
    track from translations the reviewer already superseded."""
    print("\napply_edits: exit code reflects pending re-translation")
    import subprocess
    def run(edits):
        with tempfile.TemporaryDirectory() as d:
            w = pathlib.Path(d); (w / "batches").mkdir()
            marked = _marked([(0.0, 2.0, "speech")] * 2, offset=0.0)
            for i, sn in enumerate(marked["sentences"]): sn["text"] = sn["en"] = f"english {i}"
            (w / "sentences_marked.json").write_text(json.dumps(marked), encoding="utf-8")
            ef = w / "e.json"; ef.write_text(json.dumps({"edits": edits}), encoding="utf-8")
            return subprocess.run([sys.executable, str(pathlib.Path(__file__).parent / "apply_edits.py"),
                                   str(w), str(ef)], capture_output=True, text=True).returncode
    check("queued re-translation exits non-zero",
          run({"0": {"en": "fixed", "retranslate": True}}) != 0)
    check("nothing queued exits zero",
          run({"0": {"zh": "人手写的中文。"}}) == 0)

def test_preview_cleans_up():
    """preview() shells out per size with check=True; a failure used to escape
    before the temp dir was removed."""
    print("\nbake_subs: preview cleans up when ffmpeg fails")
    import tempfile as _tf
    made = []
    real_mkdtemp, real_sh = _tf.mkdtemp, bake_subs.sh
    def spy_mkdtemp(*a, **k):
        d = real_mkdtemp(*a, **k); made.append(d); return d
    def boom(*a, **k): raise subprocess.CalledProcessError(1, "ffmpeg")
    bake_subs.tempfile.mkdtemp, bake_subs.sh = spy_mkdtemp, boom
    try:
        try:
            bake_subs.preview("v.mp4", "s.srt", "Font", [22], 40, 10, "out.html")
        except Exception:
            pass
    finally:
        bake_subs.tempfile.mkdtemp, bake_subs.sh = real_mkdtemp, real_sh
    check("temp dir was created during preview", len(made) == 1, str(made))
    check("temp dir removed despite the failure",
          all(not pathlib.Path(m).exists() for m in made), str(made))

def test_preview_uses_absolute_timeline():
    """preview() seeks the UNCUT source with -copyts, so the frame keeps its
    absolute PTS. Hand it the re-based track and libass draws the sentence that
    sits at that number in the cut, over a frame from somewhere else -- off by
    exactly --start. Verified visually once; this locks it with a stub ffmpeg."""
    print("\nbake_subs: preview frame and subtitle share one clock")
    import os
    with tempfile.TemporaryDirectory() as d:
        w = pathlib.Path(d)
        srt = w / "full.srt"
        srt.write_text("1\n00:00:30,000 --> 00:00:35,000\nCUE030\n\n"
                       "2\n00:05:20,000 --> 00:05:30,000\nCUE320\n", encoding="utf-8")
        (w / "v.mp4").write_bytes(b"\x00" * 16)
        bindir = w / "bin"; bindir.mkdir()
        log = w / "argv.log"
        body = ("#!/bin/sh\n"
                'printf "%s\\n" "$@" >> ' + str(log) + "\n"
                'for a in "$@"; do\n'
                '  case "$a" in\n'
                '    subtitles=*) p=${a#subtitles=}; p=${p%%:*};'
                '      echo "---TRACK---" >> ' + str(log) + '; cat "$p" >> ' + str(log) + ' ;;\n'
                "  esac\n"
                "  out=\"$a\"\n"
                "done\n"
                'printf x > "$out"\n')
        fake = bindir / "ffmpeg"; fake.write_text(body); fake.chmod(0o755)

        env = dict(os.environ, PATH=f"{bindir}:{os.environ['PATH']}")
        subprocess.run([sys.executable, str(pathlib.Path(__file__).parent / "bake_subs.py"),
                        "--video", str(w / "v.mp4"), "--srt", str(srt), "--start", "200",
                        "--preview", "--preview-sizes", "22", "--preview-at", "320",
                        "--out", str(w / "p.html")], capture_output=True, text=True, env=env)

        args = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
        ss = args[args.index("-ss") + 1] if "-ss" in args else None
        track = "\n".join(args[args.index("---TRACK---") + 1:]) if "---TRACK---" in args else ""
        check("preview seeks the absolute time, not the cut-relative one",
              ss is not None and abs(float(ss) - 320.0) < 1e-6, f"-ss {ss}")
        check("preview is handed the track on that same absolute clock",
              "00:05:20,000" in track, repr(track[:120]))
        check("preview is NOT handed the re-based track",
              "00:02:00,000" not in track, repr(track[:120]))

def test_check_batches():
    """A truncated subagent reply is valid JSON covering half a batch. It has to
    be caught before build_srt.py turns the gap into unsubtitled sermon."""
    print("\ncheck_batches: a short batch is caught, not built")
    import check_batches
    def setup(d, zh_ids, blank=()):
        b = pathlib.Path(d) / "batches"; b.mkdir()
        (b / "batch_0.json").write_text(json.dumps(
            {"batch": 0, "sentences": [{"id": i, "start": i, "end": i+1, "en": "x"} for i in range(3)]}))
        (b / "batch_1.json").write_text(json.dumps(
            {"batch": 1, "sentences": [{"id": i, "start": i, "end": i+1, "en": "x"} for i in range(3, 6)]}))
        (b / "zh_0.json").write_text(json.dumps({"translations": [
            {"id": i, "zh": ("" if i in blank else "中文")} for i in zh_ids if i < 3]}), encoding="utf-8")
        (b / "zh_1.json").write_text(json.dumps({"translations": [
            {"id": i, "zh": ("" if i in blank else "中文")} for i in zh_ids if i >= 3]}), encoding="utf-8")
        return b

    with tempfile.TemporaryDirectory() as d:
        b = setup(d, range(6))
        check("a complete set passes", check_batches.main(str(b)) == 0)
    with tempfile.TemporaryDirectory() as d:
        b = setup(d, [0, 1, 2, 3])            # batch_1 truncated after one line
        check("a truncated batch fails", check_batches.main(str(b)) == 1)
        asked, per, got, blank = check_batches.load(str(b))
        check("the short batch is identified",
              sorted(set(asked) - got) == [4, 5] and asked[4] == "batch_1", str(sorted(set(asked)-got)))
    with tempfile.TemporaryDirectory() as d:
        b = setup(d, range(6), blank=[2])     # present but empty
        check("an empty translation counts as missing", check_batches.main(str(b)) == 1)
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "batches").mkdir()
        check("an empty directory is an error, not a pass",
              check_batches.main(str(pathlib.Path(d) / "batches")) == 2)

def test_halluc_loops():
    """Whisper pointed at the wrong language loops instead of failing. Those
    loops classified as speech and were translated and subtitled."""
    print("\nfilter_song: repeated-token loops are caught")
    import filter_song
    def kinds(texts):
        sents = [{"start": i*5.0, "end": i*5.0+4.0, "text": t, "n_words": len(t.split())}
                 for i, t in enumerate(texts)]
        return [x["kind"] for x in filter_song.mark(sents)]

    loop_en = " ".join(["Jesus'"] * 60)
    loop_de = " ".join(["Stunden"] * 60)
    phrase  = "it must be it " * 15
    real1   = "So let's welcome Pastor Hong with a huge round of applause."
    real2   = "I pray all these things in Jesus' name."
    real3   = "이 말씀은 탕자의 비유라는 말씀으로 굉장히 많이 알려져 있는 그런 성경 말씀 중에 하나입니다"
    k = kinds([loop_en, loop_de, phrase, real1, real2, real3])
    check("a single repeated token is caught", k[0] == "halluc", k[0])
    check("a foreign repeated token is caught", k[1] == "halluc", k[1])
    check("a repeated phrase is caught", k[2] == "halluc", k[2])
    check("real English is left alone", k[3] == "speech", k[3])
    check("repetition of a normal word is not a loop", k[4] == "speech", k[4])
    check("real Korean is left alone", k[5] == "speech", k[5])

    # short emphatic repetition is speech, not a loop
    k2 = kinds(["Amen amen amen.", "Yes yes yes!"])
    check("short emphatic repetition survives", all(x == "speech" for x in k2), str(k2))

def test_offset_staleness_guard():
    """Re-running prepare.py with a corrected start leaves the sentence files on
    the old clock. The resulting track passes every QA check and is silently out
    by the difference."""
    print("\nbuild_srt: refuses to build from a stale clock")
    import subprocess
    def run(marked_offset, meta_offset):
        with tempfile.TemporaryDirectory() as d:
            w = pathlib.Path(d); (w / "batches").mkdir()
            m = _marked([(0.0, 3.0, "speech")], offset=marked_offset)
            (w / "sentences_marked.json").write_text(json.dumps(m), encoding="utf-8")
            (w / "meta.json").write_text(json.dumps({"offset": meta_offset}), encoding="utf-8")
            (w / "batches" / "zh_0.json").write_text(
                json.dumps({"translations": [{"id": 0, "zh": "中文。"}]}), encoding="utf-8")
            r = subprocess.run([sys.executable, str(pathlib.Path(__file__).parent / "build_srt.py"),
                                str(w / "sentences_marked.json"), str(w / "batches"),
                                str(w / "o.srt")], capture_output=True, text=True)
            return r.returncode, (r.stderr or "") + (r.stdout or ""), (w / "o.srt").exists()

    rc, out, made = run(2481.0, 2481.0)
    check("matching offsets build normally", rc == 0 and made, f"rc={rc}")
    rc, out, made = run(0.0, 2481.0)
    check("mismatched offsets refuse to build", rc != 0, f"rc={rc}")
    check("nothing is written on refusal", not made)
    check("the error names both numbers and the drift",
          "0.0" in out and "2481.0" in out and "2481s" in out, out[:220])

if __name__ == "__main__":
    for t in (test_cjk, test_build, test_provenance, test_shift, test_range_server, test_apply_edits,
              test_no_overlap_ever, test_416_keepalive, test_apply_edits_exit_code, test_preview_cleans_up,
              test_preview_uses_absolute_timeline, test_check_batches,
              test_halluc_loops, test_offset_staleness_guard):
        try:
            t()
        except Exception as e:
            import traceback; traceback.print_exc()
            FAIL.append(f"{t.__name__} raised {type(e).__name__}")
    print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("failures:"); [print("  -", f) for f in FAIL]
    sys.exit(1 if FAIL else 0)

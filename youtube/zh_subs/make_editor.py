#!/usr/bin/env python3
"""Build the bilingual subtitle editor page for a sermon.

The page is a single static HTML file: it embeds the YouTube player, lists every
translated line beside its English source, lets a native speaker retime nothing
but rewrite anything, and exports one small JSON of just the changes. That JSON
is the only thing that has to survive -- `build_srt.py --edits` folds it back in.

    python3 make_editor.py <workdir> <video_id> [--title T] [--date D] [--serve]
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys, http.server, socketserver, functools, webbrowser

HERE = pathlib.Path(__file__).parent

# ---------------------------------------------------------------- flags
LATIN = re.compile(r"[A-Za-z]{3,}")

def load_flags(work, rows):
    """Which lines to surface first for a human check.

    Translators record their own doubts in flags.json; on top of that we flag
    lines whose shape suggests trouble even when nobody said so.
    """
    flagged, notes = set(), {}
    for bp in sorted((work / "batches").glob("zh_*.json")):
        for t in json.load(open(bp)).get("translations", []):
            if t.get("flag"):
                flagged.add(int(t["id"])); notes[int(t["id"])] = str(t["flag"])
    fp = work / "flags.json"
    if fp.exists():
        d = json.load(open(fp))
        flagged |= {int(i) for i in d.get("flagged", [])}
        notes.update({int(k): v for k, v in d.get("notes", {}).items()})
    for r in rows:
        zh, en = r["zh"], r["en"]
        if not zh.strip():
            flagged.add(r["id"]); notes.setdefault(r["id"], "no translation")
        elif LATIN.search(zh):
            flagged.add(r["id"]); notes.setdefault(r["id"], "untranslated English left in")
        elif len(en.split()) >= 12 and len(zh) <= 4:
            flagged.add(r["id"]); notes.setdefault(r["id"], "suspiciously short for the English")
    return flagged, notes

# ---------------------------------------------------------------- build
def build(work, video, title, date, out=None, media=None, media_offset=0.0):
    work = pathlib.Path(work)
    marked = json.load(open(work / "sentences_marked.json"))
    sents, off = marked["sentences"], marked.get("offset", 0.0)

    zh = {}
    for p in sorted((work / "batches").glob("zh_*.json")):
        for t in json.load(open(p))["translations"]:
            zh[int(t["id"])] = t.get("zh", "").strip()

    rows = []
    for i, s in enumerate(sents):
        if s["kind"] != "speech":
            continue
        v = int(s["start"] + off)
        rows.append({"id": i, "t": v,
                     "hhmm": f"{v//3600:d}:{v//60%60:02d}:{v%60:02d}",
                     "en": s.get("en", s.get("text", "")).strip(),
                     "zh": zh.get(i, "")})
    flagged, notes = load_flags(work, rows)
    for r in rows:
        r["flag"] = r["id"] in flagged

    skipped = sum(1 for s in sents if s["kind"] != "speech")
    heading = f"Chinese subtitle review &mdash; {title}" if title else "Chinese subtitle review"
    sub = (f"Heartbeat Church{', ' + date if date else ''}. Simplified Chinese (zh-Hans), "
           f"translated from the English sermon audio. {len(rows)} lines, "
           f"{skipped} skipped as worship or silence.")

    msize = (work / media).stat().st_size if media and (work / media).exists() else 0

    html = (HERE / "editor_template.html").read_text(encoding="utf-8")
    html = (html.replace("__ROWS__", json.dumps(rows, ensure_ascii=False))
                .replace("__VID__", video)
                .replace("__MEDIA__", json.dumps(media))
                .replace("__MOFF__", json.dumps(round(media_offset, 3)))
                .replace("__MSIZE__", json.dumps(msize))
                .replace("__TITLE__", f"Subtitle editor — {title or video}")
                .replace("__HEADING__", heading)
                .replace("__SUBTITLE__", sub))

    out = pathlib.Path(out) if out else work / "editor_zh.html"
    out.write_text(html, encoding="utf-8")
    print(f"lines        : {len(rows)}")
    print(f"flagged      : {len(flagged)}  ({sum(1 for r in rows if not r['zh'])} with no translation)")
    print(f"skipped      : {skipped} (song / hallucination)")
    print(f"player       : " + (f"local file {media}" if media else "YouTube embed")
          + (f"  ({msize/1e6:.0f} MB, " + ("held in memory" if msize <= 80e6 else "streamed") + ")"
             if msize else ""))
    print(f"wrote        : {out}  ({out.stat().st_size//1024} KB)")
    if notes:
        print(f"auto-flag reasons: " + ", ".join(sorted({v for v in notes.values()})))
    return out

def fetch_media(work, video, kind="audio"):
    """Pull a review copy of the sermon to play locally.

    Audio by default, and deliberately. The reviewer is checking whether the
    Chinese matches what was said -- the English is already on the screen beside
    it -- so the picture earns nothing and costs 250 MB. Re-encoded to 32k mono
    it is small enough for the page to hold the whole thing in memory, which is
    what makes every seek instant instead of a range request.

    Whole stream, not just the sermon: cutting to the sermon span would need a
    frame-accurate cut (a full re-encode) or the offset silently drifts and every
    timestamp lands in the wrong place. Not worth it to save a few MB of audio.
    """
    work = pathlib.Path(work)
    want = work / (f"{video}.review." + ("m4a" if kind == "audio" else "mp4"))
    if want.exists():
        print(f"review copy already here: {want.name} ({want.stat().st_size/1e6:.0f} MB)")
        return want.name

    rt = next((r for r in ("deno", "node", "bun") if shutil.which(r)), None)
    base = ["yt-dlp"] + (["--js-runtimes", rt] if rt else [])
    url = f"https://www.youtube.com/watch?v={video}"

    if kind == "audio":
        raw = work / f"{video}.rawaudio.m4a"
        if not raw.exists():
            print(f"downloading audio for {video} ...")
            subprocess.run(base + ["-f", "bestaudio[ext=m4a]/bestaudio",
                                   "-o", str(raw), url], check=True)
        print("re-encoding to 32k mono ...")
        # +faststart puts the index at the front; without it the browser has to
        # fetch the tail before it can report a duration or seek at all.
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(raw),
                        "-vn", "-ac", "1", "-ar", "44100", "-c:a", "aac", "-b:a", "32k",
                        "-movflags", "+faststart", str(want)], check=True)
        raw.unlink(missing_ok=True)
    else:
        print(f"downloading a 360p review copy of {video} ...")
        # H.264 explicitly: "ext=mp4" alone also matches VP9-in-MP4, which Safari
        # will not play, and the reviewer may not be on Chrome.
        subprocess.run(base + ["-f", "bestvideo[height<=480][vcodec^=avc1]+bestaudio[ext=m4a]/"
                                     "best[height<=480][vcodec^=avc1]/best[height<=480]",
                               "--merge-output-format", "mp4",
                               "-o", str(want), url], check=True)
    if not want.exists():
        sys.exit("yt-dlp/ffmpeg produced no file")
    print(f"got {want.name}  ({want.stat().st_size/1e6:.0f} MB)")
    return want.name


class RangeHandler(http.server.SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"          # avoid a new connection per range
    """SimpleHTTPRequestHandler with byte-range support.

    Without this, seeking a local video is broken: the browser asks for a range,
    the stdlib handler ignores it and returns 200 with the whole file, and the
    player has to buffer from the start to reach any point you click.
    """
    def send_head(self):
        rng = self.headers.get("Range")
        if not rng:
            return super().send_head()
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            return super().send_head()
        try:
            size = os.path.getsize(path)
            f = open(path, "rb")
        except OSError:
            self.send_error(404); return None
        m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
        if not m:
            f.close(); self.send_error(400); return None
        a, b = m.group(1), m.group(2)
        if a == "":                                   # suffix range: last N bytes
            start, end = max(size - int(b or 0), 0), size - 1
        else:
            start = int(a)
            end = int(b) if b else size - 1
        end = min(end, size - 1)
        if start > end or start >= size:
            f.close()
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers(); return None
        f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        return _Slice(f, end - start + 1)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def log_message(self, *a):
        pass                                          # the console is for our output


class _Slice:
    """Reads at most `remaining` bytes, so copyfile stops at the range end."""
    def __init__(self, f, remaining):
        self.f, self.remaining = f, remaining
    def read(self, n=-1):
        if self.remaining <= 0:
            return b""
        if n < 0 or n > self.remaining:
            n = self.remaining
        data = self.f.read(n)
        self.remaining -= len(data)
        return data
    def close(self):
        self.f.close()


def serve(path, port=8777):
    """Serve the folder over HTTP.

    Two reasons this is not optional. The YouTube IFrame API refuses a file://
    page, which has no origin. And a local video needs byte-range requests to be
    seekable, which the stdlib handler does not do -- see RangeHandler.
    """
    d = str(pathlib.Path(path).parent)
    h = functools.partial(RangeHandler, directory=d)
    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True
    url = f"http://localhost:{port}/{pathlib.Path(path).name}"
    with Server(("", port), h) as srv:
        print(f"\nopen {url}\n(ctrl-c to stop)")
        webbrowser.open(url)
        try: srv.serve_forever()
        except KeyboardInterrupt: print("\nstopped")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("workdir"); ap.add_argument("video")
    ap.add_argument("--title", default=""); ap.add_argument("--date", default="")
    ap.add_argument("--out", default=None)
    ap.add_argument("--media", default=None,
                    help="local video file to embed instead of the YouTube player "
                         "(path relative to the page); seeking is instant and there are no ads")
    ap.add_argument("--fetch", nargs="?", const="audio", choices=["audio", "video"],
                    help="download a review copy and play it locally instead of embedding "
                         "YouTube: 'audio' (default, ~25 MB, instant seeking) or 'video' (360p)")
    ap.add_argument("--media-offset", type=float, default=0.0,
                    help="second of the full video at which --media begins")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8777)
    a = ap.parse_args()
    media = a.media or (fetch_media(a.workdir, a.video, a.fetch) if a.fetch else None)
    p = build(a.workdir, a.video, a.title, a.date, a.out, media, a.media_offset)
    if a.serve:
        serve(p, a.port)

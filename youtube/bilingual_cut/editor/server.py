#!/usr/bin/env python3
"""Local editor for the cut plan.

Serves source.mp4 (with range requests, so the browser can scrub), the cut plan,
the diarization turns and the transcript, and writes edits back to disk. It has
to run locally: the source file is far too big to upload anywhere, and edits
need to land in the work directory.

    python server.py --work ../../work/1OmUbXks4mw
    open http://127.0.0.1:8420
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
BIN_MS = 10        # waveform resolution
CHUNK = 4 << 20    # cap for open-ended range requests


def build_peaks(work: Path, audio="audio16k.wav"):
    """One uint8 per 10ms: peak amplitude, for drawing the waveform."""
    out = work / "peaks.u8"
    src = work / audio
    if out.exists() and out.stat().st_mtime > src.stat().st_mtime:
        return out
    print("building waveform peaks...", flush=True)
    with wave.open(str(src), "rb") as w:
        sr, n = w.getframerate(), w.getnframes()
        pcm = np.frombuffer(w.readframes(n), dtype=np.int16)
    step = int(sr * BIN_MS / 1000)
    usable = (len(pcm) // step) * step
    peaks = np.abs(pcm[:usable].reshape(-1, step)).max(axis=1)
    peaks = (peaks / 32768.0 * 255).clip(0, 255).astype(np.uint8)
    out.write_bytes(peaks.tobytes())
    print(f"  {len(peaks)} bins -> {out}")
    return out


def make_handler(work: Path, video: str):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def handle_one_request(self):
            # Seeking a video aborts the in-flight range request; that is normal
            # and would otherwise spew a traceback per scrub.
            try:
                super().handle_one_request()
            except (ConnectionResetError, BrokenPipeError):
                self.close_connection = True

        def _send(self, body, ctype="application/json", code=200):
            if isinstance(body, str):
                body = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _file(self, path: Path):
            """Range-capable static serving - video scrubbing needs it."""
            size = path.stat().st_size
            ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
            rng = self.headers.get("Range")
            start, end = 0, size - 1
            code = 200
            if rng:
                m = re.match(r"bytes=(\d*)-(\d*)", rng)
                if m:
                    open_ended = not m.group(2)
                    if m.group(1):
                        start = int(m.group(1))
                        if m.group(2):
                            end = int(m.group(2))
                    elif m.group(2):
                        start = max(0, size - int(m.group(2)))
                        open_ended = False
                    # Chrome opens video with "bytes=0-". Streaming the whole
                    # 565MB into a socket it stops reading blocks the thread and
                    # the element just stalls; a 206 may legally be short, so
                    # cap it and let the client ask for the next window.
                    if open_ended:
                        end = min(end, start + CHUNK - 1)
                    end = min(end, size - 1)
                    code = 206
            length = end - start + 1
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            # An aborted 565MB stream leaves a poisoned entry that Chrome then
            # replays forever without re-requesting - the element just stalls.
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            if code == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                left = length
                while left > 0:
                    chunk = f.read(min(262144, left))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        # the socket is out of sync now; don't reuse it
                        self.close_connection = True
                        return
                    left -= len(chunk)

        def do_GET(self):
            p = self.path.split("?")[0]
            if p == "/":
                return self._file(HERE / "index.html")
            if p == "/api/state":
                return self._send(json.dumps(state(work, video)))
            if p == "/api/baseline":
                # the plan the editor started from (cutplan.json), ignoring edits
                src = work / "cutplan.json"
                return self._send(json.dumps(json.loads(src.read_text())["clips"]))
            if p == "/peaks.u8":
                return self._file(work / "peaks.u8")
            if p == "/video":
                return self._file(work / video)
            if p in ("/app.js", "/app.css"):
                return self._file(HERE / p.lstrip("/"))
            self._send("not found", "text/plain", 404)

        def do_POST(self):
            if self.path == "/api/log":
                n = int(self.headers.get("Content-Length", 0))
                print("[page]", (self.rfile.read(n) or b"").decode()[:4000], flush=True)
                return self._send(json.dumps({"ok": True}))
            if self.path != "/api/save":
                return self._send("not found", "text/plain", 404)
            n = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(n) or b"{}")
            clips = sorted((c for c in data.get("clips", []) if not c.get("deleted")),
                           key=lambda c: c["src_start"])
            t = 0.0
            out = []
            for c in clips:
                d = round(c["src_end"] - c["src_start"], 3)
                if d <= 0.05:
                    continue
                out.append({"id": len(out), "label": c.get("label", "sermon"),
                            "src_start": round(c["src_start"], 3),
                            "src_end": round(c["src_end"], 3),
                            "out_start": round(t, 3), "out_end": round(t + d, 3),
                            "duration": d})
                t += d
            dest = work / "cutplan_edited.json"   # never cutplan.json - that plan produced v3
            json.dump({"edited": True, "output_duration": round(t, 3), "clips": out},
                      open(dest, "w"), indent=1)
            self._send(json.dumps({"ok": True, "clips": len(out),
                                   "duration": round(t, 3), "path": str(dest)}))

    return H


def state(work: Path, video: str):
    plan_file = "cutplan_edited.json" if (work / "cutplan_edited.json").exists() else "cutplan.json"
    clips = json.loads((work / plan_file).read_text())["clips"]
    diar = json.loads((work / "diarization.json").read_text())
    segs = json.loads((work / "segments.json").read_text())["segments"]
    trans = json.loads((work / "translations_anchored.json").read_text())
    sections = json.loads((work / "sections.json").read_text())
    speaker = json.loads((work / "cutplan.json").read_text()).get("speaker", "SPEAKER_06")
    dur = max(t["end"] for t in diar["turns"])
    return {"clips": clips, "turns": diar["turns"], "segments": segs,
            "translations": trans, "sections": sections, "speaker": speaker,
            "duration": dur, "bin_ms": BIN_MS, "loaded_from": plan_file,
            "totals": diar.get("totals", {})}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--video", default="source.mp4")
    ap.add_argument("--port", type=int, default=8420)
    args = ap.parse_args()
    work = Path(args.work).resolve()
    build_peaks(work)
    ThreadingHTTPServer.daemon_threads = True
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(work, args.video))
    print(f"editor on http://127.0.0.1:{args.port}   (work: {work})", flush=True)
    print("saves to cutplan_edited.json - Ctrl-C to stop", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()

# Chinese Subtitles for an English Sermon (End-to-End)

Takes a YouTube sermon and produces **a Simplified Chinese subtitle track and a
subtitled video**. Everything runs on this machine and in this session: Whisper
locally, the translation done by you or subagents you spawn, ffmpeg for the
burn-in. No external translation service is used at any point.

Unless the user says they only want the SRT, run all the way through step 8c and
hand back the burned video -- that is usually what they actually need.

Target: subtitles ready **2-3 hours after the service is published**. The compute
is about 10 minutes; the rest is translation and your review.

## Input

The user provides:
- A YouTube URL or video ID
- The second the sermon starts (`sermon_start_seconds`), and optionally where it ends

If they give only a URL, find the sermon start yourself: transcribe nothing yet,
just check the stream for where the worship set ends and the preaching begins, or
ask. **Do not guess.** A wrong offset shifts every subtitle in the file.

### Important: nix-shell requirement

All CLI commands require nix-shell for FFmpeg and the Python venv. You MUST:
1. Source nix first: `source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null`
2. Run from the **repo root** (`/Users/charles/work/heartbeat`) so the venv activates correctly
3. Use `nix-shell shell.nix --run "..."` to wrap every CLI command

```bash
source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null && cd /Users/charles/work/heartbeat && nix-shell shell.nix --run "cd youtube/zh_subs && python <SCRIPT> <ARGS>"
```

`direnv` already does this when you `cd` in interactively, but a tool call gets a
fresh shell, so wrap every command.

Work happens in `youtube/work/<VIDEO_ID>/`.

## Steps

### 1. Fetch the audio and cut it to the sermon

```bash
python prepare.py ../work/<VIDEO_ID> <VIDEO_ID> --start <SECONDS> [--end <SECONDS>]
```

**If the video ID starts with a hyphen** (they often do -- `-BMLhFhfp24`), argparse
reads it as a flag and dies with "expected one argument". Use the `--` separator for
positionals and the `=` form for options:

```bash
python prepare.py ../work/-BMLhFhfp24 -- -BMLhFhfp24 --start 2481
python bake_subs.py --download=-BMLhFhfp24 --workdir=../work/-BMLhFhfp24 ...
```

Downloads DASH audio (never the muxed progressive format -- YouTube's SABR
rollout 403s that one) and writes a 16 kHz mono WAV plus `meta.json`.

On a 403, `yt-dlp` is stale: `python -m pip install -U -r youtube/subtitle_downloader/requirements.txt`.

### 2. Transcribe with word timestamps

```bash
python asr.py ../work/<VIDEO_ID>
```

mlx-whisper `large-v3-turbo` on Apple Silicon. Speed varies with the audio far
more than you would expect: **39x realtime** measured on a clean English sermon
(64 min in under two minutes), but only **5-10x** on a service with heavy singing,
or where Whisper is hallucinating because the language is wrong -- a loop costs
more decoding than speech does. Budget for the slow case. Falls back to
openai-whisper off Apple Silicon.

**If the preacher is not speaking English, pass `--language`.** Whisper pointed at
the wrong language does not fail: it loops, emitting the same token for a minute
at a time. Those loops classify as speech and get translated and subtitled. A
Korean guest sermon run through the default English path produced 168 such lines.

```bash
python asr.py ../work/<VIDEO_ID> --language ko     # or: --language auto
```

`filter_song.py` now catches these loops, but catching them is damage control --
the words are still lost. Check who is preaching before you start.

**Word-level timestamps are mandatory.** The next step derives sentence spans from
individual word timings because 45% of Whisper's own segments end mid-sentence.
`asr.py` aborts if it gets none rather than producing a silently mistimed track.

**Never run two transcriptions in parallel** -- it saturates the GPU and both
crawl. One sermon at a time.

### 3. Cut into sentences, then mark what is not speech

```bash
python sentences.py ../work/<VIDEO_ID>/asr_en.json ../work/<VIDEO_ID>/sentences_en.json
python filter_song.py ../work/<VIDEO_ID>/sentences_en.json ../work/<VIDEO_ID>/sentences_marked.json
```

`filter_song.py` separates sung worship (slow and long: ~1.2 words/sec over 13s)
from speech (~2.9 words/sec over 3.6s), and catches Whisper's hallucination loops
on silence (identical short text in adjacent sentences).

**Check its output before continuing.** Read the reported song and hallucination
spans and confirm they are really worship and silence. A spoken line swept into
the song block gets no subtitle at all.

### 4. Make the translation batches

```bash
python make_batches.py ../work/<VIDEO_ID>
```

Speech only, 200 sentences per batch, each carrying the tail of the previous one
as `context_before`.

### 5. Translate it yourself, or with subagents

**The translation is this skill's own work.** Do not call a third-party
translation API and do not add one -- the model running this pipeline is the
translator. That is what makes this a skill rather than a wrapper around
somebody else's endpoint, and it is why there is no API key to configure.

Read `youtube/zh_subs/TRANSLATION_BRIEF.md` -- it is binding -- and
`glossary_zh.json`. Spawn **one subagent per batch, all in parallel**;
translation is not CPU-bound, unlike transcription, so parallel is safe here. A
65-minute sermon is about 4 batches.

Give each subagent, inline in its prompt:
- the full text of `TRANSLATION_BRIEF.md`
- the full text of `glossary_zh.json`
- the contents of exactly one `batches/batch_N.json`
- the output path `batches/zh_N.json` and the shape
  `{"translations":[{"id":<int>,"zh":"<text>"}]}`

Tell it to return **every id it was given**, in order, and nothing else.

Rules that matter most:
- **Sentence by sentence, never word by word.** English and Chinese word order
  differ enough that translating fragments produces unreadable Chinese.
- **Be concise** -- the reader has ~9 characters per second.
- Quoted Scripture uses **和合本 (CUV)** wording.
- "shepherd" has **no fixed translation** -- it depends on context, and 牧师 is
  reserved for Pastor Josh. See `_ambiguous` in the glossary.
- The ASR contains errors. Translate the intended meaning; never invent.
- Ask the subagent to add `"flag": "<why>"` to any line it is unsure of. Those
  surface first in the review page.

**Confirm proper nouns with the user** before shipping names -- past mistakes
include Wonki (not Wongi) and Jason (not John). In practice the review in step 7
settles most of them for free: a reviewer correcting the English writes the names
out correctly as a side effect. Ask for the review first and only ask about the
names still standing afterwards.

### 5b. Check every batch came back whole

```bash
python check_batches.py ../work/<VIDEO_ID>/batches
```

A subagent that truncates its reply returns valid JSON covering only part of its
batch. `build_srt.py` will then build a track with a hole in it, and the hole is
a stretch of sermon with no subtitle at all -- which nobody notices until it is
on screen. This names the batch to re-run and exits non-zero, so it chains:

```bash
python check_batches.py ../work/<VIDEO_ID>/batches && python build_srt.py ...
```

Re-run the short batch rather than proceeding.

### 6. Build the track and QA it

```bash
python build_srt.py ../work/<VIDEO_ID>/sentences_marked.json ../work/<VIDEO_ID>/batches ../work/<VIDEO_ID>/sermon.zh-Hans.srt
python qa_srt.py ../work/<VIDEO_ID>/sermon.zh-Hans.srt
```

QA checks overlaps, line width (16 full-width chars, max 2 lines), reading speed,
empties and residual Latin. A handful of Latin hits is usually fine -- brand names
and English wordplay the preacher made a point of.

Report the coverage figure. Anything below ~99% means translations went missing.

### 7. Review (recommended, and the point of the whole design)

```bash
python make_editor.py ../work/<VIDEO_ID> <VIDEO_ID> --title "<SERMON TITLE>" --date "<D Month YYYY>" --fetch --serve
```

Opens a page with the sermon playing beside every line. Clicking a timestamp
seeks; both columns are editable. `--fetch` pulls a ~29 MB audio copy so seeking
is instant; `--fetch video` gets the picture instead. `--serve` is required --
the player needs a real origin and byte-range support.

Hand the URL to a native speaker. They press **Export edits** and give you the JSON:

```bash
python apply_edits.py ../work/<VIDEO_ID> <edits.json>
```

- Edited **Chinese** is used verbatim.
- Edited **English** means the ASR misheard, so the line is queued in
  `batches/retranslate.json`. Translate it and save `batches/zh_retrans.json`.
- Dropped lines get no subtitle.

Then rebuild:

```bash
python build_srt.py ../work/<VIDEO_ID>/sentences_edited.json ../work/<VIDEO_ID>/batches ../work/<VIDEO_ID>/sermon.zh-Hans.srt --overrides ../work/<VIDEO_ID>/overrides_zh.json
```

It warns if a line's English was corrected but no re-translation covers it,
rather than shipping the old Chinese under new English.

Two things to get right when re-translating the queue:

- **Check the seams, not the lines.** Most corrected lines are mid-sentence
  fragments that only work as joins -- `...超过你` / `所能想象。`. Translate each
  with its neighbours in view and then read the joins; one pair this run said
  "influenced" twice across the seam and read fine line by line.
- **The corrected English is the truth, except where the reviewer plainly missed
  one.** If they left an ASR error and context contradicts it, translate the sense
  and `flag` the line rather than silently following the text. `who's gonna live`
  next to "who's come to church" is *leave*; "a home that you will never have" is
  *never lose*.

Write the rebuilt track to a **new filename** (`sermon.zh-Hans.v2.srt`) if the
first one has already been handed over. Do not overwrite a delivered artifact.

### 8. Choose a burn-in style

**Look at the source before choosing anything.** Heartbeat burns its own English
captions into the broadcast, and where they sit decides placement:

- the spoken caption sits at **84.0%-87.4% of frame height**, bottom-anchored, so
  a two-line English caption grows upward and its bottom edge stays put;
- scripture slides fill the **left half** and reach down to ~92%.

Render the cross product and flip between the frames:

```bash
python preview_styles.py --video ../work/<VIDEO_ID>/<VIDEO_ID>.source.mp4 \
  --srt ../work/<VIDEO_ID>/sermon.zh-Hans.srt \
  --at 2000 3397 1450 2598 --sizes 14,18,22,26 --out styles.html
```

Pick the `--at` moments for **what is already on screen** -- a clean shot, one with
the spoken caption, one with a scripture slide -- not for what is being said. The
right answer differs between them. Buttons rather than a scrolling page, because
two points of font size is invisible side by side and obvious when frames swap in
place.

Three placements, and **"below the English" is not one of them**: the caption
leaves 36 script units of clear space and a two-line Chinese cue needs ~51 even at
size 22.

| | `--align` | `--margin` | |
|---|---|---|---|
| **above** | 2 | 50 | Chinese above the English, both readable. Crosses a scripture slide when one is up. |
| **over** | 2 | 30 | With `--mask-english`. Chinese replaces the English entirely. |
| **top** | 6 | 16 | Top of frame, clear of both. Unusual to read. |

Chosen on the 2026-08-09 Melbourne service: **above, box, size 18**.

### 8b. Burn it in

```bash
python bake_subs.py --video ../work/<VIDEO_ID>/<VIDEO_ID>.source1080.mp4 \
  --srt ../work/<VIDEO_ID>/sermon.zh-Hans.v2.srt \
  --start <SECONDS> --size 18 --margin 50 --border box --align 2 \
  --out ../work/<VIDEO_ID>/sermon.zh-subbed.mp4
```

`--start/--end` cut the video and re-base the subtitle track onto the cut in one
step, since the track is written in full-video time.

Roughly **10-22x realtime**; a 64.6-minute sermon at 1080p took about 7 minutes.

Three things that are easy to get wrong here, all verified by rendering a frame:

- **`FontSize` and `MarginV` are fractions of frame height, not pixels.** libass
  fixes the script at `PlayResY=288` whatever the source height, so size 22 is
  7.6% of the frame at 720p and at 1080p alike, and **a size chosen on a 720p
  preview holds on the 1080p master.** Treating the script resolution as the video
  height makes every margin wrong by 3.75x.
- **`Alignment` uses legacy SSA numbering.** 4 is "toptitle", 8 is "midtitle", so
  ASS-style `Alignment=8` lands middle-**left**. Top-centre is **6**.
- **A `BorderStyle=3` box cannot cover the English caption.** It is only as wide as
  its own text, so a longer English line pokes out both sides. `--mask-english`
  paints the band edge to edge first.

The font is chosen at runtime from the Simplified Chinese faces installed
(`Hiragino Sans GB W6` first). A missing family does not error -- libass draws
empty boxes and you only find out by watching, so do not hard-code one.

### 8c. Make a version that can actually be delivered

**CRF is quality-targeted, so its size varies with content.** The default CRF 20 at
1080p produced **1.04 GB** for 64.6 minutes. When someone is waiting on a download,
re-encode the finished bake -- do not re-render the subtitles:

```bash
# 1080p, ~430 MB
ffmpeg -i sermon.zh-subbed.mp4 -c:v libx264 -preset veryfast \
  -b:v 700k -maxrate 1200k -bufsize 2400k -pix_fmt yuv420p -c:a copy \
  -movflags +faststart sermon.zh-subbed.1080p-small.mp4

# 720p, ~290 MB
ffmpeg -i sermon.zh-subbed.mp4 -vf scale=1280:-2 -c:v libx264 -preset veryfast \
  -b:v 520k -maxrate 900k -bufsize 1800k -pix_fmt yuv420p -c:a aac -b:a 64k \
  -movflags +faststart sermon.zh-subbed.720p.mp4
```

Target the bitrate rather than the quality whenever a size has been quoted to
somebody -- `-b:v 700k` landed 428 MB against a 420 MB estimate.

## Deliverables

- `youtube/work/<VIDEO_ID>/sermon.zh-Hans.srt` -- the subtitle track (suffix the
  revision if an earlier one has already been handed over)
- `youtube/work/<VIDEO_ID>/sermon.zh-subbed.mp4` -- the burned video
- a delivery-sized re-encode of it (step 8c), which is usually the one they take

Plus the line count, coverage percentage, and any QA warnings you did not resolve.

## Notes

- **Uploading the SRT to YouTube as a caption track beats burning it in** for
  normal delivery: no re-encode, and viewers can turn it off. Burn in only when
  the player will not cooperate -- a projector fed from a file, or a re-upload
  somewhere that ignores `cc_load_policy`. Do not write to YouTube without asking.
- Embedded video clips inside a sermon (a testimony video, a news insert) need
  handling as a special case; their audio is not the preacher.
- **`yt-dlp -F`'s FILESIZE column is a peak-bitrate estimate and can be wildly
  high.** It predicted 1.65 GiB for the 720p track of a service stream that came
  down at 346 MB -- a service sits on static wide shots and compresses far below
  its quoted bitrate. Do not refuse a resolution on that column's say-so.
- **Uploading to Drive or GCS does not route around an uplink bottleneck.** If the
  recipient is on the tailnet and `tailscale status` shows their node as `direct`,
  the bytes already leave at full uplink speed; pushing to Google sends them up the
  same pipe first and adds a second download. The only lever is file size (8c).
- Serving over the tailnet works well for handing a large file to someone who is
  not at this machine: `tailscale serve --bg <port>` in front of a range-capable
  static server. Range support is required or the video will not seek.
- Disk fills fast. A 360p review copy is ~300 MB per sermon; clean up
  `youtube/work/<VIDEO_ID>/*.review.*` and `sermon16k.wav` when done. The WAV
  regenerates in seconds.

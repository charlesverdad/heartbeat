# Chinese Subtitles for an English Sermon (End-to-End)

Takes a YouTube sermon and produces **a Simplified Chinese subtitle track and a
subtitled video**. Everything runs on this machine and in this session: Whisper
locally, the translation done by you or subagents you spawn, ffmpeg for the
burn-in. No external translation service is used at any point.

Unless the user says they only want the SRT, run all the way through step 8 and
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

Downloads DASH audio (never the muxed progressive format -- YouTube's SABR
rollout 403s that one) and writes a 16 kHz mono WAV plus `meta.json`.

On a 403, `yt-dlp` is stale: `python -m pip install -U -r youtube/subtitle_downloader/requirements.txt`.

### 2. Transcribe with word timestamps

```bash
python asr.py ../work/<VIDEO_ID>
```

mlx-whisper `large-v3-turbo` on Apple Silicon, roughly **39x realtime** -- a
64-minute sermon takes under two minutes. Falls back to openai-whisper elsewhere.

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
include Wonki (not Wongi) and Jason (not John).

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

### 8. Burn the subtitles into the video

```bash
# choose a size first -- renders one frame per size, no encoding.
# --download caches the source as ../work/<VIDEO_ID>/<VIDEO_ID>.source.mp4
python bake_subs.py --download <VIDEO_ID> --workdir ../work/<VIDEO_ID> \
  --srt ../work/<VIDEO_ID>/sermon.zh-Hans.srt --preview

# then the real render -- same --download, so it reuses the file already fetched
python bake_subs.py --download <VIDEO_ID> --workdir ../work/<VIDEO_ID> \
  --srt ../work/<VIDEO_ID>/sermon.zh-Hans.srt --size 22 \
  --out ../work/<VIDEO_ID>/sermon.zh-subbed.mp4
```

About **22x realtime**, so a 64-minute sermon renders in roughly three minutes.

`--start/--end` cut the video and re-base the subtitle track onto the cut in one
step, since the track is written in full-video time.

The font is chosen at runtime from the Simplified Chinese faces installed
(`Hiragino Sans GB W6` first). A missing family does not error -- libass draws
empty boxes and you only find out by watching, so do not hard-code one.

Size is **not** inherited from the English burn-ins. English was settled at
FontSize 24; Chinese starts at 22 because full-width glyphs take more of the line.
Run `--preview` and judge it at the distance the congregation sits.

## Deliverables

Report paths for both:
- `youtube/work/<VIDEO_ID>/sermon.zh-Hans.srt` -- the subtitle track
- `youtube/work/<VIDEO_ID>/sermon.zh-subbed.mp4` -- the burned video

Plus the line count, coverage percentage, and any QA warnings you did not resolve.

## Notes

- **Uploading the SRT to YouTube as a caption track beats burning it in** for
  normal delivery: no re-encode, and viewers can turn it off. Burn in only when
  the player will not cooperate -- a projector fed from a file, or a re-upload
  somewhere that ignores `cc_load_policy`. Do not write to YouTube without asking.
- Embedded video clips inside a sermon (a testimony video, a news insert) need
  handling as a special case; their audio is not the preacher.
- Disk fills fast. A 360p review copy is ~300 MB per sermon; clean up
  `youtube/work/<VIDEO_ID>/*.review.*` and `sermon16k.wav` when done. The WAV
  regenerates in seconds.

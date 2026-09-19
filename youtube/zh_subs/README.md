# Chinese sermon subtitles (zh-Hans)

Produces a Simplified Chinese subtitle track for an English sermon, for broadcast
to a Chinese-speaking location. Output is an SRT to upload as a YouTube caption
track on the **existing published video** — nothing is re-encoded or re-uploaded.

## Why a caption track and not burned-in subtitles

Burning subtitles into a new video means re-uploading it, and YouTube's transcode
for a 45-minute video can take **1-3 hours** to reach 720p. That alone would miss
a 2-3 hour deadline, and burned-in text looks worst at exactly the low resolutions
that appear first. A caption track needs no transcode, and the player renders it
crisply at any resolution.

To make captions appear without anyone touching the CC button, give the receiving
site an **embed** URL rather than a watch URL:

    https://www.youtube.com/embed/VIDEO_ID?cc_load_policy=1&cc_lang_pref=zh-Hans

`cc_load_policy=1` forces captions on even if the viewer has them off.

## Pipeline

    ffmpeg -ss <sermon_start> -i service.mp3 -ac 1 -ar 16000 sermon16k.wav
    asr.py                 # mlx-whisper large-v3-turbo, word timestamps (~39x realtime)
    sentences.py           # re-cut into sentences with accurate spans
    filter_song.py         # drop sung worship and ASR hallucination
    (translate)            # Claude subagents, batched, see TRANSLATION_BRIEF.md
    build_srt.py           # lay each Chinese sentence across its English span
    qa_srt.py              # overlaps, line width, reading speed
    make_review.py         # bilingual HTML for a native speaker to check

## Design decisions worth keeping

**Translate whole sentences, never cues.** English and Chinese word order differ
enough that translating a subtitle-sized fragment produces unreadable Chinese. So
sentences are the translation unit, and the Chinese is only afterwards split into
cues across the span its English sentence occupied. Word timestamps exist to
re-time, not to translate.

**Whisper, not YouTube's auto-captions.** Measured on the same sermon, YouTube's
track had 68 filler words to Whisper's 2, a third of the commas, and 84% of cues
ending mid-sentence against Whisper's 45%. It also has no word timestamps. Whisper
costs under two minutes, so the shortcut saves nothing and loses the clause
structure a translator needs.

**Songs are detected by rate and length, not by repetition.** Preachers repeat
deliberately, so a repetition test flags rhetoric as lyrics. Measured separation:
sung lines run ~1.18 words/sec over ~13.4s, speech ~2.94 words/sec over ~3.6s. A
line must be slow AND long AND adjacent to another such line.

**CJK line-breaking is not English line-breaking.** 16 full-width characters per
line, 2 lines, break after Chinese punctuation, never begin a line with closing
punctuation. Reading speed capped near 9 characters/second.

## Known limitations

- A short spoken aside inside a worship block is swept up with the song and left
  unsubtitled. Acceptable while lyrics are on screen anyway.
- The end of the sermon is found by discarding Whisper's hallucinated tail; a
  sermon END offset is not yet recorded anywhere, only the start.
- Quoted Scripture depends on the translator recognising the quote. The glossary
  binds book names, but CUV verse wording is not looked up automatically.

## Reviewing and correcting a translation

The machine translation is a first draft. `make_editor.py` turns it into a page a
native speaker can actually work in: the sermon plays in one pane, every line sits
beside its English source in the other, and clicking a timestamp jumps the video
there. Both columns are editable.

```bash
python3 make_editor.py <workdir> <VIDEO_ID> --title "..." --date "..." --serve
```

`--serve` matters, for two reasons. The YouTube IFrame API refuses to talk to a
`file://` page, because that page has no origin. And a local media file needs HTTP
byte-range support to be seekable at all, which Python's stdlib handler does not
provide -- `RangeHandler` adds it.

### Playing from a local file instead of YouTube

The YouTube embed works, but every seek is a network round trip and YouTube may
put an ad in front of an unreleased sermon. Since reviewing means clicking
hundreds of timestamps, `--fetch` downloads a review copy instead:

```bash
python3 make_editor.py <workdir> <VIDEO_ID> --fetch --serve         # audio, ~29 MB
python3 make_editor.py <workdir> <VIDEO_ID> --fetch video --serve   # 360p picture
python3 make_editor.py <workdir> <VIDEO_ID> --media local.m4a --serve
```

**Audio is the default and that is deliberate.** The reviewer is checking whether
the Chinese matches what was said, and the English is already on the screen beside
it, so the picture earns nothing and costs about 250 MB. At 32k mono the whole
service is ~29 MB, small enough that the page fetches it once and plays it from a
blob -- so every seek is a local demux with no network at all.

Two things that are easy to get wrong here:

- `-f bestvideo[ext=mp4]` also matches **VP9-in-MP4**, which Safari will not play.
  The selector pins `vcodec^=avc1`, because the reviewer may not be on Chrome.
- Downloading only the sermon span would save a little more, but a cut that is not
  frame-accurate shifts every timestamp, and making it frame-accurate costs a full
  re-encode. The whole stream is downloaded instead and `--media-offset` stays 0.

Edits are held in the browser's own storage as you go and exported as one small
JSON of just the changes -- never the whole track. Three kinds of change, and the
distinction is the point of the whole thing:

| In the editor | What the pipeline does |
|---|---|
| you rewrite the **Chinese** | uses your wording verbatim, never re-translates over it |
| you rewrite the **English** | the ASR misheard, so the Chinese under it is wrong too: the line is queued for a fresh translation |
| you press **×** | no subtitle is emitted for that line at all |

Editing the English *after* fixing the Chinese re-queues the line; editing the
Chinese afterwards wins again. That is why each edit is stamped with a time.

Then fold it back in:

```bash
python3 apply_edits.py <workdir> edits.<VIDEO_ID>.json
# translate batches/retranslate.json -> batches/zh_retrans.json  (same batch format)
python3 build_srt.py <workdir>/sentences_edited.json <workdir>/batches out.srt \
        --overrides <workdir>/overrides_zh.json
```

`build_srt.py` refuses to be quietly wrong about this: if a line's English was
corrected by hand but no re-translation batch covers it, it says so instead of
shipping the old Chinese under the new English. It knows the difference because
`load_translations` records which batch file each string came from.

Hand-written Chinese still goes through `cjk.cues_for`, so a long correction is
wrapped and split into readable cues like anything else. You are writing the
words, not the timing.

## Baking subtitles into the video

Uploading a caption track is still the right default -- it needs no re-encode and
viewers can switch it off. Bake only when the player will not cooperate: a
projector fed from a file, or a re-upload somewhere that ignores `cc_load_policy`.

```bash
# choose a size first -- renders one frame per size, no encoding
python3 bake_subs.py --video sermon.mp4 --srt sermon.zh-Hans.srt --preview

python3 bake_subs.py --video sermon.mp4 --srt sermon.zh-Hans.srt --size 22
python3 bake_subs.py --download VIDEO_ID --srt sermon.zh-Hans.srt --start 2451 --end 6300
```

`--start/--end` cut the video and re-base the subtitle track onto the cut in one
step, because the track is written in full-video time while a cut file starts at
zero.

The font is picked at runtime from the Simplified Chinese faces actually installed
(`Hiragino Sans GB W6` first) rather than hard-coded. A missing family does not
error -- libass just draws empty boxes, and you would only find out by watching the
finished render.

Size is not inherited from the English burn-in. English was settled at FontSize 24;
Chinese starts at 22 because full-width glyphs occupy more of the line at the same
nominal size. Run `--preview` and judge it at congregation distance.

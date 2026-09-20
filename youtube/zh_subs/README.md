# Chinese sermon subtitles (zh-Hant)

Produces a **Traditional** Chinese subtitle track for an English sermon, for
broadcast to a Chinese-speaking location. Output is an SRT to upload as a YouTube caption
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

    prepare.py             # fetch DASH audio, cut the sermon span, write meta.json
    asr.py                 # mlx-whisper large-v3-turbo, word timestamps (~39x realtime)
    sentences.py           # re-cut into sentences with accurate spans
    filter_song.py         # drop sung worship and ASR hallucination
    make_batches.py        # split into batches of 200, carrying context across the seam
    (translate)            # Claude subagents, batched, see TRANSLATION_BRIEF.md
    check_batches.py       # every sentence came back? a truncated batch fails silently
    build_srt.py           # lay each Chinese sentence across its English span
    qa_srt.py              # overlaps, line width, reading speed
    to_traditional.py      # zh-Hans -> zh-Hant; this is what ships
    make_editor.py         # bilingual editor + a range-capable server, for a native check
    apply_edits.py         # fold the reviewer's edits back in
    preview_styles.py      # contact sheet of placements/sizes over real frames
    bake_subs.py           # only if a caption track is not an option (see below)

The translate step is done by Claude subagents, not by an external API. That is
the whole point of running it as a skill: the model driving the pipeline is the one
that translates, with `TRANSLATION_BRIEF.md` and `glossary_zh.json` in front of it.
No third-party translation service is involved, and none should be added here.

Every step runs inside the repo's nix shell:

    source /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
    nix-shell shell.nix --run "python youtube/zh_subs/asr.py ..."

## Tests

    nix-shell shell.nix --run "cd youtube/zh_subs && python test_pipeline.py"

The failure this guards against is not a crash -- it is a track that builds cleanly
and is two seconds out, or attached to the wrong sentence. Nobody catches that until
it is on a screen in front of a congregation. So the tests assert timing invariants
(no overlaps, no negative or zero-length cues, every cue inside its sentence span,
song and dropped lines emitting nothing) rather than diffing output files, plus the
edit-precedence rules and the byte-range server.

## Traditional, converted rather than re-translated

The congregation reads Traditional. They said so after watching a Simplified
burn-in they otherwise praised — and that second half decides the method.

Translation still happens in **Simplified**, and `to_traditional.py` converts as
the last step. One glossary stays authoritative, the reviewed wording is carried
over untouched, and the whole back catalogue can be converted without anyone
re-reading it. OpenCC's `s2tw` changes the script and not a single word choice;
`s2twp` would "localise" 軟件 to 軟體 and 信息 to 資訊, which is exactly the
wording that was approved, so it is not the default and should not become it.

Simplified merged several distinct Traditional characters, so this is not a table
lookup — 发 is both 發 and 髮, 干 is 乾 and 幹, 后 is 后 and 後, 只 is 只 and 隻.
OpenCC resolves these by phrase and gets them right. The one it misses is **里**,
which splits into 里 (the distance unit) and 裡 (inside): a 裡 whose preceding
word is absent from its phrase table stays 里, so `教會里面` comes out wrong while
`心裡面` comes out right. Every survivor is reported with context for a human to
glance at. On a real sermon there were eight, all `公里`, all correct.

Variant matters more than it looks: Taiwan writes **裡**, Hong Kong **裏**, and
that character appeared 76 times in a single sermon. `--variant tw` is the
default because Taiwan is the variant that was named; `--variant hk` is there.

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

### The frame is already occupied

Heartbeat burns its own English captions into the broadcast, so placement is not a
free choice. Measured on the 2026-08-09 Melbourne service:

- the spoken caption sits at **84.0%-87.4% of frame height**, bottom-anchored, so a
  two-line English caption grows upward and its bottom edge does not move;
- scripture slides fill the **left half** and reach down to ~92%.

That leaves **36 script units of clear space beneath the English caption**, and a
two-line Chinese cue needs about 51 even at size 22 -- so there is no "below the
English" option. Chinese goes above it, over it, or at the top of frame.

`preview_styles.py` renders the placement x border x size cross product over
several moments and puts them behind buttons, because two points of font size is
invisible side by side and obvious when the frames swap in place. Choose the sample
moments for what is already on screen, not for what is being said.

```bash
python3 preview_styles.py --video sermon.mp4 --srt sermon.zh-Hans.srt \
    --at 2000 3397 1450 2598 --sizes 14,18,22,26 --out styles.html
```

### libass geometry

Three things here were each wrong on the first attempt and settled by rendering a
frame and measuring it:

**`FontSize` and `MarginV` are fractions of frame height, not pixels.** libass fixes
the script at `PlayResY=288` whatever the source height. Size 22 is 7.6% of the
frame at 720p and at 1080p alike, so a size chosen on a 720p preview holds on the
1080p master. Assuming the script resolution was the video height made every margin
wrong by 3.75x.

**`Alignment` is legacy SSA numbering** -- 4 is "toptitle", 8 is "midtitle" -- so
ASS-style `Alignment=8` renders middle-**left**, not top-centre. Top-centre is 6.

**A `BorderStyle=3` box cannot mask the English caption.** It is only as wide as its
own text, so a longer English line pokes out both sides of it. `--mask-english`
paints the band edge to edge with `drawbox` first.

The font is picked at runtime from the Simplified Chinese faces actually installed
(`Hiragino Sans GB W6` first) rather than hard-coded. A missing family does not
error -- libass just draws empty boxes, and you would only find out by watching the
finished render.

```bash
python3 bake_subs.py --video sermon.mp4 --srt sermon.zh-Hans.srt \
    --start 1396 --size 18 --margin 50 --border box --align 2
```

`--start/--end` cut the video and re-base the subtitle track onto the cut in one
step, because the track is written in full-video time while a cut file starts at
zero.

### Sizing it for delivery

CRF is quality-targeted, so its output size varies with content: the default CRF 20
at 1080p produced **1.04 GB** for a 64.6-minute sermon. Re-encode the finished bake
-- do not re-render the subtitles -- and target the bitrate rather than the quality
whenever a size has been quoted to somebody. `-b:v 700k -maxrate 1200k` landed
428 MB against a 420 MB estimate; the same at 720p and `-b:v 520k` landed 291 MB.

# Farsi + Traditional Chinese Subtitles for an English Sermon

Produces **one burned video carrying two subtitle languages**: a Persian (Iranian
Farsi) line directly above a Traditional Chinese line, both at the bottom of the
frame. It is an extension of `/sermon-chinese-subtitles`: steps 1-6 (fetch, ASR,
sentences, song filter, batches, Chinese translation) are the same and are not
repeated here. Run those first, then continue below.

Like the Chinese skill, all translation is done by you or subagents you spawn.
No translation API.

## Who reads it, and the decisions already made

- **Chinese: one older viewer on the Gold Coast**, reading Traditional. Size
  matters more than anything else for her.
- **Farsi: an Iranian viewer** (requested 2026-10-25). Iranian Persian, not Dari.
- **The house style the user chose (2026-10-25):**
  - **Stacked at the bottom:** Farsi just above Chinese. The user compared it
    with Farsi at the top of the frame and kept stacked.
  - **VLC-style text:** white with a black outline and a soft drop shadow. No
    grey box.
  - **Exactly one line per language per cue.** Two lines of each would cover a
    third of the frame.
  - **Sizes:** ZH 90 / FA 94 on a 1080-line script. That is ~15% larger than
    the size-18 `bake_subs.py` burn she was reading before. Farsi gets a little
    more because its x-height is low.
  - **Fonts are bundled:** Noto Sans CJK TC Medium and Vazirmatn SemiBold.
- **Names:** Chinese keeps people's names in Latin, as the Chinese skill does.
  **Farsi transliterates them** (جولی کیم, کارمن جوی آیمز), because switching
  scripts mid-line is harder to read. The user approved this.
- **Farsi quotation marks are « »** (they look like `(( ))` on a phone). That
  is standard Persian punctuation, so keep them.
- **Burn in by default.** The user watches on a phone through Google Drive,
  which ignores embedded subtitle tracks. Soft subs in an MKV only work in
  VLC/IINA/mpv.

Still open: the **Persian Bible version**. OPV (ترجمهٔ قدیم) is provisional;
New Millennium (هزارهٔ نو) is the alternative. Ask the Iranian viewer. Farsi
also needs a native speaker's read before it ships widely.

## Steps

All commands are run as in the Chinese skill: inside `nix-shell` from the repo
root, then `cd youtube/zh_subs`.

### 0. Fonts (once per machine)

```bash
python fetch_fonts.py        # -> youtube/zh_subs/fonts/ (gitignored, ~16 MB)
```

libass on macOS cannot see PingFang. The only installed Traditional face is Heiti
TC Light, which is too thin. A missing family draws empty boxes rather than
erroring, so the burn always uses `fontsdir`.

### 1. Translate into Farsi

Use the same `batches/batch_N.json` files as the Chinese. Spawn one subagent per
batch (at most 2 Claude subagents in parallel). Give each one:

- `youtube/zh_subs/TRANSLATION_BRIEF_fa.md` (binding) and `glossary_fa.json`
- one batch file, and the output path `batches/fa_N.json` with the shape
  `{"translations":[{"id":<int>,"fa":"<text>"}]}`
- one line of context: speaker, passage, the Hebrew/Greek words they teach

The rules that matter most:

- **Christian, not Islamic, vocabulary.** Never الله, حضرت عیسی, نماز or مسجد.
- **OPV wording** for quoted verses.
- **Persian ی/ک**, never the Arabic forms.
- **کشیش is for Pastor Josh only.**

Then:

```bash
python check_batches.py ../work/<ID>/batches --lang fa
```

### 2. Build the bilingual cues

```bash
python build_bilingual.py ../work/<ID>/sentences_marked.json ../work/<ID>/batches \
  ../work/<ID>/sermon.fa-zhHant.cues.json
```

- Reads `zh_*.json` (Simplified) and converts it with OpenCC `s2tw`, as
  `to_traditional.py` does. Reads `fa_*.json` as is, normalised to Persian
  letter forms.
- A sentence too long for one line is cut into the same number of pieces in
  both languages, each at its own punctuation or word break, and timed by its
  share of the text. The two halves of a cue don't have to match word for word,
  because each viewer reads only their own line.
- Cues are in full-video time, and no two cues are ever on screen together.
- Each cue keeps its slice of the English (`en`), which the sync check uses.

### 3. QA: text, frames, sync

```bash
python qa_bilingual.py ../work/<ID>/sermon.fa-zhHant.cues.json \
  --frames ../work/<ID>/<ID>.source1080.mp4 \
  --sync 12 --audio ../work/<ID>/<ID>.audio.m4a \
  --outdir ../work/<ID>/qa_bilingual
```

- **Text** (fails the run on any of these): overlaps, empty lines, a line too
  wide for one line, Arabic letter forms, banned Islamic terms.
- **Text** (warns): cues over 1.25x the reading speed (ZH 9 chars/s, FA 17
  chars/s), cues under 0.7 s, and Simplified characters that survived.
- **Frames:** renders the widest Chinese, widest Farsi, fastest Chinese and
  fastest Farsi cues, plus an even sample, into `sheet_N.jpg`.
- **Sync:** transcribes the audio under N cues with Whisper base and reports
  how much of each cue's English is actually spoken there. A median under 60%
  fails the run and usually means a stale offset.

**You must look at the contact sheets** (Read each `sheet_N.jpg`). Code can't
check these:

1. Every line is on one line, nothing is clipped at the frame edge, and there
   are no tofu boxes (□).
2. Farsi reads right to left, with its punctuation on the left end. A line that
   starts with a Latin word must still lay out right to left.
3. The Chinese bottom line sits close to the frame's bottom edge (the user's
   standing preference). The Farsi line sits just above it without touching.
4. Both lines are big enough to read at phone size. If you are unsure, render a
   720p clip (step 4) and judge that rather than the full-size frame.
5. Collisions: a scripture slide's text, burned English captions (on Melbourne
   and Brisbane streams, at 84-87% of frame height), and the bottom-left camera
   inset on slide shots. Report any you see. Don't move the layout without
   asking.

Fix text problems in `fa_N.json` / `zh_N.json`, or with
`--fa-overrides overrides_fa.json`, then rebuild. For speed warnings, shorten
the translation. Don't stretch the timing.

### 4. Preview clip, then the full burn

Send the user a 2-3 minute phone preview first whenever the style or language is
new:

```bash
python bilingual_ass.py ../work/<ID>/sermon.fa-zhHant.cues.json ../work/<ID>/preview.ass \
  --start <S> --end <S+168> --video ../work/<ID>/<ID>.source1080.mp4 \
  --out ../work/<ID>/preview-fa-zhHant-720p.mp4 --height 720 --bitrate 900k
```

Then burn the sermon cut (same `--start/--end` as the Chinese cut):

```bash
python bilingual_ass.py ../work/<ID>/sermon.fa-zhHant.cues.json ../work/<ID>/sermon.fa-zhHant.ass \
  --start <SERMON_START> [--end <SERMON_END>] --video ../work/<ID>/<ID>.source1080.mp4 \
  --out ../work/<ID>/sermon.fa-zhHant.mp4
```

- `--layout split` puts Farsi at the top of the frame instead. The user
  rejected it on 2026-10-25, so use it only if asked.
- `--zh-size` / `--fa-size` / `--bottom` are pixels at 1080p. This script writes
  its own ASS with `PlayResY 1080`, unlike `bake_subs.py`'s 288-unit script.

Deliver as in step 9 of the Chinese skill: HBC Media › Translated Sermons,
named like `Heartbeat-<date>-sermon-fa-zhHant-1080p.mp4`. Never overwrite a
delivered file. Suffix the revision instead.

## Gotchas found the first time

- **Bidi:** without `Encoding -1` on the FA style, libass lays Farsi out left to
  right and the punctuation lands on the wrong end. Without the U+200F prefix
  (added by `bilingual_ass.py`), a line starting with "Heartbeat" or a name
  still goes left to right.
- **libass `Fontsize` is the font's line height, not its em size.** Noto CJK
  therefore renders ~20% smaller than Hiragino at the same number. Compare sizes
  by measuring glyphs on rendered frames, never by the number.
- **ffmpeg input seek resets the subtitle clock.** Single frames need `-copyts`
  so the full-video-time ASS lines up (`qa_bilingual.py` does this). The burn
  instead rebases the ASS onto `--start`.

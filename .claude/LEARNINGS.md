# Learnings

## Sermon blog pipeline (2026-07-24 batch run)

- **Camp / special-event streams live on the Gold Coast channel** (`@heartbeatgoldcoast2173/streams`), not the main `@HeartbeatChurch` channel. If a Sunday has no stream on the main channel, check there before concluding no service happened.
- **A "5-min read" = 1,000-1,250 words** (user-defined). Give writer subagents a hard cap; drafts at the older 1200-1800 target will need trimming.
- **`ghost-list-posts.mjs` only lists published posts.** To check for existing drafts, copy it and change the filter `status:published` → `status:draft`. Always check drafts before creating posts (use `ghost-publish.mjs --updateId <id>` to update in place).
- **Camp session numbering ≠ sermon numbering.** QLD camp 2026 had 4 sessions but only 3 sermons (Session 2 was prayer pathways). In posts, refer to "Saturday night's message" rather than "session N" to avoid clashing with YouTube video titles. Session 3 was split across two videos (worship video first, sermon video second) — embed the sermon video.
- **Pastor Josh's daughter is "Skye" and his wife is "Yoonah"** — confirmed by the user 2026-08-05. Some already-published posts spell her "Sky"; that spelling is wrong, and an earlier version of this file wrongly endorsed it from those posts. Do not derive name spellings from published posts. She and PM were commissioned as full shepherds on 2026-07-12.
- **`ghost-publish.mjs` cannot change the slug.** There is no `--slug` flag, and Ghost keeps the existing slug on `--updateId`. If the title changes after the draft is created, the slug stays stale and must be edited by hand in the Ghost editor's post settings. Settle the title before the first publish to avoid this.
- **Excerpts must not use AI teaser phrasing.** "lands closer to home", "the answer might surprise you", "what he said next" and friends were explicitly rejected. State the actual substance instead of promising a payoff. `/codex:rescue` is a good second ear for both excerpts and full-body deglazing — Codex catches contrast formulas ("not X, but Y") and uniform paragraph rhythm that the deglaze skill leaves behind.
- **A sermon that continues a previous week's message needs re-angling, not re-summarising.** The 2026-07-26 service finished the camp's "You Are Full" message, so the already-published post covered its first half. Check the prior post's beats and build the new one on the fresh material only.
- **Pastor Josh rarely announces a sermon title.** Look for the declaration he has the congregation repeat to each other, usually near the closing prayer — that line is the intended takeaway and makes the best title.
- **Effective batch flow:** transcribe strictly sequentially (Whisper saturates the machine), but run writer/deglaze subagents in parallel — they're not CPU-bound. Chain per post: write (fresh from transcript, never from old draft) → discrete deglaze pass → Ghost draft. Finish with a single cross-post cohesion pass (series threading, repeated hooks, names, word caps) and re-push only edited posts.
- **The deglaze pass reintroduces narration.** Deglaze optimises sentence-level prose and will happily rewrite instructive lines back into "he opened with / he remembered / the message closed in", plus flourishes like "could not resist the wordplay hiding in". After deglazing, re-audit for narration frames and delete them. Grep for: opened with, stopped the sermon, remembered, could not resist, put himself, finds the, the message closed, his warning is, admitted that, explained that.
- **Instructive ≠ third person.** The failure mode in these posts is narrating the *service* (he said, then we sang), not the choice of person. Teach the claim first, attribute second, and let `<blockquote>` carry his voice. Attributing by name twice in a whole post is plenty.
- **`ghost-publish.mjs` hardcodes `status: 'draft'` (line ~180).** Running it with `--updateId` against an *already published* post will UNPUBLISH it. Before any update, check the post's current status (`filter=id:<id>`, fields include `status`). For metadata-only tweaks on a live post, PUT just the changed field plus `updated_at` and omit `status` entirely.
- **YouTube downloads broke in Aug 2026 (SABR + n-challenge); fix is nightly yt-dlp + HLS.** The venv's pinned yt-dlp (2026.02.04) 403'd on every audio format, and the web clients returned "Only images are available". Working recipe: `python -m pip install -U --pre 'yt-dlp[default]'` (NOT plain `pip`, which resolves to nix's python and errors with "externally-managed-environment"), then `yt-dlp --js-runtimes node -N 8 -f 234 ...`. Format **234 is the HLS audio track** — the fragmented m3u8 download bypasses the 403 that kills the DASH formats (139/140/251) and progressive format 18. The nightly is what surfaces the m3u8 in the first place. Node 22 from `shell.nix` satisfies `--js-runtimes`; deno is not needed.
- **`yt-dlp[default]` pulls cffi 2.0.0 and breaks the venv.** Symptom: every `yt-dlp` invocation dies with "Version mismatch: this is the 'cffi' package version 1.17.1 ... we get version 2.0.0". Nix's python3.12 site-packages leaks onto the python3.11 venv's path. Fix: `python -m pip install --force-reinstall --ignore-installed --no-deps 'cffi==1.17.1'`. Plain `pip uninstall cffi` does not work — pip resolves the nix copy and refuses.
- **Always verify the audio is not silent before transcribing.** A 118-minute transcript that is nothing but "Thank you." every 30 seconds means silence, not a bad model. Check with `ffmpeg -ss <t> -t 20 -i <file> -af volumedetect -f null -` (digital silence reads -90.3 dB) and locate real content with `-af silencedetect=n=-50dB:d=5`. On 2026-08-16 the "Afternoon Service (16/8)" stream (`i3fL-cV2A-Q`) was silent for its entire 118 minutes except a 62-second pre-roll announcements reel at 31:15 — the church's stream itself was broken, across every format, so no download flag could recover it.
- **Heartbeat sometimes streams a second afternoon service.** It appears on `@HeartbeatChurch/streams` with a different title format ("Heartbeat Church Afternoon Service (16/8)") than the canonical "Heartbeat Church - Sunday Service DD/MM/YYYY". The pipeline wants the canonical morning stream. Cross-check the channel listing before committing to a URL a user pasted.
- **Livestreams can cut off mid-sermon.** The 16/08/2026 morning stream ends mid-sentence at 1:30:02 during the closing application. Compare the last transcript timestamp against the video duration; if they match and the sentence is unfinished, tell the writer subagent explicitly not to invent an ending.
- **When a Sunday stream is cut off or silent, check the Gold Coast channel for the source-campus stream.** On 2026-08-16 three recordings existed: `i3fL-cV2A-Q` (Sydney afternoon re-stream, silent for all 118 min), `R_3hCBJD2R4` (Sydney morning, good audio but cut off mid-sentence at 1:30:02, ~10 min before the sermon ended), and `bhwWFW-COwU` (Brisbane morning on `@heartbeatgoldcoast2173`, 99 min, complete). Pastor Josh was physically in Queensland, so the Gold Coast channel had the source feed. Prefer the campus he is preaching *from*; the relaying campus is the one that drops frames.
- **Verify a stream carries the whole sermon before writing, not after.** Compare the last transcript timestamp to the video duration, and read the final lines: an unfinished sentence at the very end means the stream died mid-message. The 16/08 Sydney recording cut off during the closing application, and the first draft invented a conclusion to fill the gap. Aligning two recordings is easy: grep a distinctive phrase from the end of the short one against the long one to find the splice point.
- **Use YouTube's current copy-paste embed markup verbatim; a hand-built iframe can throw player error 153.** The template previously used in this pipeline omitted `referrerpolicy="strict-origin-when-cross-origin"` (and the `title` attribute and `si=` share token), and the 2026-08-16 post hit error 153 until the exact string from YouTube's Share > Embed dialog was used. Append `&amp;start=<seconds>` to the src (HTML-escaped ampersand, since `si=` already occupies the query string). Ghost preserves the whole tag, `referrerpolicy` included, as long as it stays wrapped in `<!--kg-card-begin: html-->` / `<!--kg-card-end: html-->`.
- **A Sunday service may exist ONLY on the Gold Coast channel even when Pastor Josh preaches from Sydney.** On 2026-08-23 `@HeartbeatChurch/streams` had nothing newer than 16/08, while `@heartbeatgoldcoast2173/streams` carried the whole service as "Heartbeat Church QLD Sunday Service (August 23)". Josh was in Sydney (he apologised to "Melbourne and Queensland" on the multicampus feed), so the relaying campus was the only one that kept a recording. Always list both channels before concluding a Sunday was not streamed.
- **A dropped livestream leaves two videos with the SAME title on the same channel.** 23/08 had `pFOQ5H48e1k` (24 min) and `_UxOgJ8YxyY` (74 min). Neither title says part 1 or part 2. Order them by `release_timestamp`: the later one is the continuation, and `duration` of the earlier one roughly matches the gap between the two timestamps. The sermon is normally in the later, longer video (the earlier one is worship/announcements).
- **Verify audio in a few places, not just one.** `ffmpeg -ss <t> -t 15 -i <f> -af volumedetect -f null -` at ~6 points across the file takes seconds and rules out the silent-stream failure mode before committing to a 5-minute transcription.
- **`?start=<seconds>` alone is fine in the embed; the `si=` share token is not needed.** The error-153 fix was `referrerpolicy="strict-origin-when-cross-origin"` plus the `title` attribute, not `si=`. Do not fabricate an `si` value for a video you have not opened the Share dialog for.
- **The auto-mode permission classifier MAY block the Ghost publish command.** `set -a && source .env && set +a && node youtube/scripts/ghost-publish.mjs ...` was denied as an outward-facing action on 2026-08-23, but went through on 2026-09-07 when the user's request explicitly asked for the draft link and a `--dry-run` had been run first. Try it once; if denied, do not route around it — finish the draft locally, hand the user the exact command, and publish once they say so. Read-only Ghost calls (`ghost-list-posts.mjs`, draft listing, GET by id) have never been blocked.
- **Quote a named, living congregation member with care.** 23/08 contained "Deborah is not our vision. She is the Moses. She has to die." about a real member described from the front as sick and fragile. In the room, under the Moses typology, it means her ministry must reproduce; as a pull-quote under her first name it reads very differently. Render lines like this as prose that carries the meaning, keep the verbatim text in the `.meta.json` `editor_note`, and tell the user what you changed.
- **Never silently repair an ASR garble inside a `<blockquote>`.** The 23/08 transcript reads "When He says yes, that means He's waiting to give you the bigger yes" — plainly a mis-heard "no". The first draft fixed it to "no" and left it in quote marks, which puts words in the preacher's mouth. Either quote a clean line from elsewhere in the transcript or paraphrase outside the blockquote. Kimi caught this; the deglaze pass did not, because deglaze is told not to touch blockquotes.
- **Deglaze removes the glaze but leaves the machine rhythm.** After a deglaze pass the 23/08 draft still read as AI to the user. The residue Kimi named: every paragraph landing on a mic-drop fragment ("Water came anyway." "Jesus is enough."); self-commenting connectives that annotate the previous sentence ("That only makes sense if...", "That cuts close...", "That makes the death the achievement."); an identical claim -> gloss -> blockquote -> punch shape in every section; and specifics traded for summary gravity, which leaves the prose correct but weightless. Vary where sections land, and keep the sermon's concrete texture (the hilltop at Picton, "chucking a tantrum", the $100/$5 illustration) instead of compressing it out.
- **`/kimi:rescue` was broken against Kimi CLI 0.38.0 and is now patched.** The companion hardcoded `--quiet` (removed in 0.38) and `--yolo` (0.38 refuses it alongside `-p`), so every job died ~1s in with a usage error and reported only "failed". `kimi-companion.mjs` now probes `kimi --help` before passing `--quiet`/`--thinking` and retries without any flag the CLI names in an "unknown option" / "Cannot combine" error. Patched in both the plugin cache and the marketplace copy, with `.orig` backups; a plugin update will overwrite it.
- **To edit a post that is already PUBLISHED, use `youtube/scripts/ghost-update-body.mjs <postId> <htmlFile> [--apply]`.** It GETs the post, prints `status`/`updated_at`, and PUTs only `html` + `updated_at` with `?source=html`, never `status` — so the post stays published. `ghost-publish.mjs --updateId` would flip it back to draft. It dry-runs by default; `--apply` writes.
- **Verify a quote against the audio before printing it in quote marks.** Isolating the segment (`ffmpeg -ss <t> -t 40 ... -ac 1 -ar 16000 seg.wav`) and re-transcribing just that clip is ~20 seconds of work and settles what was actually said. On 23/08 it showed the closing line really is "When He says **yes**, that means He's waiting to give you the bigger yes" — a misspeak or a stubborn mis-hear either way, so the post now quotes a different, unambiguous line from 01:05:04. The same check confirmed the ages in his health testimony.

## Sermon blog pipeline (2026-09-07 run, Father's Day 06/09 service)

- **Both channels can carry the same Sunday; order them by `release_timestamp`.** 06/09 was on `@HeartbeatChurch` (`fI-q7V_c5NI`, live 10:54 AEST) and on `@heartbeatgoldcoast2173` (`2vojfF9VsS8`, live 15:27 AEST, an afternoon re-stream). When Josh preaches from Sydney the main-channel morning stream is canonical; the Gold Coast copy is only the fallback. `yt-dlp -j --skip-download` gives `release_timestamp` in seconds without downloading anything.
- **Format 140 (DASH m4a) still downloads, but slowly (~150 KiB/s, 11 min for 2h).** The venv's yt-dlp 2026.08.17 works with no `--js-runtimes`, only a deprecation warning. If speed matters, the HLS recipe (`--js-runtimes node -N 8 -f 234`) from the August note is faster.
- **Check blockquotes against the CLEAN transcript, not the timestamped one.** A 4-gram matcher run over the `[HH:MM:SS]` file scores real quotes at 0.0-0.5 because the stamps break every n-gram at a line boundary. Against the clean text the same quotes score 0.9-1.0.
- **Writer subagent output for this run: 1,206 words first try, no banned phrases, but thin in two sections and one quote cut mid-thought.** Reading the draft against the transcript yourself and patching content BEFORE deglaze is worth ten minutes; the deglaze agent then has the final content to work on and only touched prose (withheld-reveal beats, a rhetorical Q&A landing, an annotating appositive). Diff deglaze output sentence-by-sentence (`sed 's/\. /.\n/g'` on both files, then `diff`) before promoting it.
- **A second draft with the same title takes the `-2` slug, and the clean slug stays locked to the first post.** On 06/09 the Claude draft held `you-are-the-gatekeeper`, so the chosen Codex draft was created as `you-are-the-gatekeeper-2`. `ghost-publish.mjs` has no `--slug` flag, so freeing the clean slug means renaming or deleting the first post, then setting the slug by hand in the editor or with a direct PUT. When two drafts of one sermon are in play and the user may pick either, settle which post keeps the canonical slug before creating the second.
- **Ask for the speaker's slide deck before writing; its slide titles ARE the sermon outline.** On 06/09 the user supplied `Sermon of FLIC in fatherhood in Joshua.pdf` after the draft was done; `pdftotext -layout` (homebrew) extracts it in a second. The slide headers ("Crisis exposes the hidden qualities of man", "Vision to see the true reality / Positivity in faith in Christ", ...) beat any H2 invented from the transcript, and the deck also settles verse ranges and ASR doubts ("choose a leader" vs "a little"). Save the text next to the transcript as `<date>-slides.txt`.
- **The church moved from infant baptism to infant dedication (announced 06/09/2026).** Two babies were still "baptised" by pouring after the benediction that day. Keep it out of sermon posts unless the sermon is about it.
- **Pastor Josh's children: Skye (with husband PM, shepherds, starting a Tuesday-night house church), Nathan (son). All in their 20s as of Sept 2026.** ASR writes "Sky" and "Yuna"; fix to Skye / Yoonah in the clean transcript before the writer sees it.

## Bilingual (Korean + live interpreter) sermon cut — 2026-09-03

Pipeline lives in `youtube/bilingual_cut/`; see its README. Hard-won points:

- **Whisper detects language once per `transcribe()` call.** Useless for
  consecutive interpretation. Run the encoder + one decode step per VAD
  utterance (`mlx_whisper.decoding.detect_language`) to build a per-turn
  language map, then transcribe each language's regions in its own pass.
- **VAD threshold is the whole ballgame.** `silencedetect` at −32dB covered only
  54% of the audio and silently dropped ~12 minutes of real speech. Measure
  coverage at several thresholds before trusting it; −48dB/0.25s gave 82%.
- **Don't pad clip ends to hide VAD slop.** A 0.45s `pad_end` is exactly what
  makes you hear the interpreter's first syllables. Instead subtract the English
  utterances (widened ~0.35s at the head) out of every kept range. That both
  trims tails and removes English turns that gap-bridging had swallowed whole.
- **Never trust a bleed metric built from the English decode pass.** That pass
  emits segments over Korean audio too, often containing the *same Korean text*.
  Measure against the langid utterances instead — it was 115s, not 893s.
- **Only one MLX process at a time.** Stray processes from earlier retries don't
  error, they just contend for unified memory: 2–3x slowdown and silent kills.
  `pgrep` before launching, and checkpoint long jobs so a kill isn't fatal.
- **Anchor translations to source timestamps, not segment ids.** Re-segmenting
  is routine; positional ids make every existing translation worthless.
- **`+faststart` writes the moov atom last** — a killed render leaves an
  unplayable file, not a truncated one.
- **Splicing an external video**: drop the room-capture span in `sections.json`,
  then concat `before + video + after` in one ffmpeg pass with `split`/`asplit`
  and two `select` filters. Frame-exact, single encode, no intermediate files.
  Match `loudnorm` `input_i` between sources first.

### Correction: diarization, not language ID (same day)

The language-ID approach above is **wrong** for consecutive interpretation, and
the way it failed is worth remembering:

- `detect_language` pads each utterance to a 30s mel window using *surrounding*
  audio. A short English turn inside a Korean stretch therefore scores Korean.
  Roughly half the interpreter survived a cut that measured as clean.
- **The bleed metric was circular.** It counted "audio langid called English"
  inside clips the planner had built by subtracting "audio langid called
  English". It reported 0.00s while whole translated sentences were audible.
  A verification metric must come from a different signal than the one that
  produced the artefact.
- The fix: `pyannote/speaker-diarization-community-1` on MPS, 33x realtime for
  73 minutes. It asks who is speaking, not what language, so the interpreter is
  separated by voice. Identify which cluster is the speaker by Hangul ratio in
  the transcript text, and sanity-check against a span whose language you
  already know (an all-English announcement block: the speaker scored 0s there).
- Diarization is not perfect either - it merged a few short interpreter turns
  into the speaker's. Catch these by decoding each kept clip **in isolation**
  (`pcm[a:b]` alone, so nothing surrounds it) and flagging Latin-script output;
  subtract what you find and re-plan. Two passes took it to 0s.
- That per-clip isolated decode doubles as the clean transcript. The two-pass
  ko/en transcript is unusable for measurement because both passes emit text
  over the same audio.
- Verify the *rendered file*, not the plan: decode random windows of the output.

Env note: whisperx/pyannote live in `~/Documents/shepherds school` (nix + .pip).
`torchaudio` has no working backend there - read 16k PCM wav with `wave` +
numpy. Pass the HF token via `HF_TOKEN=$(tr -d '\n' < ~/.cache/huggingface/token)`.

### Local editor UI (web) — gotchas worth keeping

- **Use `localhost`, not `127.0.0.1`.** The Chrome extension cannot inject into
  the raw-IP origin, so screenshots fail with "script injection timed out".
- **A background Chrome tab throttles media preload**: `<video>` fires `stalled`
  and never issues a network request at all. Symptom looks like a broken range
  server; the server log showing *zero* requests is the tell. Focus the window.
  Synthetic clicks/keys also don't land in an unfocused window.
- **Pin canvas heights in CSS.** Setting `canvas.height` from `clientHeight`
  without a fixed CSS height re-lays the element out taller every frame until
  the page hangs — no console error, just "page busy".
- **Never stream an open-ended range in full.** Chrome opens video with
  `bytes=0-`; writing 565MB into a socket it stops reading blocks the thread.
  Cap open-ended 206s (4MB) and let the client ask for the next window. Send
  `Cache-Control: no-store` — an aborted giant response poisons the cache and
  Chrome then replays it forever without re-requesting.
- **Seeking before `loadedmetadata` throws**, and the throw aborts the rest of
  the caller — here it silently killed clip selection. Guard every seek.
- **Add an in-page self-test** (`?selftest=1`) that drives the real handlers and
  reports to the server console. It verified all 14 interactions when no
  synthetic input could reach the page.
- Two Claude sessions editing one directory corrupts it: a patch of one matched
  a line in the other's file and injected a call with no definition.

### v4: midpoint cuts (2026-09-09)

- pyannote's turn for the main speaker runs **~0.6s past his last sound** (median),
  while the interpreter's turn starts only ~0.15s before their first sound. So the
  diarized gap (median 0.35s) understates the acoustic silence (median 1.31s), and
  "cut at the midpoint of the diarized gap" lands safely inside real silence with
  ~0.75s after the phrase. Measure this before choosing a guard — the bars lie
  asymmetrically.
- When re-planning with `--exclude-verified`, pass **every** verify file. Renaming
  the first-pass results to `verify_pass1.json` silently dropped the 6 leak spans
  it held, and they came straight back in v4 pass 1. Now `--verified a,b,c`.
- The editor prefers `cutplan_edited.json` over `cutplan.json`; when swapping the
  baseline, move the user's edits aside by name (`cutplan_edited_v3.json`) — never
  delete them.

### v5: keeping a verbatim tail, and the OOM at the splice join (2026-09-09)

- `10_splice.py`'s single-pass `concat=n=3` **gets SIGKILLed by macOS jetsam** on a
  long insert. concat cannot emit segment 2 until segment 1 drains, so the whole
  inserted stream is buffered as raw frames: 140s of 720p30 is ~5.8 GB. It died
  twice at exactly `time=00:22:30`, right at the join. `10b_splice_parts.py`
  encodes the three pieces separately with identical parameters and joins them
  with the concat demuxer (`-c copy`); memory stays flat and the join is still
  frame-exact. Prefer it for any insert longer than a few seconds.
- A backgrounded `nohup ffmpeg ... &` inside a short-lived shell gets killed when
  the harness reaps that task. Make the long-running command **be** the background
  task (`run_in_background: true` on the ffmpeg/python call itself).
- `--insert-src` partitions clips by `src_end <= insert_src`. If the speaker's
  "let's watch the video" line survives the cut, the split point must sit **after**
  that clip, or the insert plays before its own introduction. Check for clips
  inside the `drop` span before rendering — one clip overlapping it is the tell.
- To keep a span verbatim in the audio but subtitle only one speaker, mark the
  section `mode: "all"` **and** make sure `segments.json` holds no segments for
  the other voices in that span. `05_render.py` adds every English segment that
  falls inside an `"all"` section to the English track, so an unfiltered
  `segments.json` will re-introduce the interpreter and the song lyrics.
- Hand-edited clip boundaries orphan translations: an anchor overlapping <50% of a
  re-cut segment leaves it untranslated. Re-check coverage after every editor save
  (24 body fragments were silent after the v5 edits).
- `11_subs_splice.py` lays two independently-timed cue lists together and leaves a
  few stranded fragments and overlaps. `12_subs_tidy.py` folds short ASCII tails
  back (working on a dual cue's **last line**, since the first lines are Korean),
  drops cues that are bare punctuation, and clamps what is left.

### Re-transcribing the rendered cut beats re-timing from source (2026-09-10)

- Subtitles built from source-time segments inherit the *source* segmentation. After
  hand-editing clip boundaries, an anchor that overlaps its re-cut segment by under
  50% drops out entirely: 24 body fragments went silent that way. Decoding the
  **finished file** (`20_retranscribe.py`) puts word-level timings on the output
  timeline, so nothing drifts and every gap is explicit.
- Carry the existing English across rather than re-translating: match each anchor's
  source span to the new ASR words, and the anchor inherits an exact output span.
  269 of 278 anchors re-timed this way; only 8 real gaps needed new prose.
- Measure the result on the cue windows, not on the timestamps: decode each cue's
  own span and compare to the cue text. Median match went 0.86 -> 1.00. A
  global "how far did cues move" metric said median 0.00s and hid everything —
  the errors were per-cue (p10/p90 of ±0.5s), not a fixed offset.
- An energy-onset detector is a poor alignment metric for continuous speech: it
  needs ~200ms of silence before each onset, so it matched under half the cues
  and could not separate good timing from bad. Don't report it as evidence.
- Whisper's language forcing matters per region. Forcing `ko` over a span where the
  congregation reads Scripture **in English** yields "3, 1, 2, 3 이 말씀은"; the same
  span forced to `en` gives the verse cleanly. Decode ambiguous spans both ways.
- Splitting a long cue strands short tails ("this.", "son?") in cues of their own.
  Split at 76 chars rather than 84 so a piece wraps to two lines, then fold any
  sliver under 0.65s back — including past terminal punctuation when the gap is
  under 60ms, which only ever happens mid-split.
- Two anchors can claim overlapping ASR words and land on the same instant; laying
  both out squashes the first to an unreadable 0.35s. Merge cues starting within
  0.35s of each other instead.

### Dubbing: candidate scan (2026-09-10)

- IndexTTS-2 is out on this machine: bilibili Model Use License and CUDA-only.
- Chatterbox (Resemble AI) fits: MIT, MPS support, zero-shot cloning from ~5s,
  `exaggeration`/`cfg_weight` for emotion. Scan found no network calls, no install
  scripts, no setup.py hooks, and `weights_only=True` on the model loads.
- Two things to know before installing it: `resemble-perth` is pulled from a git
  **branch** (`@master`), not a pinned commit, and `gradio` is a hard dependency
  you do not need for batch synthesis. Install into a throwaway venv.
- Every Chatterbox output carries Resemble's Perth neural watermark. Disclosed,
  and worth keeping for a cloned-voice deliverable.

### Dubbing proof of concept: results (2026-09-10)

- Chatterbox on MPS clones cross-lingually: a **Korean** reference produced fluent
  **English** in the same voice. Cosine similarity on Chatterbox's own voice
  encoder was 0.859 against the reference, versus 0.912 and 0.808 for two other
  real recordings of the same speaker and 0.696 for a genuinely different speaker.
  Treat the number as indicative, not proof: the encoder that scores it is the one
  that conditioned the generation, so the baselines are what make it meaningful.
- English runs *shorter* than the Korean it replaces: median spoken/slot ratio
  0.79 over 19 lines, so most lines need stretching, not squeezing, and a 1.35x
  squeeze ceiling was hit only once. Time-fitting per line with `atempo` (chained
  in 0.5-2.0 stages) kept every line inside its slot.
- Group cues into whole sentences before synthesis. Reading-sized cues make the
  TTS stop mid-clause and the prosody falls apart.
- Two environment traps: nix's `PYTHONPATH` leaks into a uv venv and breaks cffi
  (`env -u PYTHONPATH -u PYTHONHOME`), and `resemble-perth` needs `pkg_resources`,
  so `setuptools<81` — with setuptools 84 the watermarker silently becomes `None`
  and Chatterbox dies with `'NoneType' object is not callable`.
- `exec cmd | grep | tail` does not do what it looks like: the process vanished with
  an empty log. Run the command plainly and redirect to a file. Also, `tail -N` in a
  background pipeline buffers everything until exit, so there is no live progress.

## Chinese subtitles for English sermons (2026-09-17)

Goal: a zh-Hans subtitle track on a published sermon within 2-3 hours, for
broadcast to a Chinese-speaking location watching a YouTube link on a screen.

**Do not burn subtitles in.** It seems obvious for a room (nothing to enable,
you control the size) but it is the wrong call: burning in requires re-uploading,
and YouTube's transcode for a ~45 min video reaches 720p only after roughly 1-3
hours. That is the entire budget. Burned-in text also looks worst at the low
resolutions YouTube serves first. A caption track needs no transcode at all and
renders crisply at any resolution.

**The "someone has to press CC" objection is solvable.** An embed URL with
`cc_load_policy=1&cc_lang_pref=zh-Hans` forces captions on. Both parameters are
current. This removes the only real advantage burn-in had.

**YouTube already auto-translates into zh-Hans**, so there is a free baseline to
beat. It is beatable: its English ASR keeps filler ("um"/"uh": 68 vs Whisper's 2),
has a third of the commas, and 84% of its cues end mid-sentence versus Whisper's
45%. Machine translation is then fed sentence fragments. Note YouTube throttles
auto-translated tracks (HTTP 429 on repeat fetches) -- fine for a viewer, not
scriptable.

**Whisper is far cheaper than assumed**: mlx-whisper large-v3-turbo did 69.8 min
of audio in 107s, i.e. **39x realtime**. Do not estimate this from memory; an
earlier guess of 8 minutes was 4x too pessimistic and led to the wrong
architecture.

**Translate sentences, never cues.** Same lesson as the Korean bilingual cut.
English/Chinese word order differs too much for fragment translation. Re-cut the
ASR into sentences using word timestamps, translate those, then split the Chinese
across the English sentence's span.

**Detecting sung worship: use rate and length, not repetition.** A repetition
test flags a preacher's deliberate rhetorical repetition as lyrics (it flagged
"It's not the ground that is holy..." as song). Measured separation on a real
sermon: sung ~1.18 words/sec over ~13.4s; speech ~2.94 words/sec over ~3.6s.
Require slow AND long AND adjacent to another such line.

**Whisper hallucinates on silence** exactly as the transcribe skill warns:
"Thank you." repeated 12x on a ~30s cycle after the service ended. Detect by
identical short text in *adjacent* sentences; scattered "Right?" through a sermon
is real speech, not hallucination.

**CJK subtitles need their own wrapper**: 16 full-width chars/line, 2 lines,
break after Chinese punctuation, never start a line with closing punctuation,
~9 chars/sec reading speed. Sub-second cues cannot simply be stretched (there may
be no silence to borrow) -- merge them into a neighbour instead.

Code: `youtube/zh_subs/` (README there). Trial output for 2026-08-09:
`youtube/work/S-A7wyAHLxk/`.

## Subtitle review editor + local media playback (2026-09-19)

**Python's `http.server` has no Range support.** `SimpleHTTPRequestHandler` ignores
the `Range` header and returns 200 with the whole file, so an HTML5 `<video>`/`<audio>`
served from it cannot seek. `make_editor.py` carries a `RangeHandler` that adds 206
responses, `Accept-Ranges`, suffix ranges and 416. Also set
`protocol_version = "HTTP/1.1"` and use `ThreadingTCPServer`, or streaming media
blocks every other request on the page.

**Chrome will not load media in a hidden tab.** `visibilityState === "hidden"` means a
`<video>`/`<audio>` element never issues its network request at all: `readyState` stays
0, `networkState` stays 2 (LOADING), and **no error fires**. `fetch()` to the same URL
works fine in the same tab, which makes it look like a media/codec bug. Any browser
automation running in a backgrounded window cannot verify media playback, full stop —
diagnose with `document.visibilityState` before chasing codecs.

**`-f "bestvideo[ext=mp4]"` also matches VP9-in-MP4.** yt-dlp now offers VP9 with
`ext=mp4` (format 605), which Safari will not play. Pin `vcodec^=avc1` when the output
is for a browser you don't control.

**Progressive format 18 is the one SABR blocks.** It is tempting because it is already
muxed, but it 403s; DASH video+audio works. See [[ytdlp_sabr_hls_workaround]].

**For a review tool, download audio and prefetch it to a blob.** 32k mono AAC of a
110-minute service is 29 MB (vs 282 MB for 360p video). Small enough to `fetch()` once
and `URL.createObjectURL()`, after which every seek is a local demux with zero network —
faster than both YouTube and a range-served file. Pass `-movflags +faststart` or the
browser must fetch the file's tail before it can report a duration.

**Don't cut to the sermon span to save bytes.** A cut that isn't frame-accurate shifts
every timestamp; making it frame-accurate (`--force-keyframes-at-cuts`) costs a full
re-encode of the span. Download the whole stream and keep the offset at 0.

**Translation provenance matters.** When a human corrects the English, the Chinese under
it is stale. `build_srt.py`'s `load_translations` returns which batch file each string
came from, so a re-translation (`zh_retrans.json`) can be told apart from the stale
string it replaces. Without that the "needs re-translating" warning fires forever.

## Subtitle timing invariants and how they break (2026-09-19)

**Enforce a timing invariant in a pass that runs last and wants nothing else.**
`build_srt.py` checked for overlapping cues in the middle of `build()`, and then two
later passes — minimum-display extension and sliver merging — both moved cue ends past
the point that had just been validated. Every one of those passes has a readability
motive for making a cue longer; only a final pass with no competing motive can hold the
line. A randomised search over plausible sentence timings found a real overlap in
**4084 of 20000** runs against code that looked correct and passed a fixed example set.

Related: never write `max(<readability floor>, <hard ceiling>)`. That lets the floor win.
A cue that ends up too short is a smaller problem than two cues on screen at once.

**Fuzz timing code; example-based tests will not find this.** The failing shapes were
sentences 60–150 ms apart, which is ordinary fast speech (the sentence splitter only
needs a 60 ms gap) but is nowhere near what anyone writes into a fixture by hand.
Twenty lines of randomised span generation found in seconds what hand-written cases
missed entirely.

**`-ss` with `-copyts` seeks the *absolute* source position.** `-copyts` preserves the
seek target as the frame's PTS instead of rebasing to zero — it does not make `-ss`
relative to anything. So a preview that seeks an uncut video with `-copyts` must be
handed a subtitle track on full-video time. Give it the track already re-based onto a
cut and libass draws whatever sentence sits at that number in the cut, over a frame from
somewhere else entirely — misaligned by exactly `--start`, silently, in the one tool
whose whole job is letting a human eyeball the result. `bake()` does not use `-copyts`,
rebases to zero, and is correct with the re-based track.

To check alignment claims like this, render a synthetic video with `drawtext` showing
`%{pts:hms}` and an SRT whose text names its own timestamp. The frame then states which
second it came from and which cue was drawn on it; one look settles it.

**A hand-rolled HTTP response must frame its body.** The 416 branch in `make_editor.py`
sent no `Content-Length`. Under HTTP/1.1 keep-alive that means "read until the server
closes", and the server does not close, so the next range request on that socket has
ambiguous framing. `BaseHTTPRequestHandler.send_error()` gets this right (it sets
`Connection: close` and a real length) — anything written by hand alongside it has to
do the same. Browsers do request past EOF while buffering, so this was reachable just by
scrubbing near the end.

**`sys.exit(0 if f() == 0 else 0)` is not a conditional.** Both arms were `0`, so
`apply_edits.py` could not tell a caller that lines were still queued for re-translation.

**`/codex:review` and `/kimi:review` cannot be invoked by an agent.** Both set
`disable-model-invocation: true`, as do `status`, `result`, `cancel` and
`adversarial-review`; only `rescue` and `setup` are open. On an unattended run the
review step in CLAUDE.md silently does not happen unless you substitute
`feature-dev:code-reviewer` and say so.

## Burning Chinese subtitles into a broadcast that already has captions (2026-09-20)

Melbourne 09/08 service, `mjHAolwGpoA`. First end-to-end run through review, edits
and burn-in. Most of what follows was found by rendering a frame and looking at it,
after asserting something different.

### Latin text inside Chinese lines

**`cues_for` stripped every space in the line.** Right for Chinese, which does not use
spaces and picks up stray ones from the translator — and it welded names together, so a
man who introduces himself as Joshua Choi appeared as `我叫JoshuaChoi。`. Whitespace still
goes, except between two Latin word characters.

**Then the same bug in the other axis.** When no punctuation break fits, `wrap()` picks
the break by width alone, which is fine for Chinese and cuts Latin words in half:
`Practi / cing the Way`, `Na / than Choi`, `Kevin Ki / m`. Both fixes are one idea —
Chinese breaks anywhere, Latin does not.

The test for this has to be per word, not per adjacent character pair. `Kevin / Kim`
breaks at a space that `.strip()` then eats, so the two lines end `n` and begin `K` and
look identical to a mid-word cut. Assert instead that every Latin word in the source
survives whole on some line.

### libass geometry, measured rather than assumed

**PlayResY is 288 whatever the source height.** So `FontSize` and `MarginV` are
fractions of frame height — size 22 is 7.6% of it — and a size chosen on a 720p preview
renders identically on the 1080p master. Measured by rendering the same style twice: on
a 720p source `MarginV 38` put the box 91px up and `MarginV 10` put it 21px up, and the
28-unit difference is exactly 70px = 28 × 720/288. Assuming the script resolution was
the video height made every margin wrong by 3.75×.

**`Alignment` is read in legacy SSA numbering**, where 4 is "toptitle" and 8 is
"midtitle". ASS-style `Alignment=8` therefore renders middle-**left**, not top-centre,
because 8 carries no horizontal bit. Top-centre is 6.

### The church burns its own English captions into the broadcast

Two different overlays, and they constrain placement more than size does:

- the spoken caption sits at **84.0%–87.4% of frame height**, bottom-anchored, so a
  two-line English caption grows upward and its bottom edge stays put;
- scripture slides fill the **left half** and reach down to ~92%.

**There is no room beneath the English caption.** It leaves 36 script units of clear
space and a two-line Chinese cue needs about 51 even at size 22. The real options are
above it, over it, or top of frame — and "below" should not be offered.

**A `BorderStyle=3` box cannot mask anything.** It is only as wide as its own text, so
Chinese laid over a longer English line leaves the ends of that line poking out either
side. Covering the English needs the band painted edge to edge first (`drawbox`), which
is what `--mask-english` does.

### Choosing a style

Put the frames behind buttons, not down a page. Two points of font size is invisible
side by side and obvious when the frames swap in place. Pick the sample moments for
**what is already on screen** — clean shot, spoken caption, scripture slide — not for
what is being said; the right answer differs between them. `preview_styles.py` renders
the placement × border × size cross product for this.

### Reviewer edits

The reviewer's corrections doubled as proper-noun confirmation, which is worth more than
asking: Yoonah, Narae, Pios/Pius, Gold Coast (ASR "Cocos"), and "my wife" in place of a
mis-heard name. Ask for the review before asking about the names.

**Most corrected lines are mid-sentence fragments**, so check the seams, not the lines.
`…超过你` / `所能想象。` only works as a join. One pair said "influenced" twice across the
seam and read fine line by line.

**Where the reviewer leaves an ASR error uncorrected and context contradicts it, flag
it rather than silently follow the corrected English.** Two survived this run:
`who's gonna live` (parallel with "who's come to church" makes it *leave*) and `a home
that you will never have` (the sense is plainly *never lose*).

### Getting a big file to someone

**`yt-dlp -F`'s FILESIZE column is a peak-bitrate estimate and can be wildly high.** It
predicted 1.65 GiB for the 720p track of this stream; the file came down at 346 MB. A
service stream sits on static wide shots and compresses far below its quoted bitrate, so
do not refuse a resolution on that column's say-so.

**Uploading to Drive or GCS does not route around an uplink bottleneck.** When the
tailnet path is already `direct` (check `tailscale status`), the bytes leave the machine
at full uplink speed; pushing them to Google sends them up that same pipe first and adds
a second download. The only lever is file size.

**CRF is quality-targeted, so its output size varies with content.** CRF 20 at 1080p
produced 1.04 GB for 64.6 minutes. When a size has been quoted to someone, target the
bitrate instead: `-b:v 700k -maxrate 1200k` landed 428 MB against a 420 MB estimate.
Re-encode from the finished bake rather than re-rendering subtitles.

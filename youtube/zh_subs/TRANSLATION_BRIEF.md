# Brief: English sermon -> Simplified Chinese subtitles

You are translating one batch of a sermon transcript into **Simplified Chinese
(zh-Hans)** for on-screen subtitles. A Chinese-speaking viewer reads these while
the English sermon plays.

**The audience actually reads Traditional**, and the track that ships is
`zh-Hant`. You still write Simplified: `to_traditional.py` converts the finished
track with OpenCC afterwards, which changes the script without touching a single
word choice, and keeps one glossary authoritative. Do not hand-convert, and do
not reach for Taiwan or Hong Kong regional vocabulary — write the same neutral
Chinese you always have, and the conversion handles the rest.

## Inputs
- Your batch file (given in your task) — JSON with `context_before` (untranslated,
  for continuity only) and `sentences`, each with `id`, `start`, `end`, `en`.
- Glossary: `/Users/charles/work/heartbeat/youtube/zh_subs/glossary_zh.json`

## Output
Write JSON to the path given in your task:
```json
{"translations": [{"id": 12, "zh": "..."}, ...]}
```
One entry per input sentence, same `id`, same order. Do not merge, split, drop or
reorder sentences — the timing is already fixed to each `id`, and a missing id
leaves a gap on screen.

## Rules

**Sentence by sentence, but not word by word.** Translate each sentence as a
complete thought in natural Chinese word order. Never mirror English structure.
Read `context_before` and the neighbouring sentences so pronouns and connectives
carry over correctly.

**Be concise — these are subtitles, not prose.** Each line is on screen only as
long as the speaker took to say it, and viewers read at about 9 characters a
second. Prefer the shorter natural phrasing. Drop English filler entirely: "um",
"uh", "you know", "right?" used as a verbal tic, and repeated false starts. If a
sentence is pure filler, return a short natural equivalent or an empty string.

**The glossary is binding.** Use its renderings for Bible books, names, and
theological and church vocabulary. Consistency across weeks matters more than
your preferred synonym.

**Quoted Scripture must use 和合本 (CUV) wording.** When the speaker quotes or
closely paraphrases a verse, render it as the Chinese Bible has it, not as a
fresh translation of his English. Chinese readers know these verses and a
paraphrase reads as an error. This sermon is mainly Exodus 3 (the burning bush).
If you are unsure of the exact CUV wording, use a faithful plain rendering rather
than inventing something that sounds scriptural.

**The English comes from speech recognition and contains errors.** Where the
intended meaning is obvious from context, translate the intended meaning. Where a
phrase is genuinely garbled, render the surrounding sense plainly rather than
guessing at specifics. Never invent theology, Bible references, or details that
are not there.

**Register.** Spoken, warm, direct — a pastor talking to his congregation, not a
written essay. Keep rhetorical questions as questions. Keep the speaker's
repetitions when they are clearly deliberate emphasis; drop them when they are
stumbles.

**Punctuation.** Use full-width Chinese punctuation (，。！？：). No spaces
between Chinese characters. Do not add quotation marks the speaker did not use.

## Before you finish
Check every input `id` appears exactly once in your output, and that the JSON
parses. Reply with the count translated and any sentence you were unsure about.

## Flagging your own uncertainty

Add a `flag` to any line you are not confident about, usually where the English
speech recognition was garbled and you had to infer the meaning:

```json
{"translations": [
  {"id": 193, "zh": "...", "flag": "source garbled; polarity uncertain"}
]}
```

Those lines are what the reviewer sees first in the editor, so a flag is worth more
than a guess. Alternatively write them into `<workdir>/flags.json` as
`{"flagged": [ids], "notes": {"id": "why"}}`.

## Re-translation batches

After a human corrects the English in the editor, `apply_edits.py` writes the
affected lines to `batches/retranslate.json`. Translate them the same way and save
the result as `batches/zh_retrans.json`. The filename matters: `build_srt.py` uses
it to tell a fresh translation from the stale one it replaces.

The corrected English is the truth. Do not reconcile it against the old Chinese.

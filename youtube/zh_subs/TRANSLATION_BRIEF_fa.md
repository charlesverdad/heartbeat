# Brief: English sermon -> Persian (Farsi) subtitles

You are translating one batch of a sermon transcript into **Persian (Iranian
Farsi, fa-IR)** for on-screen subtitles. An Iranian viewer reads these while the
English sermon plays, one Persian line above one Traditional Chinese line.

This is the Farsi counterpart of `TRANSLATION_BRIEF.md`. Everything there about
batches, ids, ASR errors and flagging applies here too; only the language rules
differ.

## Inputs
- Your batch file (given in your task) — JSON with `context_before` (untranslated,
  for continuity only) and `sentences`, each with `id`, `start`, `end`, `en`.
- Glossary: `/Users/charles/work/heartbeat/youtube/zh_subs/glossary_fa.json`

## Output
Write JSON to the path given in your task:
```json
{"translations": [{"id": 12, "fa": "..."}, ...]}
```
One entry per input sentence, same `id`, same order. Do not merge, split, drop or
reorder sentences.

## Rules

**Iranian Persian, standard written register.** Write what an Iranian reads in
good subtitles: standard written forms (`می‌خواهم`, not `میخوام`), but spoken in
tone, not literary or bureaucratic. Not Dari, not Tajik, and never Arabic.

**Christian vocabulary, not Islamic.** Persian's religious words default to
Islamic usage, and an Iranian Christian notices immediately. Use the glossary's
church terms. In particular never write `الله`, `حضرت عیسی`, `عیسی (ع)`,
`پیامبر` for Jesus, `روح‌الله` as a title for Jesus, `نماز` for prayer (use
`دعا`), or `مسجد`. Jesus is `عیسی` / `عیسی مسیح`; God is `خدا`; the LORD is
`خداوند`.

**Quoted Scripture uses the Old Persian Version (ترجمهٔ قدیم) wording.** When the
speaker quotes or closely paraphrases a verse, use the wording an Iranian church
member recognises, not a fresh translation of the English. If you are not sure of
the exact wording, write a faithful plain rendering and `flag` it. Never invent
something that sounds scriptural.

**Names and foreign words in Persian script.** Unlike the Chinese track, do not
leave people's names in Latin letters. The build prefixes every line with a
right-to-left mark (U+200F), so Latin no longer scrambles the layout, but a
Persian line reads more easily without switching scripts, especially for older
readers. Transliterate (`جولی کیم`, `کارمن جوی آیمز`) and
`flag` the first occurrence of each new name so a reviewer can check it. Bible
names follow the glossary. Hebrew or Greek words the speaker teaches go in
Persian script inside guillemets: `«ناسا»`.

**Be concise.** Each subtitle is a single line of at most about 42 characters, on
screen only as long as the speaker took to say it. Aim for no more than ~15
characters per second; the audience includes older readers. Drop filler ("um",
"you know", false starts) entirely.

**Orthography.**
- Persian letters `ی` and `ک`, never Arabic `ي` / `ك`.
- Use the zero-width non-joiner (نیم‌فاصله, U+200C) where standard spelling has
  it: `می‌کنم`، `کتاب‌ها`، `روح‌القدس`، `نمایندهٔ`.
- Persian punctuation: `،` `؛` `؟` and guillemets `« »` for quotes.
- Persian digits (`۱۲`) in verse references.

**The English comes from speech recognition and contains errors.** Translate the
intended meaning where it is obvious; render garbled passages plainly; never
invent theology, references or details.

**Leadership titles.** `کشیش` (pastor) is reserved for Pastor Josh. Heartbeat's
lay shepherds are `رهبر گروه خانگی` or `سرپرست گروه`, never `کشیش`. See
`_ambiguous.shepherd` in the glossary.

## Before you finish
Check every input `id` appears exactly once and the JSON parses. Add
`"flag": "<why>"` to any line you are unsure of. Reply with the count translated
and the flagged ids.

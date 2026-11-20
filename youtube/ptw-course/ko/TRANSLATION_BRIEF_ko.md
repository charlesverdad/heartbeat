# Brief: Practicing the Way course -> Korean subtitles

You are translating one batch of an English course video transcript (Practicing
the Way, Session 06 "Healing from Sin", John Mark Comer and guests) into
**Korean** for burned-in subtitles. A Korean viewer reads one Korean line, shown
directly above one Traditional Chinese line.

## Inputs
- Your batch file: JSON with `context_before` (do not translate; continuity only)
  and `sentences`, each with `id`, `start`, `end`, `en`.
- Glossary (binding): `/Users/charles/work/heartbeat/youtube/ptw-course/ko/glossary_ko.json`

## Output
Write JSON to the path given in your task:
```json
{"translations": [{"id": 12, "ko": "..."}, ...]}
```
One entry per input sentence, same `id`, same order. Never merge, split, drop or
reorder sentences.

## Rules
- **Register:** natural spoken Korean in 해요체/합니다체 mix as a Korean pastor
  would teach on video; consistent within the batch (default to 해요체 for the
  speaker's direct address, e.g. "~해요", "~거예요"; 합니다체 is fine for
  formal statements). Not literary, not stiff translationese.
- **Protestant vocabulary:** 하나님 (never 하느님), 예수님, 성령님, 교회, 기도.
- **Scripture:** when a verse is quoted or closely paraphrased, use the 개역개정
  wording a Korean churchgoer recognises. If unsure of exact wording, write a
  faithful plain rendering and add a `flag`. Never invent scripture-sounding text.
- **Names:** Hangul transliteration (standard 외래어 표기법), glossary forms win.
  Flag the first occurrence of any name not in the glossary.
  "Practicing the Way" (the course/book name) stays in Latin letters.
- **Concise.** The subtitle is on screen only as long as the speaker took to
  say it. Aim for ≤ 8 Hangul syllables per second of (end - start). Drop filler
  ("you know", "like", false starts). Prefer shorter phrasing over completeness
  of every adverb. Do not add explanations.
- **Punctuation:** Korean standard: `.` `,` `?` `!`, quotes as “ ” or ' '.
  Do not end every line with a period if it reads fine without; be consistent
  (use sentence-final periods).
- **The English is speech recognition output** of clean studio audio — mostly
  correct. Translate the intended meaning; flag anything that looks garbled.
- No line breaks inside a translation.

## Before you finish
Validate: every input id appears exactly once, JSON parses (run
`python3 -c "import json;json.load(open('<out>'))"`). Add `"flag": "<why>"` to
lines you are unsure of. Reply with the count translated and the flagged ids
with reasons.

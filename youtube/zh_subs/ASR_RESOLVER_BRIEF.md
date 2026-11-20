# ASR resolver brief

You are correcting a Whisper transcript of a Heartbeat Church sermon **before** a
human reviews it. The human (Charles) wants to correct as few lines as possible.
Your job is to fix what the context makes clear, and to turn every remaining doubt
into a short multiple-choice question for him.

You get `asr_review.md`: every spoken line as `<id> [time] <text>`. Lines marked
`**` contain words Whisper was unsure of, shown as `{?word?}`. Under them, `alt`
lines are a second model's hearing of the same audio, primed with church names.
Unmarked lines can be wrong too. Whisper is often confidently wrong about names,
Hebrew and Greek words, and Bible references.

## What to fix

- **Mishearings only.** Wrong words, names, places, Bible books and verse numbers,
  and phrases that make no sense where a near-homophone does ("watching the sun
  growing up" → "son"; "Harpete Church" → "Heartbeat Church").
- **Use the whole sermon.** A name spelled right on line 300 fixes it on line 12.
  A verse quoted in the passage reading tells you what a garbled paraphrase was.
  A running joke or a repeated phrase tells you what a garbled copy was.
- **Quoted Scripture:** when the speaker is clearly reading a verse, match the
  wording of the version he is reading, as far as the audio allows. Do not
  replace his paraphrase with a Bible translation.
- **Known names:** see `asr_vocab.txt`. "Pastor" is a title only Pastor Josh
  holds; others are shepherds. Don't promote anyone.

## What NOT to change

- Spoken style: "gonna", "um", repetitions, false starts, run-on sentences,
  grammar slips. Subtitles translate the meaning; fixing grammar costs the
  reviewer a diff to check and gains nothing.
- Sentence boundaries and line ids. One fix replaces one line's text.
- Anything you can't support from the audio hearings or the context. Never
  invent content to make a line read better.

## Confidence

- `high`: the context or the second hearing makes it near certain, e.g. the church
  name, a name used elsewhere, the passage being read, an obvious homophone.
  It is applied without asking. Be honest: a wrong `high` is worse than a `low`.
- `low`: probably wrong, but you can't be sure. Give your best guess as `en`
  and 1-3 alternatives in `options`. Each option is a full replacement line.
  **Include the original ASR text as one option** if it is plausible.
- `unclear`: you can't recover the sense at all. Leave `en` as the ASR text.
  Charles will listen.

## Output

Write JSON to the path you are given, and nothing else:

```json
{"fixes": [
  {"id": 12, "en": "Welcome to Heartbeat Church.", "confidence": "high",
   "why": "church name"},
  {"id": 44, "en": "And our pastoral team, Yoonah, me, and Deborah ...", "confidence": "low",
   "why": "'you and I' doesn't fit a list of names; Yoonah is on the team",
   "options": ["And our pastoral team, you and I, me, and Deborah ..."]}
]}
```

Only list lines you change or doubt. Keep `why` under 15 words. It is shown
to the reviewer on a phone.

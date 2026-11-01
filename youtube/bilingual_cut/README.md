# bilingual_cut

Tools for turning a consecutively-interpreted (Korean speaker + English translator)
service recording into a Korean-only cut with English subtitles.

Pipeline stages each read/write JSON in the work directory, so any stage can be
re-run without redoing the expensive ones. **Every segment keeps its original
source timestamps** (`src_start` / `src_end`) alongside its position in the
output timeline (`out_start` / `out_end`), so timings can be re-adjusted later.

    01_vad.py         audio -> utterance boundaries      -> vad.json
    02_langid.py      utterances -> per-utterance lang   -> langmap.json
    03_transcribe.py  lang regions -> bilingual segments -> segments.json
    04_plan.py        segments + sections -> cut plan    -> cutplan.json
    05_render.py      cut plan -> mp4 + srt

Repair / splice stages, run as needed:

    07_repair.py      re-decode Whisper loop segments     -> segments.json
    09_subs.py        report translation coverage         -> translate_new_NN.json
    10_splice.py      cut + external video -> spliced mp4 -> splice.json
    11_subs_splice.py shift + merge subs for the splice   -> subs_*_v2.srt

Run them via `pipeline.py` or individually. All paths are relative to a
`--work` directory containing `source.mp4`.

## Not cutting into the interpreter

The whole point of the cut is that you never hear the translator. Two settings
in `04_plan.py` do that work:

* `--guard` (0.35s) - every kept range has the English utterances subtracted
  from it, widened by this much at the head. A Korean clip therefore always
  stops at least 0.35s before the interpreter's first syllable, even when
  gap-bridging would otherwise have merged straight through an English turn.
* `--pad-end` (0.12s) - generous end padding is what makes tails bleed. Keep it
  small; the guard is what protects genuine pauses.

`mode: "all"` sections are exempt from the subtraction, so deliberately-kept
English (guest intro, benediction) survives intact.

Verify with: for every clip in a `ko` section, the overlap against
`langmap.json` English utterances should be 0.

## Splicing in a video that was played in the room

When the service plays a pre-recorded video, the room capture is usually not
worth keeping. Add the playback span to `sections.json` `"drop"`, then feed the
clean file to `10_splice.py`, which concatenates
`before + video + after` in a single ffmpeg pass (frame-exact, one encode).
Match the levels first - compare `loudnorm` `input_i` on both and pass the
difference as `--gain-db`. Then run `11_subs_splice.py` to push every cue after
the join later by the insert duration and lay out the video's own lines.

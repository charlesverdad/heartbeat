# Cut editor

Nudge the clip boundaries of the sermon cut by hand, listening as you go.

    ../../../venv/bin/python server.py --work ../../work/1OmUbXks4mw
    open http://localhost:8421

Use **localhost**, not 127.0.0.1 — the Chrome extension cannot inject into the
raw-IP origin, and Chrome throttles media preload in a background tab, so keep
the window focused or the video will sit at 0:00 without ever requesting.

## What you see

* **Left** — every kept clip with its Korean text. Click to select.
* **Waveform** — the pauses you are cutting to.
* **Green band** — the clip. Drag either edge, or nudge with the buttons/keys.
* **Blue lane** — the speaker you are keeping (Hong). **Red lane** — everyone
  else. A clip should never overlap red; the header warns when it does.
* **Bottom strip** — the whole service, for jumping around.

## Keys

`←` `→` clip · `[` `]` pick edge · `J` `L` nudge (`⇧` for 0.5s) · `space` play ·
`↵` play clip · `P` audition the current edge · `C` play the cut from here ·
`A` toggle **Play kept only** · `D` drop/restore · `⌘S` save.

**Play kept only** is the preview. While it is on, every way of playing — space,
the native controls, scrubbing, Clip, Edge — stays on the green: reaching the end
of a clip jumps to the next one, landing in red skips forward. Turn it off to
hear the raw audio across an edge. The setting is remembered.

## Saving and exporting

Save writes `cutplan_edited.json`. It never touches `cutplan.json`, and the plan
that produced v3 is kept read-only in `v3_locked/`. **Revert all to v3** restores
that snapshot if an edit goes wrong.

To turn saved edits into a video:

    ../../../venv/bin/python ../15_export.py --work ../../work/1OmUbXks4mw \
        --out sermon_korean_cut_v4.mp4

## Self-test

`http://localhost:8421/?selftest=1` drives the real handlers (select, nudge,
snap, drop, keys) and reports pass/fail to the server console — useful because
synthetic input from outside the page does not always reach it.

# Burn-in style for the Practicing the Way course

Chosen by rendering real frames from session 01 and looking at them, not from
the numbers. The settings live in `run_stage4.py`; this is why they are what
they are.

## What the footage does

The course cuts between four kinds of shot, and a subtitle has to survive all
of them:

| | what it looks like | what it costs a subtitle |
|---|---|---|
| **talking head** | speaker standing full-body against a pale plaster wall | most of the runtime; bottom of frame is floor, so a low cue is clear of the subject |
| **motion-graphic card** | cream ground (~`#EFEBE2`), faint grid, muted terracotta and green display type | white text is **invisible** here without a backing |
| **letterboxed B-roll** | 2.39:1 cinematic footage, black bars top and bottom | dark; a low cue lands on the bar or the picture's bottom edge |
| **seated interview** | warm ochre backdrop, subject centred | lap and chair occupy the lower frame |

The cards also place text in many positions — left, right, centre — and several
carry an **attribution or label low in the frame**, around 88–92% of frame
height. There is no band that is empty in every shot, so "never overlaps
anything" is not achievable; the aim is to sit where the design puts least.

## The settings

```
--font "Heiti TC" --size 17 --margin 18 --border box --back &H78000000 --outline 1.6 --align 2
```

**`Heiti TC`, and this one is not a preference.** `fc-list` matches **zero**
fonts for PingFang, so libass cannot see the face macOS would otherwise be the
obvious choice — naming `PingFang TC` draws empty boxes and does not error, the
exact failure the sermon skill warns about. Of what fontconfig does expose,
`Heiti TC` is the only Traditional **sans**; `Songti TC` is a serif and reads
literary against this design. Verified by rendering: 隨, 穌, 會, 確 all come out
in Traditional forms, no tofu.

**Size 17, against the sermon pipeline's default of 22.** The sermon default is
tuned for a bright, busy stage wash. This design is quiet and low-contrast, and
a cue at 22 shouts over it. Remember `FontSize` is a fraction of frame height,
not pixels — libass fixes the script at `PlayResY=288` — so 17 holds if these
are ever re-rendered at 1080p.

**Margin 18** puts the block's bottom edge at about 94% of frame height, which
tucks it *under* most of the cards' own low-sitting attributions rather than
colliding mid-band. It still crosses one occasionally; that is the residual
cost of a fixed position, and the backing keeps it legible as a separate layer
when it happens.

**`--back &H78000000`, a softer box than the `&H60000000` default.** The leading
byte is transparency, not opacity, so a higher number is lighter. The default
box is legible but reads as a hard slab against a cream card; 0x78 sits back
into the picture while still carrying white text over both cream and dark. The
flag was added to `bake_subs.py` for this.

A box rather than an outline, because the cream cards defeat an outline — CJK
strokes are thin and the counters fill with background.

## What was rejected

- **No backing at all.** White text disappears on the cream cards. This is the
  single constraint that decides the whole style.
- **Top of frame.** Clear of the floor, but the cards put their headings and
  running numerals up there.
- **Following the sermon pipeline's "above the English" placement.** That exists
  to clear Heartbeat's own burned-in captions. This course has none, so the band
  is free and there is nothing to sit above.

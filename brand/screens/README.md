# Heartbeat Screens

Full-screen screens for the projector and the livestream, as a static site (Cloudflare Pages). Each page
is one self-contained file once built: it works offline from a USB stick. No frameworks.

Open a screen, set it up in the panel, press F for full screen. H (or Minimise) hides the panel; click
anywhere to bring it back. Copy link saves your setup as a URL (add `?autostart` to start on open and
open minimised). `?demo` runs a self-looping preview with no panel (used for homepage thumbnails).

Currently: `countdown` (welcome countdown, Timer or Until a time). Links from the old single-file
countdown (`?min`, `?at`, `?bar`, `?theme`, `?big=0`, `?m=A|B`, `?autostart`) keep working.

## Commands

    npm install          # puppeteer-core, for the check only
    npm run dev          # serve src/ on :8790 (PORT to change); pages work unbuilt
    npm run build        # src/ -> dist/ (single-file pages + _headers)
    npm test             # node --test: core + settings
    npm run check        # build, then load every page at 5 sizes x 2 themes; screenshots in out/

`check` fails on any page/console error or sideways overflow, and expects Chrome at
`/Applications/Google Chrome.app` (or `CHROME=...`). Look at `out/*.png` yourself too.

Cloudflare Pages: build command `npm run build`, output directory `dist`, root `brand/screens`.
`dist/_headers` sets the security and cache headers.

## Layout

    src/<name>.html          one page per screen (page CSS + script tags)
    src/screens/<name>.js    the screen's behaviour
    src/shared/              brand.css, core.js, logo.js (generated), settings.js, stage.js, panel.js, timer.js, fonts/
    scripts/gen-logo.mjs     regenerates logo.js from brand/assets/heartbeat-lockup-white.svg
    build.mjs                inlines local <link rel=stylesheet href> and <script src>, fonts as data URIs

Shared scripts are classic scripts that attach to `globalThis.HB` (so they inline into a page and load
in node tests). Page script order: core, logo, settings, stage, panel, (timer), then the screen.

## Adding a screen

1. Create `src/<name>.html`: copy `countdown.html`; keep `<link rel="stylesheet" href="shared/brand.css">`
   (rel before href), a `<main class="stage">`, and the script tags in order. Screen-only CSS goes in a
   `<style>` in the page. Size everything off the stage with `cqw`/`cqh`; use `.portrait` (set by
   `HB.watchStage`) for tall windows. Never pulse the logo.
2. Create `src/screens/<name>.js` (an IIFE). Define a schema and call `HB.panel`:

        const schema = [
          { key: 'heading', type: 'text', label: 'Heading', default: 'Starting soon', param: 'h' },
          { key: 'show', type: 'check', label: 'Start time', text: 'Show it', default: false, param: 'show' },
          { key: 'at', type: 'time', label: 'At', default: '11:00', param: 'at', inline: true, when: v => v.show },
        ];
        const panel = HB.panel({ id: '<name>', title: '<Name> settings', schema,
          onChange(key, values) { /* redraw */ } });
        HB.watchStage(stage, ({ W, H, portrait }) => { /* measure */ });
        HB.loop(t => draw(t, panel.values));

3. Add the link to `src/index.html` (the homepage), and `check` picks the page up automatically.
4. Run `npm run build && npm run check`, then open the PNGs in `out/`.

### Schema fields

`{ key, type, label, param, default, when, inline, ... }`. Types: `seg` (`options: [[value, label]]`),
`check` (`text`), `number` (`min`, `max`, `unit`), `time` ("HH:MM"), `text`, `lines` (list of line-lists,
edited in a textarea, one `m=` style param per item with lines joined by `|`). `when(values)` hides a
row; `inline: true` puts the field on the previous row. Theme (Dark/Light) is added to every screen
(`HB.THEME` can be placed explicitly to choose its position). Link booleans are `1`/`0`; links list
only values that differ from defaults. Merge order: defaults < saved (localStorage) < link params.
List values from a link are for that visit only.

### Panel API (`HB.panel(opts)`)

Options: `id`, `title`, `schema`, `legacy(out, params)` (extra link rules), `linkKeys(values)` (keys always
written to Copy link), `skipSave`, `startable` (adds "Start on open", honours `?autostart`),
`actions` (`[{id, label, primary, onclick}]`, right-aligned in the footer), `keys` (`{ ' ': fn, r: fn }`
by lower-case `e.key`), `keyHelp` (`[['Space','start / pause']]`), `onChange(key, values)`, `enter()`,
`linesHelp`. Built in: F, H, Esc, L, click to show, double-click full screen, toast, wake lock.
Returns `{ values, set(key, v), setAction(id, {text, disabled}), toast(msg, ms), show(open), keepAwake(), demo, autostart }`.
In `?demo` there is no panel DOM, storage or keys, and `setAction`/`toast` do nothing, so guard nothing.

### Countdown engine (`timer.js`, for any screen that counts down)

`HB.timerSchema` (kind / mins / at rows), `HB.timerLegacy` (old `?at`/`?min` links), `HB.timerLinkKeys`,
`HB.createTimer({ values, onChange, keepAwake, badTime })` giving `start() reset() retarget() refresh()
button() frame()` where `frame()` is `{ idle, t, COUNT, n, phase, done }`, and `HB.rollClock(el)` which
returns `set(n, phase)` for the rolling digits. See `screens/countdown.js` for the wiring.

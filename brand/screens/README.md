# Heartbeat Screens

Full-screen screens for the projector and the livestream, as a static site (Cloudflare Pages). Each page
is one self-contained file once built, so it works offline from a USB stick. No frameworks.

## The screens

| Page | Screen | For | What it does |
|---|---|---|---|
| `countdown.html` | Welcome countdown (the hero) | Projector | Messages take turns, the timer counts down, the logo lands at zero. Count minutes or to a start time. |
| `ring.html` | Ring countdown | Projector | A quieter countdown: the mark inside a ring that empties as time runs out. |
| `starting-soon.html` | Starting soon | Livestream | Before going live when there is no exact time; can show "We go live at 11:00". |
| `be-right-back.html` | Be right back | Livestream | A break or technical hold, with an optional back-in timer. |
| `loading.html` | Loading | Any | While a feed, slide or stream comes up; four loader styles. |

`index.html` is the homepage: live thumbnails (`<page>.html?demo` in an iframe), how to use, keyboard.

## How to use

1. Open a screen and set it up in the panel. Press Start if it counts down.
2. Press F for full screen (F11 on Windows).
3. Minimise (H) hides the panel; click anywhere to bring it back.
4. Copy link saves your setup as a URL: bookmark it, or use it as a ProPresenter web view or OBS browser source.
   Add `?autostart` to start on open with the panel hidden.
5. "Download for offline" on the homepage (or save the page) gives a single file that needs no internet.

`?demo` runs a self-looping preview with no panel, storage or keys (used for homepage thumbnails).

## Keyboard

Space start / pause (timer screens) - R reset - F full screen (or double-click) - H hide / show panel -
Esc hide panel - L light / dark - Up / Down add or take off a minute (welcome countdown).

## Links and parameters

Only values that differ from the defaults appear in a copied link. Booleans are `1` / `0`. Every screen
takes `theme` (`dark` | `light`), `demo`, and `autostart` where it has Start. Merge order: defaults <
saved in the browser < link params.

| Screen | Params |
|---|---|
| Countdown | `kind` (`minutes` / `until`), `min`, `at` (HH:MM), `bar` (`top` / `bottom`), `big` (last 10 s), `m` (messages: lines joined by `|`, one `m=` per message). Old links `?min`, `?at`, `?bar`, `?theme`, `?big=0`, `?m=A|B`, `?autostart` still work. |
| Ring | `kind`, `min`, `at` (as the countdown), `label` (default "Service begins in") |
| Starting soon | `h` (heading), `show` (show start time), `at` (HH:MM), `m` (message lines) |
| Be right back | `h` (heading), `timer` (show back-in clock), `min` (minutes) |
| Loading | `style` (`blink`, `hop`, `fill`, `bar`), `caption` (default "Loading"), `cap` (`0` hides the caption) |

## Deploy (Cloudflare Pages)

Live at https://screens.heartbeatchurch.com.au. The hosting (Pages project `screens`, custom domain,
DNS) is Terraform in `terraform/screens` (see its README). Deploys are GitHub Actions
(`.github/workflows/screens.yml`): every push to `main` that touches `brand/screens/` runs `npm test`
and `npm run build`, then uploads `dist/` with `wrangler pages deploy`; pull requests get a preview URL.
The build needs only Node 18+ and no `npm install`. `dist/_headers` sets the security and cache headers.

## Commands

    npm install          # puppeteer-core, for the check only
    npm run dev          # serve src/ on :8790 (PORT to change); pages work unbuilt
    npm run build        # src/ -> dist/ (single-file pages + _headers)
    npm test             # node --test: core + settings
    npm run check        # build, then load every page at 5 sizes x 2 themes; screenshots in out/

`check` fails on any page/console error or sideways overflow, and expects Chrome at
`/Applications/Google Chrome.app` (or `CHROME=...`). Look at `out/*.png` yourself too.

## Layout

    src/<name>.html          one page per screen (page CSS + script tags)
    src/screens/<name>.js    the screen's behaviour
    src/shared/              brand.css, core.js, logo.js (generated), settings.js, stage.js, panel.js, timer.js, fonts/
    scripts/gen-logo.mjs     regenerates logo.js from brand/assets/heartbeat-lockup-white.svg
    build.mjs                inlines local <link rel=stylesheet href> and <script src>, fonts as data URIs

## Architecture

No framework and no bundler. `build.mjs` inlines each page's stylesheet, scripts and fonts so a page is one
file. Pages share `src/shared/` (tokens, panel, timer, logo) and put only screen behaviour in `src/screens/`.
`index.html` is the exception: it has its own look (the motion kit report's) and loads only `shared/fonts.css`.

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

   A screen that counts down (Timer or Until, Start/Reset, Space/R/arrows, autostart and the homepage
   demo loop) uses `HB.countdownScreen` instead, giving only its own rows and drawing:

        HB.countdownScreen({ id: 'ring', title: 'Ring countdown settings',
          schema: [...HB.timerSchema, HB.THEME, /* own rows */],
          onChange(key, values) { /* own rows changed */ }, ready(values) { /* first set-up */ },
          render(frame, values) { /* frame = { idle, t, COUNT, n, phase, done } */ } });

3. Add a card to `src/index.html` (copy one: thumbnail iframe, name, kind chip, blurb, Open / Download), a row in the README tables, and `check` picks the page up automatically.
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

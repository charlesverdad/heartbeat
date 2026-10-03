# Heartbeat brand

Logo files, logo animations, and a starter media kit for socials, slides and ProPresenter.

Open `report.html` for the first round and `report-v2.html` for the second (new loops, kinetic vision variations, merch mockups): every animation plays live and links to its MP4. Serve the folder, because ES modules don't load over `file://`:

```sh
cd brand && python3 -m http.server 8765   # then open http://localhost:8765/report.html
```

## Layout

| Path | What |
| --- | --- |
| `assets/` | Mark, lockup and echo graphic as black and white SVGs, plus the original brandmark file |
| `logo-motion/src/` | The animations. `core.js` builds the scene, `anims.js` is the catalogue, `stage.html` is the render target |
| `logo-motion/out/` | Rendered MP4s (`<id>_<aspect>_<theme>.mp4`) and last-frame posters |
| `media-kit/templates/` | HTML templates for the sample social posts, slides and ProPresenter overlays |
| `media-kit/samples/` | Rendered PNGs. `pp-*.png` are transparent; `*_preview.png` show them over a stand-in stage |
| `logo-motion/src/anims-v2.js` | Second-round animations; `catalogue.js` joins both lists for the renderer and reports |
| `mockups/` | Merch mockups: AI-generated blanks in `raw/`, logo placements in `mockups.json`, results in `out/` |
| `report.html`, `report-v2.html` | Galleries for each round |

## Rendering

Needs Google Chrome and `ffmpeg` (from the repo's `shell.nix`).

```sh
cd brand && npm install
npm run motion                                   # every animation × 16:9, 1:1, 9:16 × black, white
npm run motion -- --only mark-pulse --aspects 16x9 --themes dark
npm run motion -- --only mark-pulse --alpha      # adds a ProRes 4444 .mov with transparency for editors
npm run motion -- --sheet                        # contact sheets of 12 frames each, for reviewing motion
npm run motion -- --only mark-ecg --at 1.5       # one full-size still
npm run kit                                      # media-kit sample PNGs
node mockups/compose.mjs                         # put the logo on every blank in mockups.json
python3 mockups/draw.py --id mug-green --prompt "..."   # new blank via NanoGPT (key from keychain: nanogpt-api-key)
```

Mockups: the blank product photo comes from an image model, but the logo is never drawn by AI. `compose.mjs` warps the real SVG onto the photo (a perspective quad for flat items, a cylinder for mugs and bottles) and shades it with the photo's own light. To place a logo on a new blank, read pixel coordinates off the photo and add an entry to `mockups.json`.

Each animation is a pure function of time (`frame(scene, state, t)`), so the browser preview and the rendered video match frame for frame. To add one, append an entry to `ANIMS_V2` in `logo-motion/src/anims-v2.js`; the renderer and the report pick it up.

## Notes

- Vision line: "Living Out The Gospel Together Wholeheartedly".
- Type is Inter Tight (SIL Open Font License, `logo-motion/src/fonts/OFL.txt`), the closest free match to the wordmark.
- MP4s are H.264, yuv420p, 30 fps, CRF 18. Most editors and ProPresenter play them directly.

// Render the media-kit sample templates to PNG.
//
//   node media-kit/render-kit.mjs            # every template
//   node media-kit/render-kit.mjs pp-name    # just one
//
// Overlay templates (pp-lyrics, pp-name, pp-scripture, pp-bug) render twice:
// a transparent PNG to drop into ProPresenter, and a *_preview.png over a stand-in stage.
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { extname, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..'); // brand/
const OUT = join(HERE, 'samples');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const SAMPLES = [
  { id: 'social-quote', w: 1080, h: 1080 },
  { id: 'social-series', w: 1080, h: 1350 },
  { id: 'social-story', w: 1080, h: 1920, preview: true },
  { id: 'social-youtube', w: 1280, h: 720 },
  { id: 'slide-title', w: 1920, h: 1080 },
  { id: 'slide-point', w: 1920, h: 1080 },
  { id: 'slide-scripture', w: 1920, h: 1080 },
  { id: 'slide-announcement', w: 1920, h: 1080 },
  { id: 'pp-lyrics', w: 1920, h: 1080, alpha: true },
  { id: 'pp-name', w: 1920, h: 1080, alpha: true },
  { id: 'pp-scripture', w: 1920, h: 1080, alpha: true },
  { id: 'pp-bug', w: 1920, h: 1080, alpha: true },
  { id: 'pp-holding', w: 1920, h: 1080 },
  { id: 'banner-art', w: 800, h: 2000, alpha: true, noPreview: true },
];

const TYPES = { '.html': 'text/html', '.css': 'text/css', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const body = await readFile(join(ROOT, path));
    res.writeHead(200, { 'content-type': TYPES[extname(path)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}/media-kit/templates`;

const only = process.argv[2];
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--hide-scrollbars', '--force-color-profile=srgb'] });
const page = await browser.newPage();
page.on('pageerror', e => console.error('page error:', e.message));
await mkdir(OUT, { recursive: true });

const snap = async (s, query, file, transparent) => {
  await page.setViewport({ width: s.w, height: s.h, deviceScaleFactor: 1 });
  await page.goto(`${BASE}/${s.id}.html${query}`, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: join(OUT, file), omitBackground: transparent });
  console.log(`✓ samples/${file}`);
};

try {
  for (const s of SAMPLES.filter(x => !only || x.id === only)) {
    await snap(s, '', `${s.id}.png`, !!s.alpha);
    if ((s.alpha && !s.noPreview) || s.preview) await snap(s, '?preview', `${s.id}_preview.png`, false);
  }
} finally {
  await browser.close();
  server.close();
}

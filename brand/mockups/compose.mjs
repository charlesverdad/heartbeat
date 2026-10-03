// Put the logo on every blank listed in mockups.json and write mockups/out/<id>.jpg.
//
//   node mockups/compose.mjs            # all
//   node mockups/compose.mjs tee-black  # one
//
// Each spec: { id, base, logo: 'mark'|'lockup' | art: 'path from brand/', ink: 'white'|'black',
//              quad: [[x,y]×4 tl,tr,br,bl] | cylinder: { cx, r, r2?, top, bottom, arc, sag }, opacity?, crop?: [x,y,w,h] }
import { createServer } from 'node:http';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { extname, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = join(HERE, '..');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const TYPES = { '.html': 'text/html', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp' };

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
const BASE = `http://127.0.0.1:${server.address().port}`;

const specs = JSON.parse(await readFile(join(HERE, 'mockups.json'), 'utf8'));
const only = process.argv[2];
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true });
const page = await browser.newPage();
page.on('pageerror', e => console.error('page error:', e.message));
await page.goto(`${BASE}/mockups/compose.html`);
await page.waitForFunction('window.READY === true');
await mkdir(join(HERE, 'out'), { recursive: true });

try {
  for (const s of specs.filter(x => !only || x.id === only)) {
    const logo = s.art ? `/${s.art}` : `/assets/heartbeat-${s.logo}-${s.ink === 'white' ? 'white' : 'black'}.svg`;
    await page.evaluate(spec => window.compose(spec), { ...s, base: `/mockups/${s.base}`, logo });
    const url = await page.evaluate(() => document.getElementById('out').toDataURL('image/jpeg', 0.9));
    await writeFile(join(HERE, 'out', `${s.id}.jpg`), Buffer.from(url.split(',')[1], 'base64'));
    console.log(`✓ mockups/out/${s.id}.jpg`);
  }
} finally {
  await browser.close();
  server.close();
}

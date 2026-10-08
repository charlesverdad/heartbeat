// Browser check: loads every built page (dist/) in several window sizes and both themes, fails on any
// page error or console error and on content spilling past the window sideways, and saves screenshots to out/.
//
//   node build.mjs && node scripts/check.mjs [pageName ...]
import puppeteer from 'puppeteer-core';
import { readdir, mkdir, rm } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const DIST = join(HERE, '../dist');
const OUT = join(HERE, '../out');
const CHROME = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const SIZES = [[1920, 1080], [1024, 768], [390, 844], [844, 390], [1080, 1920]];
const THEMES = ['dark', 'light'];
// Extra demo moments for the countdown: the big final count and the logo landed.
const DEMO_TIMES = { countdown: [0, 15, 26], ring: [0, 21.5, 24, 28] };

const only = process.argv.slice(2);
const pages = (await readdir(DIST)).filter(f => f.endsWith('.html')).map(f => f.replace(/\.html$/, '')).filter(p => !only.length || only.includes(p));
// A full run starts from a clean out/; a run for named pages leaves other pages' screenshots alone.
if (!only.length) await rm(OUT, { recursive: true, force: true });
await mkdir(OUT, { recursive: true });

const browser = await puppeteer.launch({ executablePath: CHROME, args: ['--no-sandbox'] });
const problems = [];
let shots = 0;

// Anything visible that sticks out sideways past the window (hidden panel and invisible items excepted).
const overflow = () => {
  const W = document.documentElement.clientWidth;
  const bad = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('[hidden], .controls.hide, svg') || el.tagName === 'SCRIPT' || el.tagName === 'STYLE') continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const r = el.getBoundingClientRect();
    if (r.width && (r.right > W + 1 || r.left < -1)) bad.push(`${el.tagName.toLowerCase()}${el.id ? '#' + el.id : ''}.${el.className} [${Math.round(r.left)}..${Math.round(r.right)}] of ${W}`);
  }
  if (document.documentElement.scrollWidth > W + 1) bad.push(`page scrolls sideways: ${document.documentElement.scrollWidth} > ${W}`);
  return bad;
};

async function visit(name, [w, h], theme, state) {
  const label = `${name} ${w}x${h} ${theme} ${state}`;
  const page = await browser.newPage();
  page.on('pageerror', e => problems.push(`${label}: pageerror ${e.message}`));
  page.on('console', m => { if (m.type() === 'error') problems.push(`${label}: console ${m.text()}`); });
  await page.setViewport({ width: w, height: h });
  const q = new URLSearchParams({ theme });
  if (state.startsWith('demo')) { q.set('demo', ''); const t = state.split('-')[1]; if (t) q.set('t', t); }
  await page.goto(`${pathToFileURL(join(DIST, name + '.html'))}?${q}`);
  await page.evaluate(() => document.fonts.ready);
  await new Promise(r => setTimeout(r, 900));
  if (state === 'min') {
    await page.keyboard.press('h');
    await new Promise(r => setTimeout(r, 500));
  }
  if (state.startsWith('demo')) {
    const hasPanel = await page.evaluate(() => !!document.querySelector('.controls'));
    if (hasPanel) problems.push(`${label}: demo mode built a panel`);
  }
  for (const b of await page.evaluate(overflow)) problems.push(`${label}: overflow ${b}`);
  await page.screenshot({ path: join(OUT, `${name}-${w}x${h}-${theme}-${state}.png`) });
  shots++;
  await page.close();
}

for (const name of pages) {
  const times = (DEMO_TIMES[name] || [0]).map(t => (t ? `demo-${t}` : 'demo'));
  for (const size of SIZES) for (const theme of THEMES) for (const state of ['open', 'min', ...times]) await visit(name, size, theme, state);
}
await browser.close();

console.log(`${shots} screenshots in out/`);
if (problems.length) {
  console.error(`\n${problems.length} problem(s):\n` + problems.join('\n'));
  process.exit(1);
}
console.log('✓ no page errors, no sideways overflow');

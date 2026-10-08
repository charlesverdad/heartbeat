// Build the single-file welcome countdown: inlines the lockup SVG and the Inter Tight
// fonts into countdown.src.html, so the page works offline from a USB stick or desktop.
//
//   node countdown/build.mjs   ->  countdown/heartbeat-countdown.html
import { readFile, writeFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const BRAND = join(HERE, '..');
const FONTS = join(BRAND, 'logo-motion/src/fonts');

const src = await readFile(join(HERE, 'countdown.src.html'), 'utf8');

// The lockup's first three shapes are the H, B and C mark; group them so the mark can beat on its own.
const svg = (await readFile(join(BRAND, 'assets/heartbeat-lockup-white.svg'), 'utf8')).trim();
const inner = svg.replace(/^<svg[^>]*>/, '').replace(/<\/svg>$/, '');
const shapes = inner.match(/<(polygon|path)[^>]*\/>/g);
if (shapes?.length !== 5) throw new Error(`expected 5 shapes in the lockup, found ${shapes?.length}`);
const logo = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 252.2 111.27" aria-hidden="true"><g class="mark">${shapes.slice(0, 3).join('')}</g>${shapes.slice(3).join('')}</svg>`;

const face = async w => {
  const b64 = (await readFile(join(FONTS, `InterTight-${w}.woff2`))).toString('base64');
  return `@font-face { font-family: 'Inter Tight'; font-weight: ${w}; font-display: block; src: url(data:font/woff2;base64,${b64}) format('woff2'); }`;
};
const fonts = `${await face(500)}\n${await face(700)}`;

const out = src.replace('<!--@LOGO-->', logo).replace('/*@FONTS*/', fonts);
if (out.includes('@LOGO') || out.includes('@FONTS')) throw new Error('placeholder left unreplaced');
await writeFile(join(HERE, 'heartbeat-countdown.html'), out);
console.log(`✓ countdown/heartbeat-countdown.html (${(out.length / 1024).toFixed(0)} KB)`);

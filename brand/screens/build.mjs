// Build the site: src/*.html -> dist/*.html, each a single file with its CSS, scripts and fonts inlined,
// so every page works offline from a USB stick or the desktop.
//
//   node build.mjs
import { readFile, writeFile, readdir, mkdir, rm } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, 'src');
const DIST = join(HERE, 'dist');

const fail = msg => { throw new Error(`build: ${msg}`); };
const read = async (base, rel, from) => {
  try { return await readFile(join(base, rel)); } catch { return fail(`${from} references missing file ${rel}`); }
};
const isLocal = ref => !/^([a-z]+:)?\/\//i.test(ref) && !ref.startsWith('data:');

// Fonts: url(fonts/x.woff2) in a stylesheet becomes a data URI.
async function inlineFonts(css, dir, from) {
  const re = /url\((['"]?)([^)'"]+\.woff2)\1\)/g;
  let out = '', last = 0, m;
  while ((m = re.exec(css))) {
    const b64 = (await read(dir, m[2], from)).toString('base64');
    out += css.slice(last, m.index) + `url(data:font/woff2;base64,${b64})`;
    last = m.index + m[0].length;
  }
  return out + css.slice(last);
}

async function buildPage(name) {
  let html = await readFile(join(SRC, name), 'utf8');
  const jobs = [];
  // Replace each match with the awaited text, in order.
  const swap = (re, make) => {
    for (const m of html.matchAll(re)) jobs.push(make(m).then(text => [m[0], text]));
  };
  swap(/<link[^>]*rel=["']stylesheet["'][^>]*href=["']([^"']+)["'][^>]*>/g, async m => {
    if (!isLocal(m[1])) return m[0];
    const css = (await read(SRC, m[1], name)).toString('utf8');
    return `<style>\n${await inlineFonts(css, dirname(join(SRC, m[1])), m[1])}\n</style>`;
  });
  swap(/<script[^>]*src=["']([^"']+)["'][^>]*><\/script>/g, async m => {
    if (!isLocal(m[1])) return m[0];
    const js = (await read(SRC, m[1], name)).toString('utf8');
    return `<script>\n${js.replaceAll('</script', '<\\/script')}\n</script>`;
  });
  for (const [from, to] of await Promise.all(jobs)) html = html.replace(from, () => to);
  if (/@[A-Z]{3,}\b/.test(html.replace(/@(media|font-face|import|keyframes|supports|container)/g, ''))) fail(`${name}: placeholder left unreplaced`);
  await writeFile(join(DIST, name), html);
  return html.length;
}

const HEADERS = `/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
/*.html
  Cache-Control: public, max-age=300
`;

await rm(DIST, { recursive: true, force: true });
await mkdir(DIST, { recursive: true });
const pages = (await readdir(SRC)).filter(f => f.endsWith('.html')).sort();
for (const p of pages) console.log(`✓ dist/${p} (${((await buildPage(p)) / 1024).toFixed(0)} KB)`);
await writeFile(join(DIST, '_headers'), HEADERS);
console.log('✓ dist/_headers');

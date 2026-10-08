// Render the logo animations to video with headless Chrome + ffmpeg.
//
//   node render.mjs                         # every animation, default variants
//   node render.mjs --only mark-pulse,mark-ecg --aspects 16x9 --themes dark
//   node render.mjs --alpha                 # also write ProRes 4444 .mov with transparency
//   node render.mjs --sheet                 # contact sheets only (for visual review), no video
//   node render.mjs --only mark-pulse --at 1.4   # one full-size still at t=1.4s
//
// An animation can limit its own aspects (countdowns are 16:9 only) unless --aspects is given.
// Animations marked gif: true also get a small looping GIF from the 1:1 render, for web pages.
//
// Needs Google Chrome (or CHROME_PATH) and ffmpeg on PATH (shell.nix provides ffmpeg).
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import { spawn } from 'node:child_process';
import { extname, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import puppeteer from 'puppeteer-core';

const HERE = dirname(fileURLToPath(import.meta.url));
const SRC = join(HERE, 'src');
const args = process.argv.slice(2);
const opt = (name, def) => {
  const i = args.indexOf(`--${name}`);
  return i < 0 ? def : args[i + 1];
};
const flag = name => args.includes(`--${name}`);

const FPS = Number(opt('fps', 30));
const OUT = join(HERE, opt('out', 'out'));
const ASPECTS = opt('aspects', '16x9,1x1,9x16').split(',');
const THEMES = opt('themes', 'dark,light').split(',');
const ONLY = opt('only', '');
const SHEET = flag('sheet');
const AT = opt('at', null);
const ALPHA = flag('alpha');
const ASPECTS_GIVEN = args.includes('--aspects');
const CHROME = process.env.CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2', '.svg': 'image/svg+xml' };
const server = createServer(async (req, res) => {
  try {
    const path = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    const body = await readFile(join(SRC, path));
    res.writeHead(200, { 'content-type': TYPES[extname(path)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404).end();
  }
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const BASE = `http://127.0.0.1:${server.address().port}`;

const { ALL: ANIMS } = await import(join(SRC, 'catalogue.js'));
// anims.js touches the DOM only inside setup/frame, so importing it in node is safe.
const list = ANIMS.filter(a => !ONLY || ONLY.split(',').includes(a.id));

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: true,
  args: ['--hide-scrollbars', '--force-color-profile=srgb', '--disable-lcd-text', '--font-render-hinting=none'],
});
const page = await browser.newPage();
page.on('pageerror', e => console.error('page error:', e.message));
page.on('console', m => m.type() === 'error' && console.error('console:', m.text()));
const cdp = await page.createCDPSession();

const run = (cmd, argv, stdinFn) =>
  new Promise((resolve, reject) => {
    const p = spawn(cmd, argv, { stdio: ['pipe', 'ignore', 'pipe'] });
    let err = '';
    p.stderr.on('data', d => (err += d));
    p.on('close', code => (code ? reject(new Error(`${cmd} exited ${code}\n${err.slice(-2000)}`)) : resolve()));
    stdinFn(p.stdin);
  });

async function load(anim, aspect, theme) {
  const [W, H] = { '16x9': [1920, 1080], '1x1': [1080, 1080], '9x16': [1080, 1920] }[aspect];
  await page.setViewport({ width: W, height: H, deviceScaleFactor: 1 });
  await page.goto(`${BASE}/stage.html?anim=${anim.id}&aspect=${aspect}&theme=${theme}`);
  await page.waitForFunction('window.READY === true', { timeout: 15000 });
  return [W, H];
}

async function shot(t, transparent) {
  await page.evaluate(t => window.seek(t), t);
  if (transparent) await cdp.send('Emulation.setDefaultBackgroundColorOverride', { color: { r: 0, g: 0, b: 0, a: 0 } });
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png', optimizeForSpeed: true });
  return Buffer.from(data, 'base64');
}

async function renderVideo(anim, aspect, theme) {
  await load(anim, aspect, theme);
  const frames = Math.round(anim.duration * FPS);
  const alpha = theme === 'alpha';
  const name = `${anim.id}_${aspect}_${theme}`;
  const file = join(OUT, alpha ? `${name}.mov` : `${name}.mp4`);
  const enc = alpha
    ? ['-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-vendor', 'apl0']
    : ['-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'];
  const t0 = Date.now();
  await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-', ...enc, file], async stdin => {
    for (let f = 0; f < frames; f++) {
      const buf = await shot(f / FPS, alpha);
      if (!stdin.write(buf)) await new Promise(r => stdin.once('drain', r));
    }
    stdin.end();
  });
  // Poster = last frame, used by the report.
  await mkdir(join(OUT, 'posters'), { recursive: true });
  const { writeFile } = await import('node:fs/promises');
  if (!alpha) await writeFile(join(OUT, 'posters', `${name}.png`), await shot(anim.duration - 1 / FPS, false));
  console.log(`✓ ${file.replace(HERE + '/', '')}  (${frames} frames, ${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  if (anim.gif && aspect === '1x1' && !alpha) {
    const gif = join(OUT, 'gif', `${name}.gif`);
    await mkdir(dirname(gif), { recursive: true });
    await run('ffmpeg', ['-y', '-loglevel', 'error', '-i', file, '-vf',
      'fps=25,scale=360:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48[p];[b][p]paletteuse=dither=none', '-loop', '0', gif], s => s.end());
    console.log(`✓ ${gif.replace(HERE + '/', '')}`);
  }
}

// A contact sheet of N evenly spaced frames, for eyeballing motion without a video player.
async function renderSheet(anim, aspect, theme, n = 12) {
  const [W, H] = await load(anim, aspect, theme);
  const cols = 4;
  const rows = Math.ceil(n / cols);
  const tw = aspect === '9x16' ? 270 : 480;
  const th = Math.round((tw * H) / W);
  const file = join(OUT, 'sheets', `${anim.id}_${aspect}_${theme}.png`);
  await mkdir(dirname(file), { recursive: true });
  await run('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-c:v', 'png', '-i', '-',
    '-vf', `scale=${tw}:${th},drawtext=text='%{n}':x=8:y=8:fontsize=18:fontcolor=red,tile=${cols}x${rows}:padding=4:color=gray`, '-frames:v', '1', file], async stdin => {
    for (let i = 0; i < n; i++) stdin.write(await shot((anim.duration * i) / (n - 1) - (i === n - 1 ? 1 / FPS : 0), false));
    stdin.end();
  });
  console.log(`✓ ${file.replace(HERE + '/', '')}`);
}

await mkdir(OUT, { recursive: true });
try {
  for (const anim of list) {
    const aspects = ASPECTS_GIVEN || !anim.aspects ? ASPECTS : ASPECTS.filter(x => anim.aspects.includes(x));
    for (const aspect of aspects) {
      for (const theme of THEMES) {
        if (AT !== null) {
          await load(anim, aspect, theme);
          const file = join(OUT, 'stills', `${anim.id}_${aspect}_${theme}_${AT}.png`);
          await mkdir(dirname(file), { recursive: true });
          await (await import('node:fs/promises')).writeFile(file, await shot(Number(AT), false));
          console.log(`✓ ${file.replace(HERE + '/', '')}`);
        } else if (SHEET) await renderSheet(anim, aspect, theme);
        else await renderVideo(anim, aspect, theme);
      }
      if (ALPHA && !SHEET) await renderVideo(anim, aspect, 'alpha');
    }
  }
} finally {
  await browser.close();
  server.close();
}

#!/usr/bin/env node

/**
 * Ghost CMS: append HTML to an existing post
 *
 * Fetches a post by slug, appends extra HTML to its body, and updates it
 * in place (preserving status, published_at, tags, etc).
 *
 * Usage:
 *   node ghost-append-html.mjs --slug <post-slug> --html-file path/to/snippet.html [--dry-run]
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

function ghostJWT(apiKey) {
  const [id, secret] = apiKey.split(':');
  if (!id || !secret) throw new Error('GHOST_ADMIN_API_KEY must be in "id:secret" format');
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: id })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({ iat: now, exp: now + 300, aud: '/admin/' })).toString('base64url');
  const signature = crypto.createHmac('sha256', Buffer.from(secret, 'hex')).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${signature}`;
}

async function resolveGhostUrl(ghostUrl) {
  const url = `${ghostUrl.replace(/\/$/, '')}/ghost/api/admin/site/`;
  const response = await fetch(url, { method: 'HEAD', redirect: 'manual' });
  if (response.status >= 300 && response.status < 400) {
    const location = response.headers.get('location');
    if (location) {
      const resolved = new URL(location);
      return `${resolved.protocol}//${resolved.host}`;
    }
  }
  return ghostUrl.replace(/\/$/, '');
}

async function ghostFetch(ghostUrl, endpoint, token, options = {}) {
  const url = `${ghostUrl.replace(/\/$/, '')}/ghost/api/admin/${endpoint}`;
  const headers = { 'Authorization': `Ghost ${token}`, 'Accept-Version': 'v5.0', ...options.headers };
  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Ghost API error ${response.status}: ${body}`);
  }
  return response.json();
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') { args.dryRun = true; continue; }
    if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) {
        console.error(`Missing value for ${arg}`); process.exit(1);
      }
      const camel = key.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      args[camel] = argv[++i];
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);
  const apiKey = process.env.GHOST_ADMIN_API_KEY;
  const ghostUrl = process.env.GHOST_URL;
  if (!apiKey || !ghostUrl) {
    console.error('Set GHOST_ADMIN_API_KEY and GHOST_URL'); process.exit(1);
  }
  if (!args.slug || !args.htmlFile) {
    console.error('Usage: --slug <slug> --html-file <file> [--dry-run]'); process.exit(1);
  }

  const snippet = fs.readFileSync(path.resolve(args.htmlFile), 'utf-8');
  const resolvedUrl = await resolveGhostUrl(ghostUrl);
  const token = ghostJWT(apiKey);

  // Fetch existing post by slug with html format
  const existing = await ghostFetch(resolvedUrl, `posts/slug/${args.slug}/?formats=html`, token);
  const post = existing.posts?.[0];
  if (!post) { console.error(`Post not found: ${args.slug}`); process.exit(1); }

  if (post.html?.includes(snippet.trim().slice(0, 80))) {
    console.log('Snippet already present in post body — skipping.');
    console.log(`Edit URL: ${resolvedUrl}/ghost/#/editor/post/${post.id}`);
    return;
  }

  const newHtml = `${post.html || ''}\n${snippet}`;
  const updateBody = {
    posts: [{
      html: newHtml,
      updated_at: post.updated_at,
    }],
  };

  if (args.dryRun) {
    console.log(`Post: ${post.title} (status=${post.status})`);
    console.log(`Current HTML length: ${(post.html || '').length}`);
    console.log(`New HTML length: ${newHtml.length}`);
    console.log(`Appending:\n${snippet}`);
    return;
  }

  const updated = await ghostFetch(resolvedUrl, `posts/${post.id}/?source=html`, token, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updateBody),
  });
  const u = updated.posts?.[0];
  console.log(`Updated post: ${u.title} (status=${u.status})`);
  console.log(`Edit URL: ${resolvedUrl}/ghost/#/editor/post/${u.id}`);
}

main().catch(err => { console.error(`Fatal: ${err.message}`); process.exit(1); });

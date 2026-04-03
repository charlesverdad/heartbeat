#!/usr/bin/env node

/**
 * Ghost CMS Post Lister
 *
 * Fetches recent published posts from Ghost CMS using the Admin API.
 * Useful for checking style consistency before generating new posts.
 *
 * Usage:
 *   node ghost-list-posts.mjs [--limit 5] [--tag sermons] [--html] [--fields title,html]
 *
 * Options:
 *   --limit N     Number of posts to fetch (default: 5)
 *   --tag TAG     Filter by tag slug (e.g. "sermons")
 *   --html        Include full HTML body in output (default: excluded for brevity)
 *   --fields F    Comma-separated fields (default: title,slug,published_at,custom_excerpt)
 *
 * Environment variables:
 *   GHOST_ADMIN_API_KEY - Ghost Admin API key in "id:secret" format
 *   GHOST_URL           - Ghost site URL (e.g. https://heartbeatchurch.com.au)
 */

import crypto from 'node:crypto';

function ghostJWT(apiKey) {
  const [id, secret] = apiKey.split(':');
  if (!id || !secret) {
    throw new Error('GHOST_ADMIN_API_KEY must be in "id:secret" format');
  }

  const header = Buffer.from(JSON.stringify({
    alg: 'HS256', typ: 'JWT', kid: id
  })).toString('base64url');

  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({
    iat: now, exp: now + 300, aud: '/admin/'
  })).toString('base64url');

  const signature = crypto
    .createHmac('sha256', Buffer.from(secret, 'hex'))
    .update(`${header}.${payload}`)
    .digest('base64url');

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

function parseArgs(argv) {
  const args = { limit: 5, html: false };
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--html') {
      args.html = true;
    } else if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) {
        console.error(`Error: Missing value for argument: ${arg}`);
        process.exit(1);
      }
      args[key] = argv[++i];
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);

  const apiKey = process.env.GHOST_ADMIN_API_KEY;
  const ghostUrl = process.env.GHOST_URL;

  if (!apiKey) {
    console.error('Error: GHOST_ADMIN_API_KEY environment variable is not set.');
    process.exit(1);
  }
  if (!ghostUrl) {
    console.error('Error: GHOST_URL environment variable is not set.');
    process.exit(1);
  }

  const resolvedUrl = await resolveGhostUrl(ghostUrl);
  const token = ghostJWT(apiKey);

  const limit = parseInt(args.limit) || 5;
  const fields = args.fields || 'title,slug,published_at,custom_excerpt';

  let filter = 'status:published';
  if (args.tag) {
    filter += `+tag:${args.tag}`;
  }

  const params = new URLSearchParams({
    filter,
    limit: limit.toString(),
    order: 'published_at desc',
    fields,
  });

  if (args.html) {
    params.set('formats', 'html');
  }

  const url = `${resolvedUrl}/ghost/api/admin/posts/?${params}`;
  const response = await fetch(url, {
    headers: {
      'Authorization': `Ghost ${token}`,
      'Accept-Version': 'v5.0',
    },
  });

  if (!response.ok) {
    const body = await response.text();
    console.error(`Ghost API error ${response.status}: ${body}`);
    process.exit(1);
  }

  const data = await response.json();
  const posts = data.posts || [];

  console.log(JSON.stringify(posts, null, 2));
}

main().catch(err => {
  console.error(`Fatal error: ${err.message}`);
  process.exit(1);
});

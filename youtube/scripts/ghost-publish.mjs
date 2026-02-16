#!/usr/bin/env node

/**
 * Ghost CMS Draft Publisher
 *
 * Creates draft blog posts on Ghost CMS using the Admin API.
 * Zero external dependencies - uses only Node.js built-in modules.
 *
 * Usage:
 *   node ghost-publish.mjs \
 *     --title "Sermon Title" \
 *     --html-file path/to/post.html \
 *     --excerpt "Short excerpt" \
 *     --tag sermons \
 *     --author heartbeat \
 *     [--published-at "2026-02-01T10:00:00.000+11:00"] \
 *     [--dry-run]
 *
 * Environment variables:
 *   GHOST_ADMIN_API_KEY - Ghost Admin API key in "id:secret" format
 *   GHOST_URL           - Ghost site URL (e.g. https://heartbeatchurch.com.au)
 */

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

// --- JWT Generation (zero dependencies) ---

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

// --- Argument Parsing ---

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dry-run') {
      args.dryRun = true;
    } else if (arg.startsWith('--')) {
      const key = arg.slice(2);
      if (i + 1 >= argv.length || argv[i + 1].startsWith('--')) {
        console.error(`Error: Missing value for argument: ${arg}`);
        process.exit(1);
      }
      const value = argv[++i];
      // Convert kebab-case to camelCase
      const camelKey = key.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
      args[camelKey] = value;
    }
  }
  return args;
}

// --- Ghost API Client ---

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
  const headers = {
    'Authorization': `Ghost ${token}`,
    'Accept-Version': 'v5.0',
    ...options.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Ghost API error ${response.status}: ${body}`);
  }

  return response.json();
}

async function createDraftPost(ghostUrl, token, postData) {
  return ghostFetch(ghostUrl, 'posts/?source=html', token, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ posts: [postData] }),
  });
}

async function lookupAuthor(ghostUrl, token, authorSlug) {
  try {
    const data = await ghostFetch(ghostUrl, `users/slug/${authorSlug}/`, token);
    return data.users?.[0] || null;
  } catch {
    return null;
  }
}

// --- Main ---

async function main() {
  const args = parseArgs(process.argv);

  // Validate required environment variables
  const apiKey = process.env.GHOST_ADMIN_API_KEY;
  const ghostUrl = process.env.GHOST_URL;

  if (!apiKey) {
    console.error('Error: GHOST_ADMIN_API_KEY environment variable is not set.');
    console.error('Create one at: Ghost Admin > Settings > Integrations > Add Custom Integration');
    process.exit(1);
  }
  if (!ghostUrl) {
    console.error('Error: GHOST_URL environment variable is not set.');
    console.error('Example: export GHOST_URL=https://heartbeatchurch.com.au');
    process.exit(1);
  }

  // Validate required arguments
  if (!args.title) {
    console.error('Error: --title is required');
    process.exit(1);
  }
  if (!args.htmlFile) {
    console.error('Error: --html-file is required');
    process.exit(1);
  }

  // Read HTML content
  const htmlPath = path.resolve(args.htmlFile);
  if (!fs.existsSync(htmlPath)) {
    console.error(`Error: HTML file not found: ${htmlPath}`);
    process.exit(1);
  }
  const html = fs.readFileSync(htmlPath, 'utf-8');

  // Build post data
  const postData = {
    title: args.title,
    html: html,
    status: 'draft',
  };

  if (args.excerpt) {
    postData.custom_excerpt = args.excerpt;
  }

  if (args.tag) {
    postData.tags = args.tag.split(',').map(t => ({ name: t.trim() }));
  }

  if (args.publishedAt) {
    postData.published_at = args.publishedAt;
  }

  // Dry run: print what would be sent
  if (args.dryRun) {
    console.log('=== DRY RUN ===');
    console.log(`Ghost URL: ${ghostUrl}`);
    console.log(`Title: ${postData.title}`);
    console.log(`Status: ${postData.status}`);
    console.log(`Excerpt: ${postData.custom_excerpt || '(none)'}`);
    console.log(`Tags: ${JSON.stringify(postData.tags || [])}`);
    console.log(`Author: ${args.author || '(default)'}`);
    console.log(`Published at: ${postData.published_at || '(not set)'}`);
    console.log(`HTML length: ${html.length} chars`);
    console.log(`HTML preview: ${html.slice(0, 200)}...`);
    console.log('=== Would create draft post ===');
    process.exit(0);
  }

  // Resolve the Ghost URL (handles domain redirects like non-www -> www)
  const resolvedUrl = await resolveGhostUrl(ghostUrl);
  if (resolvedUrl !== ghostUrl.replace(/\/$/, '')) {
    console.log(`Resolved Ghost URL: ${resolvedUrl}`);
  }

  // Generate JWT
  const token = ghostJWT(apiKey);

  // Look up author if specified
  if (args.author) {
    const author = await lookupAuthor(resolvedUrl, token, args.author);
    if (author) {
      postData.authors = [{ id: author.id }];
    } else {
      console.warn(`Warning: Author "${args.author}" not found in Ghost. Using default author.`);
    }
  }

  // Create the draft post
  console.log(`Creating draft post: "${args.title}"...`);
  const result = await createDraftPost(resolvedUrl, token, postData);

  const post = result.posts?.[0];
  if (!post) {
    console.error('Error: Unexpected API response - no post returned');
    process.exit(1);
  }

  const adminUrl = `${resolvedUrl}/ghost/#/editor/post/${post.id}`;

  console.log('Draft created successfully!');
  console.log(`Post ID: ${post.id}`);
  console.log(`Slug: ${post.slug}`);
  console.log(`Edit URL: ${adminUrl}`);

  // Output JSON for programmatic use
  const output = {
    id: post.id,
    slug: post.slug,
    title: post.title,
    url: post.url,
    adminUrl: adminUrl,
    status: post.status,
  };
  console.log(`\nJSON: ${JSON.stringify(output)}`);
}

main().catch(err => {
  console.error(`Fatal error: ${err.message}`);
  process.exit(1);
});

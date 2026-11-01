#!/usr/bin/env node
// Updates ONLY the body of an existing Ghost post. Never sends `status`, so a
// published post stays published (ghost-publish.mjs --updateId would unpublish it).
import crypto from 'node:crypto';
import fs from 'node:fs';

function ghostJWT(apiKey) {
  const [id, secret] = apiKey.split(':');
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: id })).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const payload = Buffer.from(JSON.stringify({ iat: now, exp: now + 300, aud: '/admin/' })).toString('base64url');
  const sig = crypto.createHmac('sha256', Buffer.from(secret, 'hex')).update(`${header}.${payload}`).digest('base64url');
  return `${header}.${payload}.${sig}`;
}

const base = 'https://www.heartbeatchurch.com.au';
const key = process.env.GHOST_ADMIN_API_KEY;
const id = process.argv[2];
const htmlFile = process.argv[3];
const apply = process.argv.includes('--apply');
const html = fs.readFileSync(htmlFile, 'utf8');
const auth = { Authorization: `Ghost ${ghostJWT(key)}`, 'Content-Type': 'application/json' };

const getRes = await fetch(`${base}/ghost/api/admin/posts/${id}/?fields=id,title,slug,status,updated_at,published_at`, { headers: auth });
const got = await getRes.json();
if (!getRes.ok) { console.error(JSON.stringify(got, null, 2)); process.exit(1); }
const post = got.posts[0];
console.log(`current: status=${post.status} slug=${post.slug} updated_at=${post.updated_at} published_at=${post.published_at}`);

if (!apply) { console.log('(dry run — pass --apply to write)'); process.exit(0); }

const putRes = await fetch(`${base}/ghost/api/admin/posts/${id}/?source=html`, {
  method: 'PUT',
  headers: auth,
  body: JSON.stringify({ posts: [{ html, updated_at: post.updated_at }] })
});
const put = await putRes.json();
if (!putRes.ok) { console.error(JSON.stringify(put, null, 2)); process.exit(1); }
const after = put.posts[0];
console.log(`after:   status=${after.status} slug=${after.slug} updated_at=${after.updated_at} published_at=${after.published_at}`);
console.log(`url:     ${after.url}`);

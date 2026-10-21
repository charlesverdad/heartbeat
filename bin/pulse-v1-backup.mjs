#!/usr/bin/env node
// Back up every document in hb-pulse (v1) through its /api/v1 API.
//
// The API key is read from the macOS keychain (service "heartbeat-pulse-api-key"),
// never from a file or argv. Store it once with:
//   security add-generic-password -a "$USER" -s heartbeat-pulse-api-key -w
//
// Usage: node bin/pulse-v1-backup.mjs [outDir]
// Default outDir: backups/pulse-v1/<timestamp> (gitignored).
//
// Covers spaces, collections and documents (HTML + plain text + metadata), as
// visible to the key's owner — use an admin's key or drafts/restricted docs are
// skipped. Images under /uploads need a browser session, so they are only listed
// in manifest.json; take them from the VM with manifests/hb-pulse/backup-vm.sh.

import { execFileSync } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE = process.env.PULSE_BASE_URL || 'https://pulse.heartbeatchurch.com.au';
const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
const outDir = process.argv[2] || join('backups', 'pulse-v1', stamp);

const key = execFileSync(
	'security',
	['find-generic-password', '-s', 'heartbeat-pulse-api-key', '-w'],
	{ encoding: 'utf8' },
).trim();

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// v1 allows 60 requests/min per key.
const GAP_MS = 1100;

async function get(path, { raw = false } = {}) {
	for (let attempt = 0; attempt < 5; attempt++) {
		await sleep(GAP_MS);
		const res = await fetch(BASE + path, { headers: { Authorization: `Bearer ${key}` } });
		if (res.status === 429) {
			const wait = Number(res.headers.get('retry-after') || 60) * 1000;
			console.warn(`rate limited, waiting ${wait / 1000}s`);
			await sleep(wait);
			continue;
		}
		if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`);
		return raw ? res.text() : res.json();
	}
	throw new Error(`gave up on ${path}`);
}

const safe = (s) => String(s).replace(/[^\w.-]+/g, '-').slice(0, 80);
const write = (p, data) => {
	mkdirSync(join(p, '..'), { recursive: true });
	writeFileSync(p, typeof data === 'string' ? data : JSON.stringify(data, null, 2));
};

const manifest = { base: BASE, startedAt: new Date().toISOString(), spaces: [], uploads: [], errors: [] };

// Write the manifest even if a listing call fails, so a partial run is still usable.
try {
	const { spaces } = await get('/api/v1/spaces');
	console.log(`${spaces.length} spaces`);

	for (const space of spaces) {
		const spaceDir = join(outDir, safe(space.slug));
		const { collections } = await get(`/api/v1/spaces/${encodeURIComponent(space.slug)}/collections`);
		const spaceEntry = { ...space, collections: [] };
		manifest.spaces.push(spaceEntry);

		for (const col of collections) {
			const colDir = join(spaceDir, safe(col.slug));
			const { documents } = await get(`/api/v1/documents?collectionId=${col.id}`);
			const colEntry = { ...col, documents: [] };
			spaceEntry.collections.push(colEntry);
			console.log(`${space.name} / ${col.name}: ${documents.length} documents`);

			for (const d of documents) {
				const base = join(colDir, `${d.id}-${safe(d.slug)}`);
				try {
					const doc = await get(`/api/v1/documents/${d.id}`);
					write(`${base}.json`, doc);
					write(`${base}.html`, doc.content || '');
					write(`${base}.txt`, doc.contentText || '');
					for (const m of (doc.content || '').matchAll(/["'(](\/uploads\/[^"')\s]+)/g)) {
						manifest.uploads.push({ docId: d.id, path: m[1] });
					}
					colEntry.documents.push({ id: d.id, title: doc.title, slug: doc.slug, file: base });
				} catch (e) {
					manifest.errors.push({ docId: d.id, title: d.title, error: String(e) });
					console.error(`  failed ${d.id} ${d.title}: ${e}`);
				}
			}
		}
	}
} finally {
	manifest.finishedAt = new Date().toISOString();
	write(join(outDir, 'manifest.json'), manifest);
}

const docCount = manifest.spaces.flatMap((s) => s.collections).flatMap((c) => c.documents).length;
console.log(
	`done: ${docCount} documents, ${manifest.uploads.length} upload refs, ${manifest.errors.length} errors -> ${outDir}`,
);

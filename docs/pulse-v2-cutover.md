# hb-pulse → pulse-v2 cutover

Prepared 2026-10-21 by Opus 5.5. Not yet acknowledged by Charles.

## Where things are today

| | v1 (hb-pulse) | v2 (pulse-v2) |
|---|---|---|
| Runtime | Docker on Azure `vm1` (`manifests/hb-pulse/docker-compose.yml`, image `pulse:0.3.1`) | Cloudflare Worker + D1 + R2 + Queue |
| Data | Postgres at `/data/hb-pulse/postgres`, images at `/data/hb-pulse/uploads` | D1 `pulse`, R2 `pulse-files` |
| Ingress | Cloudflare tunnel → `localhost:3001`; DNS CNAME is in `terraform/vm-hb-pulse` (`cloudflare_record.pulse`) | Worker custom domain |
| Secrets | Azure Key Vault `kv-vm-pulse-prod-*` | `wrangler secret put` |
| Email | Gmail SMTP (`noreply@`) | Cloudflare Email Service or Resend only; no SMTP |
| Content | HTML | TipTap JSON |
| API keys | `pulse_…` | `pk_…` (all keys must be issued again) |

## Backup taken 2026-10-21

`backups/pulse-v1/vm-20261021-155457/`: `pulse.dump` (pg_dump custom format), `pulse.sql.gz` (plain SQL), `image.txt` (`pulse:0.3.1`).
It contains 4 spaces, 12 collections, 42 documents, 261 revisions, 20 users and 4 groups.
**The 6 uploaded images are lost.** v1 writes uploads to a relative `data/uploads` (`/app/data/uploads`), not the mounted `/data/uploads`, so they lived only inside the container, and the 2026-06-17 redeploy replaced that container. The affected docs are 21 Gold Coast Camp!, 22 Partnership Class (draft), 32 Survival Kit and 33 Experiencing God. Their images have to come from the original sources.

## Steps

1. **Back up v1.** `bin/pulse-v1-backup.mjs` copies every space, collection and document through the API, using an admin's key so drafts and restricted docs are included. Images aren't included, because `/uploads` needs a browser session. `manifests/hb-pulse/backup-vm.sh` is optional: it adds the full `pg_dump` and the uploads tarball. Azure also keeps daily data-disk snapshots for 60 days (`terraform/vm/backup.tf`).
2. **Provision and deploy v2** straight onto `pulse.heartbeatchurch.com.au` (v1 has no real users): `terraform/pulse-v2/README.md`, First deploy. Tofu creates D1, R2, the queue and the domain. `manifests/pulse-v2/deploy.sh` deploys the v0.2.0 bundle. The Google sign-in client and the Drive key are reused from v1's Key Vault. Push (VAPID), tunnel, session and SMTP secrets are not carried over.
3. **Choose an email provider.** v2 can't use v1's Gmail SMTP. Pick Cloudflare Email or Resend, verify the domain, and leave sending mode Off until a test email arrives.
4. **Migrate content.** v2 has no importer (decision 007). Options:
   - Re-author by hand. Fine if there are only a few dozen docs.
   - Script it: v1 HTML → TipTap JSON (`@tiptap/html` `generateJSON` with v2's extension set), then v2 `POST /api/v1/pages` + `POST /pages/{id}/publish` using a `write:docs` key. Spaces and collections are made in the UI first, because the API only creates pages. Images have to be uploaded again by hand, since v2's API has no attachment upload.
5. **Rebuild access.** v2 permissions *add* (decision 014), while v1's narrowed. Re-check anything that was restricted in v1, such as Digital Platform Team › Internal. Re-invite people. v1 accounts and sessions don't carry over.
6. **Decommission v1** (follow-up PR, after a quiet week or two): remove the `vm-hb-pulse` stack and the hb-pulse containers on vm1. Keep `/data/hb-pulse` and the backups until v2 has run for a while.

## Open decisions
- Content migration: by hand or by script. Depends on how many documents the backup finds.
- Email provider for v2.
- Whether to keep v1 read-only on a different hostname during the transition.

## Decisions (2026-10-21/22)

| Decision | By |
| --- | --- |
| No staging subdomain: v1 has no real users, so v2 goes straight onto `pulse.heartbeatchurch.com.au` | Charles |
| Reuse v1's Google sign-in client and Drive service account; drop the VAPID, tunnel, session and SMTP secrets | Charles (secrets), Opus 5.5 (mapping) |
| Deploy from the published v0.2.0 bundle with our own `wrangler.jsonc` (pulse-v2 deploy.md §10), wrangler 4.149.0 to match the build | Opus 5.5 |
| Wrangler authenticates with the Terraform token from the keychain via `.envrc`; no `wrangler login` | Charles |
| The DNS switch was held overnight, then done on request on 2026-10-22 | Charles |
| The teardown keeps the Drive service account by adopting it into `terraform/pulse-v2` (#45) | Opus 5.5 (not yet acknowledged) |

## State (2026-10-22)
- **Live:** `pulse.heartbeatchurch.com.au` is served by the Worker `pulse` (v0.2.0, version `acb49667`) through a Workers custom domain. v1's tunnel CNAME is destroyed. v1's containers and Azure resources still run, untouched.
- **Created:** D1 `pulse` (`1c1aaf30-7402-4bfa-9ada-971912050a30`), R2 `pulse-files`, queue `pulse-email`.
- **Smoke test:** `/` redirects to sign-in, and `/auth/signin`, `/service-worker.js` and the manifest return 200. `/api/v1` returns 401 without a key, unknown paths return 404, and the HSTS and CSP headers are present. The sign-in page renders on desktop and at 390px with no console errors.
- **Rollback** (while v1 runs): `tofu destroy -target=cloudflare_workers_custom_domain.pulse` in `terraform/pulse-v2`, then `bin/tf -f prod apply` in `terraform/vm-hb-pulse`.
- **Next:** v1 teardown, #45.

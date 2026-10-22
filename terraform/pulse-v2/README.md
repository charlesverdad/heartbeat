# Pulse v2 on Cloudflare

[Pulse v2](https://github.com/charlesverdad/pulse-v2) is live at https://pulse.heartbeatchurch.com.au. It runs as the
Worker `pulse` with D1 (`pulse`), R2 (`pulse-files`), a queue (`pulse-email`) and a Workers custom domain.

| What | Where |
| --- | --- |
| Resources and the domain | this stack (OpenTofu, `bin/tf`) |
| Worker code, migrations | `manifests/pulse-v2/deploy.sh` (prebuilt bundle + our `manifests/pulse-v2/wrangler.jsonc`) |
| Secrets | the Worker only (see Secrets below) |
| Cutover history, decisions | `docs/pulse-v2-cutover.md` |

Run everything from the repo root, in the nix shell with direnv loaded.

## Access

- **Tofu:** `bin/tf` loads the Cloudflare token (`tf-cloudflare-api-token` in `kv-terraform-terraform`). It is a
  *user* token (id `a98f9cc48382cd62c78a8e217777b05f`) under My Profile > API Tokens of the login that created it.
  - Account permissions: D1, Workers R2 Storage, Queues and Workers Scripts edit, plus Account Settings read.
  - Zone permissions: DNS and Workers Routes edit.
- **Wrangler:** `.envrc` pins `CLOUDFLARE_ACCOUNT_ID` and exports the same token from the keychain
  (`heartbeat-cloudflare-api-token`), so no `wrangler login` is needed. To copy it there once (then `direnv allow`):
  `security add-generic-password -U -a "$USER" -s heartbeat-cloudflare-api-token -w "$(az keyvault secret show --vault-name kv-terraform-terraform --name tf-cloudflare-api-token --query value -o tsv)"`.
- **First `bin/tf` run in a fresh checkout:** `cd terraform/pulse-v2 && ../../bin/tf -f prod init`.

## Deploy a new release

1. Check the release notes for new bindings, migrations that need preparing, or new secrets
   (pulse-v2 `docs/deploy.md` §1–2).
2. Take a D1 bookmark, which is the rollback point for data:
   `npx wrangler@<version> d1 time-travel info pulse`.
3. Deploy:
   ```bash
   CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z
   ```
   The script:
   - downloads the bundle and checks its checksum;
   - fills in our `wrangler.jsonc`;
   - refuses to deploy if the bundle's bindings differ from ours (update `manifests/pulse-v2/wrangler.jsonc` to
     match first);
   - applies remote D1 migrations, then deploys.

   `--ref <git ref>` builds from `~/work/pulse-v2` instead, and `--bundle <tarball>` uses a local build.
4. Smoke test:
   ```bash
   for p in / /auth/signin /service-worker.js /manifest.webmanifest /api/v1/spaces; do
     curl -s -o /dev/null -w "$p %{http_code}\n" https://pulse.heartbeatchurch.com.au$p; done
   # expect 303, 200, 200, 200, 401
   ```
   Then sign in and open a page.

## Roll back

- **Code:** in the bundle directory or anywhere with direnv loaded:
  - `npx wrangler@<version> versions list --name pulse` to find the last good version;
  - `npx wrangler@<version> rollback <version-id> --name pulse` to return to it.

  Or redeploy the previous tag with `deploy.sh --release`.
- **Data:** `npx wrangler@<version> d1 time-travel restore pulse --bookmark <bookmark>`. This overwrites everything
  written since the bookmark.
- Migrations only move forward. A release that needs a migration rolled back needs a new release.

## Secrets

These live only in the Worker. List them with `wrangler secret list --name pulse`. To rotate one, run
`wrangler secret put <NAME> --name pulse`: it prompts for the value and never writes it to disk.

| Secret | Source |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | The Pulse web client in the Google Cloud console > Credentials. Redirect URI `https://pulse.heartbeatchurch.com.au/auth/callback` |
| `GDRIVE_SA_EMAIL`, `GDRIVE_SA_PRIVATE_KEY` | A key of the `pulse-drive-browser` service account: `client_email` and `private_key` from its JSON |
| `ADMIN_EMAILS` | Comma list of bootstrap admins |
| `HMAC_SECRET` | `openssl rand -base64 48 \| tr -d '\n' \| wrangler secret put HMAC_SECRET --name pulse`. Rotating it signs everyone out and voids open invites |

Until v1 is torn down (#45), `manifests/pulse-v2/secrets.sh` can also re-upload the Google and Drive values from v1's
Key Vault: `ADMIN_EMAILS=... CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z --secrets`.

## Rebuild from scratch

This is how it was first set up on 2026-10-22. Use it only if the stack is ever recreated. The Worker must exist
before its custom domain, and the hostname must be free.

```bash
cd terraform/pulse-v2 && ../../bin/tf -f prod init
../../bin/tf -f prod apply \
  -target=cloudflare_d1_database.pulse -target=cloudflare_r2_bucket.files -target=cloudflare_queue.email
cd ../.. && ADMIN_EMAILS=<admins> CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z --secrets --rotate-hmac
cd terraform/pulse-v2 && ../../bin/tf -f prod apply   # attaches the domain
```

R2 must be enabled once per account in the dashboard (error 10042 otherwise). `prevent_destroy` guards D1 and R2.

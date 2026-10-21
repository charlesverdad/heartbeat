# Pulse v2 on Cloudflare

Cloudflare resources for [pulse-v2](https://github.com/charlesverdad/pulse-v2): a Worker with D1 (`pulse`),
R2 (`pulse-files`), a queue (`pulse-email`) and the custom domain `pulse.heartbeatchurch.com.au`. The stack also holds
the Google service account behind Drive folder embeds (`drive.tf`). The Worker code goes up with wrangler:
`manifests/pulse-v2/deploy.sh` takes a prebuilt bundle and fills in our `wrangler.jsonc` (the D1 id from this stack's
outputs, `PUBLIC_ORIGIN` from `hostname` in `prod.tfvars`). It then applies D1 migrations and deploys.

Run everything from the repo root, in the nix shell with direnv loaded.

## Access

- **Tofu:** `bin/tf` loads the Cloudflare token (`tf-cloudflare-api-token` in `kv-terraform-terraform`). It is a
  *user* token (id `a98f9cc48382cd62c78a8e217777b05f`) under My Profile > API Tokens of the login that created it.
  - Account permissions: D1, Workers R2 Storage, Queues and Workers Scripts edit, plus Account Settings read.
  - Zone permissions: DNS and Workers Routes edit.
- **Google provider:** uses gcloud Application Default Credentials (`gcloud auth application-default login`).
- **Wrangler:** `.envrc` pins `CLOUDFLARE_ACCOUNT_ID` and exports the same token from the keychain
  (`heartbeat-cloudflare-api-token`), so no `wrangler login` is needed. To copy it there once (then `direnv allow`):
  `security add-generic-password -U -a "$USER" -s heartbeat-cloudflare-api-token -w "$(az keyvault secret show --vault-name kv-terraform-terraform --name tf-cloudflare-api-token --query value -o tsv)"`.

## Deploy

```bash
CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z   # or --ref <git ref> to build from pulse-v2
```

## Secrets

These live only in the Worker. Rotate one with `wrangler secret put <NAME> --name pulse`, which prompts for the value
and never writes it to disk.

| Secret | Source |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | The Pulse web client in the Google Cloud console > Credentials. Redirect URI `https://pulse.heartbeatchurch.com.au/auth/callback` |
| `GDRIVE_SA_EMAIL`, `GDRIVE_SA_PRIVATE_KEY` | A key of `pulse-drive-browser` (`drive.tf`): `client_email` and `private_key` from its JSON |
| `ADMIN_EMAILS` | Comma list of bootstrap admins |
| `HMAC_SECRET` | `openssl rand -base64 48 \| tr -d '\n' \| wrangler secret put HMAC_SECRET --name pulse`. Rotating it signs everyone out and voids open invites |

# Pulse v2 on Cloudflare

Cloudflare resources for [pulse-v2](https://github.com/charlesverdad/pulse-v2): a Worker with D1 (`pulse`),
R2 (`pulse-files`), a queue (`pulse-email`) and one custom domain. This stack owns the resources. The Worker code and
its secrets go up with wrangler: `manifests/pulse-v2/deploy.sh` builds or downloads a prebuilt bundle, fills in our
`wrangler.jsonc` (the D1 id from this stack's outputs, `PUBLIC_ORIGIN` from `hostname` in `prod.tfvars`), applies D1
migrations and deploys.

Run everything from the repo root in the nix shell. `bin/tf` loads the Cloudflare token from Key Vault.

## Before the first apply

- The Terraform Cloudflare token (`tf-cloudflare-api-token` in `kv-terraform-terraform`) needs these permissions on
  the Heartbeat account: **D1 Edit**, **Workers R2 Storage Edit**, **Queues Edit** and **Workers Scripts Edit**.
  On the zone it needs **DNS Edit** and **Workers Routes Edit**. If it was made for tunnels and DNS only, add these in
  the Cloudflare dashboard (My Profile > API Tokens).
- `npx wrangler@4.149.0 login` (or whatever version the bundle names). It deploys the Worker as you.
- Google OAuth client (the one v1 uses; the Google Cloud console only, no API for this): APIs & Services >
  Credentials > the Pulse web client > Authorized redirect URIs, add
  `https://pulse-v2.heartbeatchurch.com.au/auth/callback`. If the consent screen is *Internal*, only
  `@heartbeatchurch.com.au` accounts can sign in. v2 expects it published *External* so gmail partners can sign in.

## Stage 1: staging hostname (pulse-v2.heartbeatchurch.com.au)

```bash
cd terraform/pulse-v2
../../bin/tf -f prod init
# The custom domain needs the Worker to exist, so create the data resources first:
../../bin/tf -f prod apply \
  -target=cloudflare_d1_database.pulse -target=cloudflare_r2_bucket.files -target=cloudflare_queue.email
cd ../..

# First deploy: uploads the secrets (Google sign-in + Drive from v1's Key Vault, a new HMAC_SECRET).
ADMIN_EMAILS=charles@heartbeatchurch.com.au CONFIRM=yes manifests/pulse-v2/deploy.sh --secrets --rotate-hmac

cd terraform/pulse-v2 && ../../bin/tf -f prod apply   # attaches pulse-v2.heartbeatchurch.com.au
```

Then sign in at https://pulse-v2.heartbeatchurch.com.au and work through `/admin` > Get started (pulse-v2
`docs/owner-setup.md` section 6). Email stays **Off**: v1's Gmail SMTP password doesn't carry over (v2 sends through
Cloudflare Email or Resend). Content entered now stays: promotion renames the hostname and keeps the same Worker and
database.

Later deploys: `CONFIRM=yes manifests/pulse-v2/deploy.sh` (from `origin/main`), or `--release vX.Y.Z` once releases
are tagged. Add `--secrets` (with `ADMIN_EMAILS`) to refresh secrets. Leave out `--rotate-hmac`: it signs everyone out
and voids open invites.

## Stage 2: promote to pulse.heartbeatchurch.com.au

v1 still holds that name with a tunnel CNAME (state `vm-hb-pulse`). Pulse is down between the first and last step,
usually a few minutes.

1. Add `https://pulse.heartbeatchurch.com.au/auth/callback` to the Google OAuth client.
2. Free the name: `cd terraform/vm-hb-pulse && ../../bin/tf -f prod destroy -target=cloudflare_record.pulse`.
   (The follow-up PR removes the v1 stacks entirely.)
3. Set `hostname = "pulse.heartbeatchurch.com.au"` in `prod.tfvars`, then `../../bin/tf -f prod apply` here. This
   replaces the staging domain.
4. `CONFIRM=yes manifests/pulse-v2/deploy.sh`, which picks up the new `PUBLIC_ORIGIN`. Everyone signs in again.
5. Remove the staging redirect URI from the Google client.

Phones that had v1 installed still have its service worker. v2's `/service-worker.js` unregisters it on the next
visit.

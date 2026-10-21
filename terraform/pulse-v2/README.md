# Pulse v2 on Cloudflare

Cloudflare resources for [pulse-v2](https://github.com/charlesverdad/pulse-v2): a Worker with D1 (`pulse`),
R2 (`pulse-files`), a queue (`pulse-email`) and the custom domain `pulse.heartbeatchurch.com.au`. This stack owns the
resources. The Worker code and its secrets go up with wrangler: `manifests/pulse-v2/deploy.sh` takes a prebuilt
bundle and fills in our `wrangler.jsonc` (the D1 id from this stack's outputs, `PUBLIC_ORIGIN` from `hostname` in
`prod.tfvars`). It then applies D1 migrations and deploys.

Run everything from the repo root in the nix shell. `bin/tf` loads the Cloudflare token from Key Vault.

## Before the first apply

- The Terraform Cloudflare token (`tf-cloudflare-api-token` in `kv-terraform-terraform`) needs these permissions on
  the Heartbeat account: **D1 Edit**, **Workers R2 Storage Edit**, **Queues Edit** and **Workers Scripts Edit**.
  On the zone it needs **DNS Edit** and **Workers Routes Edit**. If it was made for tunnels and DNS only, add these in
  the Cloudflare dashboard. It is a *user* token (id `a98f9cc48382cd62c78a8e217777b05f`), so it sits under
  My Profile > API Tokens of the login that created it, not under the account's API Tokens page. Editing a token
  shows its id in the URL.
- `npx wrangler@4.149.0 login` (the version the bundle's `DEPLOY.md` names). It deploys the Worker as you.
- Google sign-in needs nothing new: v2 reuses v1's OAuth client, and `https://pulse.heartbeatchurch.com.au/auth/callback`
  (the same path v1 uses) is already an authorized redirect URI.

## First deploy

v1 still holds `pulse.heartbeatchurch.com.au` with a tunnel CNAME (state `vm-hb-pulse`). Pulse is unreachable between
step 3 and step 4, usually under a minute.

```bash
# 1. Data resources first: the custom domain needs the Worker to exist.
cd terraform/pulse-v2
../../bin/tf -f prod init
../../bin/tf -f prod apply \
  -target=cloudflare_d1_database.pulse -target=cloudflare_r2_bucket.files -target=cloudflare_queue.email
cd ../..

# 2. Deploy v0.2.0, with secrets (Google sign-in and Drive from v1's Key Vault, plus a new HMAC_SECRET).
ADMIN_EMAILS=charles@heartbeatchurch.com.au CONFIRM=yes manifests/pulse-v2/deploy.sh \
  --release v0.2.0 --secrets --rotate-hmac
#    (until v0.2.0 is published: --bundle ~/work/pulse-v2/.claude/worktrees/rel-020/dist/pulse-v0.2.0.tar.gz)

# 3. Free the name: delete v1's tunnel CNAME (the follow-up PR removes the v1 stacks entirely).
cd terraform/vm-hb-pulse && ../../bin/tf -f prod init
../../bin/tf -f prod destroy -target=cloudflare_record.pulse

# 4. Attach pulse.heartbeatchurch.com.au to the Worker.
cd ../pulse-v2 && ../../bin/tf -f prod apply
```

Then sign in at https://pulse.heartbeatchurch.com.au and work through `/admin` > Get started (pulse-v2
`docs/owner-setup.md` section 6). Email stays **Off**: v1's Gmail SMTP password doesn't carry over (v2 sends through
Cloudflare Email or Resend). Phones that had v1 installed still have its service worker. v2's `/service-worker.js`
unregisters it on the next visit.

Rollback while v1's containers still run: `tofu destroy -target=cloudflare_workers_custom_domain.pulse` here, then
`tf -f prod apply` in `terraform/vm-hb-pulse` to restore the CNAME.

## Later deploys

`CONFIRM=yes manifests/pulse-v2/deploy.sh --release vX.Y.Z` (or `--ref <git ref>` to build from pulse-v2 directly).
Add `--secrets` (with `ADMIN_EMAILS`) to refresh secrets. Leave out `--rotate-hmac`: it signs everyone out and voids
open invites.

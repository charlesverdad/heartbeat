# terraform/screens

Cloudflare Pages hosting for **Heartbeat Screens** (`brand/screens`): the welcome and ring countdowns,
starting soon, be right back and loading screens.

| Resource | What |
|---|---|
| `cloudflare_pages_project.screens` | Pages project `screens`, production branch `main`, direct upload (no Git source) |
| `cloudflare_pages_domain.screens` | Custom domain `screens.heartbeatchurch.com.au` on the project |
| `cloudflare_dns_record.screens` | Proxied CNAME `screens` → the project's `*.pages.dev` subdomain |

This stack creates the hosting only. Content is deployed by GitHub Actions
(`.github/workflows/screens.yml`): it runs `npm test` and `npm run build` in `brand/screens`, then
`wrangler pages deploy dist`. Pushes to `main` go to production; pull requests get a preview URL in the
job summary. So there is no Cloudflare GitHub app to install, and Terraform never sees the site files.

Uses Cloudflare provider **v5** (other stacks are still on v4; each stack has its own state, so this is safe).

## Apply

```bash
cd terraform/screens
../../bin/tf -f prod init
../../bin/tf -f prod plan
../../bin/tf -f prod apply
```

`bin/tf` loads `CLOUDFLARE_API_TOKEN` from Azure Key Vault (`kv-terraform-terraform` /
`tf-cloudflare-api-token`), so run `az login` first. That token needs **Account › Cloudflare Pages ›
Edit** on top of the DNS and tunnel permissions the other stacks use. State lives in the shared Azure
backend under `screens/prod.tfstate`.

## GitHub Actions setup (once)

The workflow needs its own narrow token, separate from the Terraform one:

1. Cloudflare dashboard › My Profile › API Tokens › Create token › Custom: **Account › Cloudflare
   Pages › Edit**, limited to the Heartbeat account.
2. Store it straight into GitHub without saving it to a file (paste at the prompt):

   ```bash
   gh secret set CLOUDFLARE_PAGES_TOKEN --repo charlesverdad/heartbeat
   gh variable set CLOUDFLARE_ACCOUNT_ID --repo charlesverdad/heartbeat --body d26a8771162442a563371ea8097acc89
   ```

3. Re-run the workflow (Actions › screens › Run workflow) or push a change under `brand/screens/`.

## Outputs

`project_name`, `pages_dev_url`, `url`.

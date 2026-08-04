# DNS

Standalone Cloudflare DNS records for `heartbeatchurch.com.au`.

Records belonging to a service that already has its own Terraform stack stay
with that service (e.g. `terraform/vm-bookstack/`, `terraform/website-container/`).
This stack holds records that point at infrastructure we do not manage —
third-party hosting, verification tokens, and similar.

## Current records

| Type | Name          | Value                              | Purpose                              |
|------|---------------|------------------------------------|--------------------------------------|
| A    | `ipt`         | `185.158.133.1`                    | Lovable-hosted site, DNS-only        |
| TXT  | `_lovable.ipt`| `lovable_verify=cbb9...720a`       | Lovable domain ownership verification|

The A record is intentionally **not proxied** — Lovable terminates TLS itself
and requires DNS-only for verification to pass.

## Usage

```bash
cd terraform/dns
../../bin/tf -f prod init
../../bin/tf -f prod plan
../../bin/tf -f prod apply
```

The `bin/tf` wrapper pulls the Cloudflare API token from Azure Key Vault
(`kv-terraform-terraform` / `tf-cloudflare-api-token`), so `az login` is
required first.

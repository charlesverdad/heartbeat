# Pulse v2 (~/work/pulse-v2): a Cloudflare Worker with D1, R2 and a queue.
#
# Tofu owns the resources and the custom domains. The Worker code and its secrets
# are deployed with wrangler by manifests/pulse-v2/deploy.sh, which reads the
# D1 id and PUBLIC_ORIGIN from this stack's outputs.
#
# Rollout and promotion steps: README.md.

resource "cloudflare_d1_database" "pulse" {
  account_id            = var.cloudflare_account_id
  name                  = "pulse"
  primary_location_hint = "oc"

  # Deleting this deletes every page. D1 Time Travel only covers the database's lifetime.
  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_r2_bucket" "files" {
  account_id = var.cloudflare_account_id
  name       = "pulse-files"
  location   = "oc"

  lifecycle {
    prevent_destroy = true
  }
}

resource "cloudflare_queue" "email" {
  account_id = var.cloudflare_account_id
  queue_name = "pulse-email"
}

# Creates the proxied DNS record and certificate. Needs the Worker to exist
# (first deploy) and fails if another record already uses the name.
resource "cloudflare_workers_custom_domain" "pulse" {
  account_id = var.cloudflare_account_id
  zone_id    = var.cloudflare_zone_id
  hostname   = var.hostname
  service    = var.worker_name
}

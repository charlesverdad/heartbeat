# Heartbeat Screens (brand/screens): the static countdown and holding screens.
#
# This stack owns the Pages project, its custom domain and the DNS record.
# It does not upload the site: the project is a "direct upload" project (no
# `source` block), and .github/workflows/screens.yml builds brand/screens and
# deploys dist/ with `wrangler pages deploy`. Keeping the build in GitHub
# Actions means the Cloudflare GitHub app is not needed and the build runs the
# same `npm run build` + tests as locally.

resource "cloudflare_pages_project" "screens" {
  account_id        = var.cloudflare_account_id
  name              = var.project_name
  production_branch = var.production_branch
}

# Attach the custom domain to the project. Cloudflare validates it through
# the CNAME below and issues the certificate.
resource "cloudflare_pages_domain" "screens" {
  account_id   = var.cloudflare_account_id
  project_name = cloudflare_pages_project.screens.name
  name         = var.domain_name
}

resource "cloudflare_dns_record" "screens" {
  zone_id = var.cloudflare_zone_id
  name    = var.domain_name
  content = cloudflare_pages_project.screens.subdomain
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Terraform (terraform/screens) - Heartbeat Screens on Cloudflare Pages"
}

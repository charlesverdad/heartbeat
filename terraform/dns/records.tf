# Standalone DNS records for heartbeatchurch.com.au.
#
# Records that belong to a service with its own Terraform stack (the VM, the
# Ghost container app, BookStack, Pulse, ...) live alongside that service.
# This file is for records pointing at things we do not manage ourselves.

# ipt.heartbeatchurch.com.au -> Lovable hosting
# Lovable requires the record to be DNS-only (not proxied) so it can terminate
# TLS and verify the domain.
resource "cloudflare_record" "ipt" {
  zone_id = var.cloudflare_zone_id
  name    = "ipt"
  content = var.ipt_ip_address
  type    = "A"
  proxied = false
  ttl     = 1
  comment = "Managed by Terraform - Lovable-hosted site"
}

# Domain ownership verification for the Lovable site above.
resource "cloudflare_record" "ipt_lovable_verify" {
  zone_id = var.cloudflare_zone_id
  name    = "_lovable.ipt"
  content = var.ipt_lovable_verify
  type    = "TXT"
  ttl     = 1
  comment = "Managed by Terraform - Lovable domain verification for ipt"
}

# Standalone DNS records for heartbeatchurch.com.au.
#
# Records that belong to a service with its own Terraform stack (the VM, the
# Ghost container app, BookStack, Pulse, ...) live alongside that service.
# This file is for records pointing at things we do not manage ourselves, so
# every record names an owner in its comment - they are usually the only person
# who knows whether it is still needed.

# ipt.heartbeatchurch.com.au -> Lovable hosting.
# Must stay DNS-only: Lovable terminates TLS itself and proxying breaks
# its domain verification.
resource "cloudflare_record" "ipt" {
  zone_id = var.cloudflare_zone_id
  name    = "ipt"
  content = "185.158.133.1"
  type    = "A"
  proxied = false
  ttl     = 1
  comment = "Terraform - Lovable site - owner: Kevin Kim (GC)"
}

# Domain ownership verification for the Lovable site above.
resource "cloudflare_record" "ipt_lovable_verify" {
  zone_id = var.cloudflare_zone_id
  name    = "_lovable.ipt"
  content = "lovable_verify=cbb952e51ebcb3f1bec1055d56005695990ac4898525dd64de8b12eb9dee720a"
  type    = "TXT"
  ttl     = 1
  comment = "Terraform - Lovable verification - owner: Kevin Kim (GC)"
}

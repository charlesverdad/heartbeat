# Resend for Pulse's account email (Invite, Welcome, ...), sent from var.resend_domain.
#
# The Resend provider is a community one (softwarehuset-com/resend; Resend publishes none), pinned exactly in
# providers.tf. It authenticates with a full-access key, RESEND_API_KEY, which bin/tf loads from Key Vault.
#
# The send-only key and the webhook's signing secret are only returned when they are created, so they live in this
# stack's state. manifests/pulse-v2/secrets.sh reads them from the outputs and uploads them to the Worker.
#
# First apply is two steps, because the DNS records come from the domain and are unknown until it exists:
#   ../../bin/tf -f prod apply -target=resend_domain.mail
#   ../../bin/tf -f prod apply

resource "resend_domain" "mail" {
  name = var.resend_domain

  # Region and return path cannot change without replacing the domain (and its key and DNS records).
  region = var.resend_region

  capabilities = {
    sending   = "enabled"
    receiving = "disabled"
  }

  tls = "opportunistic"

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  zone_name = "heartbeatchurch.com.au"

  # cloudflare_dns_record wants full names; Resend's may be relative to the zone ("send.mail").
  resend_records = {
    for r in resend_domain.mail.records :
    "${r.record}-${r.type}-${r.name}" => merge(r, {
      fqdn = endswith(r.name, local.zone_name) ? r.name : "${r.name}.${local.zone_name}"
    })
  }
}

resource "cloudflare_dns_record" "resend" {
  for_each = local.resend_records

  zone_id  = var.cloudflare_zone_id
  name     = each.value.fqdn
  type     = each.value.type
  content  = each.value.value
  priority = each.value.type == "MX" ? each.value.priority : null
  proxied  = false
  ttl      = 1
  comment  = "Terraform (terraform/pulse-v2) - Resend ${each.value.record} for ${var.resend_domain}"
}

# Asks Resend to re-check DNS once; the status settles to verified on later refreshes.
resource "resend_domain_verification" "mail" {
  domain_id = resend_domain.mail.id

  depends_on = [cloudflare_dns_record.resend]
}

# Send-only, and only from this domain, so the Worker never holds the full-access key. It cannot remove addresses
# from Resend's suppression list: Pulse says so, and that is done by hand in the dashboard (pulse-v2 owner-setup §5).
resource "resend_api_key" "pulse" {
  name       = "pulse-worker"
  permission = "sending_access"
  domain_id  = resend_domain.mail.id
}

resource "resend_webhook" "pulse" {
  endpoint = "https://${var.hostname}/api/webhooks/resend"
  events   = ["email.delivered", "email.bounced", "email.complained"]
}

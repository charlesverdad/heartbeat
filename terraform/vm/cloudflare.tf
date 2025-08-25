# Random secret for Cloudflare tunnel
resource "random_string" "tunnel_secret" {
  length  = 64
  special = false
}

# Create a Cloudflare tunnel for SSH access to the VM
resource "cloudflare_zero_trust_tunnel_cloudflared" "vm_ssh" {
  account_id = var.cloudflare_account_id
  name       = "${var.vm_name}-${var.environment}-ssh-tunnel"
  secret     = base64encode(random_string.tunnel_secret.result)
}

# DNS record pointing to the tunnel
resource "cloudflare_record" "vm_ssh" {
  zone_id = var.cloudflare_zone_id
  name    = replace(var.domain_name, ".heartbeatchurch.com.au", "")
  content = cloudflare_zero_trust_tunnel_cloudflared.vm_ssh.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - SSH tunnel for ${var.vm_name}-${var.environment}"
}

# Tunnel configuration for SSH access
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "vm_ssh" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.vm_ssh.id

  config {
    ingress_rule {
      hostname = var.domain_name
      service  = "ssh://localhost:22"
    }
    
    # Catch-all rule (required)
    ingress_rule {
      service = "http_status:404"
    }
  }
}

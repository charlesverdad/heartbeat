# Cloudflare Tunnel
resource "cloudflare_tunnel" "ghost" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-${var.environment}-tunnel"
  secret     = base64encode(random_password.tunnel_secret.result)
}

# Random secret for Cloudflare tunnel
resource "random_password" "tunnel_secret" {
  length  = 32
  special = false
}

# Cloudflare Tunnel Configuration
resource "cloudflare_tunnel_config" "ghost" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_tunnel.ghost.id

  config {
    warp_routing {
      enabled = false
    }
    
    ingress_rule {
      hostname = "${var.subdomain}.${var.domain_name}"
      service  = "https://${azurerm_container_app.ghost.latest_revision_fqdn}"
      
      origin_request {
        connect_timeout          = "1m"
        tls_timeout             = "1m"
        tcp_keep_alive          = "1m"
        no_happy_eyeballs       = false
        keep_alive_connections  = 1024
        keep_alive_timeout      = "1m30s"
        http_host_header        = "${var.subdomain}.${var.domain_name}"
        origin_server_name      = "${var.subdomain}.${var.domain_name}"
      }
    }
    
    # Catch-all rule
    ingress_rule {
      service = "http_status:404"
    }
  }
}

# DNS record pointing to Cloudflare tunnel
resource "cloudflare_record" "ghost" {
  zone_id = var.cloudflare_zone_id
  name    = var.subdomain
  value   = cloudflare_tunnel.ghost.cname
  type    = "CNAME"
  proxied = true
  
  comment = "Ghost blog via Cloudflare tunnel"
}

# Store tunnel token in Key Vault
resource "azurerm_key_vault_secret" "tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = cloudflare_tunnel.ghost.tunnel_token
  key_vault_id = azurerm_key_vault.ghost.id

  depends_on = [azurerm_role_assignment.kv_admin]

  tags = var.common_tags
}

# Cloudflare Access Application for admin protection
resource "cloudflare_access_application" "ghost_admin" {
  zone_id          = var.cloudflare_zone_id
  name             = "${var.project_name}-${var.environment}-admin"
  domain           = "${var.subdomain}.${var.domain_name}/ghost"
  type             = "self_hosted"
  session_duration = "24h"
  
  cors_headers {
    allowed_methods = ["GET", "POST", "OPTIONS"]
    allowed_origins = ["https://${var.subdomain}.${var.domain_name}"]
    allow_credentials = true
    max_age = 300
  }
}

# Cloudflare Access Policy - Allow specific emails (configure as needed)
resource "cloudflare_access_policy" "ghost_admin_policy" {
  application_id = cloudflare_access_application.ghost_admin.id
  zone_id        = var.cloudflare_zone_id
  name           = "Allow Admin Users"
  precedence     = 1
  decision       = "allow"

  include {
    email = var.admin_emails
  }
}

# Optional: Cloudflare Page Rules for caching
resource "cloudflare_page_rule" "ghost_cache" {
  zone_id  = var.cloudflare_zone_id
  target   = "${var.subdomain}.${var.domain_name}/*"
  priority = 1

  actions {
    cache_level = "cache_everything"
    edge_cache_ttl = 86400  # 24 hours
    
    # Cache static content longer
    cache_ttl_by_status {
      codes = "200-299"
      ttl   = 86400
    }
    
    cache_ttl_by_status {
      codes = "300-399"
      ttl   = 3600
    }
    
    cache_ttl_by_status {
      codes = "400-499"
      ttl   = 300
    }
  }
}

# Page rule to bypass cache for admin pages
resource "cloudflare_page_rule" "ghost_admin_no_cache" {
  zone_id  = var.cloudflare_zone_id
  target   = "${var.subdomain}.${var.domain_name}/ghost/*"
  priority = 2

  actions {
    cache_level = "bypass"
  }
}

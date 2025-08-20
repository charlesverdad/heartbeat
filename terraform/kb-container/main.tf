# Data sources
data "azurerm_client_config" "current" {}

# Random string for naming
resource "random_string" "suffix" {
  length  = 4
  special = false
  upper   = false
}

# Resource group for BookStack infrastructure
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location = var.location
  tags     = var.tags
}

# Azure Key Vault for storing secrets
resource "azurerm_key_vault" "main" {
  name                = "kv-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  # Enable RBAC authorization instead of access policies
  enable_rbac_authorization = true

  soft_delete_retention_days = 7
  purge_protection_enabled   = false

  network_acls {
    default_action = "Allow"
    bypass         = "AzureServices"
  }

  tags = var.tags
}

# User-Assigned Managed Identity for the Container App
resource "azurerm_user_assigned_identity" "main" {
  name                = "id-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# Role assignment to allow the identity to access Key Vault secrets
resource "azurerm_role_assignment" "keyvault_secrets_user" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Role assignment for current user to manage secrets during deployment
resource "azurerm_role_assignment" "current_user_keyvault_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Storage account for Azure Files
resource "azurerm_storage_account" "main" {
  name                     = "st${replace(var.project_name, "-", "")}${var.environment}${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  tags = var.tags
}

# Azure Files share for BookStack data (reduced since uploads go to MinIO)
resource "azurerm_storage_share" "bookstack_data" {
  name                 = "bookstack-data"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 5
}

# Azure Files share for MariaDB data
resource "azurerm_storage_share" "mariadb_data" {
  name                 = "mariadb-data"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 5
}

# Azure Files share for MinIO data
resource "azurerm_storage_share" "minio_data" {
  name                 = "minio-data"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 10
}

# Container Apps Environment
resource "azurerm_container_app_environment" "main" {
  name                = "cae-${var.project_name}-${var.environment}-${random_string.suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

# Generate random passwords
resource "random_password" "mysql_root" {
  length  = 16
  special = true
}

resource "random_password" "mysql_user" {
  length  = 16
  special = true
}

# Generate BookStack APP_KEY
resource "random_password" "app_key" {
  length  = 32
  special = true
}

# Generate MinIO credentials
resource "random_password" "minio_root_user" {
  length  = 16
  special = false
  upper   = true
  lower   = true
  numeric = true
}

resource "random_password" "minio_root_password" {
  length  = 24
  special = true
}


# Note: Google OAuth 2.0 credentials will be created manually in Google Cloud Console
# and then updated in Azure Key Vault

# Store secrets in Key Vault
resource "azurerm_key_vault_secret" "mysql_root_password" {
  name         = "mysql-root-password"
  value        = random_password.mysql_root.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "mysql_user_password" {
  name         = "mysql-user-password"
  value        = random_password.mysql_user.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "bookstack_app_key" {
  name         = "bookstack-app-key"
  value        = "base64:${base64encode(random_password.app_key.result)}"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# Store Google OAuth credentials (placeholder - to be updated manually)
resource "azurerm_key_vault_secret" "google_client_id" {
  name         = "google-client-id"
  value        = "placeholder-will-be-replaced-with-google-oauth-client-id"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
  
  lifecycle {
    ignore_changes = [value]
  }
}

resource "azurerm_key_vault_secret" "google_client_secret" {
  name         = "google-client-secret"
  value        = "placeholder-will-be-replaced-with-google-oauth-client-secret"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
  
  lifecycle {
    ignore_changes = [value]
  }
}

# Store Gmail app password
resource "azurerm_key_vault_secret" "gmail_app_password" {
  name         = "gmail-app-password"
  value        = "placeholder-gmail-app-password-replace-with-actual-value"
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
  
  lifecycle {
    ignore_changes = [value]
  }
}

# Store MinIO credentials in Key Vault
resource "azurerm_key_vault_secret" "minio_root_user" {
  name         = "minio-root-user"
  value        = random_password.minio_root_user.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

resource "azurerm_key_vault_secret" "minio_root_password" {
  name         = "minio-root-password"
  value        = random_password.minio_root_password.result
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# Cloudflare Tunnel Resources
# Create a tunnel that will connect to the BookStack container app
resource "cloudflare_zero_trust_tunnel_cloudflared" "bookstack" {
  account_id = var.cloudflare_account_id
  name       = "${var.project_name}-${var.environment}-tunnel"
  secret     = base64encode(random_string.tunnel_secret.result)
}

# Random secret for Cloudflare tunnel
resource "random_string" "tunnel_secret" {
  length  = 64
  special = false
}

# Store Cloudflare tunnel token in Key Vault
resource "azurerm_key_vault_secret" "cloudflare_tunnel_token" {
  name         = "cloudflare-tunnel-token"
  value        = cloudflare_zero_trust_tunnel_cloudflared.bookstack.tunnel_token
  key_vault_id = azurerm_key_vault.main.id
  
  depends_on = [
    azurerm_role_assignment.current_user_keyvault_admin
  ]
}

# DNS record pointing to the tunnel
resource "cloudflare_record" "bookstack" {
  zone_id = var.cloudflare_zone_id
  name    = replace(var.domain_name, ".heartbeatchurch.com.au", "")
  value   = cloudflare_zero_trust_tunnel_cloudflared.bookstack.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - points to Cloudflare tunnel for ${var.project_name}-${var.environment}"
}

# DNS record for assets subdomain (MinIO)
resource "cloudflare_record" "assets" {
  zone_id = var.cloudflare_zone_id
  name    = "assets.${replace(var.domain_name, ".heartbeatchurch.com.au", "")}"
  value   = cloudflare_zero_trust_tunnel_cloudflared.bookstack.cname
  type    = "CNAME"
  proxied = true
  ttl     = 1
  comment = "Managed by Terraform - points to Cloudflare tunnel for ${var.project_name}-${var.environment} assets"
}

# Tunnel configuration to route traffic to BookStack app and MinIO assets
resource "cloudflare_zero_trust_tunnel_cloudflared_config" "bookstack" {
  account_id = var.cloudflare_account_id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.bookstack.id

  config {
    # Route main BookStack domain to port 80
    ingress_rule {
      hostname = var.domain_name
      service  = "http://localhost:80"
      
      origin_request {
        http_host_header = var.domain_name
      }
    }
    
    # Route assets domain to MinIO on port 9080
    ingress_rule {
      hostname = "assets.${replace(var.domain_name, ".heartbeatchurch.com.au", "")}.heartbeatchurch.com.au"
      service  = "http://localhost:9080"
      
      origin_request {
        http_host_header = "assets.${replace(var.domain_name, ".heartbeatchurch.com.au", "")}.heartbeatchurch.com.au"
      }
    }
    
    # Catch-all rule (required)
    ingress_rule {
      service = "http_status:404"
    }
  }
}

# Container App with BookStack, MariaDB, Redis, and Cloudflare tunnel
resource "azurerm_container_app" "bookstack" {
  name                         = "ca-bookstack-${var.environment}-${random_string.suffix.result}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  template {
    min_replicas = 1
    max_replicas = 1

    volume {
      name         = "bookstack-data"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.bookstack_data.name
    }

    volume {
      name         = "mariadb-data"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.mariadb_data.name
    }

    volume {
      name         = "minio-data"
      storage_type = "AzureFile"
      storage_name = azurerm_container_app_environment_storage.minio_data.name
    }

    # Init container to fix permissions on Azure Files
    init_container {
      name   = "permission-fix"
      image  = "busybox:latest"
      cpu    = 0.1
      memory = "0.1Gi"
      
      command = ["/bin/sh"]
      args = [
        "-c",
        "chown -R 1000:1000 /config && mkdir -p /config/www/uploads /config/www/storage && chmod -R 755 /config/www/uploads /config/www/storage && chown -R 1000:1000 /config/www/uploads /config/www/storage"
      ]
      
      volume_mounts {
        name = "bookstack-data"
        path = "/config"
      }
    }



    # BookStack container
    container {
      name   = "bookstack"
      image  = "lscr.io/linuxserver/bookstack:version-v25.02"
      cpu    = 0.4
      memory = "0.95Gi"

      env {
        name  = "PUID"
        value = "1000"
      }

      env {
        name  = "PGID"
        value = "1000"
      }

      env {
        name  = "TZ"
        value = "Australia/Sydney"
      }

      env {
        name  = "APP_URL"
        value = "https://${var.domain_name}"
      }

      env {
        name        = "APP_KEY"
        secret_name = "bookstack-app-key"
      }

      # Database connection - Use 127.0.0.1 to force TCP instead of socket
      env {
        name  = "DB_HOST"
        value = "127.0.0.1"
      }

      env {
        name  = "DB_PORT"
        value = "3306"
      }

      env {
        name  = "DB_DATABASE"
        value = "bookstack"
      }

      env {
        name  = "DB_USERNAME"
        value = "bookstack"
      }

      env {
        name        = "DB_PASSWORD"
        secret_name = "mysql-user-password"
      }

      # Add database connection timeout and retry settings
      env {
        name  = "DB_TIMEOUT"
        value = "60"
      }

      # Add custom init script to wait for database and fix permissions
      env {
        name  = "CUSTOM_INIT"
        value = "true"
      }

      # Configure S3 storage using MinIO
      env {
        name  = "STORAGE_TYPE"
        value = "s3"
      }

      env {
        name  = "STORAGE_S3_KEY"
        secret_name = "minio-root-user"
      }

      env {
        name  = "STORAGE_S3_SECRET"
        secret_name = "minio-root-password"
      }

      env {
        name  = "STORAGE_S3_BUCKET"
        value = "bookstack-uploads"
      }

      env {
        name  = "STORAGE_S3_ENDPOINT"
        value = "http://127.0.0.1:9080"
      }

      env {
        name  = "STORAGE_URL"
        value = "https://assets.${replace(var.domain_name, ".heartbeatchurch.com.au", "")}.heartbeatchurch.com.au/bookstack-uploads"
      }


      # Redis configuration for sessions/cache
      env {
        name  = "REDIS_SERVERS"
        value = "localhost:6379:1"
      }

      env {
        name  = "CACHE_DRIVER"
        value = "redis"
      }

      env {
        name  = "SESSION_DRIVER"
        value = "redis"
      }

      # Google OAuth 2.0 Social Authentication
      env {
        name        = "GOOGLE_APP_ID"
        secret_name = "google-client-id"
      }

      env {
        name        = "GOOGLE_APP_SECRET"
        secret_name = "google-client-secret"
      }

      env {
        name  = "GOOGLE_AUTO_REGISTER"
        value = "true"
      }

      env {
        name  = "GOOGLE_AUTO_CONFIRM_EMAIL"
        value = "true"
      }

      # SMTP configuration
      env {
        name  = "MAIL_DRIVER"
        value = "smtp"
      }

      env {
        name  = "MAIL_HOST"
        value = "smtp.gmail.com"
      }

      env {
        name  = "MAIL_PORT"
        value = "587"
      }

      env {
        name  = "MAIL_USERNAME"
        value = "hello@heartbeatchurch.com.au"
      }

      env {
        name        = "MAIL_PASSWORD"
        secret_name = "gmail-app-password"
      }

      env {
        name  = "MAIL_ENCRYPTION"
        value = "tls"
      }

      env {
        name  = "MAIL_FROM_ADDRESS"
        value = "hello@heartbeatchurch.com.au"
      }

      env {
        name  = "MAIL_FROM_NAME"
        value = "Heartbeat Church"
      }

      volume_mounts {
        name = "bookstack-data"
        path = "/config"
      }
    }

    # MariaDB container
    container {
      name   = "mariadb"
      image  = "lscr.io/linuxserver/mariadb:11.4.4"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "PUID"
        value = "1000"
      }

      env {
        name  = "PGID"
        value = "1000"
      }

      env {
        name  = "TZ"
        value = "Australia/Sydney"
      }

      env {
        name        = "MYSQL_ROOT_PASSWORD"
        secret_name = "mysql-root-password"
      }

      env {
        name  = "MYSQL_DATABASE"
        value = "bookstack"
      }

      env {
        name  = "MYSQL_USER"
        value = "bookstack"
      }

      env {
        name        = "MYSQL_PASSWORD"
        secret_name = "mysql-user-password"
      }

      volume_mounts {
        name = "mariadb-data"
        path = "/config"
      }
    }

    # Redis container
    container {
      name   = "redis"
      image  = "redis:7-alpine"
      cpu    = 0.1
      memory = "0.15Gi"

      args = [
        "redis-server",
        "--appendonly",
        "yes"
      ]
    }

    # MinIO S3-compatible storage container
    container {
      name   = "minio"
      image  = "minio/minio:latest"
      cpu    = 0.15
      memory = "0.3Gi"
      
      command = ["/bin/sh"]
      args = [
        "-c",
        "mkdir -p /data/bookstack-uploads && /usr/bin/minio server /data --console-address :9090 --address :9080"
      ]
      
      env {
        name        = "MINIO_ROOT_USER"
        secret_name = "minio-root-user"
      }
      
      env {
        name        = "MINIO_ROOT_PASSWORD"
        secret_name = "minio-root-password"
      }
      
      volume_mounts {
        name = "minio-data"
        path = "/data"
      }
    }

    # MinIO setup sidecar container to create bucket with public access
    container {
      name   = "minio-setup"
      image  = "minio/mc:latest"
      cpu    = 0.1
      memory = "0.1Gi"
      
      command = ["/bin/sh"]
      args = [
        "-c",
        "while ! /usr/bin/mc alias set myminio http://127.0.0.1:9080 $(MINIO_ROOT_USER) $(MINIO_ROOT_PASSWORD) 2>/dev/null; do echo 'Waiting for MinIO...'; sleep 5; done && /usr/bin/mc mb myminio/bookstack-uploads --ignore-existing && /usr/bin/mc anonymous set public myminio/bookstack-uploads && echo 'MinIO bucket setup complete'"
      ]
      
      env {
        name        = "MINIO_ROOT_USER"
        secret_name = "minio-root-user"
      }
      
      env {
        name        = "MINIO_ROOT_PASSWORD"
        secret_name = "minio-root-password"
      }
    }

    # Cloudflare tunnel container
    container {
      name   = "cloudflared"
      image  = "cloudflare/cloudflared:latest"
      cpu    = 0.1
      memory = "0.1Gi"
      
      args = [
        "tunnel",
        "run",
        "--token",
        "$(TUNNEL_TOKEN)"
      ]
      
      env {
        name        = "TUNNEL_TOKEN"
        secret_name = "cloudflare-tunnel-token"
      }
    }
  }

  # Secrets configuration
  secret {
    name                = "mysql-root-password"
    key_vault_secret_id = azurerm_key_vault_secret.mysql_root_password.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "mysql-user-password"
    key_vault_secret_id = azurerm_key_vault_secret.mysql_user_password.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "bookstack-app-key"
    key_vault_secret_id = azurerm_key_vault_secret.bookstack_app_key.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "google-client-id"
    key_vault_secret_id = azurerm_key_vault_secret.google_client_id.versionless_id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "google-client-secret"
    key_vault_secret_id = azurerm_key_vault_secret.google_client_secret.versionless_id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "gmail-app-password"
    key_vault_secret_id = azurerm_key_vault_secret.gmail_app_password.versionless_id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "cloudflare-tunnel-token"
    key_vault_secret_id = azurerm_key_vault_secret.cloudflare_tunnel_token.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "minio-root-user"
    key_vault_secret_id = azurerm_key_vault_secret.minio_root_user.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  secret {
    name                = "minio-root-password"
    key_vault_secret_id = azurerm_key_vault_secret.minio_root_password.id
    identity            = azurerm_user_assigned_identity.main.id
  }

  depends_on = [
    azurerm_role_assignment.keyvault_secrets_user,
    azurerm_container_app_environment_storage.bookstack_data,
    azurerm_container_app_environment_storage.mariadb_data,
    azurerm_container_app_environment_storage.minio_data,
    cloudflare_zero_trust_tunnel_cloudflared_config.bookstack
  ]

  tags = var.tags
}

# Container App Environment Storage for BookStack data
resource "azurerm_container_app_environment_storage" "bookstack_data" {
  name                         = "bookstack-data-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.bookstack_data.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

# Container App Environment Storage for MariaDB data
resource "azurerm_container_app_environment_storage" "mariadb_data" {
  name                         = "mariadb-data-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.mariadb_data.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

# Container App Environment Storage for MinIO data
resource "azurerm_container_app_environment_storage" "minio_data" {
  name                         = "minio-data-storage"
  container_app_environment_id = azurerm_container_app_environment.main.id
  account_name                 = azurerm_storage_account.main.name
  share_name                   = azurerm_storage_share.minio_data.name
  access_key                   = azurerm_storage_account.main.primary_access_key
  access_mode                  = "ReadWrite"
}

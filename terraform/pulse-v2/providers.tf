terraform {
  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.28"
    }
    # Community provider (Resend publishes none). Pinned exactly; v2.0.0 was read before adoption, and its checksums
    # are in the committed .terraform.lock.hcl. Read the diff before bumping it.
    resend = {
      source  = "softwarehuset-com/resend"
      version = "2.0.0"
    }
  }
  required_version = ">= 1.6"
}

provider "cloudflare" {
  # API token is provided via CLOUDFLARE_API_TOKEN environment variable
  # This is set automatically by the tf.py wrapper script
}

provider "resend" {
  # Full-access key from RESEND_API_KEY, which bin/tf loads from Key Vault (tf-resend-api-key)
}
